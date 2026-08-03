from __future__ import annotations

import httpx
import pytest

from containerlab_mcp import server
from containerlab_mcp.client import ContainerlabApiError, ContainerlabClient
from containerlab_mcp.config import Settings, get_settings
from containerlab_mcp.safety import (
    validate_netem,
    validate_relative_path,
    validate_topology,
    validate_vxlan,
)


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


def test_relative_paths_reject_traversal_and_absolute_paths() -> None:
    with pytest.raises(ValueError, match="inside the lab directory"):
        validate_relative_path("../etc/passwd")
    with pytest.raises(ValueError, match="inside the lab directory"):
        validate_relative_path("/etc/passwd")


def test_safe_topology_rejects_privileged_capabilities() -> None:
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
        validate_topology(topology)


def test_safe_topology_rejects_unknown_link_nodes() -> None:
    topology = {
        "name": "broken",
        "topology": {
            "nodes": {"node1": {"kind": "linux", "image": "alpine:3"}},
            "links": [{"endpoints": ["node1:eth1", "missing:eth1"]}],
        },
    }

    with pytest.raises(ValueError, match="unknown node"):
        validate_topology(topology)


def test_network_bounds_are_enforced() -> None:
    with pytest.raises(ValueError, match="vni"):
        validate_vxlan(
            link="vx-test",
            remote="192.0.2.1",
            vni=0,
            port=4789,
            mtu=1500,
            dev="eth0",
        )
    with pytest.raises(ValueError, match="loss"):
        validate_netem(
            interface="eth1",
            delay="10ms",
            jitter=None,
            loss=101,
            rate=0,
            corruption=0,
        )


def test_direct_writes_are_blocked_in_safe_mode(monkeypatch, tmp_path) -> None:
    configured = settings(tmp_path)
    monkeypatch.setattr(server, "get_settings", lambda: configured)

    with pytest.raises(RuntimeError, match="create_change_plan"):
        server.destroy_lab("demo")


def test_configuration_defaults_to_tls_and_safe_mode(monkeypatch) -> None:
    monkeypatch.setenv("CLAB_API_URL", "https://example.test")
    monkeypatch.setenv("CLAB_USERNAME", "operator")
    monkeypatch.setenv("CLAB_PASSWORD", "secret")
    monkeypatch.delenv("CLAB_VERIFY_TLS", raising=False)
    monkeypatch.delenv("CLAB_SAFE_MODE", raising=False)

    configured = get_settings()

    assert configured.verify_tls is True
    assert configured.safe_mode is True


def test_configuration_rejects_plain_http(monkeypatch) -> None:
    monkeypatch.setenv("CLAB_API_URL", "http://example.test")
    monkeypatch.setenv("CLAB_USERNAME", "operator")
    monkeypatch.setenv("CLAB_PASSWORD", "secret")

    with pytest.raises(RuntimeError, match="must use HTTPS"):
        get_settings()


def test_post_is_not_retried_after_unauthorized_response(tmp_path) -> None:
    target_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal target_calls
        if request.url.path == "/login":
            return httpx.Response(200, json={"token": "test-token"})
        target_calls += 1
        return httpx.Response(401, json={"error": "expired"})

    ContainerlabClient._token_cache.clear()
    client = ContainerlabClient(settings(tmp_path))
    client._client.close()
    client._client = httpx.Client(
        base_url="https://example.test",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(ContainerlabApiError, match="HTTP 401"):
        client.request("POST", "/api/v1/labs/demo/stop")

    assert target_calls == 1
    client.close()


def test_get_reauthenticates_once_after_unauthorized_response(tmp_path) -> None:
    target_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal target_calls
        if request.url.path == "/login":
            return httpx.Response(200, json={"token": f"token-{target_calls}"})
        target_calls += 1
        if target_calls == 1:
            return httpx.Response(401, json={"error": "expired"})
        return httpx.Response(200, json={"ok": True})

    ContainerlabClient._token_cache.clear()
    client = ContainerlabClient(settings(tmp_path))
    client._client.close()
    client._client = httpx.Client(
        base_url="https://example.test",
        transport=httpx.MockTransport(handler),
    )

    assert client.request("GET", "/api/v1/labs") == {"ok": True}
    assert target_calls == 2
    client.close()


def test_error_details_are_redacted_and_bounded() -> None:
    request = httpx.Request("GET", "https://example.test/fail")
    response = httpx.Response(
        500,
        request=request,
        json={"error": "password=bad token=abc authorization=Bearer-xyz"},
    )

    with pytest.raises(ContainerlabApiError) as exc_info:
        ContainerlabClient._raise_for_status(response)

    message = str(exc_info.value)
    assert "bad" not in message
    assert "abc" not in message
    assert "Bearer-xyz" not in message
    assert message.count("[REDACTED]") == 3


def test_oversized_responses_are_rejected() -> None:
    response = httpx.Response(200, content=b"x" * 101)

    with pytest.raises(ContainerlabApiError, match="exceeded"):
        ContainerlabClient._decode_response(response, max_bytes=100)
