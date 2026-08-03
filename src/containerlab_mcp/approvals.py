from __future__ import annotations

import inspect
import json
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .audit import AuditLogger
from .client import ContainerlabClient
from .config import Settings
from .safety import (
    validate_command,
    validate_content,
    validate_identifier,
    validate_idempotency_key,
    validate_image_reference,
    validate_netem,
    validate_relative_path,
    validate_topology,
    validate_vxlan,
)


@dataclass(frozen=True)
class ActionSpec:
    risk: str
    raw_command: bool = False
    shell_capable: bool = False


ACTION_SPECS: dict[str, ActionSpec] = {
    "create_terminal_session": ActionSpec("high", shell_capable=True),
    "create_vxlan": ActionSpec("high"),
    "create_wireshark_capture_sessions": ActionSpec("medium"),
    "delete_custom_node_template": ActionSpec("medium"),
    "delete_image": ActionSpec("high"),
    "delete_topology_file": ActionSpec("high"),
    "delete_vxlan": ActionSpec("high"),
    "deploy_on_disk_lab": ActionSpec("high"),
    "deploy_topology_content": ActionSpec("high"),
    "destroy_lab": ActionSpec("critical"),
    "execute_lab_command": ActionSpec("critical", raw_command=True),
    "execute_node_command": ActionSpec("critical", raw_command=True),
    "install_edgeshark": ActionSpec("high"),
    "pause_node": ActionSpec("medium"),
    "pull_image": ActionSpec("medium"),
    "put_topology_file": ActionSpec("high"),
    "rename_topology_file": ActionSpec("high"),
    "replace_custom_node_templates": ActionSpec("medium"),
    "request_ssh_access": ActionSpec("high"),
    "reset_link_impairment": ActionSpec("medium"),
    "restart_node": ActionSpec("medium"),
    "save_custom_node_template": ActionSpec("medium"),
    "save_lab_config": ActionSpec("medium"),
    "set_default_custom_node_template": ActionSpec("medium"),
    "set_link_impairment": ActionSpec("medium"),
    "start_lab": ActionSpec("medium"),
    "start_node": ActionSpec("medium"),
    "stop_lab": ActionSpec("medium"),
    "stop_node": ActionSpec("medium"),
    "terminate_all_capture_sessions": ActionSpec("medium"),
    "terminate_capture_session": ActionSpec("medium"),
    "terminate_ssh_session": ActionSpec("medium"),
    "terminate_terminal_session": ActionSpec("medium"),
    "uninstall_edgeshark": ActionSpec("high"),
    "unpause_node": ActionSpec("medium"),
    "update_topology_annotations": ActionSpec("high"),
    "update_topology_yaml": ActionSpec("high"),
}


class ApprovalStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.path = Path(settings.approval_db).expanduser()
        self.audit = AuditLogger(settings.audit_log, settings.username)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()
        os.chmod(self.path, 0o600)

    def create_plan(self, action: str, arguments: dict[str, Any], reason: str) -> dict[str, Any]:
        spec = _get_spec(action)
        normalized = validate_action_arguments(action, arguments, self.settings)
        plan_id = f"plan-{uuid.uuid4()}"
        now = time.time()
        expires_at = now + self.settings.approval_ttl
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO plans VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    plan_id,
                    self.settings.username,
                    action,
                    json.dumps(normalized, separators=(",", ":")),
                    reason.strip(),
                    spec.risk,
                    "planned",
                    now,
                    expires_at,
                ),
            )
        self.audit.write(
            {
                "correlation_id": plan_id,
                "tool_name": "create_change_plan",
                "action_risk": spec.risk,
                "target_resource": action,
                "authorization_decision": "approval_required",
                "outcome": "planned",
            }
        )
        return {
            "plan_id": plan_id,
            "action": action,
            "arguments": normalized,
            "reason": reason.strip(),
            "risk": spec.risk,
            "approval_required": True,
            "expires_at_epoch": expires_at,
        }

    def approve(self, plan_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            plan = self._get_plan(connection, plan_id)
            self._assert_live(plan)
            self._assert_owner(plan)
            if plan[6] != "planned":
                raise ValueError(f"plan is already {plan[6]}")
            approval_id = f"approval-{uuid.uuid4()}"
            now = time.time()
            connection.execute(
                "INSERT INTO approvals VALUES (?, ?, ?, ?)",
                (approval_id, plan_id, self.settings.username, now),
            )
            connection.execute(
                "UPDATE plans SET status = 'approved' WHERE plan_id = ?",
                (plan_id,),
            )
        self.audit.write(
            {
                "correlation_id": plan_id,
                "tool_name": "approve_change",
                "target_resource": str(plan[2]),
                "approval_id": approval_id,
                "authorization_decision": "approved",
                "outcome": "success",
            }
        )
        return {
            "plan_id": plan_id,
            "approval_id": approval_id,
            "approved_by": self.settings.username,
            "approved_at_epoch": now,
        }

    def execute(
        self,
        plan_id: str,
        approval_id: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        validate_idempotency_key(idempotency_key)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT result_json, outcome FROM executions WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            if existing:
                if existing[1] == "in_progress":
                    raise ValueError("an execution with this idempotency key is in progress")
                return {
                    "idempotent_replay": True,
                    "outcome": existing[1],
                    "result": json.loads(existing[0]) if existing[0] else None,
                }
            plan = self._get_plan(connection, plan_id)
            self._assert_live(plan)
            self._assert_owner(plan)
            approval = connection.execute(
                "SELECT approval_id FROM approvals WHERE approval_id = ? AND plan_id = ?",
                (approval_id, plan_id),
            ).fetchone()
            if not approval or plan[6] != "approved":
                raise ValueError("approval does not authorize this plan")
            connection.execute(
                "INSERT INTO executions VALUES (?, ?, ?, ?, ?, ?)",
                (
                    idempotency_key,
                    plan_id,
                    approval_id,
                    "in_progress",
                    None,
                    time.time(),
                ),
            )

        action = str(plan[2])
        arguments = validate_action_arguments(
            action,
            json.loads(plan[3]),
            self.settings,
        )
        client = ContainerlabClient(self.settings)
        try:
            method = getattr(client, action)
            result = method(**arguments)
            outcome = "succeeded"
        except Exception as exc:
            result = {"error": str(exc)[:4096]}
            outcome = "failed"
            self._record_execution(
                plan_id,
                approval_id,
                idempotency_key,
                outcome,
                result,
            )
            self.audit.write(
                {
                    "correlation_id": plan_id,
                    "tool_name": "execute_approved_change",
                    "target_resource": action,
                    "approval_id": approval_id,
                    "idempotency_key": idempotency_key,
                    "outcome": outcome,
                    "error_code": type(exc).__name__,
                }
            )
            raise
        finally:
            client.close()

        self._record_execution(
            plan_id,
            approval_id,
            idempotency_key,
            outcome,
            result,
        )
        self.audit.write(
            {
                "correlation_id": plan_id,
                "tool_name": "execute_approved_change",
                "target_resource": action,
                "approval_id": approval_id,
                "idempotency_key": idempotency_key,
                "outcome": outcome,
            }
        )
        return {
            "idempotent_replay": False,
            "plan_id": plan_id,
            "approval_id": approval_id,
            "action": action,
            "outcome": outcome,
            "result": result,
        }

    def _record_execution(
        self,
        plan_id: str,
        approval_id: str,
        idempotency_key: str,
        outcome: str,
        result: Any,
    ) -> None:
        encoded = json.dumps(result, separators=(",", ":"), default=str)
        if len(encoded) > self.settings.max_response_bytes:
            encoded = json.dumps({"truncated": True, "size": len(encoded)})
        with self._connect() as connection:
            connection.execute(
                "UPDATE executions SET outcome = ?, result_json = ?, executed_at = ? "
                "WHERE idempotency_key = ?",
                (outcome, encoded, time.time(), idempotency_key),
            )
            connection.execute(
                "UPDATE plans SET status = ? WHERE plan_id = ?",
                ("executed" if outcome == "succeeded" else "failed", plan_id),
            )

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS plans (
                    plan_id TEXT PRIMARY KEY,
                    principal TEXT NOT NULL,
                    action TEXT NOT NULL,
                    arguments_json TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    risk TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS approvals (
                    approval_id TEXT PRIMARY KEY,
                    plan_id TEXT NOT NULL,
                    principal TEXT NOT NULL,
                    approved_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS executions (
                    idempotency_key TEXT PRIMARY KEY,
                    plan_id TEXT NOT NULL,
                    approval_id TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    result_json TEXT,
                    executed_at REAL NOT NULL
                );
                """
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    @staticmethod
    def _get_plan(connection: sqlite3.Connection, plan_id: str) -> sqlite3.Row:
        plan = connection.execute(
            "SELECT * FROM plans WHERE plan_id = ?",
            (plan_id,),
        ).fetchone()
        if not plan:
            raise ValueError("plan was not found")
        return plan

    @staticmethod
    def _assert_live(plan: sqlite3.Row) -> None:
        if float(plan[8]) < time.time():
            raise ValueError("plan has expired")

    def _assert_owner(self, plan: sqlite3.Row) -> None:
        if plan[1] != self.settings.username:
            raise ValueError("plan belongs to a different API principal")


def validate_action_arguments(
    action: str,
    arguments: dict[str, Any],
    settings: Settings,
) -> dict[str, Any]:
    spec = _get_spec(action)
    if not isinstance(arguments, dict):
        raise ValueError("arguments must be an object")
    signature = inspect.signature(getattr(ContainerlabClient, action))
    allowed = {name for name in signature.parameters if name != "self"}
    required = {
        name
        for name, parameter in signature.parameters.items()
        if name != "self"
        and parameter.default is inspect.Parameter.empty
        and parameter.kind not in {inspect.Parameter.VAR_KEYWORD, inspect.Parameter.VAR_POSITIONAL}
    }
    unknown = set(arguments) - allowed
    missing = required - set(arguments)
    if unknown:
        raise ValueError(f"unsupported arguments for {action}: {sorted(unknown)}")
    if missing:
        raise ValueError(f"missing arguments for {action}: {sorted(missing)}")

    bound = signature.bind(None, **arguments)
    bound.apply_defaults()
    normalized = {
        name: value
        for name, value in bound.arguments.items()
        if name != "self"
    }
    encoded_arguments = json.dumps(
        normalized,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    if len(encoded_arguments) > settings.max_response_bytes:
        raise ValueError("change arguments exceed the configured safety limit")

    for field in (
        "lab_name",
        "lab_name_override",
        "node_name",
        "node_filter",
        "interface",
    ):
        value = normalized.get(field)
        if value is not None:
            validate_identifier(str(value), field)
    for field in ("path", "old_path", "new_path", "topology_path"):
        value = normalized.get(field)
        if value is not None:
            validate_relative_path(str(value), field)
    for field in ("content",):
        value = normalized.get(field)
        if value is not None:
            validate_content(str(value), field, settings.max_response_bytes)
    if "image" in normalized:
        validate_image_reference(str(normalized["image"]))
    if "reference" in normalized:
        validate_image_reference(str(normalized["reference"]))
    if "topology" in normalized:
        validate_topology(normalized["topology"])
    if action == "update_topology_yaml":
        document = yaml.safe_load(str(normalized["content"]))
        if not isinstance(document, dict):
            raise ValueError("topology YAML must contain an object")
        validate_topology(document)
    if action == "update_topology_annotations":
        try:
            annotations = json.loads(str(normalized["content"]))
        except json.JSONDecodeError as exc:
            raise ValueError("topology annotations must be valid JSON") from exc
        if not isinstance(annotations, (dict, list)):
            raise ValueError("topology annotations must contain an object or list")
    if spec.raw_command:
        if not settings.allow_raw_commands:
            raise ValueError("raw command execution is disabled by CLAB_ALLOW_RAW_COMMANDS")
        validate_command(str(normalized.get("command", "")))
    if (
        spec.shell_capable
        and normalized.get("protocol") == "shell"
        and not settings.allow_shell_terminal
    ):
        raise ValueError("shell terminal sessions are disabled by CLAB_ALLOW_SHELL_TERMINAL")
    if action == "create_vxlan":
        validate_vxlan(**normalized)
    if action == "set_link_impairment":
        validate_netem(
            interface=str(normalized["interface"]),
            delay=normalized.get("delay"),
            jitter=normalized.get("jitter"),
            loss=float(normalized.get("loss", 0.0)),
            rate=int(normalized.get("rate", 0)),
            corruption=float(normalized.get("corruption", 0.0)),
        )
    if action == "create_terminal_session" and normalized.get("protocol") not in {
        "ssh",
        "shell",
        "telnet",
    }:
        raise ValueError("protocol must be ssh, shell, or telnet")
    if action == "delete_vxlan":
        validate_identifier(str(normalized["prefix"]), "prefix")
    if action in {"terminate_ssh_session"} and not 1 <= int(normalized["port"]) <= 65535:
        raise ValueError("port must be between 1 and 65535")
    return normalized


def _get_spec(action: str) -> ActionSpec:
    try:
        return ACTION_SPECS[action]
    except KeyError as exc:
        raise ValueError(f"unsupported change action {action!r}") from exc
