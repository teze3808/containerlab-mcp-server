from __future__ import annotations

from html import escape
from itertools import combinations
from typing import Any


DEFAULT_AOSCX_IMAGE = "vrnetlab/aruba_arubaos-cx:10.18.0001"
DEFAULT_VJUNOS_SWITCH_IMAGE = (
    "vrnetlab/juniper_vjunos-switch:26.2R1.7-nativefix"
)
DEFAULT_VJUNOS_ROUTER_IMAGE = (
    "vrnetlab/juniper_vjunos-router:26.2R1.7-nativefix"
)
DEFAULT_VSRX_IMAGE = "vrnetlab/juniper_vsrx:26.2R1.7"
DEFAULT_LINUX_IMAGE = "ghcr.io/srl-labs/network-multitool:latest"


def _validate_name(name: str) -> None:
    if not name.strip():
        raise ValueError("topology name must not be empty")


def _validate_counts(**counts: int) -> None:
    for field, value in counts.items():
        if value < 1:
            raise ValueError(f"{field} must be at least 1")


def _validate_optional_counts(**counts: int) -> None:
    for field, value in counts.items():
        if value < 0:
            raise ValueError(f"{field} must be at least 0")


def _nodes(
    prefix: str,
    count: int,
    kind: str,
    image: str,
    group: str,
) -> tuple[list[str], dict[str, dict[str, str]]]:
    names = [f"{prefix}{index}" for index in range(1, count + 1)]
    return names, {
        name: {"kind": kind, "image": image, "group": group}
        for name in names
    }


def _full_mesh(nodes: list[str]) -> list[tuple[str, str]]:
    return list(combinations(nodes, 2))


def _full_bipartite(
    left_nodes: list[str],
    right_nodes: list[str],
) -> list[tuple[str, str]]:
    return [(left, right) for left in left_nodes for right in right_nodes]


def _make_topology(
    name: str,
    nodes: dict[str, dict[str, str]],
    edges: list[tuple[str, str]],
) -> dict[str, Any]:
    _validate_name(name)
    interface_counters = {node: 0 for node in nodes}
    links: list[dict[str, list[str]]] = []
    seen_edges: set[tuple[str, str]] = set()

    for left, right in edges:
        if left not in nodes or right not in nodes:
            raise ValueError(f"link references unknown node: {left}, {right}")
        if left == right:
            raise ValueError(f"self-links are not supported: {left}")
        edge_key = tuple(sorted((left, right)))
        if edge_key in seen_edges:
            raise ValueError(f"duplicate link: {left}, {right}")
        seen_edges.add(edge_key)
        interface_counters[left] += 1
        interface_counters[right] += 1
        links.append(
            {
                "endpoints": [
                    f"{left}:eth{interface_counters[left]}",
                    f"{right}:eth{interface_counters[right]}",
                ]
            }
        )

    return {"name": name, "topology": {"nodes": nodes, "links": links}}


def generate_topology_preview(
    topology: dict[str, Any],
    connection_purposes: list[str] | None = None,
    notes: list[str] | None = None,
) -> dict[str, Any]:
    """Build a review bundle without sending anything to Containerlab."""
    topology_body = topology.get("topology")
    if not isinstance(topology_body, dict):
        raise ValueError("topology must contain a topology object")
    nodes = topology_body.get("nodes")
    links = topology_body.get("links", [])
    if not isinstance(nodes, dict) or not nodes:
        raise ValueError("topology must contain at least one node")
    if not isinstance(links, list):
        raise ValueError("topology links must be a list")
    if (
        connection_purposes is not None
        and len(connection_purposes) != len(links)
    ):
        raise ValueError("connection purposes must match the number of links")

    node_ids = {name: f"n{index}" for index, name in enumerate(nodes)}
    diagram = ["flowchart TB"]
    devices: list[dict[str, str]] = []
    for name, attributes in nodes.items():
        if not isinstance(attributes, dict):
            raise ValueError(f"node attributes must be an object: {name}")
        kind = str(attributes.get("kind", "unknown"))
        image = str(attributes.get("image", ""))
        devices.append(
            {
                "node": name,
                "group": str(attributes.get("group", "ungrouped")),
                "brand": _infer_brand(kind, image),
                "kind": kind,
                "image": image,
                "version": _image_version(image),
            }
        )
        diagram.append(f'  {node_ids[name]}["{escape(name, quote=True)}"]')

    connections: list[dict[str, str]] = []
    for link_index, link in enumerate(links):
        endpoints = link.get("endpoints") if isinstance(link, dict) else None
        if not isinstance(endpoints, list) or len(endpoints) != 2:
            raise ValueError("every link must contain exactly two endpoints")
        left_node, left_interface = _split_endpoint(str(endpoints[0]))
        right_node, right_interface = _split_endpoint(str(endpoints[1]))
        if left_node not in node_ids or right_node not in node_ids:
            raise ValueError("link endpoint references an unknown node")
        connection = {
            "node_a": left_node,
            "interface_a": left_interface,
            "node_b": right_node,
            "interface_b": right_interface,
        }
        if connection_purposes is not None:
            connection["purpose"] = connection_purposes[link_index]
        connections.append(connection)
        diagram.append(f"  {node_ids[left_node]} --- {node_ids[right_node]}")

    preview = {
        "name": str(topology.get("name", "topology")),
        "status": "preview-only",
        "summary": {"node_count": len(nodes), "link_count": len(links)},
        "diagram": {"format": "mermaid", "content": "\n".join(diagram)},
        "connection_table": connections,
        "devices": devices,
        "topology": topology,
        "next_step": (
            "Review this preview, then pass the topology field to "
            "deploy_topology_content to build the lab."
        ),
    }
    if connection_purposes is not None:
        preview["link_summary"] = {
            purpose: connection_purposes.count(purpose)
            for purpose in dict.fromkeys(connection_purposes)
        }
    if notes:
        preview["notes"] = notes
    return preview


