from __future__ import annotations

from typing import Any

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
