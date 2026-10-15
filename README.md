# Zivi

**Zivi** is a personal, Ubuntu/Linux-focused customization fork of [Hermes Agent](https://github.com/NousResearch/hermes-agent), maintained for private testing and experimentation.

Zivi keeps the upstream CLI command **`hermes`** for compatibility. Zivi is the user-facing product identity; internal Python modules, package names, packaging hooks, and compatibility namespaces remain unchanged until a coordinated and tested migration is available.

> **Status:** personal development fork. This is not an official Nous Research product and is not production-certified.

## Goals

- Make Ubuntu/Linux the primary development and test environment.
- Preserve the upstream runtime, providers, tools, skills, and gateway wherever possible.
- Add Zivi-specific defaults and documentation without unnecessary core rewrites.
- Keep changes reviewable and verify them with tests before relying on them.
- Preserve upstream attribution and the applicable MIT license.

## What's included

### Autonomous engineering foundation

The engineering foundation merged in PR #1 adds an end-to-end engineering workflow to the agent:

- Inspect the repository and its instructions before making changes.
- Define acceptance criteria and plan dependency-aware tasks.
- Implement in small steps and run relevant tests and checks.
- Report evidence, blockers, and unverified items instead of claiming unsupported success.
- Persist task state in a project-local SQLite fallback ledger when that backend is used, including dependency gates, auditable events, and evidence-required completion.
- Read resumable local task state as untrusted data, with project-root path containment and protections against mutating databases owned by another backend.

This is a foundation, not a fully autonomous or production-certified engineering organization. Structured role orchestration, deterministic action gates, independent verification, and end-to-end project-build certification remain future work. Passing CI does not certify every workflow or external integration.

## Requirements

Use the Python version and package workflow supported by the current repository. The project declares Python `>=3.11,<3.15`, while its lock and development workflow may impose a narrower version. Check [pyproject.toml](pyproject.toml) and [CONTRIBUTING.md](CONTRIBUTING.md) before creating an environment.

Recommended tools:

- Ubuntu/Linux and Git
- Python and the repository's maintained package/runtime workflow
- Node.js for workflows that need JavaScript/TUI/desktop components
- Docker or Nix only when running the corresponding checks

## Personal test setup

### 1. Clone the repository

```bash
git clone https://github.com/xarvea/hermes-agent.git
cd hermes-agent
```

Use the branch you intend to test. If working from an open pull request, switch to that PR's head branch before following its changes. Check `git status` before switching branches, and do not overwrite uncommitted work.

### 2. Isolate Zivi's local data

Use a dedicated home directory so test sessions, memory, skills, logs, and credentials do not mix with an existing Hermes installation.

Export these variables in the shell used to launch the agent:

```bash
export ZIVI_HOME="${ZIVI_HOME:-$HOME/.zivi}"
export HERMES_HOME="$ZIVI_HOME"  # Compatibility bridge for current runtime components
mkdir -p "$ZIVI_HOME"
```

The public-facing variable is `ZIVI_HOME`; current runtime components still read `HERMES_HOME`, so both point to the same directory. This does not rename internal modules or change the `hermes` CLI.

Use separate test API keys where possible. Keep credentials out of Git, commits, logs, and task descriptions. Do not copy production credentials into the test home.

### 3. Prepare the development environment

Follow the maintained developer workflow in [CONTRIBUTING.md](CONTRIBUTING.md). The development/test environment command is:

```bash
python -m pm.build_env --source . --out .venv --group dev --group test
```

This prepares a development/test environment; it does not guarantee every optional backend or external integration is installed. Use the repository's setup instructions for the features you plan to test.

### 4. Verify the CLI

The CLI remains **`hermes`**:

```bash
hermes --help
hermes doctor
```

Use the repository's supported installation/activation workflow first. If the command resolves to another installation, inspect `command -v hermes` and `PATH`; do not uninstall or overwrite an existing installation just to change command precedence.

## Configuration and compatibility

- User-facing product name: **Zivi**.
- CLI command: **`hermes`**, unchanged by design.
- Personal test data home: **`$ZIVI_HOME`**, defaulting to **`~/.zivi`**.
- Runtime compatibility: **`HERMES_HOME`** points to the same directory for components that still use the upstream variable.
- Internal distribution name remains **`hermes-agent`**.
- Internal packaging metadata namespace remains **`[tool.hermes]`**.
- Do not rename Python packages, console entry points, environment variables, or configuration tables without updating all consumers, lockfiles, tests, and installer/update paths in one reviewed change.
- Do not commit API keys, session databases, logs, generated memory, caches, or local test artifacts.

## Verification

Use the repository's test runner rather than bare `pytest`:

```bash
scripts/run_tests.sh
```

For a targeted test:

```bash
scripts/run_tests.sh tests/test_hermes_constants.py
```

Before relying on a change:

1. Run relevant unit and behavioral tests.
2. Run applicable lint, type, packaging, and CI checks.
3. Review the complete diff for unintended changes and secret exposure.
4. Confirm the Zivi test home is isolated from normal user data.
5. Mark checks that could not run as **NOT VERIFIED**; never report proposed commands as completed tests.

## Branch and release safety

- Make changes on a feature branch and use a pull request for review.
- Do not push directly to `main`, merge pull requests, publish packages/images, or create releases without explicit authorization.
- Prefer small, reversible commits.
- Keep the upstream baseline identifiable so upstream changes can be compared and integrated deliberately.

## Upstream and license

Zivi is a personal fork derived from [NousResearch/Hermes-Agent](https://github.com/NousResearch/hermes-agent). Retain upstream license and copyright notices, and review dependency-specific licenses before redistribution. Zivi is not affiliated with or endorsed by Nous Research.

See [LICENSE](LICENSE) for the license text and [CONTRIBUTING.md](CONTRIBUTING.md) for development guidance.
