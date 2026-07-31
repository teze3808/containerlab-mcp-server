from __future__ import annotations

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from .client import ContainerlabClient
from .config import get_settings
from .topologies import (
    DEFAULT_AOSCX_IMAGE,
    DEFAULT_LINUX_IMAGE,
    DEFAULT_VJUNOS_ROUTER_IMAGE,
    DEFAULT_VJUNOS_SWITCH_IMAGE,
    DEFAULT_VSRX_IMAGE,
    generate_branch_topology as build_branch_topology,
    generate_campus_topology as build_campus_topology,
    generate_dual_plane_ai_fabric as build_dual_plane_ai_fabric,
    generate_evpn_vxlan_fabric as build_evpn_vxlan_fabric,
    generate_hub_spoke_wan as build_hub_spoke_wan,
    generate_topology_preview as build_topology_preview,
    generate_three_tier_clos as build_three_tier_clos,
    make_two_switch_aoscx_topology as make_topology,
)

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
def execute_lab_command(
    lab_name: str,
    command: str,
    node_filter: str | None = None,
) -> Any:
    """Execute a native container command on all lab nodes or one filtered node."""
    client = get_client()
    try:
        return client.execute_lab_command(
            lab_name,
            command,
            node_filter=node_filter,
        )
    finally:
        client.close()


@mcp.tool()
def execute_node_command(lab_name: str, node_name: str, command: str) -> Any:
    """Execute a native container command on one node. Confirm mutating commands first."""
    client = get_client()
    try:
        return client.execute_node_command(lab_name, node_name, command)
    finally:
        client.close()


@mcp.tool()
def validate_node_command(
    lab_name: str,
    node_name: str,
    command: str,
    expected_text: str | None = None,
) -> Any:
    """Run a command and report pass when it exits zero and optionally contains text."""
    client = get_client()
    try:
        return client.validate_node_command(
            lab_name,
            node_name,
            command,
            expected_text=expected_text,
        )
    finally:
        client.close()


@mcp.tool()
def save_lab_config(lab_name: str, node_name: str | None = None) -> Any:
    """Save running configurations for all supported nodes or one named node."""
    client = get_client()
    try:
        return client.save_lab_config(lab_name, node_name=node_name)
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
def get_edgeshark_status() -> Any:
    """Return EdgeShark packet-capture service status."""
    client = get_client()
    try:
        return client.get_edgeshark_status()
    finally:
        client.close()


@mcp.tool()
def install_edgeshark() -> Any:
    """Install and start EdgeShark. Requires API superuser and explicit approval."""
    client = get_client()
    try:
        return client.install_edgeshark()
    finally:
        client.close()


@mcp.tool()
def uninstall_edgeshark() -> Any:
    """Uninstall EdgeShark. Requires API superuser and explicit approval."""
    client = get_client()
    try:
        return client.uninstall_edgeshark()
    finally:
        client.close()


@mcp.tool()
def build_packetflix_capture(
    lab_name: str,
    targets: list[dict[str, str]],
    remote_hostname: str | None = None,
) -> Any:
    """Build Packetflix capture URIs for node/interface targets."""
    client = get_client()
    try:
        return client.build_packetflix_capture(
            lab_name,
            targets,
            remote_hostname=remote_hostname,
        )
    finally:
        client.close()


@mcp.tool()
def create_wireshark_capture_sessions(
    lab_name: str,
    targets: list[dict[str, str]],
    theme: str | None = None,
) -> Any:
    """Create EdgeShark Wireshark/noVNC sessions for node/interface targets."""
    client = get_client()
    try:
        return client.create_wireshark_capture_sessions(
            lab_name,
            targets,
            theme=theme,
        )
    finally:
        client.close()


@mcp.tool()
def get_capture_session_ready(session_id: str) -> Any:
    """Return capture-session readiness and its proxied noVNC URL."""
    client = get_client()
    try:
        return client.get_capture_session_ready(session_id)
    finally:
        client.close()


@mcp.tool()
def terminate_capture_session(session_id: str) -> Any:
    """Terminate one Wireshark capture session after explicit approval."""
    client = get_client()
    try:
        return client.terminate_capture_session(session_id)
    finally:
        client.close()


