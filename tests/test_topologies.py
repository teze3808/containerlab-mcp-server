import pytest

from containerlab_mcp import server
from containerlab_mcp.topologies import (
    generate_branch_topology,
    generate_campus_topology,
    generate_dual_plane_ai_fabric,
    generate_evpn_vxlan_fabric,
    generate_hub_spoke_wan,
    generate_lacp_topology,
    generate_topology_preview,
    generate_three_tier_clos,
    generate_virtual_chassis_topology,
    generate_vsx_topology,
    make_two_switch_aoscx_topology,
)


def assert_interfaces_are_unique(topology: dict) -> None:
    endpoints = [
        endpoint
        for link in topology["topology"]["links"]
        for endpoint in link["endpoints"]
    ]
    assert len(endpoints) == len(set(endpoints))


def test_make_two_switch_aoscx_topology_defaults() -> None:
    topology = make_two_switch_aoscx_topology("demo")

    assert topology["name"] == "demo"
    assert topology["topology"]["nodes"]["cx1"]["kind"] == "aruba_aoscx"
    assert topology["topology"]["nodes"]["cx2"]["image"] == "vrnetlab/aruba_arubaos-cx:10.17.1010"
    assert topology["topology"]["links"] == [{"endpoints": ["cx1:eth1", "cx2:eth1"]}]


def test_generate_campus_topology() -> None:
    topology = generate_campus_topology("campus1")

    assert len(topology["topology"]["nodes"]) == 8
    assert len(topology["topology"]["links"]) == 13
    assert topology["topology"]["nodes"]["core1"]["group"] == "core"
    assert topology["topology"]["nodes"]["access4"]["kind"] == (
        "juniper_vjunosswitch"
    )
    assert_interfaces_are_unique(topology)


def test_generate_branch_topology() -> None:
    topology = generate_branch_topology("branch1")

    assert len(topology["topology"]["nodes"]) == 6
    assert len(topology["topology"]["links"]) == 5
    assert topology["topology"]["nodes"]["firewall1"]["kind"] == "juniper_vsrx"
    assert topology["topology"]["nodes"]["client2"]["kind"] == "linux"
    assert_interfaces_are_unique(topology)


def test_generate_evpn_vxlan_fabric() -> None:
    topology = generate_evpn_vxlan_fabric("dc1")

    assert len(topology["topology"]["nodes"]) == 12
    assert len(topology["topology"]["links"]) == 16
    assert topology["topology"]["nodes"]["border2"]["group"] == "border-leaf"
    assert topology["topology"]["nodes"]["host4-1"]["group"] == "servers"
    assert_interfaces_are_unique(topology)


def test_generate_network_only_evpn_vxlan_fabric() -> None:
    topology = generate_evpn_vxlan_fabric(
        "dc-network-only",
        border_leaf_count=0,
        hosts_per_leaf=0,
    )

    assert len(topology["topology"]["nodes"]) == 6
    assert len(topology["topology"]["links"]) == 8
    assert_interfaces_are_unique(topology)


def test_generate_dual_plane_ai_fabric() -> None:
    topology = generate_dual_plane_ai_fabric("ai1")

    assert len(topology["topology"]["nodes"]) == 12
    assert len(topology["topology"]["links"]) == 16
    host_links = [
        link
        for link in topology["topology"]["links"]
        if any("ai-host1:" in endpoint for endpoint in link["endpoints"])
    ]
    assert len(host_links) == 2
    assert any("leaf-a1:" in link["endpoints"][0] for link in host_links)
    assert any("leaf-b1:" in link["endpoints"][0] for link in host_links)
    assert_interfaces_are_unique(topology)


def test_generate_hub_spoke_wan() -> None:
    topology = generate_hub_spoke_wan("wan1", hub_count=2, spoke_count=4)

    assert len(topology["topology"]["nodes"]) == 6
    assert len(topology["topology"]["links"]) == 8
    assert_interfaces_are_unique(topology)


def test_generate_three_tier_clos() -> None:
    topology = generate_three_tier_clos("clos3")

    assert len(topology["topology"]["nodes"]) == 14
    assert len(topology["topology"]["links"]) == 40
    assert topology["topology"]["nodes"]["super-spine2"]["group"] == (
        "super-spine"
    )
    assert_interfaces_are_unique(topology)


def test_generate_lacp_topology_uses_parallel_unique_links() -> None:
    topology, purposes = generate_lacp_topology("lag1", member_link_count=2)

    assert topology["topology"]["links"] == [
        {"endpoints": ["device1:eth1", "device2:eth1"]},
        {"endpoints": ["device1:eth2", "device2:eth2"]},
    ]
    assert purposes == ["lacp-member", "lacp-member"]
    assert_interfaces_are_unique(topology)


