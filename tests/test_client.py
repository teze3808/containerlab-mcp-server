from unittest.mock import Mock, call

import httpx

from containerlab_mcp.client import ContainerlabClient
from containerlab_mcp.config import Settings


def make_client() -> ContainerlabClient:
    return ContainerlabClient(
        Settings(api_url="https://example.test", username="u", password="p")
    )


def test_resolve_container_name_accepts_full_container_name() -> None:
    client = make_client()

    assert client.resolve_container_name("lab", "clab-lab-cx1") == "clab-lab-cx1"
    client.close()


def test_resolve_container_name_accepts_short_node_name() -> None:
    client = make_client()
    client.inspect_lab = Mock(
        return_value=[
            {"nodeName": "cx1", "name": "clab-lab-cx1"},
            {"nodeName": "cx2", "name": "clab-lab-cx2"},
        ]
    )

    assert client.resolve_container_name("lab", "cx1") == "clab-lab-cx1"
    client.close()


def test_decode_response_returns_text_for_yaml() -> None:
    response = httpx.Response(
        200,
        headers={"content-type": "text/plain"},
        text="name: demo\n",
    )

    assert ContainerlabClient._decode_response(response) == "name: demo\n"


def test_node_and_interface_requests() -> None:
    client = make_client()
    client.request = Mock(return_value={"success": True})

    client.version_check()
    client.list_lab_interfaces("lab", node_name="cx1")
    client.get_node_browser_ports("lab", "clab-lab-cx1")
    client.start_node("lab", "clab-lab-cx1")
    client.stop_node("lab", "clab-lab-cx1")
    client.restart_node("lab", "clab-lab-cx1")
    client.pause_node("lab", "clab-lab-cx1")
    client.unpause_node("lab", "clab-lab-cx1")

    assert client.request.call_args_list == [
        call("GET", "/api/v1/version/check"),
        call("GET", "/api/v1/labs/lab/interfaces", params={"node": "cx1"}),
        call(
            "GET",
            "/api/v1/labs/lab/nodes/clab-lab-cx1/browser-ports",
        ),
        call("POST", "/api/v1/labs/lab/nodes/clab-lab-cx1/start"),
        call("POST", "/api/v1/labs/lab/nodes/clab-lab-cx1/stop"),
        call("POST", "/api/v1/labs/lab/nodes/clab-lab-cx1/restart"),
        call("POST", "/api/v1/labs/lab/nodes/clab-lab-cx1/pause"),
        call("POST", "/api/v1/labs/lab/nodes/clab-lab-cx1/unpause"),
    ]
    client.close()


def test_image_and_drawio_requests() -> None:
    client = make_client()
    client.request = Mock(return_value={"success": True})

    client.list_images()
    client.pull_image("ghcr.io/example/router:1")
    client.delete_image("ghcr.io/example/router:1", force=True)
    client.generate_drawio("lab", layout="horizontal", theme="nokia_modern")

    assert client.request.call_args_list == [
        call("GET", "/api/v1/images"),
        call(
            "POST",
            "/api/v1/images/pull",
            json={"image": "ghcr.io/example/router:1"},
        ),
        call(
            "DELETE",
            "/api/v1/images",
            params={
                "reference": "ghcr.io/example/router:1",
                "force": True,
            },
        ),
        call(
            "POST",
            "/api/v1/labs/lab/graph/drawio",
            json={"layout": "horizontal", "theme": "nokia_modern"},
        ),
    ]
    client.close()


def test_remote_access_requests() -> None:
    client = make_client()
    client.request = Mock(return_value={"success": True})

    client.request_ssh_access(
        "lab",
        "clab-lab-cx1",
        duration="30m",
        ssh_username="admin",
    )
    client.list_ssh_sessions(all_sessions=True)
    client.terminate_ssh_session(22001)
    client.create_terminal_session(
        "lab",
        "clab-lab-cx1",
        protocol="ssh",
        rows=40,
        cols=120,
        ssh_username="admin",
    )
    client.get_terminal_session("session-1")
    client.terminate_terminal_session("session-1")

    assert client.request.call_args_list == [
        call(
            "POST",
            "/api/v1/labs/lab/nodes/clab-lab-cx1/ssh",
            json={"duration": "30m", "sshUsername": "admin"},
        ),
        call("GET", "/api/v1/ssh/sessions", params={"all": True}),
        call("DELETE", "/api/v1/ssh/sessions/22001"),
        call(
            "POST",
            "/api/v1/labs/lab/nodes/clab-lab-cx1/terminal-sessions",
            json={
                "protocol": "ssh",
                "rows": 40,
                "cols": 120,
                "sshUsername": "admin",
            },
        ),
        call("GET", "/api/v1/terminal-sessions/session-1"),
        call("DELETE", "/api/v1/terminal-sessions/session-1"),
    ]
    client.close()


def test_vxlan_requests() -> None:
    client = make_client()
    client.request = Mock(return_value={"success": True})

    client.create_vxlan(
        link="cx1-eth1",
        remote="192.0.2.20",
        vni=100,
        port=4789,
        mtu=1400,
        dev="eth0",
    )
    client.delete_vxlan(prefix="vx-lab-")

    assert client.request.call_args_list == [
        call(
            "POST",
            "/api/v1/tools/vxlan",
            json={
                "link": "cx1-eth1",
                "remote": "192.0.2.20",
                "id": 100,
                "port": 4789,
                "mtu": 1400,
                "dev": "eth0",
            },
        ),
        call(
            "DELETE",
            "/api/v1/tools/vxlan",
            params={"prefix": "vx-lab-"},
        ),
    ]
    client.close()
