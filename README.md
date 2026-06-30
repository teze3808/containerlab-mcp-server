# Containerlab MCP Server

Small MCP server that wraps the official Containerlab API Server over HTTPS.

It targets the official Containerlab API Server systemd service.

## Setup

```bash
cd /Users/vincent/Documents/Containerlab/containerlab-mcp-server
uv sync
```

Create a local environment file if you want shell-friendly defaults:

```bash
cp .env.example .env
```

Required runtime variables:

```bash
export CLAB_API_URL="https://containerlab-host.example:8090"
export CLAB_USERNAME="se"
export CLAB_PASSWORD='your-password'
export CLAB_VERIFY_TLS="false"
```

## Run

```bash
uv run containerlab-mcp
```

For Codex, add an MCP server entry similar to:

```toml
[mcp_servers.containerlab]
command = "uv"
args = ["run", "--directory", "/Users/vincent/Documents/Containerlab/containerlab-mcp-server", "containerlab-mcp"]
startup_timeout_sec = 30

[mcp_servers.containerlab.env]
CLAB_API_URL = "https://containerlab-host.example:8090"
CLAB_USERNAME = "se"
CLAB_PASSWORD = "REPLACE_ME"
CLAB_VERIFY_TLS = "false"
```

## Tools

Read-only:

- `health`
- `version`
- `list_labs`
- `inspect_lab`
- `get_topology_yaml`
- `get_node_logs`
- `health_metrics`

Operational:

- `start_lab`
- `stop_lab`
- `deploy_on_disk_lab`
- `deploy_topology_content`
- `destroy_lab`

Helpers:

- `make_two_switch_aoscx_topology`

## Notes

- `get_node_logs` accepts either a short node name such as `cx1` or a full container name such as `clab-aoscx-two-switch-cx1`.
- Destructive tools are intentionally explicit. Avoid adding a generic shell execution tool.
- TLS verification defaults to `false` because the current lab API server uses an automatically generated certificate.
