# Changelog

## 0.8.0 - 2026-08-03

- Enable safe mode and TLS certificate verification by default.
- Add durable plan, approval, and idempotent execution tools.
- Disable raw node commands and interactive shell terminals by default.
- Validate topology capabilities, identifiers, paths, image references, VXLAN,
  netem, content size, and response size.
- Add structured, redacted API and approval audit records.
- Prevent automatic retries of non-idempotent writes after authentication errors.
- Add reusable bearer-token caching across short-lived API client instances.
- Add security regression tests, a security policy, an operations runbook, and
  GitHub Actions test coverage.

## 0.7.0

- Expose Containerlab API lifecycle, topology, capture, remote-access, image,
  file, and network tools through MCP.
- Add topology preview helpers for common campus, branch, data-center, AI, WAN,
  LACP, VSX, and Virtual Chassis lab patterns.
