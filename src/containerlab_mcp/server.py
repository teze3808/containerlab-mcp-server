from __future__ import annotations

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from .client import ContainerlabClient
from .config import get_settings
from .topologies import make_two_switch_aoscx_topology as make_topology

mcp = FastMCP("containerlab")


def get_client() -> ContainerlabClient:
    return ContainerlabClient(get_settings())


@mcp.tool()
def health() -> Any:
    """Return Containerlab API server health."""
    client = get_client()
    try:
        return client.health()
    finally:
        client.close()


@mcp.tool()
def health_metrics() -> Any:
    """Return Containerlab API server CPU, memory, and disk metrics."""
    client = get_client()
    try:
        return client.health_metrics()
    finally:
        client.close()


@mcp.tool()
def version() -> Any:
    """Return the Containerlab version reported by the API server."""
    client = get_client()
    try:
        return client.version()
    finally:
        client.close()


@mcp.tool()
def version_check() -> Any:
    """Check whether a newer Containerlab release is available."""
    client = get_client()
    try:
        return client.version_check()
    finally:
        client.close()


@mcp.tool()
def list_labs() -> Any:
    """List labs visible to the authenticated API user."""
    client = get_client()
    try:
        return client.list_labs()
    finally:
        client.close()


@mcp.tool()
def inspect_lab(lab_name: str) -> Any:
    """Inspect a lab and return node/container state."""
    client = get_client()
    try:
        return client.inspect_lab(lab_name)
    finally:
        client.close()


@mcp.tool()
def list_lab_interfaces(
    lab_name: str,
    node_name: str | None = None,
) -> Any:
    """List interface details for every node in a lab or one named node."""
    client = get_client()
    try:
        return client.list_lab_interfaces(lab_name, node_name=node_name)
    finally:
        client.close()


@mcp.tool()
def get_topology_yaml(lab_name: str) -> str:
    """Return the lab topology YAML."""
    client = get_client()
    try:
        return client.get_topology_yaml(lab_name)
    finally:
        client.close()


@mcp.tool()
def get_node_logs(lab_name: str, node_name: str) -> Any:
    """Return node logs. node_name may be short name like cx1 or full clab container name."""
    client = get_client()
    try:
        return client.get_node_logs(lab_name, node_name)
    finally:
        client.close()


@mcp.tool()
def get_node_browser_ports(lab_name: str, node_name: str) -> Any:
    """Return exposed node ports suitable for opening in a browser."""
    client = get_client()
    try:
        return client.get_node_browser_ports(lab_name, node_name)
    finally:
        client.close()


@mcp.tool()
def start_lab(lab_name: str, include_logs: bool = True) -> Any:
    """Start all stopped nodes in a deployed lab."""
    client = get_client()
    try:
        return client.start_lab(lab_name, include_logs=include_logs)
    finally:
        client.close()


@mcp.tool()
def stop_lab(lab_name: str, include_logs: bool = True) -> Any:
    """Stop all nodes in a deployed lab while preserving dataplane links."""
    client = get_client()
    try:
        return client.stop_lab(lab_name, include_logs=include_logs)
    finally:
        client.close()


@mcp.tool()
def start_node(lab_name: str, node_name: str) -> Any:
    """Start one stopped node while preserving the rest of the lab."""
    client = get_client()
    try:
        return client.start_node(lab_name, node_name)
    finally:
        client.close()


@mcp.tool()
def stop_node(lab_name: str, node_name: str) -> Any:
    """Stop one running node while preserving its dataplane links."""
    client = get_client()
    try:
        return client.stop_node(lab_name, node_name)
    finally:
        client.close()


@mcp.tool()
def restart_node(lab_name: str, node_name: str) -> Any:
    """Restart one node while preserving its dataplane links."""
    client = get_client()
    try:
        return client.restart_node(lab_name, node_name)
    finally:
        client.close()


@mcp.tool()
def pause_node(lab_name: str, node_name: str) -> Any:
    """Pause one running node."""
    client = get_client()
    try:
        return client.pause_node(lab_name, node_name)
    finally:
        client.close()


@mcp.tool()
def unpause_node(lab_name: str, node_name: str) -> Any:
    """Resume one paused node."""
    client = get_client()
    try:
        return client.unpause_node(lab_name, node_name)
    finally:
        client.close()


@mcp.tool()
def deploy_on_disk_lab(
    lab_name: str,
    topology_path: str | None = None,
    reconfigure: bool = False,
    include_logs: bool = True,
) -> Any:
    """Deploy an on-disk topology already present in the API user's lab directory."""
    client = get_client()
    try:
        return client.deploy_on_disk_lab(
            lab_name,
            topology_path=topology_path,
            reconfigure=reconfigure,
            include_logs=include_logs,
        )
    finally:
        client.close()


