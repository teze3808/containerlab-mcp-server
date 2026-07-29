from __future__ import annotations

import time
from typing import Any

import httpx

from .config import Settings


class ContainerlabApiError(RuntimeError):
    """Raised when the Containerlab API returns an error response."""


class ContainerlabClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._token: str | None = None
        self._token_time = 0.0
        self._client = httpx.Client(
            base_url=settings.api_url,
            verify=settings.verify_tls,
            timeout=settings.timeout,
        )

    def close(self) -> None:
        self._client.close()

    def login(self, force: bool = False) -> str:
        if self._token and not force and time.time() - self._token_time < 3600:
            return self._token

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
        return token

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
        retry_auth: bool = True,
    ) -> Any:
        token = self.login()
        response = self._client.request(
            method,
            path,
            params=params,
            json=json,
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code == 401 and retry_auth:
            token = self.login(force=True)
            response = self._client.request(
                method,
                path,
                params=params,
                json=json,
                headers={"Authorization": f"Bearer {token}"},
            )

        self._raise_for_status(response)
        return self._decode_response(response)

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
        return self.request("GET", f"/api/v1/labs/{lab_name}")

    def list_lab_interfaces(
        self,
        lab_name: str,
        node_name: str | None = None,
    ) -> Any:
        params = {"node": node_name} if node_name else None
        return self.request(
            "GET",
            f"/api/v1/labs/{lab_name}/interfaces",
            params=params,
        )

    def get_topology_yaml(self, lab_name: str) -> str:
        return self.request("GET", f"/api/v1/labs/{lab_name}/topology/yaml")

    def get_node_logs(self, lab_name: str, node_name: str) -> Any:
        container_name = self.resolve_container_name(lab_name, node_name)
        return self.request(
            "GET",
            f"/api/v1/labs/{lab_name}/nodes/{container_name}/logs",
        )

    def get_node_browser_ports(self, lab_name: str, node_name: str) -> Any:
        container_name = self.resolve_container_name(lab_name, node_name)
        return self.request(
            "GET",
            f"/api/v1/labs/{lab_name}/nodes/{container_name}/browser-ports",
        )

    def start_lab(self, lab_name: str, include_logs: bool = True) -> Any:
        return self.request(
            "POST",
            f"/api/v1/labs/{lab_name}/start",
            params={"includeLogs": include_logs},
        )

    def stop_lab(self, lab_name: str, include_logs: bool = True) -> Any:
        return self.request(
            "POST",
            f"/api/v1/labs/{lab_name}/stop",
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
            params["path"] = topology_path
        return self.request("POST", f"/api/v1/labs/{lab_name}/deploy", params=params)

    def deploy_topology_content(
        self,
        topology: dict[str, Any],
        lab_name_override: str | None = None,
        reconfigure: bool = False,
    ) -> Any:
        params: dict[str, Any] = {"reconfigure": reconfigure}
        if lab_name_override:
            params["labNameOverride"] = lab_name_override
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
        return self.request("DELETE", f"/api/v1/labs/{lab_name}", params=params)

    def list_images(self) -> Any:
        return self.request("GET", "/api/v1/images")

    def pull_image(self, image: str) -> Any:
        return self.request(
            "POST",
            "/api/v1/images/pull",
            json={"image": image},
        )

    def delete_image(self, reference: str, force: bool = False) -> Any:
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
            f"/api/v1/labs/{lab_name}/graph/drawio",
            json=payload,
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
            f"/api/v1/labs/{lab_name}/nodes/{container_name}/ssh",
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
            f"/api/v1/labs/{lab_name}/nodes/{container_name}/terminal-sessions",
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

    def _node_action(self, lab_name: str, node_name: str, action: str) -> Any:
        container_name = self.resolve_container_name(lab_name, node_name)
        return self.request(
            "POST",
            f"/api/v1/labs/{lab_name}/nodes/{container_name}/{action}",
        )

    def resolve_container_name(self, lab_name: str, node_name: str) -> str:
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
    def _decode_response(response: httpx.Response) -> Any:
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
        raise ContainerlabApiError(
            f"Containerlab API {response.request.method} {response.request.url} "
            f"returned HTTP {response.status_code}: {detail}"
        )
