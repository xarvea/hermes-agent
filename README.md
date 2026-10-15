# Zivi

**Zivi** is a personal, Ubuntu/Linux-focused customization fork of [Hermes Agent](https://github.com/NousResearch/hermes-agent), maintained for private testing and experimentation.

This repository intentionally keeps the upstream CLI command **`hermes`**. Zivi is the product identity; internal Python module names, packaging hooks, and compatibility identifiers that the runtime currently depends on are retained unless a tested migration replaces them.

> **Status:** personal development fork — not an official Nous Research product, not a production-certified distribution, and not intended as a public release.

## Goals

- Use Ubuntu/Linux as the primary development and test platform.
- Keep the upstream agent runtime, providers, tools, skills, and gateway working.
- Apply Zivi-specific defaults and documentation without unnecessary core rewrites.
- Preserve a reviewable change history and run tests before treating changes as complete.
- Keep upstream attribution and the applicable MIT license.

## Requirements

Use the Python version supported by the current repository lock and development workflow. The project currently declares Python `>=3.11,<3.15`; the lock/build workflow may impose a narrower version for reproducible development. Check `pyproject.toml` and [CONTRIBUTING.md](CONTRIBUTING.md) before setting up a fresh environment.

Recommended tools for development:

- Ubuntu/Linux
- Git
- Python and the repository's pinned package manager/runtime
- Node.js only for workflows that need the JavaScript/TUI/desktop portions
- Docker or Nix only when running the corresponding checks

## Personal test setup

### 1. Clone the repository

```bash
git clone https://github.com/xarvea/hermes-agent.git
cd hermes-agent
git switch feat/zivi-personal-customization
```

If the branch has not been pushed to your remote yet, switch to the branch only after it exists on GitHub. Do not run these commands in a working tree that contains uncommitted work without first reviewing `git status`.

### 2. Keep Zivi data separate

For personal testing, use a dedicated home directory so the fork does not mix test sessions, memory, skills, logs, or credentials with an existing Hermes installation.

Add the following to the shell session used to launch Zivi:

```bash
export ZIVI_HOME="${ZIVI_HOME:-$HOME/.zivi}"
export HERMES_HOME="$ZIVI_HOME"  # Compatibility bridge for the current upstream runtime
mkdir -p "$ZIVI_HOME"
```

The public-facing variable is `ZIVI_HOME`; `HERMES_HOME` is set to the same directory because existing runtime components still read that upstream variable directly. This does not rename internal Python modules or change the CLI command.

Do not copy existing production or personal credentials into the test home. Use a separate test API key where possible and keep secrets in the ignored `.env` file under the selected home, never in Git.

### 3. Prepare the development environment

Follow the repository's maintained developer workflow in [CONTRIBUTING.md](CONTRIBUTING.md). The documented test environment command is:

```bash
python -m pm.build_env --source . --out .venv --group dev --group test
```

This builds a development/test environment; it is not a promise that every optional backend or external integration is installed. Use the project's own setup and package-management instructions for the selected features.

### 4. Run the existing command

The command remains **`hermes`**. Use the repository's supported installation/activation workflow, then verify:

```bash
hermes --help
hermes doctor
```

If `hermes` resolves to another installation, inspect `command -v hermes` and `PATH` before testing. Do not uninstall or overwrite the existing installation just to make the fork take precedence.

## Configuration rules

- Product name in user-facing documentation: **Zivi**.
- CLI command: **`hermes`** (unchanged by design).
- Personal test data home: **`$ZIVI_HOME`**, defaulting to **`~/.zivi`**.
- Runtime compatibility: **`HERMES_HOME`** points to the same directory for components that still use the upstream variable.
- Keep provider secrets separate from non-secret settings.
- Do not commit API keys, session databases, logs, generated memory, caches, or local test artifacts.
- Do not rename Python packages, console entry points, or internal configuration tables without updating their consumers, lockfiles, tests, and installer/update paths in the same reviewed change.

## Verification

Use the repository's test runner rather than bare `pytest`:

```bash
scripts/run_tests.sh
```

For a targeted test, pass the path to the test file or directory:

```bash
scripts/run_tests.sh tests/test_hermes_constants.py
```

Before opening or updating a pull request:

1. Run the relevant tests and record the actual result.
2. Run the repository's relevant lint, static/type, packaging, and CI checks.
3. Review the full diff for accidental upstream changes and secret exposure.
4. Confirm that Zivi's test home is isolated from the user's normal data.
5. Do not describe a check as passing unless it was actually executed.

## Branch and release safety

- Make changes on a feature branch and deliver them through a reviewable pull request.
- Never push directly to `main`, merge a pull request, publish a package/image, or create a release without explicit authorization.
- Prefer small, reversible commits.
- Keep the upstream baseline identifiable so upstream changes can be compared and integrated deliberately.

## Upstream and license

Zivi is a personal fork derived from [NousResearch/Hermes-Agent](https://github.com/NousResearch/hermes-agent). Retain the upstream license and copyright notices and review dependency-specific licenses before redistributing anything. Zivi is not affiliated with or endorsed by Nous Research.

See [LICENSE](LICENSE) for the license text and [CONTRIBUTING.md](CONTRIBUTING.md) for development guidance.