def _make_parallel_topology(
    name: str,
    nodes: dict[str, dict[str, str]],
    edges: list[tuple[str, str, str]],
) -> tuple[dict[str, Any], list[str]]:
    _validate_name(name)
    interface_counters = {node: 0 for node in nodes}
    links: list[dict[str, list[str]]] = []
    purposes: list[str] = []
    for left, right, purpose in edges:
        if left not in nodes or right not in nodes:
            raise ValueError(f"link references unknown node: {left}, {right}")
        if left == right:
            raise ValueError(f"self-links are not supported: {left}")
        interface_counters[left] += 1
        interface_counters[right] += 1
        links.append(
            {
                "endpoints": [
                    f"{left}:eth{interface_counters[left]}",
                    f"{right}:eth{interface_counters[right]}",
                ]
            }
        )
        purposes.append(purpose)
    return {"name": name, "topology": {"nodes": nodes, "links": links}}, purposes


def _split_endpoint(endpoint: str) -> tuple[str, str]:
    if ":" not in endpoint:
        raise ValueError(f"invalid link endpoint: {endpoint}")
    node, interface = endpoint.rsplit(":", 1)
    if not node or not interface:
        raise ValueError(f"invalid link endpoint: {endpoint}")
    return node, interface


def _infer_brand(kind: str, image: str) -> str:
    value = f"{kind} {image}".lower()
    brands = (
        (("aruba", "aoscx", "aos-cx"), "Aruba"),
        (("juniper", "vjunos", "vsrx", "vmx", "vqfx"), "Juniper"),
        (("arista", "ceos"), "Arista"),
        (("cisco", "ios", "cat9kv", "n9kv", "xrv"), "Cisco"),
        (("nokia", "srlinux", "sros"), "Nokia"),
        (("linux", "network-multitool"), "Linux"),
    )
    for markers, brand in brands:
        if any(marker in value for marker in markers):
            return brand
    return "Unknown"


def _image_version(image: str) -> str:
    if "@" in image:
        return image.rsplit("@", 1)[1]
    image_name = image.rsplit("/", 1)[-1]
    if ":" in image_name:
        return image_name.rsplit(":", 1)[1]
    return "unspecified"


