# Security Policy

## Intended Use

This project is designed for trusted lab, demonstration, validation, and
operational-assist environments. It is not a production network controller and
must not be connected to production infrastructure without an independent
security and operations review.

## Safe Defaults

- `CLAB_SAFE_MODE=true` blocks direct state-changing tools.
- Changes use plan, approval, and idempotent execution handles stored in SQLite.
- `CLAB_VERIFY_TLS=true` verifies the Containerlab API certificate.
- Raw node-container commands and interactive shell terminals are disabled.
- Topology deployment rejects host binds, exec hooks, privileged mode, custom
  runtimes, host networking, stages, and sysctls.
- Lab names, node names, relative paths, image references, VXLAN values, netem
  values, content size, and response size are validated.
- API errors are bounded and common credential fields are redacted.
- Audit and approval files are created with owner-only permissions.

## Privileged Capabilities

Raw command execution requires both an approved change and
`CLAB_ALLOW_RAW_COMMANDS=true`. Interactive `shell` terminal sessions require
`CLAB_ALLOW_SHELL_TERMINAL=true`. Keep both disabled unless a trusted operator
needs them in an isolated lab.

Setting `CLAB_SAFE_MODE=false` allows direct state-changing calls and bypasses
the durable approval workflow. Do not use this setting in shared environments.

## Credentials

Use a dedicated, least-privileged Containerlab API account. Provide credentials
at runtime through the MCP host environment or an approved secret manager.
Never commit credentials, bearer tokens, private keys, or `.env` files.

Install the private CA certificate when the API server uses an internal PKI.
Disabling TLS verification is only appropriate for a fully trusted, isolated
test network where interception risk has been accepted.

## Reporting

Do not open a public issue containing credentials, private topology data, image
licenses, device configuration, or exploit details. Contact the repository
owner privately before publishing a vulnerability.
