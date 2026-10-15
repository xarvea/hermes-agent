# Hermes Agent integration notes

The upstream template targets OpenClaw, not Hermes Agent. This directory is therefore an isolated vendor/reference snapshot until an adapter is implemented and tested.

## Boundary

- Do not load `openclaw_template/workspace/AGENTS.md`, `SOUL.md`, or `BOOTSTRAP.md` as Hermes Agent's root instructions.
- Do not overwrite root identity, startup, provider, tool, or security configuration.
- The upstream bootstrap asks the agent to follow strict first-message/login behavior. That behavior is OpenClaw-template-specific and must not be adopted implicitly.
- The upstream setup script installs a third-party package through `npx`; audit package provenance and script effects before execution.

## Suggested phased integration

1. **Inventory:** install OnchainOS in a disposable Linux user/container; record CLI version, skill files, and exact command schemas.
2. **Adapter:** design a Hermes-compatible tool/MCP adapter with strict argument schemas, timeouts, bounded output, and no shell interpolation of user-controlled strings.
3. **Policy:** require read-only research by default; expose transaction construction/execution only behind explicit authorization and pre-trade risk review.
4. **Secrets:** retrieve OKX credentials from environment/secret storage only; redact values in logs and tool output.
5. **Tests:** test missing CLI, bad credentials, timeout, malformed JSON, API rate limiting, malicious token metadata, failed quote/simulation, and user rejection.
6. **Rollout:** start with read-only operations, monitor errors and latency, then separately approve execution capabilities.

## Security checks before production

- Pin and verify installer/package versions where supported; avoid unattended `npx -y` in production bootstrap.
- Do not run the installer as root.
- Keep wallet auth and credentials out of logs, traces, crash reports, shell history, and Git.
- Apply network egress allowlists, request deadlines, output size limits, and per-tool rate limits.
- Confirm the actual guarantees of the wallet custody / TEE and MEV-protection architecture from current OKX documentation; do not treat marketing statements as a security audit.
- Validate chain/network and token contract before signing or broadcasting any transaction.

## Upstream

https://github.com/okx/onchainos-skills/tree/main/openclaw_template
