from __future__ import annotations

from typing import Any


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
