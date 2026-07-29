from unittest.mock import Mock, call

import httpx
import pytest

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


def test_command_validation_and_save_requests() -> None:
    client = make_client()
    client.request = Mock(
        return_value={
            "cx1": [
                {
                    "return-code": 0,
                    "stdout": "neighbor is Full",
                    "stderr": "",
                }
            ]
        }
    )

    client.resolve_container_name = Mock(return_value="clab-lab-cx1")
    result = client.validate_node_command(
        "lab",
        "clab-lab-cx1",
        "show ospf neighbor",
        expected_text="Full",
    )
    client.save_lab_config("lab", node_name="cx1")

    assert result["passed"] is True
    assert client.request.call_args_list == [
        call(
            "POST",
            "/api/v1/labs/lab/exec",
            params={"nodeFilter": "clab-lab-cx1"},
            json={"command": "show ospf neighbor"},
        ),
        call(
            "POST",
            "/api/v1/labs/lab/save",
            params={"nodeFilter": "clab-lab-cx1"},
        ),
    ]
    client.close()


def test_capture_requests() -> None:
    client = make_client()
    client.request = Mock(return_value={"success": True})
    client.resolve_container_name = Mock(return_value="clab-lab-cx1")
    targets = [{"nodeName": "cx1", "interfaceName": "eth1"}]

    client.get_edgeshark_status()
    client.build_packetflix_capture(
        "lab",
        targets,
        remote_hostname="capture.example.test",
    )
    client.create_wireshark_capture_sessions("lab", targets, theme="dark")
    client.get_capture_session_ready("session/1")
    client.terminate_capture_session("session/1")
    client.terminate_all_capture_sessions()

    assert client.request.call_args_list == [
        call("GET", "/api/v1/tools/edgeshark/status"),
        call(
            "POST",
            "/api/v1/labs/lab/capture/packetflix",
            json={
                "targets": [
                    {
                        "containerName": "clab-lab-cx1",
                        "interfaceName": "eth1",
                    }
                ],
                "remoteHostname": "capture.example.test",
            },
        ),
        call(
            "POST",
            "/api/v1/labs/lab/capture/wireshark-vnc-sessions",
            json={
                "targets": [
                    {
                        "containerName": "clab-lab-cx1",
                        "interfaceName": "eth1",
                    }
                ],
                "theme": "dark",
            },
        ),
        call(
            "GET",
            "/api/v1/capture/wireshark-vnc-sessions/session%2F1/ready",
        ),
        call(
            "DELETE",
            "/api/v1/capture/wireshark-vnc-sessions/session%2F1",
        ),
        call("DELETE", "/api/v1/capture/wireshark-vnc-sessions"),
    ]
    client.close()


def test_netem_requests() -> None:
    client = make_client()
    client.request = Mock(return_value={"success": True})
    client.resolve_container_name = Mock(return_value="clab-lab-cx1")

    client.set_link_impairment(
        "lab",
        "cx1",
        "eth1",
        delay="50ms",
        jitter="5ms",
        loss=1.5,
        rate=1000,
        corruption=0.1,
    )
    client.show_link_impairments("lab", "cx1")
    client.reset_link_impairment("lab", "cx1", "eth1")

    assert client.request.call_args_list == [
        call(
            "POST",
            "/api/v1/tools/netem/set",
            json={
                "containerName": "clab-lab-cx1",
                "interface": "eth1",
                "loss": 1.5,
                "rate": 1000,
                "corruption": 0.1,
                "delay": "50ms",
                "jitter": "5ms",
            },
        ),
        call(
            "GET",
            "/api/v1/tools/netem/show",
            params={"containerName": "clab-lab-cx1"},
        ),
        call(
            "POST",
            "/api/v1/tools/netem/reset",
            json={
                "containerName": "clab-lab-cx1",
                "interface": "eth1",
            },
        ),
    ]
    client.close()