@mcp.tool()
def terminate_all_capture_sessions() -> Any:
    """Terminate all visible Wireshark capture sessions after explicit approval."""
    client = get_client()
    try:
        return client.terminate_all_capture_sessions()
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
def set_link_impairment(
    lab_name: str,
    node_name: str,
    interface: str,
    delay: str | None = None,
    jitter: str | None = None,
    loss: float = 0.0,
    rate: int = 0,
    corruption: float = 0.0,
) -> Any:
    """Set delay, jitter, loss, rate, or corruption after explicit approval."""
    client = get_client()
    try:
        return client.set_link_impairment(
            lab_name,
            node_name,
            interface,
            delay=delay,
            jitter=jitter,
            loss=loss,
            rate=rate,
            corruption=corruption,
        )
    finally:
        client.close()


@mcp.tool()
def show_link_impairments(lab_name: str, node_name: str) -> Any:
    """Show active netem impairments for one node."""
    client = get_client()
    try:
        return client.show_link_impairments(lab_name, node_name)
    finally:
        client.close()


@mcp.tool()
def reset_link_impairment(
    lab_name: str,
    node_name: str,
    interface: str,
) -> Any:
    """Remove netem impairments from an interface after explicit approval."""
    client = get_client()
    try:
        return client.reset_link_impairment(lab_name, node_name, interface)
    finally:
        client.close()


@mcp.tool()
def list_topology_files() -> Any:
    """List editable topology files visible to the API user."""
    client = get_client()
    try:
        return client.list_topology_files()
    finally:
        client.close()


@mcp.tool()
def update_topology_yaml(lab_name: str, content: str) -> Any:
    """Replace a lab topology YAML document after explicit approval."""
    client = get_client()
    try:
        return client.update_topology_yaml(lab_name, content)
    finally:
        client.close()


@mcp.tool()
def get_topology_annotations(lab_name: str) -> str:
    """Return the TopoViewer annotations JSON for a lab."""
    client = get_client()
    try:
        return client.get_topology_annotations(lab_name)
    finally:
        client.close()


@mcp.tool()
def update_topology_annotations(lab_name: str, content: str) -> Any:
    """Replace the TopoViewer annotations JSON after explicit approval."""
    client = get_client()
    try:
        return client.update_topology_annotations(lab_name, content)
    finally:
        client.close()


@mcp.tool()
def get_topology_file(lab_name: str, path: str) -> str:
    """Read a scoped file from a lab directory."""
    client = get_client()
    try:
        return client.get_topology_file(lab_name, path)
    finally:
        client.close()


@mcp.tool()
def put_topology_file(lab_name: str, path: str, content: str) -> Any:
    """Write a scoped lab file, including startup configs, after approval."""
    client = get_client()
    try:
        return client.put_topology_file(lab_name, path, content)
    finally:
        client.close()


@mcp.tool()
def put_startup_config(
    lab_name: str,
    node_name: str,
    content: str,
    path: str | None = None,
) -> Any:
    """Write a startup config under configs/ and return its topology-relative path."""
    config_path = path or f"configs/{node_name}.cfg"
    client = get_client()
    try:
        result = client.put_topology_file(lab_name, config_path, content)
        return {"path": config_path, "result": result}
    finally:
        client.close()


@mcp.tool()
def delete_topology_file(lab_name: str, path: str) -> Any:
    """Delete a scoped file from a lab directory after explicit approval."""
    client = get_client()
    try:
        return client.delete_topology_file(lab_name, path)
    finally:
        client.close()


@mcp.tool()
def rename_topology_file(
    lab_name: str,
    old_path: str,
    new_path: str,
) -> Any:
    """Rename or move a scoped file inside a lab directory."""
    client = get_client()
    try:
        return client.rename_topology_file(lab_name, old_path, new_path)
    finally:
        client.close()


