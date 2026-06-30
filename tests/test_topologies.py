from containerlab_mcp.topologies import make_two_switch_aoscx_topology


def test_make_two_switch_aoscx_topology_defaults() -> None:
    topology = make_two_switch_aoscx_topology("demo")

    assert topology["name"] == "demo"
    assert topology["topology"]["nodes"]["cx1"]["kind"] == "aruba_aoscx"
    assert topology["topology"]["nodes"]["cx2"]["image"] == "vrnetlab/aruba_arubaos-cx:10.17.1010"
    assert topology["topology"]["links"] == [{"endpoints": ["cx1:eth1", "cx2:eth1"]}]