def make_two_switch_aoscx_topology(
    name: str,
    image: str = "vrnetlab/aruba_arubaos-cx:10.17.1010",
    link_interface: str = "eth1",
) -> dict[str, Any]:
    return {
        "name": name,
        "topology": {
            "nodes": {
                "cx1": {
                    "kind": "aruba_aoscx",
                    "image": image,
                },
                "cx2": {
                    "kind": "aruba_aoscx",
                    "image": image,
                },
            },
            "links": [
                {
                    "endpoints": [
                        f"cx1:{link_interface}",
                        f"cx2:{link_interface}",
                    ]
                }
            ],
        },
    }


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
) -> dict[str, Any]:
    """Build a redundant core-distribution-access campus topology."""
    _validate_counts(
        core_count=core_count,
        distribution_count=distribution_count,
        access_count=access_count,
    )
    cores, core_nodes = _nodes(
        "core", core_count, core_kind, core_image, "core"
    )
    distributions, distribution_nodes = _nodes(
        "dist",
        distribution_count,
        distribution_kind,
        distribution_image,
        "distribution",
    )
    access, access_nodes = _nodes(
        "access", access_count, access_kind, access_image, "access"
    )
    nodes = core_nodes | distribution_nodes | access_nodes
    edges = (
        _full_mesh(cores)
        + _full_bipartite(cores, distributions)
        + _full_bipartite(distributions, access)
    )
    return _make_topology(name, nodes, edges)


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
) -> dict[str, Any]:
    """Build a dual-WAN branch with a firewall, access switch, and clients."""
    _validate_counts(wan_count=wan_count)
    _validate_optional_counts(client_count=client_count)
    routers, router_nodes = _nodes(
        "wan", wan_count, router_kind, router_image, "wan"
    )
    clients, client_nodes = _nodes(
        "client", client_count, client_kind, client_image, "clients"
    )
    nodes = router_nodes | {
        "firewall1": {
            "kind": firewall_kind,
            "image": firewall_image,
            "group": "security",
        },
        "access1": {
            "kind": switch_kind,
            "image": switch_image,
            "group": "access",
        },
    } | client_nodes
    edges = (
        [(router, "firewall1") for router in routers]
        + [("firewall1", "access1")]
        + [("access1", client) for client in clients]
    )
    return _make_topology(name, nodes, edges)


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
) -> dict[str, Any]:
    """Build a leaf-spine fabric with border leaves and attached hosts."""
    _validate_counts(
        spine_count=spine_count,
        leaf_count=leaf_count,
    )
    _validate_optional_counts(
        border_leaf_count=border_leaf_count,
        hosts_per_leaf=hosts_per_leaf,
    )
    spines, spine_nodes = _nodes(
        "spine", spine_count, spine_kind, spine_image, "spine"
    )
    leaves, leaf_nodes = _nodes(
        "leaf", leaf_count, leaf_kind, leaf_image, "leaf"
    )
    borders, border_nodes = _nodes(
        "border", border_leaf_count, leaf_kind, leaf_image, "border-leaf"
    )
    nodes = spine_nodes | leaf_nodes | border_nodes
    edges = _full_bipartite(spines, leaves + borders)
    for leaf_index, leaf in enumerate(leaves, start=1):
        for host_index in range(1, hosts_per_leaf + 1):
            host = f"host{leaf_index}-{host_index}"
            nodes[host] = {
                "kind": host_kind,
                "image": host_image,
                "group": "servers",
            }
            edges.append((leaf, host))
    return _make_topology(name, nodes, edges)


def generate_dual_plane_ai_fabric(
    name: str,
    spines_per_plane: int = 2,
    leaves_per_plane: int = 2,
    host_count: int = 4,
    switch_kind: str = "aruba_aoscx",
    switch_image: str = DEFAULT_AOSCX_IMAGE,
    host_kind: str = "linux",
    host_image: str = DEFAULT_LINUX_IMAGE,
) -> dict[str, Any]:
    """Build isolated A/B leaf-spine planes with dual-attached AI hosts."""
    _validate_counts(
        spines_per_plane=spines_per_plane,
        leaves_per_plane=leaves_per_plane,
        host_count=host_count,
    )
    nodes: dict[str, dict[str, str]] = {}
    edges: list[tuple[str, str]] = []
    plane_leaves: dict[str, list[str]] = {}

    for plane in ("a", "b"):
        spines, spine_nodes = _nodes(
            f"spine-{plane}",
            spines_per_plane,
            switch_kind,
            switch_image,
            f"plane-{plane}-spine",
        )
        leaves, leaf_nodes = _nodes(
            f"leaf-{plane}",
            leaves_per_plane,
            switch_kind,
            switch_image,
            f"plane-{plane}-leaf",
        )
        nodes.update(spine_nodes | leaf_nodes)
        edges.extend(_full_bipartite(spines, leaves))
        plane_leaves[plane] = leaves

    for host_index in range(1, host_count + 1):
        host = f"ai-host{host_index}"
        nodes[host] = {
            "kind": host_kind,
            "image": host_image,
            "group": "ai-hosts",
        }
        leaf_index = (host_index - 1) % leaves_per_plane
        edges.append((plane_leaves["a"][leaf_index], host))
        edges.append((plane_leaves["b"][leaf_index], host))
    return _make_topology(name, nodes, edges)