@mcp.tool()
def deploy_topology_content(
    topology: dict[str, Any],
    lab_name_override: str | None = None,
    reconfigure: bool = False,
) -> Any:
    """Deploy a topology object through the API server."""
    client = get_client()
    try:
        return client.deploy_topology_content(
            topology,
            lab_name_override=lab_name_override,
            reconfigure=reconfigure,
        )
    finally:
        client.close()


@mcp.tool()
def destroy_lab(
    lab_name: str,
    cleanup: bool = False,
    graceful: bool = True,
    include_logs: bool = True,
) -> Any:
    """Destroy a lab. This is destructive and should only be used after explicit user approval."""
    client = get_client()
    try:
        return client.destroy_lab(
            lab_name,
            cleanup=cleanup,
            graceful=graceful,
            include_logs=include_logs,
        )
    finally:
        client.close()


@mcp.tool()
def list_images() -> Any:
    """List images available in the Containerlab host runtime."""
    client = get_client()
    try:
        return client.list_images()
    finally:
        client.close()


@mcp.tool()
def pull_image(image: str) -> Any:
    """Pull a public or pre-authorized runtime image by reference."""
    client = get_client()
    try:
        return client.pull_image(image)
    finally:
        client.close()


@mcp.tool()
def delete_image(reference: str, force: bool = False) -> Any:
    """Delete a runtime image after explicit user approval. This is destructive."""
    client = get_client()
    try:
        return client.delete_image(reference, force=force)
    finally:
        client.close()


@mcp.tool()
def generate_drawio(
    lab_name: str,
    layout: str | None = None,
    theme: str | None = None,
) -> Any:
    """Generate draw.io XML for a deployed lab topology."""
    client = get_client()
    try:
        return client.generate_drawio(lab_name, layout=layout, theme=theme)
    finally:
        client.close()


@mcp.tool()
def request_ssh_access(
    lab_name: str,
    node_name: str,
    duration: str | None = None,
    ssh_username: str | None = None,
) -> Any:
    """Create temporary external SSH access and return connection details."""
    client = get_client()
    try:
        return client.request_ssh_access(
            lab_name,
            node_name,
            duration=duration,
            ssh_username=ssh_username,
        )
    finally:
        client.close()


@mcp.tool()
def list_ssh_sessions(all_sessions: bool = False) -> Any:
    """List active temporary SSH sessions visible to the API user."""
    client = get_client()
    try:
        return client.list_ssh_sessions(all_sessions=all_sessions)
    finally:
        client.close()


@mcp.tool()
def terminate_ssh_session(port: int) -> Any:
    """Terminate a temporary SSH access session by its allocated port."""
    client = get_client()
    try:
        return client.terminate_ssh_session(port)
    finally:
        client.close()


@mcp.tool()
def create_terminal_session(
    lab_name: str,
    node_name: str,
    protocol: Literal["ssh", "shell", "telnet"],
    rows: int = 24,
    cols: int = 80,
    ssh_username: str | None = None,
    telnet_port: int | None = None,
) -> Any:
    """Create a constrained API terminal session and return its metadata."""
    client = get_client()
    try:
        return client.create_terminal_session(
            lab_name,
            node_name,
            protocol=protocol,
            rows=rows,
            cols=cols,
            ssh_username=ssh_username,
            telnet_port=telnet_port,
        )
    finally:
        client.close()


@mcp.tool()
def get_terminal_session(session_id: str) -> Any:
    """Return metadata and lifecycle state for a terminal session."""
    client = get_client()
    try:
        return client.get_terminal_session(session_id)
    finally:
        client.close()


@mcp.tool()
def terminate_terminal_session(session_id: str) -> Any:
    """Terminate an API terminal session by ID."""
    client = get_client()
    try:
        return client.terminate_terminal_session(session_id)
    finally:
        client.close()


@mcp.tool()
def create_vxlan(
    link: str,
    remote: str,
    vni: int = 10,
    port: int = 14789,
    mtu: int | None = None,
    dev: str | None = None,
) -> Any:
    """Create a VXLAN tunnel for multi-host dataplane connectivity. Requires superuser."""
    client = get_client()
    try:
        return client.create_vxlan(
            link=link,
            remote=remote,
            vni=vni,
            port=port,
            mtu=mtu,
            dev=dev,
        )
    finally:
        client.close()


@mcp.tool()
def delete_vxlan(prefix: str = "vx-") -> Any:
    """Delete VXLAN interfaces matching a prefix after explicit user approval."""
    client = get_client()
    try:
        return client.delete_vxlan(prefix=prefix)
    finally:
        client.close()


@mcp.tool()
def make_two_switch_aoscx_topology(
    name: str,
    image: str = "vrnetlab/aruba_arubaos-cx:10.17.1010",
    link_interface: str = "eth1",
) -> dict[str, Any]:
    """Generate a two-switch AOS-CX topology object without deploying it."""
    return make_topology(name=name, image=image, link_interface=link_interface)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
