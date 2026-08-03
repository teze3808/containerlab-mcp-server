from __future__ import annotations

import ipaddress
import json
import re
from pathlib import PurePosixPath
from typing import Any


IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
IMAGE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/:@-]{0,255}$")
DURATION_RE = re.compile(r"^[0-9]+(?:\.[0-9]+)?(?:us|ms|s)$")
IDEMPOTENCY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{7,127}$")

FORBIDDEN_TOPOLOGY_KEYS = {
    "binds",
    "cap-add",
    "cmd",
    "entrypoint",
    "exec",
    "network-mode",
    "privileged",
    "runtime",
    "stages",
    "sysctls",
}


def validate_identifier(value: str, field: str) -> str:
    if not IDENTIFIER_RE.fullmatch(value):
        raise ValueError(
            f"{field} must contain only letters, numbers, dots, underscores, "
            "or hyphens and be at most 128 characters"
        )
    return value


def validate_image_reference(value: str) -> str:
    if not IMAGE_RE.fullmatch(value) or ".." in value:
        raise ValueError("image reference contains unsupported characters")
    return value


def validate_relative_path(value: str, field: str = "path") -> str:
    if not value or len(value) > 255 or "\x00" in value:
        raise ValueError(f"{field} must be a non-empty relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise ValueError(f"{field} must remain inside the lab directory")
    return value


def validate_idempotency_key(value: str) -> str:
    if not IDEMPOTENCY_RE.fullmatch(value):
        raise ValueError(
            "idempotency_key must be 8-128 characters using letters, numbers, "
            "dots, underscores, colons, or hyphens"
        )
    return value


def validate_command(value: str) -> str:
    if not value.strip() or len(value) > 4096 or "\x00" in value:
        raise ValueError("command must be non-empty and at most 4096 characters")
    return value


def validate_content(value: str, field: str = "content", max_bytes: int = 1_000_000) -> str:
    if len(value.encode("utf-8")) > max_bytes:
        raise ValueError(f"{field} exceeds the {max_bytes}-byte safety limit")
    return value


def validate_vxlan(
    *,
    link: str,
    remote: str,
    vni: int,
    port: int,
    mtu: int | None,
    dev: str | None,
) -> None:
    validate_identifier(link, "link")
    ipaddress.ip_address(remote)
    if not 1 <= vni <= 16_777_215:
        raise ValueError("vni must be between 1 and 16777215")
    if not 1 <= port <= 65_535:
        raise ValueError("port must be between 1 and 65535")
    if mtu is not None and not 576 <= mtu <= 9216:
        raise ValueError("mtu must be between 576 and 9216")
    if dev is not None:
        validate_identifier(dev, "dev")


def validate_netem(
    *,
    interface: str,
    delay: str | None,
    jitter: str | None,
    loss: float,
    rate: int,
    corruption: float,
) -> None:
    validate_identifier(interface, "interface")
    for field, value in (("delay", delay), ("jitter", jitter)):
        if value is not None and not DURATION_RE.fullmatch(value):
            raise ValueError(f"{field} must use us, ms, or s, for example 50ms")
    if not 0 <= loss <= 100:
        raise ValueError("loss must be between 0 and 100 percent")
    if not 0 <= corruption <= 100:
        raise ValueError("corruption must be between 0 and 100 percent")
    if not 0 <= rate <= 100_000_000:
        raise ValueError("rate must be between 0 and 100000000")


def validate_topology(topology: dict[str, Any]) -> dict[str, Any]:
    encoded = json.dumps(topology, separators=(",", ":"), default=str).encode()
    if len(encoded) > 1_000_000:
        raise ValueError("topology exceeds the 1 MB safety limit")

    name = topology.get("name")
    body = topology.get("topology")
    if not isinstance(name, str) or not isinstance(body, dict):
        raise ValueError("topology requires a valid name and topology object")
    validate_identifier(name, "topology name")

    nodes = body.get("nodes")
    links = body.get("links", [])
    if not isinstance(nodes, dict) or not nodes or len(nodes) > 100:
        raise ValueError("topology must contain between 1 and 100 nodes")
    if not isinstance(links, list) or len(links) > 1000:
        raise ValueError("topology may contain at most 1000 links")

    _reject_forbidden_topology_keys(topology)
    for node_name, node in nodes.items():
        validate_identifier(str(node_name), "node name")
        if not isinstance(node, dict):
            raise ValueError(f"node {node_name!r} must be an object")
        image = node.get("image")
        if image is not None:
            validate_image_reference(str(image))
        startup = node.get("startup-config")
        if startup is not None:
            validate_relative_path(str(startup), "startup-config")

    for link in links:
        endpoints = link.get("endpoints") if isinstance(link, dict) else None
        if not isinstance(endpoints, list) or len(endpoints) != 2:
            raise ValueError("each link requires exactly two endpoints")
        for endpoint in endpoints:
            if not isinstance(endpoint, str) or ":" not in endpoint:
                raise ValueError("link endpoints must use node:interface format")
            node_name, interface = endpoint.split(":", 1)
            if node_name not in nodes:
                raise ValueError(f"link references unknown node {node_name!r}")
            validate_identifier(interface, "interface")
    return topology


def _reject_forbidden_topology_keys(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).lower().replace("_", "-")
            if normalized in FORBIDDEN_TOPOLOGY_KEYS:
                raise ValueError(f"topology key {key!r} is disabled in safe mode")
            _reject_forbidden_topology_keys(child)
    elif isinstance(value, list):
        for child in value:
            _reject_forbidden_topology_keys(child)
