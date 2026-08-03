from __future__ import annotations

import json
import os
import sqlite3

import pytest

from containerlab_mcp.approvals import ApprovalStore
from containerlab_mcp.client import ContainerlabClient
from containerlab_mcp.config import Settings


def settings(tmp_path, **overrides) -> Settings:
    values = {
        "api_url": "https://example.test",
        "username": "operator",
        "password": "secret",
        "audit_log": str(tmp_path / "audit.jsonl"),
        "approval_db": str(tmp_path / "approvals.sqlite3"),
    }
    values.update(overrides)
    return Settings(**values)


def test_plan_approve_execute_and_idempotent_replay(monkeypatch, tmp_path) -> None:
    configured = settings(tmp_path)
    store = ApprovalStore(configured)
    calls = []

    def fake_stop_lab(self, lab_name: str, include_logs: bool = True):
        calls.append((lab_name, include_logs))
        return {"message": "stopped", "lab": lab_name}

    monkeypatch.setattr(ContainerlabClient, "stop_lab", fake_stop_lab)
    plan = store.create_plan(
        "stop_lab",
        {"lab_name": "demo"},
        "Maintenance test",
    )
    approval = store.approve(plan["plan_id"])
    result = store.execute(
        plan["plan_id"],
        approval["approval_id"],
        "stop-demo-001",
    )
    replay = store.execute(
        plan["plan_id"],
        approval["approval_id"],
        "stop-demo-001",
    )

    assert result["outcome"] == "succeeded"
    assert replay["idempotent_replay"] is True
    assert replay["result"] == {"message": "stopped", "lab": "demo"}
    assert calls == [("demo", True)]


def test_raw_command_plan_requires_explicit_capability(tmp_path) -> None:
    store = ApprovalStore(settings(tmp_path))

    with pytest.raises(ValueError, match="CLAB_ALLOW_RAW_COMMANDS"):
        store.create_plan(
            "execute_node_command",
            {"lab_name": "demo", "node_name": "node1", "command": "id"},
            "Test command",
        )


def test_topology_plan_rejects_host_bind(tmp_path) -> None:
    store = ApprovalStore(settings(tmp_path))
    topology = {
        "name": "unsafe",
        "topology": {
            "nodes": {
                "node1": {
                    "kind": "linux",
                    "image": "alpine:3",
                    "binds": ["/:/host"],
                }
            },
            "links": [],
        },
    }

    with pytest.raises(ValueError, match="disabled in safe mode"):
        store.create_plan(
            "deploy_topology_content",
            {"topology": topology},
            "Unsafe topology",
        )


def test_plan_is_bound_to_api_principal(tmp_path) -> None:
    owner = ApprovalStore(settings(tmp_path, username="owner"))
    plan = owner.create_plan("stop_lab", {"lab_name": "demo"}, "Owner request")
    other = ApprovalStore(settings(tmp_path, username="other"))

    with pytest.raises(ValueError, match="different API principal"):
        other.approve(plan["plan_id"])


def test_approval_database_and_audit_log_are_private(tmp_path) -> None:
    store = ApprovalStore(settings(tmp_path))
    store.create_plan("stop_lab", {"lab_name": "demo"}, "Audit permissions")

    db_mode = os.stat(tmp_path / "approvals.sqlite3").st_mode & 0o777
    audit_mode = os.stat(tmp_path / "audit.jsonl").st_mode & 0o777
    assert db_mode == 0o600
    assert audit_mode == 0o600

    audit = [json.loads(line) for line in (tmp_path / "audit.jsonl").read_text().splitlines()]
    assert audit[-1]["tool_name"] == "create_change_plan"
    assert audit[-1]["authorization_decision"] == "approval_required"


def test_expired_plan_cannot_be_approved(tmp_path) -> None:
    configured = settings(tmp_path)
    store = ApprovalStore(configured)
    plan = store.create_plan("stop_lab", {"lab_name": "demo"}, "Expire test")
    with sqlite3.connect(configured.approval_db) as connection:
        connection.execute(
            "UPDATE plans SET expires_at = 0 WHERE plan_id = ?",
            (plan["plan_id"],),
        )

    with pytest.raises(ValueError, match="expired"):
        store.approve(plan["plan_id"])