def test_generate_vsx_topology_counts_link_purposes() -> None:
    topology, purposes = generate_vsx_topology("vsx1")
    preview = generate_topology_preview(topology, purposes)

    assert len(topology["topology"]["nodes"]) == 3
    assert len(topology["topology"]["links"]) == 5
    assert preview["link_summary"] == {
        "vsx-isl": 2,
        "vsx-keepalive": 1,
        "downstream-lag-member": 2,
    }
    assert_interfaces_are_unique(topology)


def test_generate_virtual_chassis_ring_link_count() -> None:
    topology, purposes = generate_virtual_chassis_topology(
        "vc1",
        member_count=4,
        vcp_links_per_adjacency=2,
    )

    assert len(topology["topology"]["nodes"]) == 4
    assert len(topology["topology"]["links"]) == 8
    assert purposes == ["virtual-chassis-port"] * 8
    assert topology["topology"]["links"][-1]["endpoints"] == [
        "member4:eth4",
        "member1:eth4",
    ]
    assert_interfaces_are_unique(topology)


@pytest.mark.parametrize(
    ("builder", "kwargs"),
    [
        (generate_campus_topology, {"core_count": 0}),
        (generate_branch_topology, {"wan_count": 0}),
        (generate_evpn_vxlan_fabric, {"hosts_per_leaf": -1}),
        (generate_dual_plane_ai_fabric, {"host_count": 0}),
        (generate_hub_spoke_wan, {"spoke_count": 0}),
        (generate_three_tier_clos, {"leaf_count": 0}),
        (generate_lacp_topology, {"member_link_count": 0}),
        (generate_vsx_topology, {"isl_link_count": 0}),
        (generate_virtual_chassis_topology, {"member_count": 1}),
    ],
)
def test_topology_generators_reject_invalid_counts(builder, kwargs) -> None:
    with pytest.raises(ValueError, match="must be at least"):
        builder("invalid", **kwargs)


def test_topology_generators_reject_empty_names() -> None:
    with pytest.raises(ValueError, match="name must not be empty"):
        generate_hub_spoke_wan("  ")


def test_generate_topology_preview() -> None:
    topology = generate_branch_topology("branch1", wan_count=1, client_count=1)
    preview = generate_topology_preview(topology)

    assert preview["status"] == "preview-only"
    assert preview["topology"] is topology
    assert preview["diagram"]["format"] == "mermaid"
    assert preview["diagram"]["content"].startswith("flowchart TB")
    assert "eth1" not in preview["diagram"]["content"]
    assert len(preview["connection_table"]) == 3
    assert preview["connection_table"][0] == {
        "node_a": "wan1",
        "interface_a": "eth1",
        "node_b": "firewall1",
        "interface_b": "eth1",
    }

    devices = {device["node"]: device for device in preview["devices"]}
    assert devices["wan1"]["brand"] == "Juniper"
    assert devices["wan1"]["version"] == "26.2R1.7-nativefix"
    assert devices["access1"]["brand"] == "Aruba"
    assert devices["access1"]["version"] == "10.18.0001"


def test_preview_topology_rejects_invalid_topology() -> None:
    with pytest.raises(ValueError, match="topology object"):
        generate_topology_preview({"name": "empty"})


def test_preview_topology_rejects_mismatched_purposes() -> None:
    topology, _ = generate_lacp_topology("lag1")

    with pytest.raises(ValueError, match="purposes"):
        generate_topology_preview(topology, ["only-one-purpose"])


def test_mcp_topology_helper_returns_preview() -> None:
    preview = server.generate_campus_topology(
        "campus1",
        core_count=1,
        distribution_count=1,
        access_count=1,
    )

    assert preview["status"] == "preview-only"
    assert preview["topology"]["name"] == "campus1"
    assert len(preview["devices"]) == 3


def test_mcp_link_intent_helpers_return_preview_notes() -> None:
    lacp = server.generate_lacp_topology("lag1")
    vsx = server.generate_vsx_topology("vsx1")
    vc = server.generate_virtual_chassis_topology("vc1")

    assert lacp["summary"]["link_count"] == 2
    assert lacp["connection_table"][0]["purpose"] == "lacp-member"
    assert vsx["summary"]["link_count"] == 5
    assert vc["summary"]["link_count"] == 2
    assert "does not support" in vc["notes"][1]


def test_native_clos_mcp_generation_never_deploys(monkeypatch) -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.deploy = None
            self.closed = False

        def generate_clos_topology(self, *args, **kwargs):
            self.deploy = kwargs["deploy"]
            return {"name": "clos1", "topology": {"nodes": {}, "links": []}}

        def close(self) -> None:
            self.closed = True

    fake_client = FakeClient()
    monkeypatch.setattr(server, "get_client", lambda: fake_client)

    server.generate_clos_topology(
        "clos1",
        [{"name": "spine", "count": 1}],
        {"spine": "example/spine:1"},
    )

    assert fake_client.deploy is False
    assert fake_client.closed is True
