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

    def list_labs(self) -> Any:
        return self.request("GET", "/api/v1/labs")

    def inspect_lab(self, lab_name: str) -> list[dict[str, Any]]:
        return self.request("GET", f"/api/v1/labs/{lab_name}")

    def get_topology_yaml(self, lab_name: str) -> str:
        return self.request("GET", f"/api/v1/labs/{lab_name}/topology/yaml")

    def get_node_logs(self, lab_name: str, node_name: str) -> Any:
        container_name = self.resolve_container_name(lab_name, node_name)
        return self.request(
            "GET",
            f"/api/v1/labs/{lab_name}/nodes/{container_name}/logs",
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
