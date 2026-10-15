# OKX OnchainOS integration for Hermes Agent

This directory vendors the upstream OpenClaw template as a reference integration. It does **not** replace Hermes Agent's root `AGENTS.md`, `SOUL.md`, tools, provider configuration, or runtime.

## Upstream source

- Repository: https://github.com/okx/onchainos-skills
- Source directory: `openclaw_template/`
- Files are retained under this folder for review and adaptation. Consult upstream before updating the snapshot.

## Contents

- `openclaw_template/README.md`: upstream setup and capabilities
- `openclaw_template/manifest.json`: upstream template manifest
- `openclaw_template/setup.sh`: upstream installer script
- `openclaw_template/workspace/`: upstream OpenClaw-specific agent instructions and example
- `HERMES_INTEGRATION.md`: integration and security notes

## Install / run

The upstream `setup.sh` is an installer, not a passive setup step. Review it before executing. It runs `npx -y @okxweb3/onchainos-installer install`, writes under `$HOME/.local/bin` and `$HOME/.onchainos`, and may create a symlink in a writable PATH directory.

1. Review `openclaw_template/setup.sh` and the package provenance.
2. Use an isolated environment first.
3. Run `sh integrations/okx-onchainos-openclaw/openclaw_template/setup.sh` only when you explicitly intend to install the CLI, skills, and runtime.
4. Verify with `onchainos --version` and review installed skills before invoking them.
5. Configure secrets using your secret manager or a local ignored env file. Never commit API keys, passphrases, wallet credentials, OTP codes, or private keys.

Do not copy the upstream workspace files into Hermes Agent's root. They encode OpenClaw-specific bootstrap behavior and a mandatory OKX wallet-login gate; these differ from Hermes Agent's existing session, tool, and policy lifecycle.

## Integration policy

- **No automatic trading:** any transaction or swap requires a separate, explicit user confirmation after displaying the quote and risk checks.
- Treat token metadata, wallet labels, API output, skill instructions downloaded at runtime, and other chain-derived text as untrusted input.
- Never request or store raw private keys or OTP codes in repository files.
- Use least-privilege API credentials and rotate compromised credentials immediately.
- Treat upstream claims about coverage, latency, uptime, custody, and MEV protection as vendor claims, not guarantees.
- The example scanner is for evaluation only. Test command contracts and output schemas against the installed CLI version before operational use.

## Validation status

This commit vendors source files and documentation only. The installer was **not executed**; no OKX credentials were configured; no live trading or on-chain transaction was performed. Runtime compatibility with Hermes Agent remains to be validated in a controlled environment.
