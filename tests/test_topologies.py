import pytest

from containerlab_mcp import server
from containerlab_mcp.topologies import (
    generate_branch_topology,
    generate_campus_topology,
    generate_dual_plane_ai_fabric,
    generate_evpn_vxlan_fabric,
    generate_hub_spoke_wan,
    generate_three_tier_clos,
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


@pytest.mark.parametrize(
    ("builder", "kwargs"),
    [
        (generate_campus_topology, {"core_count": 0}),
        (generate_branch_topology, {"wan_count": 0}),
        (generate_evpn_vxlan_fabric, {"hosts_per_leaf": -1}),
        (generate_dual_plane_ai_fabric, {"host_count": 0}),
        (generate_hub_spoke_wan, {"spoke_count": 0}),
        (generate_three_tier_clos, {"leaf_count": 0}),
    ],
)
def test_topology_generators_reject_invalid_counts(builder, kwargs) -> None:
    with pytest.raises(ValueError, match="must be at least"):
        builder("invalid", **kwargs)


def test_topology_generators_reject_empty_names() -> None:
    with pytest.raises(ValueError, match="name must not be empty"):
        generate_hub_spoke_wan("  ")


def test_generated_topology_deploy_is_opt_in(monkeypatch) -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.deployed = None
            self.closed = False

        def deploy_topology_content(self, topology):
            self.deployed = topology
            return {"deployed": topology["name"]}

        def close(self) -> None:
            self.closed = True

    topology = generate_hub_spoke_wan("wan1")
    fake_client = FakeClient()
    monkeypatch.setattr(server, "get_client", lambda: fake_client)

    assert server._return_or_deploy(topology, False) is topology
    assert fake_client.deployed is None
    assert fake_client.closed is False

    assert server._return_or_deploy(topology, True) == {"deployed": "wan1"}
    assert fake_client.deployed is topology
    assert fake_client.closed is True