def test_topology_document_and_file_requests() -> None:
    client = make_client()
    client.request = Mock(return_value={"success": True})

    client.list_topology_files()
    client.update_topology_yaml("lab", "name: lab\n")
    client.get_topology_annotations("lab")
    client.update_topology_annotations("lab", "{}\n")
    client.get_topology_file("lab", "configs/cx1.cfg")
    client.put_topology_file("lab", "configs/cx1.cfg", "hostname cx1\n")
    client.rename_topology_file(
        "lab",
        "configs/cx1.cfg",
        "configs/cx1.startup.cfg",
    )
    client.delete_topology_file("lab", "configs/cx1.startup.cfg")

    text_headers = {"Content-Type": "text/plain; charset=utf-8"}
    assert client.request.call_args_list == [
        call("GET", "/api/v1/labs/topology/files"),
        call(
            "PUT",
            "/api/v1/labs/lab/topology/yaml",
            params=None,
            content="name: lab\n",
            headers=text_headers,
        ),
        call("GET", "/api/v1/labs/lab/topology/annotations"),
        call(
            "PUT",
            "/api/v1/labs/lab/topology/annotations",
            params=None,
            content="{}\n",
            headers=text_headers,
        ),
        call(
            "GET",
            "/api/v1/labs/lab/topology/file",
            params={"path": "configs/cx1.cfg"},
        ),
        call(
            "PUT",
            "/api/v1/labs/lab/topology/file",
            params={"path": "configs/cx1.cfg"},
            content="hostname cx1\n",
            headers=text_headers,
        ),
        call(
            "POST",
            "/api/v1/labs/lab/topology/file/rename",
            json={
                "oldPath": "configs/cx1.cfg",
                "newPath": "configs/cx1.startup.cfg",
            },
        ),
        call(
            "DELETE",
            "/api/v1/labs/lab/topology/file",
            params={"path": "configs/cx1.startup.cfg"},
        ),
    ]
    client.close()


def test_clos_and_custom_template_requests() -> None:
    client = make_client()
    client.request = Mock(return_value={"success": True})

    client.generate_clos_topology(
        "clos1",
        [{"count": 2, "kind": "nokia_srlinux"}],
        {"nokia_srlinux": "ghcr.io/nokia/srlinux:latest"},
        default_kind="nokia_srlinux",
        deploy=False,
    )
    client.list_custom_node_templates()
    client.save_custom_node_template({"name": "AOS-CX", "kind": "aruba_aoscx"})
    client.replace_custom_node_templates([{"name": "AOS-CX"}])
    client.set_default_custom_node_template("AOS-CX")
    client.delete_custom_node_template("AOS CX/10.18")

    assert client.request.call_args_list == [
        call(
            "POST",
            "/api/v1/generate",
            json={
                "name": "clos1",
                "tiers": [{"count": 2, "kind": "nokia_srlinux"}],
                "images": {
                    "nokia_srlinux": "ghcr.io/nokia/srlinux:latest"
                },
                "deploy": False,
                "defaultKind": "nokia_srlinux",
            },
        ),
        call("GET", "/api/v1/ui/custom-nodes"),
        call(
            "POST",
            "/api/v1/ui/custom-nodes",
            json={"name": "AOS-CX", "kind": "aruba_aoscx"},
        ),
        call(
            "PUT",
            "/api/v1/ui/custom-nodes",
            json={"customNodes": [{"name": "AOS-CX"}]},
        ),
        call(
            "POST",
            "/api/v1/ui/custom-nodes/default",
            json={"name": "AOS-CX"},
        ),
        call("DELETE", "/api/v1/ui/custom-nodes/AOS%20CX%2F10.18"),
    ]
    client.close()


def test_event_collection_limits() -> None:
    client = make_client()

    with pytest.raises(ValueError, match="duration_seconds"):
        client.collect_events(duration_seconds=61)
    with pytest.raises(ValueError, match="max_events"):
        client.collect_events(max_events=0)

    client.close()
