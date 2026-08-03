from __future__ import annotations

import json as json_module
import re
import threading
import time
from typing import Any
from urllib.parse import quote
from uuid import uuid4

import httpx

from .audit import AuditLogger
from .config import Settings
from .safety import (
    validate_content,
    validate_identifier,
    validate_image_reference,
    validate_netem,
    validate_relative_path,
    validate_topology,
    validate_vxlan,
)


class ContainerlabApiError(RuntimeError):
    """Raised when the Containerlab API returns an error response."""


class ContainerlabClient:
    _token_cache: dict[tuple[str, str], tuple[str, float]] = {}
    _token_lock = threading.Lock()

    def __init__(self, settings: Settings):
        self.settings = settings
        self._token: str | None = None
        self._token_time = 0.0
        self._client = httpx.Client(
            base_url=settings.api_url,
            verify=settings.verify_tls,
            timeout=settings.timeout,
        )
        self._audit = AuditLogger(settings.audit_log, settings.username)

    def close(self) -> None:
        self._client.close()

    def login(self, force: bool = False) -> str:
        cache_key = (self.settings.api_url, self.settings.username)
        if not force:
            with self._token_lock:
                cached = self._token_cache.get(cache_key)
            if cached and time.time() - cached[1] < 3600:
                self._token, self._token_time = cached
                return cached[0]

        response = self._client.post(
            "/login",
            json={
                "username": self.settings.username,
                "password": self.settings.password,
            },
        )
        self._raise_for_status(response)
        token = response.json()["token"]
        self._token = token
        self._token_time = time.time()
        with self._token_lock:
            self._token_cache[cache_key] = (token, self._token_time)
        return token

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
        content: str | bytes | None = None,
        headers: dict[str, str] | None = None,
        retry_auth: bool = True,
        idempotency_key: str | None = None,
    ) -> Any:
        correlation_id = str(uuid4())
        token = self.login()
        request_headers = {
            **(headers or {}),
            "Authorization": f"Bearer {token}",
            "X-Correlation-ID": correlation_id,
        }
        if idempotency_key:
            request_headers["X-Idempotency-Key"] = idempotency_key
        started = time.monotonic()
        retry_allowed = method.upper() in {"GET", "HEAD", "OPTIONS"} or bool(
            idempotency_key
        )
        try:
            response = self._client.request(
                method,
                path,
                params=params,
                json=json,
                content=content,
                headers=request_headers,
            )
            if response.status_code == 401 and retry_auth and retry_allowed:
                token = self.login(force=True)
                request_headers["Authorization"] = f"Bearer {token}"
                response = self._client.request(
                    method,
                    path,
                    params=params,
                    json=json,
                    content=content,
                    headers=request_headers,
                )

            self._raise_for_status(response)
            result = self._decode_response(
                response,
                max_bytes=self.settings.max_response_bytes,
            )
        except Exception as exc:
            self._audit.write(
                {
                    "correlation_id": correlation_id,
                    "downstream_system": "clab-api-server",
                    "method": method.upper(),
                    "path": path,
                    "outcome": "error",
                    "error_code": type(exc).__name__,
                    "latency_ms": round((time.monotonic() - started) * 1000, 3),
                }
            )
            raise

        self._audit.write(
            {
                "correlation_id": correlation_id,
                "downstream_system": "clab-api-server",
                "method": method.upper(),
                "path": path,
                "outcome": "success",
                "status_code": response.status_code,
                "latency_ms": round((time.monotonic() - started) * 1000, 3),
                "response_size": len(response.content),
            }
        )
        return result

    def get_root(self) -> Any:
        response = self._client.get("/")
        self._raise_for_status(response)
        return self._decode_response(response)

    def health(self) -> Any:
        return self.request("GET", "/health")

    def health_metrics(self) -> Any:
        return self.request("GET", "/api/v1/health/metrics")

    def version(self) -> Any:
        return self.request("GET", "/api/v1/version")

    def version_check(self) -> Any:
        return self.request("GET", "/api/v1/version/check")

    def list_labs(self) -> Any:
        return self.request("GET", "/api/v1/labs")

    def inspect_lab(self, lab_name: str) -> list[dict[str, Any]]:
        return self.request("GET", f"/api/v1/labs/{self._segment(lab_name, 'lab_name')}")

    def list_lab_interfaces(
        self,
        lab_name: str,
        node_name: str | None = None,
    ) -> Any:
        params = {"node": node_name} if node_name else None
        return self.request(
            "GET",
            f"/api/v1/labs/{self._segment(lab_name, 'lab_name')}/interfaces",
            params=params,
        )

    def get_topology_yaml(self, lab_name: str) -> str:
        lab = self._segment(lab_name, "lab_name")
        return self.request("GET", f"/api/v1/labs/{lab}/topology/yaml")

    def get_node_logs(self, lab_name: str, node_name: str) -> Any:
        container_name = self.resolve_container_name(lab_name, node_name)
        return self.request(
            "GET",
            f"/api/v1/labs/{self._segment(lab_name, 'lab_name')}/nodes/"
            f"{self._segment(container_name, 'node_name')}/logs",
        )

    def get_node_browser_ports(self, lab_name: str, node_name: str) -> Any:
        container_name = self.resolve_container_name(lab_name, node_name)
        return self.request(
            "GET",
            f"/api/v1/labs/{self._segment(lab_name, 'lab_name')}/nodes/"
            f"{self._segment(container_name, 'node_name')}/browser-ports",
        )

    def execute_lab_command(
        self,
        lab_name: str,
        command: str,
        node_filter: str | None = None,
    ) -> Any:
        params = (
            {
                "nodeFilter": self.resolve_container_name(
                    lab_name,
                    node_filter,
                )
            }
            if node_filter
            else None
        )
        return self.request(
            "POST",
            f"/api/v1/labs/{self._segment(lab_name, 'lab_name')}/exec",
            params=params,
            json={"command": command},
        )

    def execute_node_command(
        self,
        lab_name: str,
        node_name: str,
        command: str,
    ) -> Any:
        return self.execute_lab_command(
            lab_name,
            command,
            node_filter=self.resolve_container_name(lab_name, node_name),
        )

    def validate_node_command(
        self,
        lab_name: str,
        node_name: str,
        command: str,
        expected_text: str | None = None,
    ) -> dict[str, Any]:
        result = self.execute_node_command(lab_name, node_name, command)
        entries = [
            entry
            for node_entries in result.values()
            for entry in node_entries
            if isinstance(entry, dict)
        ] if isinstance(result, dict) else []
        return_codes = [entry.get("return-code") for entry in entries]
        stdout = "\n".join(str(entry.get("stdout", "")) for entry in entries)
        passed = bool(entries) and all(code == 0 for code in return_codes)
        if expected_text is not None:
            passed = passed and expected_text in stdout
        return {
            "passed": passed,
            "expectedText": expected_text,
            "result": result,
        }

    def save_lab_config(
        self,
        lab_name: str,
        node_name: str | None = None,
    ) -> Any:
        params = (
            {"nodeFilter": self.resolve_container_name(lab_name, node_name)}
            if node_name
            else None
        )
        return self.request(
            "POST",
            f"/api/v1/labs/{self._segment(lab_name, 'lab_name')}/save",
            params=params,
        )

    def start_lab(self, lab_name: str, include_logs: bool = True) -> Any:
        return self.request(
            "POST",
            f"/api/v1/labs/{self._segment(lab_name, 'lab_name')}/start",
            params={"includeLogs": include_logs},
        )

    def stop_lab(self, lab_name: str, include_logs: bool = True) -> Any:
        return self.request(
            "POST",
            f"/api/v1/labs/{self._segment(lab_name, 'lab_name')}/stop",
            params={"includeLogs": include_logs},
        )

    def start_node(self, lab_name: str, node_name: str) -> Any:
        return self._node_action(lab_name, node_name, "start")

    def stop_node(self, lab_name: str, node_name: str) -> Any:
        return self._node_action(lab_name, node_name, "stop")

    def restart_node(self, lab_name: str, node_name: str) -> Any:
        return self._node_action(lab_name, node_name, "restart")

    def pause_node(self, lab_name: str, node_name: str) -> Any:
        return self._node_action(lab_name, node_name, "pause")

    def unpause_node(self, lab_name: str, node_name: str) -> Any:
        return self._node_action(lab_name, node_name, "unpause")

    def deploy_on_disk_lab(
        self,
        lab_name: str,
        topology_path: str | None = None,
        reconfigure: bool = False,
        include_logs: bool = True,
    ) -> Any:
        params: dict[str, Any] = {
            "reconfigure": reconfigure,
            "includeLogs": include_logs,
        }
        if topology_path:
            params["path"] = validate_relative_path(topology_path, "topology_path")
        lab = self._segment(lab_name, "lab_name")
        return self.request("POST", f"/api/v1/labs/{lab}/deploy", params=params)

    def deploy_topology_content(
        self,
        topology: dict[str, Any],
        lab_name_override: str | None = None,
        reconfigure: bool = False,
    ) -> Any:
        if self.settings.safe_mode:
            validate_topology(topology)
        params: dict[str, Any] = {"reconfigure": reconfigure}
        if lab_name_override:
            params["labNameOverride"] = validate_identifier(
                lab_name_override,
                "lab_name_override",
            )
        return self.request(
            "POST",
            "/api/v1/labs",
            params=params,
            json={"topologyContent": topology},
        )

    def destroy_lab(
        self,
        lab_name: str,
        cleanup: bool = False,
        graceful: bool = True,
        include_logs: bool = True,
    ) -> Any:
        params = {
            "cleanup": cleanup,
            "graceful": graceful,
            "includeLogs": include_logs,
        }
        lab = self._segment(lab_name, "lab_name")
        return self.request("DELETE", f"/api/v1/labs/{lab}", params=params)

    def list_images(self) -> Any:
        return self.request("GET", "/api/v1/images")

    def pull_image(self, image: str) -> Any:
        image = validate_image_reference(image)
        return self.request(
            "POST",
            "/api/v1/images/pull",
            json={"image": image},
        )

    def delete_image(self, reference: str, force: bool = False) -> Any:
        reference = validate_image_reference(reference)
        return self.request(
            "DELETE",
            "/api/v1/images",
            params={"reference": reference, "force": force},
        )

    def generate_drawio(
        self,
        lab_name: str,
        layout: str | None = None,
        theme: str | None = None,
    ) -> Any:
        payload = {
            key: value
            for key, value in {"layout": layout, "theme": theme}.items()
            if value is not None
        }
        return self.request(
            "POST",
            f"/api/v1/labs/{self._segment(lab_name, 'lab_name')}/graph/drawio",
            json=payload,
        )

    def get_edgeshark_status(self) -> Any:
        return self.request("GET", "/api/v1/tools/edgeshark/status")

    def install_edgeshark(self) -> Any:
        return self.request("POST", "/api/v1/tools/edgeshark/install")

    def uninstall_edgeshark(self) -> Any:
        return self.request("POST", "/api/v1/tools/edgeshark/uninstall")

    def build_packetflix_capture(
        self,
        lab_name: str,
        targets: list[dict[str, str]],
        remote_hostname: str | None = None,
    ) -> Any:
        payload: dict[str, Any] = {
            "targets": self._resolve_capture_targets(lab_name, targets)
        }
        if remote_hostname:
            payload["remoteHostname"] = remote_hostname
        return self.request(
            "POST",
            f"/api/v1/labs/{self._segment(lab_name, 'lab_name')}/capture/packetflix",
            json=payload,
        )

    def create_wireshark_capture_sessions(
        self,
        lab_name: str,
        targets: list[dict[str, str]],
        theme: str | None = None,
    ) -> Any:
        payload: dict[str, Any] = {
            "targets": self._resolve_capture_targets(lab_name, targets)
        }
        if theme:
            payload["theme"] = theme
        return self.request(
            "POST",
            f"/api/v1/labs/{self._segment(lab_name, 'lab_name')}/capture/wireshark-vnc-sessions",
            json=payload,
        )

    def get_capture_session_ready(self, session_id: str) -> Any:
        return self.request(
            "GET",
            f"/api/v1/capture/wireshark-vnc-sessions/{quote(session_id, safe='')}/ready",
        )

    def terminate_capture_session(self, session_id: str) -> Any:
        return self.request(
            "DELETE",
            f"/api/v1/capture/wireshark-vnc-sessions/{quote(session_id, safe='')}",
        )

    def terminate_all_capture_sessions(self) -> Any:
        return self.request(
            "DELETE",
            "/api/v1/capture/wireshark-vnc-sessions",
        )

    def request_ssh_access(
        self,
        lab_name: str,
        node_name: str,
        duration: str | None = None,
        ssh_username: str | None = None,
    ) -> Any:
        container_name = self.resolve_container_name(lab_name, node_name)
        payload = {
            key: value
            for key, value in {
                "duration": duration,
                "sshUsername": ssh_username,
            }.items()
            if value is not None
        }
        return self.request(
            "POST",
            f"/api/v1/labs/{self._segment(lab_name, 'lab_name')}/nodes/"
            f"{self._segment(container_name, 'node_name')}/ssh",
            json=payload,
        )

    def list_ssh_sessions(self, all_sessions: bool = False) -> Any:
        return self.request(
            "GET",
            "/api/v1/ssh/sessions",
            params={"all": all_sessions},
        )

    def terminate_ssh_session(self, port: int) -> Any:
        return self.request("DELETE", f"/api/v1/ssh/sessions/{port}")

    def create_terminal_session(
        self,
        lab_name: str,
        node_name: str,
        protocol: str,
        rows: int = 24,
        cols: int = 80,
        ssh_username: str | None = None,
        telnet_port: int | None = None,
    ) -> Any:
        container_name = self.resolve_container_name(lab_name, node_name)
        payload: dict[str, Any] = {
            "protocol": protocol,
            "rows": rows,
            "cols": cols,
        }
        if ssh_username is not None:
            payload["sshUsername"] = ssh_username
        if telnet_port is not None:
            payload["telnetPort"] = telnet_port
        return self.request(
            "POST",
            f"/api/v1/labs/{self._segment(lab_name, 'lab_name')}/nodes/"
            f"{self._segment(container_name, 'node_name')}/terminal-sessions",
            json=payload,
        )

    def get_terminal_session(self, session_id: str) -> Any:
        return self.request("GET", f"/api/v1/terminal-sessions/{session_id}")

    def terminate_terminal_session(self, session_id: str) -> Any:
        return self.request("DELETE", f"/api/v1/terminal-sessions/{session_id}")

    def create_vxlan(
        self,
        link: str,
        remote: str,
        vni: int = 10,
        port: int = 14789,
        mtu: int | None = None,
        dev: str | None = None,
    ) -> Any:
        validate_vxlan(
            link=link,
            remote=remote,
            vni=vni,
            port=port,
            mtu=mtu,
            dev=dev,
        )
        payload: dict[str, Any] = {
            "link": link,
            "remote": remote,
            "id": vni,
            "port": port,
        }
        if mtu is not None:
            payload["mtu"] = mtu
        if dev is not None:
            payload["dev"] = dev
        return self.request("POST", "/api/v1/tools/vxlan", json=payload)

    def delete_vxlan(self, prefix: str = "vx-") -> Any:
        return self.request(
            "DELETE",
            "/api/v1/tools/vxlan",
            params={"prefix": prefix},
        )

    def set_link_impairment(
        self,
        lab_name: str,
        node_name: str,
        interface: str,
        delay: str | None = None,
        jitter: str | None = None,
        loss: float = 0.0,
        rate: int = 0,
        corruption: float = 0.0,
    ) -> Any:
        validate_netem(
            interface=interface,
            delay=delay,
            jitter=jitter,
            loss=loss,
            rate=rate,
            corruption=corruption,
        )
        payload: dict[str, Any] = {
            "containerName": self.resolve_container_name(lab_name, node_name),
            "interface": interface,
            "loss": loss,
            "rate": rate,
            "corruption": corruption,
        }
        if delay:
            payload["delay"] = delay
        if jitter:
            payload["jitter"] = jitter
        return self.request("POST", "/api/v1/tools/netem/set", json=payload)

    def show_link_impairments(self, lab_name: str, node_name: str) -> Any:
        return self.request(
            "GET",
            "/api/v1/tools/netem/show",
            params={
                "containerName": self.resolve_container_name(lab_name, node_name)
            },
        )

    def reset_link_impairment(
        self,
        lab_name: str,
        node_name: str,
        interface: str,
    ) -> Any:
        return self.request(
            "POST",
            "/api/v1/tools/netem/reset",
            json={
                "containerName": self.resolve_container_name(lab_name, node_name),
                "interface": interface,
            },
        )

    def list_topology_files(self) -> Any:
        return self.request("GET", "/api/v1/labs/topology/files")

    def update_topology_yaml(self, lab_name: str, content: str) -> Any:
        validate_content(content, max_bytes=self.settings.max_response_bytes)
        return self._put_text(
            f"/api/v1/labs/{self._segment(lab_name, 'lab_name')}/topology/yaml",
            content,
        )

    def get_topology_annotations(self, lab_name: str) -> str:
        return self.request(
            "GET",
            f"/api/v1/labs/{self._segment(lab_name, 'lab_name')}/topology/annotations",
        )

    def update_topology_annotations(self, lab_name: str, content: str) -> Any:
        validate_content(content, max_bytes=self.settings.max_response_bytes)
        return self._put_text(
            f"/api/v1/labs/{self._segment(lab_name, 'lab_name')}/topology/annotations",
            content,
        )

    def get_topology_file(self, lab_name: str, path: str) -> str:
        path = validate_relative_path(path)
        return self.request(
            "GET",
            f"/api/v1/labs/{self._segment(lab_name, 'lab_name')}/topology/file",
            params={"path": path},
        )

    def put_topology_file(self, lab_name: str, path: str, content: str) -> Any:
        path = validate_relative_path(path)
        validate_content(content, max_bytes=self.settings.max_response_bytes)
        return self._put_text(
            f"/api/v1/labs/{self._segment(lab_name, 'lab_name')}/topology/file",
            content,
            params={"path": path},
        )

    def delete_topology_file(self, lab_name: str, path: str) -> Any:
        path = validate_relative_path(path)
        return self.request(
            "DELETE",
            f"/api/v1/labs/{self._segment(lab_name, 'lab_name')}/topology/file",
            params={"path": path},
        )

    def rename_topology_file(
        self,
        lab_name: str,
        old_path: str,
        new_path: str,
    ) -> Any:
        old_path = validate_relative_path(old_path, "old_path")
        new_path = validate_relative_path(new_path, "new_path")
        return self.request(
            "POST",
            f"/api/v1/labs/{self._segment(lab_name, 'lab_name')}/topology/file/rename",
            json={"oldPath": old_path, "newPath": new_path},
        )

    def collect_events(
        self,
        duration_seconds: float = 10.0,
        max_events: int = 100,
        initial_state: bool = True,
        interface_stats: bool = False,
        interface_stats_interval: str = "10s",
    ) -> list[dict[str, Any]]:
        if duration_seconds <= 0 or duration_seconds > 60:
            raise ValueError("duration_seconds must be between 0 and 60")
        if max_events < 1 or max_events > 1000:
            raise ValueError("max_events must be between 1 and 1000")

        token = self.login()
        params: dict[str, Any] = {
            "initialState": initial_state,
            "interfaceStats": interface_stats,
        }
        if interface_stats:
            params["interfaceStatsInterval"] = interface_stats_interval

        timeout = httpx.Timeout(
            connect=self.settings.timeout,
            read=duration_seconds,
            write=self.settings.timeout,
            pool=self.settings.timeout,
        )
        deadline = time.monotonic() + duration_seconds
        events: list[dict[str, Any]] = []
        try:
            with self._client.stream(
                "GET",
                "/api/v1/events",
                params=params,
                headers={"Authorization": f"Bearer {token}"},
                timeout=timeout,
            ) as response:
                self._raise_for_status(response)
                for line in response.iter_lines():
                    if time.monotonic() >= deadline or len(events) >= max_events:
                        break
                    if not line.strip():
                        continue
                    try:
                        event = json_module.loads(line)
                    except json_module.JSONDecodeError:
                        continue
                    if isinstance(event, dict) and event:
                        events.append(event)
        except httpx.ReadTimeout:
            pass
        return events

    def generate_clos_topology(
        self,
        name: str,
        tiers: list[dict[str, Any]],
        images: dict[str, str],
        *,
        default_kind: str | None = None,
        deploy: bool = False,
        node_prefix: str | None = None,
        group_prefix: str | None = None,
        management_network: str | None = None,
        ipv4_subnet: str | None = None,
        ipv6_subnet: str | None = None,
        licenses: dict[str, str] | None = None,
        max_workers: int | None = None,
        output_file: str | None = None,
    ) -> Any:
        payload: dict[str, Any] = {
            "name": name,
            "tiers": tiers,
            "images": images,
            "deploy": deploy,
        }
        optional = {
            "defaultKind": default_kind,
            "nodePrefix": node_prefix,
            "groupPrefix": group_prefix,
            "managementNetwork": management_network,
            "ipv4Subnet": ipv4_subnet,
            "ipv6Subnet": ipv6_subnet,
            "licenses": licenses,
            "maxWorkers": max_workers,
            "outputFile": output_file,
        }
        payload.update({key: value for key, value in optional.items() if value is not None})
        return self.request("POST", "/api/v1/generate", json=payload)

    def list_custom_node_templates(self) -> Any:
        return self.request("GET", "/api/v1/ui/custom-nodes")

    def save_custom_node_template(self, template: dict[str, Any]) -> Any:
        return self.request("POST", "/api/v1/ui/custom-nodes", json=template)

    def replace_custom_node_templates(
        self,
        templates: list[dict[str, Any]],
    ) -> Any:
        return self.request(
            "PUT",
            "/api/v1/ui/custom-nodes",
            json={"customNodes": templates},
        )

    def set_default_custom_node_template(self, name: str) -> Any:
        return self.request(
            "POST",
            "/api/v1/ui/custom-nodes/default",
            json={"name": name},
        )

    def delete_custom_node_template(self, name: str) -> Any:
        return self.request(
            "DELETE",
            f"/api/v1/ui/custom-nodes/{quote(name, safe='')}",
        )

    def _put_text(
        self,
        path: str,
        content: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        return self.request(
            "PUT",
            path,
            params=params,
            content=content,
            headers={"Content-Type": "text/plain; charset=utf-8"},
        )

    def _resolve_capture_targets(
        self,
        lab_name: str,
        targets: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        resolved = []
        for target in targets:
            node_name = target.get("nodeName") or target.get("containerName")
            interface_name = target.get("interfaceName")
            if not node_name or not interface_name:
                raise ValueError(
                    "Each capture target requires nodeName (or containerName) "
                    "and interfaceName"
                )
            resolved.append(
                {
                    "containerName": self.resolve_container_name(
                        lab_name,
                        node_name,
                    ),
                    "interfaceName": interface_name,
                }
            )
        if not resolved:
            raise ValueError("At least one capture target is required")
        return resolved

    def _node_action(self, lab_name: str, node_name: str, action: str) -> Any:
        container_name = self.resolve_container_name(lab_name, node_name)
        return self.request(
            "POST",
            f"/api/v1/labs/{self._segment(lab_name, 'lab_name')}/nodes/"
            f"{self._segment(container_name, 'node_name')}/{action}",
        )

    def resolve_container_name(self, lab_name: str, node_name: str) -> str:
        validate_identifier(lab_name, "lab_name")
        validate_identifier(node_name, "node_name")
        if node_name.startswith("clab-"):
            return node_name

        nodes = self.inspect_lab(lab_name)
        for node in nodes:
            if node.get("nodeName") == node_name or node.get("name") == node_name:
                return str(node["name"])

        known = ", ".join(
            sorted(
                str(node.get("nodeName") or node.get("name"))
                for node in nodes
                if node.get("nodeName") or node.get("name")
            )
        )
        raise ContainerlabApiError(
            f"Node {node_name!r} was not found in lab {lab_name!r}. Known nodes: {known}"
        )

    @staticmethod
    def _segment(value: str, field: str) -> str:
        return quote(validate_identifier(value, field), safe="")

    @staticmethod
    def _decode_response(
        response: httpx.Response,
        max_bytes: int = 1_000_000,
    ) -> Any:
        if len(response.content) > max_bytes:
            raise ContainerlabApiError(
                f"Containerlab API response exceeded {max_bytes} bytes"
            )
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.json()
        return response.text

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        if response.status_code < 400:
            return
        try:
            detail = response.json().get("error", response.text)
        except Exception:
            detail = response.text
        detail = ContainerlabClient._redact(str(detail))[:4096]
        raise ContainerlabApiError(
            f"Containerlab API {response.request.method} {response.request.url} "
            f"returned HTTP {response.status_code}: {detail}"
        )

    @staticmethod
    def _redact(value: str) -> str:
        patterns = (
            r"(?i)(authorization\s*[:=]\s*)([^\s,;]+)",
            r"(?i)((?:password|token|secret)\s*[:=]\s*)([^\s,;]+)",
            r"(?i)(bearer\s+)([A-Za-z0-9._~+/-]+=*)",
        )
        for pattern in patterns:
            value = re.sub(pattern, r"\1[REDACTED]", value)
        return value