def generate_hub_spoke_wan(
    name: str,
    hub_count: int = 1,
    spoke_count: int = 3,
    router_kind: str = "juniper_vjunosrouter",
    router_image: str = DEFAULT_VJUNOS_ROUTER_IMAGE,
) -> dict[str, Any]:
    """Build a full-redundancy hub-and-spoke WAN topology."""
    _validate_counts(hub_count=hub_count, spoke_count=spoke_count)
    hubs, hub_nodes = _nodes(
        "hub", hub_count, router_kind, router_image, "hub"
    )
    spokes, spoke_nodes = _nodes(
        "spoke", spoke_count, router_kind, router_image, "spokes"
    )
    return _make_topology(
        name,
        hub_nodes | spoke_nodes,
        _full_bipartite(hubs, spokes),
    )


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
) -> dict[str, Any]:
    """Build a super-spine, spine, and leaf CLOS topology."""
    _validate_counts(
        super_spine_count=super_spine_count,
        spine_count=spine_count,
        leaf_count=leaf_count,
    )
    super_spines, super_spine_nodes = _nodes(
        "super-spine",
        super_spine_count,
        super_spine_kind,
        super_spine_image,
        "super-spine",
    )
    spines, spine_nodes = _nodes(
        "spine", spine_count, spine_kind, spine_image, "spine"
    )
    leaves, leaf_nodes = _nodes(
        "leaf", leaf_count, leaf_kind, leaf_image, "leaf"
    )
    return _make_topology(
        name,
        super_spine_nodes | spine_nodes | leaf_nodes,
        _full_bipartite(super_spines, spines)
        + _full_bipartite(spines, leaves),
    )


def generate_lacp_topology(
    name: str,
    member_link_count: int = 2,
    device_a_kind: str = "aruba_aoscx",
    device_a_image: str = DEFAULT_AOSCX_IMAGE,
    device_b_kind: str = "juniper_vjunosswitch",
    device_b_image: str = DEFAULT_VJUNOS_SWITCH_IMAGE,
) -> tuple[dict[str, Any], list[str]]:
    """Build two devices joined by parallel links intended for one LAG."""
    _validate_counts(member_link_count=member_link_count)
    nodes = {
        "device1": {
            "kind": device_a_kind,
            "image": device_a_image,
            "group": "lag-peer",
        },
        "device2": {
            "kind": device_b_kind,
            "image": device_b_image,
            "group": "lag-peer",
        },
    }
    edges = [
        ("device1", "device2", "lacp-member") for _ in range(member_link_count)
    ]
    return _make_parallel_topology(name, nodes, edges)


def generate_vsx_topology(
    name: str,
    isl_link_count: int = 2,
    keepalive_link_count: int = 1,
    downstream_count: int = 1,
    downstream_links_per_peer: int = 1,
    vsx_kind: str = "aruba_aoscx",
    vsx_image: str = DEFAULT_AOSCX_IMAGE,
    downstream_kind: str = "juniper_vjunosswitch",
    downstream_image: str = DEFAULT_VJUNOS_SWITCH_IMAGE,
) -> tuple[dict[str, Any], list[str]]:
    """Build VSX peer, keepalive, and dual-homed downstream cabling."""
    _validate_counts(
        isl_link_count=isl_link_count,
        downstream_links_per_peer=downstream_links_per_peer,
    )
    _validate_optional_counts(
        keepalive_link_count=keepalive_link_count,
        downstream_count=downstream_count,
    )
    nodes = {
        "vsx1": {"kind": vsx_kind, "image": vsx_image, "group": "vsx"},
        "vsx2": {"kind": vsx_kind, "image": vsx_image, "group": "vsx"},
    }
    edges = [("vsx1", "vsx2", "vsx-isl") for _ in range(isl_link_count)]
    edges.extend(
        ("vsx1", "vsx2", "vsx-keepalive")
        for _ in range(keepalive_link_count)
    )
    for downstream_index in range(1, downstream_count + 1):
        downstream = f"access{downstream_index}"
        nodes[downstream] = {
            "kind": downstream_kind,
            "image": downstream_image,
            "group": "downstream",
        }
        for peer in ("vsx1", "vsx2"):
            edges.extend(
                (peer, downstream, "downstream-lag-member")
                for _ in range(downstream_links_per_peer)
            )
    return _make_parallel_topology(name, nodes, edges)


def generate_virtual_chassis_topology(
    name: str,
    member_count: int = 2,
    vcp_links_per_adjacency: int = 2,
    ring: bool = True,
    member_kind: str = "juniper_vjunosswitch",
    member_image: str = DEFAULT_VJUNOS_SWITCH_IMAGE,
) -> tuple[dict[str, Any], list[str]]:
    """Build a Virtual Chassis cabling plan without device configuration."""
    if member_count < 2:
        raise ValueError("member_count must be at least 2")
    _validate_counts(vcp_links_per_adjacency=vcp_links_per_adjacency)
    members, nodes = _nodes(
        "member",
        member_count,
        member_kind,
        member_image,
        "virtual-chassis",
    )
    adjacencies = list(zip(members, members[1:]))
    if ring and member_count > 2:
        adjacencies.append((members[-1], members[0]))
    edges = [
        (left, right, "virtual-chassis-port")
        for left, right in adjacencies
        for _ in range(vcp_links_per_adjacency)
    ]
    return _make_parallel_topology(name, nodes, edges)
