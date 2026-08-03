# Operations Runbook

## Health Checks

1. Run `health` and verify that the Containerlab API responds successfully.
2. Run `health_metrics` and review CPU, memory, disk usage, and API uptime.
3. Run `list_labs` and inspect unexpected or unhealthy nodes.
4. Review the MCP audit log for recent errors and authorization decisions.

Default state files:

```text
~/.local/state/containerlab-mcp/audit.jsonl
~/.local/state/containerlab-mcp/approvals.sqlite3
```

## Common Failures

### TLS verification failure

Install the Containerlab API CA certificate on the MCP client host and keep
`CLAB_VERIFY_TLS=true`. Confirm that `CLAB_API_URL` uses the certificate's valid
hostname or IP address.

### Authentication failure

Confirm that the configured Linux API user is active and belongs to the required
Containerlab API authorization group. Rotate the password outside the repository
and restart the MCP host so it receives the updated environment.

### Approval expired

Create a new plan, review its normalized arguments, approve it, and execute it
before `CLAB_APPROVAL_TTL` expires. Do not edit the SQLite database manually.

### Duplicate execution

Reuse the same idempotency key only when retrying the same approved request. A
successful replay returns the stored result without calling Containerlab again.
Use a new plan and key for a genuinely new action.

### Response exceeded limit

Narrow the request, reduce log output, or carefully increase
`CLAB_MAX_RESPONSE_BYTES`. Avoid returning complete large logs to the model.

## Recovery

- A failed write is recorded against its idempotency key. Inspect the downstream
  state before creating a replacement plan.
- Containerlab deployment rollback is normally `destroy_lab` with an approved
  change plan. Save required device configurations before destruction.
- Back up the approval database only when durable change history is required.
  Audit records contain operational metadata and should follow the lab's data
  retention policy.

## Upgrade Verification

1. Review dependency and Containerlab API release notes.
2. Run `uv sync --locked` and `uv run pytest`.
3. Test with MCP Inspector and at least one supported host.
4. Verify read tools, approval flow, idempotent replay, TLS, and audit output.
5. Keep the previous package version and lockfile available for rollback.