@mcp.tool()
def collect_events(
    duration_seconds: float = 10.0,
    max_events: int = 100,
    initial_state: bool = True,
    interface_stats: bool = False,
    interface_stats_interval: str = "10s",
) -> Any:
    """Collect a bounded snapshot from the native NDJSON event stream."""
    client = get_client()
    try:
        return client.collect_events(
            duration_seconds=duration_seconds,
            max_events=max_events,
            initial_state=initial_state,
            interface_stats=interface_stats,
            interface_stats_interval=interface_stats_interval,
        )
    finally:
        client.close()


@mcp.tool()
def generate_clos_topology(
    name: str,
    tiers: list[dict[str, Any]],
    images: dict[str, str],
    default_kind: str | None = None,
    node_prefix: str | None = None,
    group_prefix: str | None = None,
    management_network: str | None = None,
    ipv4_subnet: str | None = None,
    ipv6_subnet: str | None = None,
    licenses: dict[str, str] | None = None,
    max_workers: int | None = None,
    output_file: str | None = None,
) -> Any:
    """Generate a native CLOS topology without deploying it."""
    client = get_client()
    try:
        return client.generate_clos_topology(
            name,
            tiers,
            images,
            default_kind=default_kind,
            deploy=False,
            node_prefix=node_prefix,
            group_prefix=group_prefix,
            management_network=management_network,
            ipv4_subnet=ipv4_subnet,
            ipv6_subnet=ipv6_subnet,
            licenses=licenses,
            max_workers=max_workers,
            output_file=output_file,
        )
    finally:
        client.close()


@mcp.tool()
def list_custom_node_templates() -> Any:
    """List the API user's TopoViewer custom node templates."""
    client = get_client()
    try:
        return client.list_custom_node_templates()
    finally:
        client.close()


@mcp.tool()
def save_custom_node_template(template: dict[str, Any]) -> Any:
    """Create or update one custom node template."""
    client = get_client()
    try:
        return client.save_custom_node_template(template)
    finally:
        client.close()


@mcp.tool()
def replace_custom_node_templates(
    templates: list[dict[str, Any]],
) -> Any:
    """Replace the complete custom node template collection after approval."""
    client = get_client()
    try:
        return client.replace_custom_node_templates(templates)
    finally:
        client.close()


@mcp.tool()
def set_default_custom_node_template(name: str) -> Any:
    """Select the default TopoViewer custom node template."""
    client = get_client()
    try:
        return client.set_default_custom_node_template(name)
    finally:
        client.close()


@mcp.tool()
def delete_custom_node_template(name: str) -> Any:
    """Delete one custom node template after explicit approval."""
    client = get_client()
    try:
        return client.delete_custom_node_template(name)
    finally:
        client.close()


@mcp.tool()
def make_two_switch_aoscx_topology(
    name: str,
    image: str = "vrnetlab/aruba_arubaos-cx:10.17.1010",
    link_interface: str = "eth1",
) -> dict[str, Any]:
    """Preview two linked AOS-CX switches without deploying them."""
    return build_topology_preview(
        make_topology(
            name=name,
            image=image,
            link_interface=link_interface,
        )
    )


@mcp.tool()
def preview_topology(topology: dict[str, Any]) -> dict[str, Any]:
    """Preview any topology with a diagram, links, devices, and image versions."""
    return build_topology_preview(topology)


@mcp.tool()
def generate_campus_topology(
    name: str,
    core_count: int = 2,
    distribution_count: int = 2,
    access_count: int = 4,
    core_kind: str = "aruba_aoscx",
    core_image: str = DEFAULT_AOSCX_IMAGE,
    distribution_kind: str = "aruba_aoscx",
    distribution_image: str = DEFAULT_AOSCX_IMAGE,
    access_kind: str = "juniper_vjunosswitch",
    access_image: str = DEFAULT_VJUNOS_SWITCH_IMAGE,
) -> Any:
    """Preview a redundant campus topology without deploying it."""
    topology = build_campus_topology(
        name,
        core_count,
        distribution_count,
        access_count,
        core_kind,
        core_image,
        distribution_kind,
        distribution_image,
        access_kind,
        access_image,
    )
    return build_topology_preview(topology)


