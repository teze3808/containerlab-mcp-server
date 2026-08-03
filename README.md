# containerlab-mcp-server

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![MCP](https://img.shields.io/badge/MCP-server-0b7f5f)
![Containerlab](https://img.shields.io/badge/Containerlab-API-00c9ff)
![Status](https://img.shields.io/badge/status-unofficial%20community%20project-lightgrey)

Community MCP server for managing Containerlab environments through the official
Containerlab API Server. It lets MCP-capable AI clients inspect, deploy, start,
stop, and destroy labs without exposing the Containerlab host shell. Raw command
execution inside node containers is disabled by default.

> [!WARNING]
>
> This is an unofficial and unsupported community project. It is not affiliated
> with, endorsed by, or maintained by the Containerlab project or any network
> equipment vendor. Some tools create or destroy lab resources. Review proposed
> actions, credentials, topology content, and your organization's AI
> data-handling policies before connecting a lab host to an AI assistant.

## Overview

`containerlab-mcp-server` wraps the official Containerlab HTTPS API and exposes
78 focused MCP tools for lab lifecycle, approved command execution, configuration
artifacts, packet capture, network impairments, topology generation, remote
access, and multi-host network stitching. Once configured, an AI assistant can
answer requests such as:

- "List every Containerlab lab and show node health."
- "Deploy two AOS-CX switches connected on `eth1`."
- "Show the topology YAML for `mixed-cx-ex`."
- "Get the boot logs from node `cx1`."
- "Stop the lab but preserve its dataplane links."
- "Destroy the lab and clean up its generated files."

## Architecture

![Animated Containerlab MCP request flow](docs/containerlab-mcp-flow.svg)

The MCP server runs locally with the AI client. It authenticates to
`clab-api-server`, caches the returned bearer token for up to one hour, and
re-authenticates once when an API request returns HTTP 401.

Safe mode is enabled by default. Read and preview tools execute directly, while
state-changing actions use explicit, durable workflow handles:

```text
create_change_plan(...) -> plan_id
approve_change(plan_id, confirmation="approve") -> approval_id
execute_approved_change(plan_id, approval_id, idempotency_key) -> result
```

Plans, approvals, and execution outcomes are stored in a private SQLite database.
Executed idempotency keys cannot run the same operation twice. API calls emit
redacted JSON audit records with correlation IDs, outcomes, latency, and response
size. Safe mode also rejects path traversal, oversized content, invalid network
parameters, and dangerous topology keys such as `binds`, `exec`, `privileged`,
and `network-mode`.

## Implemented API Server Features

The implementation follows the feature areas published by
[`srl-labs/clab-api-server`](https://github.com/srl-labs/clab-api-server).
These API server capabilities are currently exposed through MCP:

- **Lab Management:** list, inspect, deploy, start, stop, and destroy labs.
- **Node Operations:** start, stop, restart, pause, unpause, execute commands,
  validate command output, and save configurations.
- **SSH Access:** request temporary SSH access, list sessions, and terminate
  sessions.
- **Terminal Sessions:** create, inspect, and terminate constrained SSH,
  shell, and telnet sessions.
- **Topology Tools:** generate CLOS, campus, branch, EVPN-VXLAN, dual-plane AI,
  hub-and-spoke WAN, LACP, VSX, Virtual Chassis cabling, and two-switch previews
  with Mermaid diagrams, connection tables, device inventories, and Draw.io
  XML.
- **Network Tools:** inspect interfaces, apply or reset netem impairments, and
  create or delete multi-host VXLAN tunnels.
- **Packet Capture:** inspect or manage EdgeShark and create Packetflix or
  Wireshark/noVNC capture sessions.
- **Health Monitoring:** check API health, host metrics, Containerlab version,
  and available updates.
- **Logs and Events:** read node logs and collect bounded runtime event
  snapshots.
- **Runtime Images:** list, pull, and delete container images.
- **User Context and Multitenancy:** authenticate as a Linux API user and
  preserve server-side ownership and lab visibility boundaries.
- **Standalone Topology Editing:** list and update topology YAML, annotations,
  startup configurations, and scoped lab files.
- **Custom Node Templates:** list, save, replace, select, and delete TopoViewer
  templates.

Destructive or state-changing actions such as `destroy_lab`, `delete_image`,
`execute_node_command`, `set_link_impairment`, file writes/deletes, and template
replacement are blocked from direct execution in safe mode. Use the approval
workflow above after reviewing the generated action and arguments.

## Tool Categories

### Change Control

| Tool | Description |
| --- | --- |
| `list_change_actions` | List approved workflow actions and their risk levels |
| `create_change_plan` | Validate and store a proposed change without executing it |
| `approve_change` | Record explicit approval for one unexpired plan |
| `execute_approved_change` | Execute an approved plan with an idempotency key |

### Health and Inventory

| Tool | Description |
| --- | --- |
| `health` | Return API server health |
| `health_metrics` | Return API server CPU, memory, and disk metrics |
| `version` | Return the Containerlab version reported by the API server |
| `version_check` | Check whether a newer Containerlab release is available |
| `list_labs` | List labs visible to the authenticated API user |
| `inspect_lab` | Return node and container state for one lab |
| `list_lab_interfaces` | Return interface details for all nodes or one node |

### Topology and Logs

| Tool | Description |
| --- | --- |
| `get_topology_yaml` | Return a deployed lab's topology YAML |
| `get_node_logs` | Return logs using a short node name or full container name |
| `get_node_browser_ports` | Return exposed node ports suitable for browser access |
| `generate_drawio` | Generate draw.io XML for a deployed topology |

Draw.io generation depends on the external `clab-io-draw` image and may fail
for a one-node topology with no links or position data.

### Lab Lifecycle

| Tool | Description |
| --- | --- |
| `deploy_on_disk_lab` | Deploy topology YAML already stored in the API user's lab directory |
| `deploy_topology_content` | Submit and deploy a topology object through the API |
| `start_lab` | Start all stopped nodes in a deployed lab |
| `stop_lab` | Stop all nodes while preserving dataplane links |
| `destroy_lab` | Destroy a lab with optional cleanup and graceful shutdown |

### Node Lifecycle

| Tool | Description |
| --- | --- |
| `start_node` | Start one stopped node |
| `stop_node` | Stop one node while preserving its links |
| `restart_node` | Restart one node while preserving its links |
| `pause_node` | Pause one running node |
| `unpause_node` | Resume one paused node |

### Commands and Configuration

| Tool | Description |
| --- | --- |
| `execute_lab_command` | Execute a native container command on all or filtered nodes |
| `execute_node_command` | Execute a native container command on one resolved node |
| `validate_node_command` | Check exit status and optional expected output |
| `save_lab_config` | Save running configuration for supported node kinds |

The native exec API runs commands in the node container. It does not translate
vendor configuration intent into Aruba CX or Junos CLI syntax. The caller must
provide the command appropriate to that image and confirm mutating commands.

### Runtime Images

| Tool | Description |
| --- | --- |
| `list_images` | List images in the Containerlab host runtime |
| `pull_image` | Pull a public or pre-authorized image reference |
| `delete_image` | Delete an image after explicit operator approval |

Image pull uses the runtime's existing registry authentication. This project
does not collect registry credentials or build vrnetlab images.

### Packet Capture

| Tool | Description |
| --- | --- |
| `get_edgeshark_status` | Return EdgeShark runtime status |
| `install_edgeshark` | Install/start EdgeShark as an API superuser |
| `uninstall_edgeshark` | Remove EdgeShark as an API superuser |
| `build_packetflix_capture` | Build Packetflix URIs for capture targets |
| `create_wireshark_capture_sessions` | Create Wireshark/noVNC capture sessions |
| `get_capture_session_ready` | Check session readiness and URL |
| `terminate_capture_session` | Terminate one capture session |
| `terminate_all_capture_sessions` | Terminate all visible capture sessions |

The v0.5.1 API exposes capture through EdgeShark Packetflix and proxied
Wireshark/noVNC sessions. It does not expose a direct PCAP download operation.

### Link Impairments

| Tool | Description |
| --- | --- |
| `set_link_impairment` | Apply delay, jitter, loss, rate, or corruption |
| `show_link_impairments` | Inspect active netem settings |
| `reset_link_impairment` | Remove impairment from one interface |

### Topology Documents and Files

| Tool | Description |
| --- | --- |
| `list_topology_files` | List editable topology entries |
| `update_topology_yaml` | Replace a lab topology YAML document |
| `get_topology_annotations` | Read TopoViewer annotations |
| `update_topology_annotations` | Replace TopoViewer annotations |
| `get_topology_file` | Read a scoped lab file |
| `put_topology_file` | Write a scoped lab file or startup configuration |
| `put_startup_config` | Write a startup config under `configs/` and return its path |
| `rename_topology_file` | Rename or move a scoped lab file |
| `delete_topology_file` | Delete a scoped lab file |

Startup configuration support uses `put_topology_file` to store the config and
`update_topology_yaml` to reference it from the intended node.

### Events and Generation

| Tool | Description |
| --- | --- |
| `collect_events` | Collect up to 60 seconds of native NDJSON events |
| `generate_clos_topology` | Generate a native CLOS topology without deployment |
| `generate_campus_topology` | Generate a redundant core-distribution-access campus |
| `generate_branch_topology` | Generate a dual-WAN branch with firewall, switch, and clients |
| `generate_evpn_vxlan_fabric` | Generate a leaf-spine fabric with border leaves and hosts |
| `generate_dual_plane_ai_fabric` | Generate isolated A/B fabrics with dual-attached AI hosts |
| `generate_hub_spoke_wan` | Generate a single- or multi-hub routed WAN |
| `generate_three_tier_clos` | Generate a super-spine, spine, and leaf CLOS |
| `generate_lacp_topology` | Generate parallel links intended for one LACP LAG |
| `generate_vsx_topology` | Generate VSX ISL, keepalive, and downstream links |
| `generate_virtual_chassis_topology` | Generate Virtual Chassis VCP cabling |
| `preview_topology` | Preview any topology with a diagram, links, brands, and image versions |

### Custom Node Templates

| Tool | Description |
| --- | --- |
| `list_custom_node_templates` | List the user's TopoViewer templates |
| `save_custom_node_template` | Create or update one template |
| `replace_custom_node_templates` | Replace the full template collection |
| `set_default_custom_node_template` | Select the default template |
| `delete_custom_node_template` | Delete one template |

### Remote Access

| Tool | Description |
| --- | --- |
| `request_ssh_access` | Create temporary external SSH access to one node |
| `list_ssh_sessions` | List temporary SSH sessions visible to the API user |
| `terminate_ssh_session` | Terminate temporary SSH access by allocated port |
| `create_terminal_session` | Create a constrained SSH, shell, or telnet terminal session |
| `get_terminal_session` | Return terminal session metadata and state |
| `terminate_terminal_session` | Terminate a terminal session by ID |

Terminal tools manage session lifecycle and metadata. Interactive terminal data
is transported by the API server's WebSocket stream and is not returned as a
normal MCP tool result.

### Multi-Host Networking

| Tool | Description |
| --- | --- |
| `create_vxlan` | Create a VXLAN tunnel for multi-host dataplane connectivity |
| `delete_vxlan` | Delete VXLAN interfaces matching an approved prefix |

VXLAN operations require an API superuser and matching configuration on the
remote host.

### Topology Helpers

| Tool | Pattern | Deployment behavior |
| --- | --- | --- |
| `generate_clos_topology` | Multi-tier CLOS or leaf-spine fabric | Generate only |
| `generate_campus_topology` | Core, distribution, and dual-homed access | Preview only |
| `generate_branch_topology` | WAN routers, firewall, access switch, and clients | Preview only |
| `generate_evpn_vxlan_fabric` | Spines, leaves, border leaves, and server hosts | Preview only |
| `generate_dual_plane_ai_fabric` | Isolated A/B fabrics and dual-attached AI hosts | Preview only |
| `generate_hub_spoke_wan` | One or more hubs connected to every spoke | Preview only |
| `generate_three_tier_clos` | Super-spines, spines, and leaves | Preview only |
| `generate_lacp_topology` | Parallel links between two LAG peers | Preview only |
| `generate_vsx_topology` | VSX peers, ISL, keepalive, and downstream devices | Preview only |
| `generate_virtual_chassis_topology` | Chain or ring of VCP-connected members | Preview only |
| `make_two_switch_aoscx_topology` | Two linked AOS-CX switches | Preview only |
| `preview_topology` | Any valid topology object | Preview only |
| `deploy_topology_content` | Arbitrary topology object | Deploy submitted topology |
| `deploy_on_disk_lab` | Topology YAML already stored on the API host | Deploy stored topology |

`generate_clos_topology` accepts tier definitions, node kinds, runtime images,
management addressing, and naming prefixes. The MCP wrapper always sends
`deploy=false`; pass its topology object to `preview_topology` before any
containers are created.

The preview helpers allocate unique `ethN` interfaces and set node groups for
visualization. They are preview-only and never contact the Containerlab API.
Each result contains:

- `diagram`: a compact Mermaid network diagram.
- `connection_table`: both endpoints and interfaces for every link.
- `link_summary`: physical-link counts by purpose when the helper understands
  LACP, VSX, or Virtual Chassis intent.
- `devices`: node, group, detected brand, kind, full image reference, and image
  version.
- `topology`: the exact object that can be submitted after review.

After confirming the design, host capacity, and image availability, call
`deploy_topology_content` with the returned `topology` field. This explicit
second call is the deployment boundary.

Image references are selected by the MCP user for each node role. Use only
images that are installed, licensed, compatible, and already validated in the
target Containerlab environment. The diagrams below illustrate topology roles;
they do not require a particular image version.

This MCP server has been tested only with Aruba AOS-CX and Juniper virtual
devices. Other Containerlab kinds may work through the native API wrappers, but
they have not been validated by this project.

These helpers build nodes and links only. They do not generate VLAN, OSPF, BGP,
EVPN-VXLAN, LACP, VSX, Virtual Chassis, firewall, QoS, PFC, ECN, or RoCE
configuration. Apply those features separately with startup configurations or
supported node command tools.

The MCP client can still compose arbitrary patterns such as a ring, triangle,
full mesh, or linear chain. Pass the resulting object to `preview_topology`,
review its diagram and tables, and then submit its `topology` field with
`deploy_topology_content`.

#### Campus

Example prompt:

```text
Create a campus lab called campus1 with one core switch, one distribution
switch, and two access switches. Do not deploy it. Show the network diagram,
connection table, device brands, and image versions for review.
```

Example output:

**Network diagram**

```mermaid
flowchart TB
  C1["core1"] --- D1["dist1"]
  D1 --- A1["access1"]
  D1 --- A2["access2"]
```

**Connection table**

| Node A | Interface A | Node B | Interface B |
| --- | --- | --- | --- |
| core1 | eth1 | dist1 | eth1 |
| dist1 | eth2 | access1 | eth1 |
| dist1 | eth3 | access2 | eth1 |

**Device inventory**

| Node | Brand | Kind | Image version |
| --- | --- | --- | --- |
| core1 | Aruba | `aruba_aoscx` | `10.18.0001` |
| dist1 | Aruba | `aruba_aoscx` | `10.18.0001` |
| access1 | Juniper | `juniper_vjunosswitch` | `26.2R1.7-nativefix` |
| access2 | Juniper | `juniper_vjunosswitch` | `26.2R1.7-nativefix` |

#### Branch

Example prompt:

```text
Create a branch lab called branch1 with one WAN router, one firewall, one access
switch, and one Linux client. Do not deploy it. Show the network diagram,
connection table, device brands, and image versions for review.
```

Example output:

**Network diagram**

```mermaid
flowchart TB
  W1["wan1"] --- F["firewall1"]
  F --- S["access1"]
  S --- C1["client1"]
```

**Connection table**

| Node A | Interface A | Node B | Interface B |
| --- | --- | --- | --- |
| wan1 | eth1 | firewall1 | eth1 |
| firewall1 | eth2 | access1 | eth1 |
| access1 | eth2 | client1 | eth1 |

**Device inventory**

| Node | Brand | Kind | Image version |
| --- | --- | --- | --- |
| wan1 | Juniper | `juniper_vjunosrouter` | `26.2R1.7-nativefix` |
| firewall1 | Juniper | `juniper_vsrx` | `26.2R1.7` |
| access1 | Aruba | `aruba_aoscx` | `10.18.0001` |
| client1 | Linux | `linux` | `latest` |

#### EVPN-VXLAN Fabric

Example prompt:

```text
Create an EVPN-VXLAN fabric called dc1 with two spine switches, two leaf
switches, no border leaves, and one Linux host on each leaf. Do not deploy it.
Show the network diagram, connection table, device brands, and image versions.
```

Example output:

**Network diagram**

```mermaid
flowchart TB
  S1["spine1"] --- L1["leaf1"]
  S1 --- L2["leaf2"]
  S2["spine2"] --- L1
  S2 --- L2
  L1 --- H1["host1-1"]
  L2 --- H2["host2-1"]
```

**Connection table**

| Node A | Interface A | Node B | Interface B |
| --- | --- | --- | --- |
| spine1 | eth1 | leaf1 | eth1 |
| spine1 | eth2 | leaf2 | eth1 |
| spine2 | eth1 | leaf1 | eth2 |
| spine2 | eth2 | leaf2 | eth2 |
| leaf1 | eth3 | host1-1 | eth1 |
| leaf2 | eth3 | host2-1 | eth1 |

**Device inventory**

| Node | Brand | Kind | Image version |
| --- | --- | --- | --- |
| spine1 | Aruba | `aruba_aoscx` | `10.18.0001` |
| spine2 | Aruba | `aruba_aoscx` | `10.18.0001` |
| leaf1 | Juniper | `juniper_vjunosswitch` | `26.2R1.7-nativefix` |
| leaf2 | Juniper | `juniper_vjunosswitch` | `26.2R1.7-nativefix` |
| host1-1 | Linux | `linux` | `latest` |
| host2-1 | Linux | `linux` | `latest` |

#### Dual-Plane AI Fabric

Example prompt:

```text
Create a dual-plane AI fabric called ai1 with one spine and one leaf in each
plane, plus two hosts connected to both planes. Do not deploy it. Show the
network diagram, connection table, device brands, and image versions.
```

Example output:

**Network diagram**

```mermaid
flowchart TB
  SA["spine-a1"] --- LA["leaf-a1"]
  SB["spine-b1"] --- LB["leaf-b1"]
  LA --- H1["ai-host1"]
  LB --- H1
  LA --- H2["ai-host2"]
  LB --- H2
```

**Connection table**

| Node A | Interface A | Node B | Interface B |
| --- | --- | --- | --- |
| spine-a1 | eth1 | leaf-a1 | eth1 |
| spine-b1 | eth1 | leaf-b1 | eth1 |
| leaf-a1 | eth2 | ai-host1 | eth1 |
| leaf-b1 | eth2 | ai-host1 | eth2 |
| leaf-a1 | eth3 | ai-host2 | eth1 |
| leaf-b1 | eth3 | ai-host2 | eth2 |

**Device inventory**

| Node | Brand | Kind | Image version |
| --- | --- | --- | --- |
| spine-a1 | Aruba | `aruba_aoscx` | `10.18.0001` |
| leaf-a1 | Aruba | `aruba_aoscx` | `10.18.0001` |
| spine-b1 | Aruba | `aruba_aoscx` | `10.18.0001` |
| leaf-b1 | Aruba | `aruba_aoscx` | `10.18.0001` |
| ai-host1 | Linux | `linux` | `latest` |
| ai-host2 | Linux | `linux` | `latest` |

#### Hub-and-Spoke WAN

Example prompt:

```text
Create a hub-and-spoke WAN called wan1 with one hub router and three spoke
routers. Do not deploy it. Show the network diagram, connection table, device
brands, and image versions for review.
```

Example output:

**Network diagram**

```mermaid
flowchart TB
  H1["hub1"] --- S1["spoke1"]
  H1 --- S2["spoke2"]
  H1 --- S3["spoke3"]
```

**Connection table**

| Node A | Interface A | Node B | Interface B |
| --- | --- | --- | --- |
| hub1 | eth1 | spoke1 | eth1 |
| hub1 | eth2 | spoke2 | eth1 |
| hub1 | eth3 | spoke3 | eth1 |

**Device inventory**

| Node | Brand | Kind | Image version |
| --- | --- | --- | --- |
| hub1 | Juniper | `juniper_vjunosrouter` | `26.2R1.7-nativefix` |
| spoke1 | Juniper | `juniper_vjunosrouter` | `26.2R1.7-nativefix` |
| spoke2 | Juniper | `juniper_vjunosrouter` | `26.2R1.7-nativefix` |
| spoke3 | Juniper | `juniper_vjunosrouter` | `26.2R1.7-nativefix` |

#### Three-Tier CLOS

Example prompt:

```text
Create a three-tier CLOS called fabric3 with one super-spine, two spine
switches, and two leaf switches. Do not deploy it. Show the network diagram,
connection table, device brands, and image versions for review.
```

Example output:

**Network diagram**

```mermaid
flowchart TB
  SS1["super-spine1"] --- S1["spine1"]
  SS1 --- S2["spine2"]
  S1 --- L1["leaf1"]
  S1 --- L2["leaf2"]
  S2 --- L1
  S2 --- L2
```

**Connection table**

| Node A | Interface A | Node B | Interface B |
| --- | --- | --- | --- |
| super-spine1 | eth1 | spine1 | eth1 |
| super-spine1 | eth2 | spine2 | eth1 |
| spine1 | eth2 | leaf1 | eth1 |
| spine1 | eth3 | leaf2 | eth1 |
| spine2 | eth2 | leaf1 | eth2 |
| spine2 | eth3 | leaf2 | eth2 |

**Device inventory**

| Node | Brand | Kind | Image version |
| --- | --- | --- | --- |
| super-spine1 | Aruba | `aruba_aoscx` | `10.18.0001` |
| spine1 | Aruba | `aruba_aoscx` | `10.18.0001` |
| spine2 | Aruba | `aruba_aoscx` | `10.18.0001` |
| leaf1 | Juniper | `juniper_vjunosswitch` | `26.2R1.7-nativefix` |
| leaf2 | Juniper | `juniper_vjunosswitch` | `26.2R1.7-nativefix` |

#### LACP Links

Example prompt:

```text
Create two switches connected by a two-member LACP bundle. Create physical
links only and do not configure or deploy the switches. Show the preview.
```

Example output:

```mermaid
flowchart TB
  D1["device1"] --- D2["device2"]
  D1 --- D2
```

Link summary: **2 `lacp-member` links**

| Node A | Interface A | Node B | Interface B | Purpose |
| --- | --- | --- | --- | --- |
| device1 | eth1 | device2 | eth1 | `lacp-member` |
| device1 | eth2 | device2 | eth2 | `lacp-member` |

| Node | Brand | Kind | Image version |
| --- | --- | --- | --- |
| device1 | Aruba | `aruba_aoscx` | `10.18.0001` |
| device2 | Juniper | `juniper_vjunosswitch` | `26.2R1.7-nativefix` |

#### Aruba VSX Links

Example prompt:

```text
Create an Aruba VSX cabling preview called vsx1 with two ISL member links, one
direct keepalive link, and one downstream switch connected once to each VSX
peer. Do not configure or deploy the devices.
```

Example output:

```mermaid
flowchart TB
  V1["vsx1"] --- V2["vsx2"]
  V1 --- V2
  V1 --- V2
  V1 --- A1["access1"]
  V2 --- A1
```

Link summary: **2 `vsx-isl` + 1 `vsx-keepalive` + 2
`downstream-lag-member` = 5 physical links**

| Node A | Interface A | Node B | Interface B | Purpose |
| --- | --- | --- | --- | --- |
| vsx1 | eth1 | vsx2 | eth1 | `vsx-isl` |
| vsx1 | eth2 | vsx2 | eth2 | `vsx-isl` |
| vsx1 | eth3 | vsx2 | eth3 | `vsx-keepalive` |
| vsx1 | eth4 | access1 | eth1 | `downstream-lag-member` |
| vsx2 | eth4 | access1 | eth2 | `downstream-lag-member` |

| Node | Brand | Kind | Image version |
| --- | --- | --- | --- |
| vsx1 | Aruba | `aruba_aoscx` | `10.18.0001` |
| vsx2 | Aruba | `aruba_aoscx` | `10.18.0001` |
| access1 | Juniper | `juniper_vjunosswitch` | `26.2R1.7-nativefix` |

Set `keepalive_link_count=0` when the keepalive uses an existing routed path.

#### Juniper Virtual Chassis Cabling

Example prompt:

```text
Create a three-member Juniper Virtual Chassis cabling preview called vc1 in a
ring, using one VCP link per adjacency. Do not configure or deploy it.
```

Example output:

```mermaid
flowchart TB
  M1["member1"] --- M2["member2"]
  M2 --- M3["member3"]
  M3 --- M1
```

Link summary: **3 `virtual-chassis-port` links**

| Node A | Interface A | Node B | Interface B | Purpose |
| --- | --- | --- | --- | --- |
| member1 | eth1 | member2 | eth1 | `virtual-chassis-port` |
| member2 | eth2 | member3 | eth1 | `virtual-chassis-port` |
| member3 | eth2 | member1 | eth2 | `virtual-chassis-port` |

| Node | Brand | Kind | Image version |
| --- | --- | --- | --- |
| member1 | Juniper | `juniper_vjunosswitch` | `26.2R1.7-nativefix` |
| member2 | Juniper | `juniper_vjunosswitch` | `26.2R1.7-nativefix` |
| member3 | Juniper | `juniper_vjunosswitch` | `26.2R1.7-nativefix` |

This helper previews cabling only. Juniper vJunos-switch does not support
forming a Virtual Chassis.

Example topology requests:

```text
Generate a CLOS topology called fabric1 with two AOS-CX spines and four
vJunos-switch leaves. Do not deploy it.

Generate a campus topology called campus1 with one core, one distribution, and
two access switches. Show the network diagram, connection table, device brand,
and image version. Do not deploy it.

Generate a branch called branch1 with one WAN router, one vSRX firewall, one CX
access switch, and one Linux client. Show the complete preview for review.

Generate an EVPN-VXLAN-ready fabric called dc1 with two spines, four leaves,
two border leaves, and one host per leaf. Do not deploy it.

Generate a dual-plane AI fabric called ai1 with two spines and four leaves per
plane plus eight dual-attached hosts. Do not deploy it.

Generate a redundant WAN called wan1 with two hubs and six spokes. Show the
topology before deployment.

Generate a three-tier CLOS called fabric3 with two super-spines, four spines,
and eight leaves. Do not deploy it.

Generate a four-node AOS-CX ring using eth1 and eth2. Show the topology object
for review before deployment.

Create a triangle with one AOS-CX switch, one vJunos-switch, and one Linux
client. Connect every node to the other two nodes.

Create a linear lab with four routers and show the topology before deployment.
```

## Example Prompts

Try these in an MCP-capable AI client:

```text
Check the Containerlab API health and version.
Check whether a newer Containerlab version is available.
List all labs and summarize unhealthy nodes.
Inspect the mixed-cx-ex lab.
Show every interface in mixed-cx-ex.
Show the topology YAML for mixed-cx-ex.
Get the last logs from node ex1 in mixed-cx-ex.
Generate a horizontal draw.io diagram for mixed-cx-ex.
Restart only node ex1 and wait until it becomes healthy.
List all runtime images on the lab host.
Pull ghcr.io/srl-labs/alpine:latest.
Create temporary SSH access to cx1 for 30 minutes.

Generate a two-switch AOS-CX topology called cx-demo using eth1. Show its
diagram, connection table, brands, and image versions without deploying it.
After I approve the preview, deploy its topology object.
Deploy the topology stored at /home/lab/topologies/demo.clab.yml.
Stop cx-demo while preserving its links.
Start cx-demo and verify every node becomes healthy.
Destroy cx-demo and clean up its generated lab directory.

Create a VXLAN with VNI 100 from cx1-eth1 to remote host 192.0.2.20.
```

## Prerequisites

### Containerlab Host

- A Linux host with Containerlab installed and working independently of this
  MCP server.
- A supported container runtime, normally Docker, with sufficient CPU, memory,
  disk space, and network permissions for the intended labs.
- KVM support when using VM-based images such as vrnetlab appliances. If the
  Containerlab host is itself a virtual machine, nested virtualization must
  also be enabled.
- The official
  [Containerlab API Server](https://containerlab.dev/manual/api-server/)
  installed, configured, and reachable over HTTPS from the MCP client host.
- A Containerlab API user with permission to access the required labs and any
  privileged API operations that will be used.

### Network Images

- Every image referenced by a topology must already exist in the Containerlab
  host's runtime or be available from a registry that the runtime can access.
- Private vendor images must be obtained under the appropriate vendor license,
  converted when required, and imported into the runtime before MCP deployment.
- Each image must be compatible with the installed Containerlab and vrnetlab
  versions, the host CPU architecture, and the selected Containerlab node kind.
  Check the
  [vrnetlab compatibility matrix](https://containerlab.dev/manual/vrnetlab/#compatibility-matrix)
  when selecting versions.
- VM-based images must be able to access `/dev/kvm` and fit within the host's
  available CPU and memory.
- Validate each image with a small direct Containerlab deployment first. It
  should boot, become healthy, and accept its expected management login before
  using it in an MCP-generated topology.

> [!IMPORTANT]
>
> This MCP server controls an existing, working Containerlab environment. It
> does not convert network operating system images, enable virtualization,
> install vendor licenses, or make an incompatible image bootable. If an image
> cannot run in Containerlab directly, deploying the same image through MCP
> will also fail.

### MCP Client Host

- Python 3.11 or newer.
- [`uv`](https://docs.astral.sh/uv/).
- An MCP-capable client such as Codex, Claude Desktop, Claude Code, or Visual
  Studio Code with GitHub Copilot.
- Network and certificate access to the configured `CLAB_API_URL`.

## Setup

Clone the repository and install its dependencies:

```bash
git clone https://github.com/teze3808/containerlab-mcp-server.git
cd containerlab-mcp-server
uv sync
```

Create a local environment file:

```bash
cp .env.example .env
```

Edit `.env` with your API server details:

```env
CLAB_API_URL=https://containerlab-host.example:8090
CLAB_USERNAME=your-username
CLAB_PASSWORD=your-password
CLAB_VERIFY_TLS=true
CLAB_TIMEOUT=60
CLAB_SAFE_MODE=true
CLAB_ALLOW_RAW_COMMANDS=false
CLAB_ALLOW_SHELL_TERMINAL=false
CLAB_MAX_RESPONSE_BYTES=1000000
CLAB_APPROVAL_TTL=900
```

Do not commit `.env`. TLS verification is enabled by default. For a private lab
using a self-signed certificate, install its CA certificate on the MCP client
host instead of disabling verification where possible.

## Run Locally

```bash
uv run containerlab-mcp
```

Run the test suite:

```bash
uv run pytest
```

## MCP Client Configuration

### Codex

Add this to the Codex MCP configuration after replacing the placeholders:

```toml
[mcp_servers.containerlab]
command = "uv"
args = ["run", "--directory", "/path/to/containerlab-mcp-server", "containerlab-mcp"]
startup_timeout_sec = 30

[mcp_servers.containerlab.env]
CLAB_API_URL = "https://containerlab-host.example:8090"
CLAB_USERNAME = "your-username"
CLAB_PASSWORD = "your-password"
CLAB_VERIFY_TLS = "true"
CLAB_TIMEOUT = "60"
CLAB_SAFE_MODE = "true"
```

Restart Codex after editing the configuration.

### Hermes Agent

Install [Hermes Agent](https://github.com/NousResearch/hermes-agent) on Linux,
macOS, or WSL2 using its official installer. Review downloaded scripts first
when required by your security policy.

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
source ~/.zshrc  # use ~/.bashrc when running Bash
hermes setup
hermes doctor
```

For native Windows, run the official installer in PowerShell:

```powershell
iex (irm https://hermes-agent.nousresearch.com/install.ps1)
hermes setup
hermes doctor
```

The standard installer includes MCP support. For a minimal or manual Hermes
installation, add it separately:

```bash
cd ~/.hermes/hermes-agent
uv pip install -e ".[mcp]"
```

Complete this project's [Setup](#setup) first. Then store the Containerlab API
credentials in `~/.hermes/.env`:

```env
CLAB_API_URL=https://containerlab-host.example:8090
CLAB_USERNAME=your-username
CLAB_PASSWORD=your-password
CLAB_VERIFY_TLS=true
CLAB_TIMEOUT=60
CLAB_SAFE_MODE=true
```

Protect the credentials file:

```bash
chmod 600 ~/.hermes/.env
```

Add the stdio server to `~/.hermes/config.yaml`, replacing the project path.
If `mcp_servers` already exists, merge only the `containerlab` entry beneath
it instead of creating a second `mcp_servers` key.

```yaml
mcp_servers:
  containerlab:
    command: "uv"
    args:
      - "run"
      - "--directory"
      - "/path/to/containerlab-mcp-server"
      - "containerlab-mcp"
    env:
      CLAB_API_URL: "${CLAB_API_URL}"
      CLAB_USERNAME: "${CLAB_USERNAME}"
      CLAB_PASSWORD: "${CLAB_PASSWORD}"
      CLAB_VERIFY_TLS: "${CLAB_VERIFY_TLS}"
      CLAB_TIMEOUT: "${CLAB_TIMEOUT}"
    enabled: true
    timeout: 120
    connect_timeout: 60
```

Hermes resolves `${VAR}` references from `~/.hermes/.env`. Start Hermes and
verify that it discovers the Containerlab tools:

```bash
hermes mcp list
hermes chat
```

After changing MCP configuration in a running session, enter `/reload-mcp`.
Try this prompt:

```text
Check the Containerlab API health, list the available runtime images, and show
all labs. Do not deploy, stop, or destroy anything.
```

See the official
[Hermes MCP documentation](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/mcp.md)
for tool filtering, timeouts, and troubleshooting.

### Claude Desktop

Add this server entry to the Claude Desktop MCP configuration:

```json
{
  "mcpServers": {
    "containerlab": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/path/to/containerlab-mcp-server",
        "containerlab-mcp"
      ],
      "env": {
        "CLAB_API_URL": "https://containerlab-host.example:8090",
        "CLAB_USERNAME": "your-username",
        "CLAB_PASSWORD": "your-password",
        "CLAB_VERIFY_TLS": "true",
        "CLAB_SAFE_MODE": "true",
        "CLAB_TIMEOUT": "60"
      }
    }
  }
}
```

Restart Claude Desktop after editing its configuration.

### Claude Code

Claude Code can add the stdio MCP server from JSON:

```bash
claude mcp add-json containerlab '{
  "type": "stdio",
  "command": "uv",
  "args": ["run", "--directory", "/path/to/containerlab-mcp-server", "containerlab-mcp"],
  "env": {
    "CLAB_API_URL": "https://containerlab-host.example:8090",
    "CLAB_USERNAME": "your-username",
    "CLAB_PASSWORD": "your-password",
    "CLAB_VERIFY_TLS": "true",
    "CLAB_SAFE_MODE": "true",
    "CLAB_TIMEOUT": "60"
  }
}'
```

### Visual Studio Code with GitHub Copilot

VS Code stores MCP configuration in `.vscode/mcp.json` or the user profile:

```json
{
  "servers": {
    "containerlab": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/path/to/containerlab-mcp-server",
        "containerlab-mcp"
      ],
      "env": {
        "CLAB_API_URL": "https://containerlab-host.example:8090",
        "CLAB_USERNAME": "your-username",
        "CLAB_PASSWORD": "your-password",
        "CLAB_VERIFY_TLS": "true",
        "CLAB_SAFE_MODE": "true",
        "CLAB_TIMEOUT": "60"
      }
    }
  }
}
```

Save the file and reload or restart the MCP server in VS Code.

### Generic Stdio MCP Client

Run this command from the project directory:

```bash
uv run containerlab-mcp
```

Pass the `CLAB_*` environment variables through the MCP client's server
configuration.

## Notes

- `get_node_logs` accepts `cx1` or a full name such as
  `clab-aoscx-two-switch-cx1`.
- Node lifecycle, browser-port, SSH, and terminal tools also accept short node
  names and resolve them to full container names.
- Labs returned by the API are limited by the authenticated user's access.
- A submitted topology must reference images already available to Docker on the
  Containerlab host, or images that Docker is authorized to pull.
- `stop_lab` preserves the deployed lab and dataplane links; `destroy_lab`
  removes the deployment.
- `delete_image`, `destroy_lab`, and `delete_vxlan` are destructive operations.
- Safe mode is enabled by default and blocks direct state-changing tool calls.
  Use `list_change_actions`, `create_change_plan`, `approve_change`, and
  `execute_approved_change` for controlled execution.
- `CLAB_SAFE_MODE=false` restores direct write calls for isolated personal labs.
  This bypasses the durable approval workflow and is not recommended for shared
  environments.
- Raw node-container commands additionally require
  `CLAB_ALLOW_RAW_COMMANDS=true`. Interactive `shell` terminal sessions require
  `CLAB_ALLOW_SHELL_TERMINAL=true`.
- The default approval database and audit log are stored under
  `~/.local/state/containerlab-mcp/` with owner-only permissions. Override them
  with `CLAB_APPROVAL_DB` and `CLAB_AUDIT_LOG`.
- Listing all users' SSH sessions and managing VXLAN tunnels may require an API
  superuser.
- Self-signed API certificates are common in labs. Prefer a trusted certificate
  or install the private CA instead of disabling TLS verification.
- This project is intended for lab, demo, validation, and operational-assist
  workflows. Apply appropriate review and change control before adapting it for
  shared environments.

## Documentation

- [Containerlab API Server](https://containerlab.dev/manual/api-server/)
- [Containerlab documentation](https://containerlab.dev/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Security policy](docs/SECURITY.md)
- [Operations runbook](docs/RUNBOOK.md)
- [Claude Code MCP documentation](https://code.claude.com/docs/en/mcp)
- [VS Code MCP configuration reference](https://code.visualstudio.com/docs/copilot/reference/mcp-configuration)