@mcp.tool()
def generate_branch_topology(
    name: str,
    wan_count: int = 2,
    client_count: int = 2,
    router_kind: str = "juniper_vjunosrouter",
    router_image: str = DEFAULT_VJUNOS_ROUTER_IMAGE,
    firewall_kind: str = "juniper_vsrx",
    firewall_image: str = DEFAULT_VSRX_IMAGE,
    switch_kind: str = "aruba_aoscx",
    switch_image: str = DEFAULT_AOSCX_IMAGE,
    client_kind: str = "linux",
    client_image: str = DEFAULT_LINUX_IMAGE,
) -> Any:
    """Preview a dual-WAN branch topology without deploying it."""
    topology = build_branch_topology(
        name,
        wan_count,
        client_count,
        router_kind,
        router_image,
        firewall_kind,
        firewall_image,
        switch_kind,
        switch_image,
        client_kind,
        client_image,
    )
    return build_topology_preview(topology)


@mcp.tool()
def generate_evpn_vxlan_fabric(
    name: str,
    spine_count: int = 2,
    leaf_count: int = 4,
    border_leaf_count: int = 2,
    hosts_per_leaf: int = 1,
    spine_kind: str = "aruba_aoscx",
    spine_image: str = DEFAULT_AOSCX_IMAGE,
    leaf_kind: str = "juniper_vjunosswitch",
    leaf_image: str = DEFAULT_VJUNOS_SWITCH_IMAGE,
    host_kind: str = "linux",
    host_image: str = DEFAULT_LINUX_IMAGE,
) -> Any:
    """Preview an EVPN-VXLAN-ready fabric without deploying it."""
    topology = build_evpn_vxlan_fabric(
        name,
        spine_count,
        leaf_count,
        border_leaf_count,
        hosts_per_leaf,
        spine_kind,
        spine_image,
        leaf_kind,
        leaf_image,
        host_kind,
        host_image,
    )
    return build_topology_preview(topology)


@mcp.tool()
def generate_dual_plane_ai_fabric(
    name: str,
    spines_per_plane: int = 2,
    leaves_per_plane: int = 2,
    host_count: int = 4,
    switch_kind: str = "aruba_aoscx",
    switch_image: str = DEFAULT_AOSCX_IMAGE,
    host_kind: str = "linux",
    host_image: str = DEFAULT_LINUX_IMAGE,
) -> Any:
    """Preview dual A/B AI fabrics without deploying them."""
    topology = build_dual_plane_ai_fabric(
        name,
        spines_per_plane,
        leaves_per_plane,
        host_count,
        switch_kind,
        switch_image,
        host_kind,
        host_image,
    )
    return build_topology_preview(topology)


@mcp.tool()
def generate_hub_spoke_wan(
    name: str,
    hub_count: int = 1,
    spoke_count: int = 3,
    router_kind: str = "juniper_vjunosrouter",
    router_image: str = DEFAULT_VJUNOS_ROUTER_IMAGE,
) -> Any:
    """Preview a hub-and-spoke WAN without deploying it."""
    topology = build_hub_spoke_wan(
        name,
        hub_count,
        spoke_count,
        router_kind,
        router_image,
    )
    return build_topology_preview(topology)


@mcp.tool()
def generate_three_tier_clos(
    name: str,
    super_spine_count: int = 2,
    spine_count: int = 4,
    leaf_count: int = 8,
    super_spine_kind: str = "aruba_aoscx",
    super_spine_image: str = DEFAULT_AOSCX_IMAGE,
    spine_kind: str = "aruba_aoscx",
    spine_image: str = DEFAULT_AOSCX_IMAGE,
    leaf_kind: str = "juniper_vjunosswitch",
    leaf_image: str = DEFAULT_VJUNOS_SWITCH_IMAGE,
) -> Any:
    """Preview a three-tier CLOS without deploying it."""
    topology = build_three_tier_clos(
        name,
        super_spine_count,
        spine_count,
        leaf_count,
        super_spine_kind,
        super_spine_image,
        spine_kind,
        spine_image,
        leaf_kind,
        leaf_image,
    )
    return build_topology_preview(topology)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
