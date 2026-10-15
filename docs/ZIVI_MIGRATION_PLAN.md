# Zivi Identity Migration Plan

## Objective

Make Zivi the user-facing identity for a personal Ubuntu/Linux learning fork while preserving the existing agent's behavior, safe upgrade paths, and required license notices.

This is a staged migration, not a global string replacement. No release, package publication, deployment, or destructive data migration is in scope.

## Current baseline

Repository: `xarvea/zivi`

- PR #1 is merged into `main` and contains the autonomous engineering foundation.
- PR #3 proposes the Zivi-first README and project description.
- Ubuntu/Linux is the primary development and verification target.
- The current project metadata still uses the distribution name `hermes-agent`.
- The current CLI entry point is implemented by `hermes_cli.main:main`; the public console scripts currently include `hermes`, `hermes-agent`, and `hermes-acp`.
- The runtime currently uses compatibility names such as `HERMES_HOME`, and the installer script defaults to the upstream repository unless configured.
- The existing updater compatibility contract deliberately protects older installations. Package, path, and command renames must not bypass it.
- `setup.py` blocks ordinary wheel/sdist builds outside the intended Nix build flow; do not assume a generic `pip install` packaging workflow is supported.
- The current `LICENSE` is MIT and includes an upstream copyright notice. Preserve the notice and license terms in accordance with the license.

## Inventory of known migration-sensitive surfaces

| Surface | Current evidence | Risk |
|---|---|---|
| CLI entry points | `pyproject.toml` `[project.scripts]` | Existing scripts, tests, docs, and integrations can break if removed too early |
| CLI implementation | `hermes_cli/main.py`, `hermes_cli/__init__.py` | Help text, update/recovery paths, and imports may depend on module names |
| User data home | Runtime constants and tests such as `tests/test_hermes_constants.py` | Incorrect migration could split or orphan sessions, memory, credentials, and configuration |
| Installer | `scripts/install.sh` | Defaults include repository URL, home variable, install flags, and user-facing messages |
| Development runner | `scripts/run-in-hermes-env` and `scripts/run_tests.sh` | Renaming scripts prematurely can break contributor and CI workflows |
| Python distribution metadata | `pyproject.toml`, `setup.py`, `nix/python.nix` | Build, Nix evaluation, and updater assumptions may be coupled |
| Old-updater compatibility | `tests/compat/README.md` and the frozen old-updater surface | Existing users may run older updater code against the new checkout |
| CI and test fixtures | Workflows, test names, snapshots, shell scripts | Search-based renames can invalidate fixtures or change behavior unintentionally |
| Branding and assets | README banner, CLI strings, docs, app assets | Branding should change without silently altering functionality or attribution |

This inventory is based on inspected files and is **not yet exhaustive**. Code search was not available through the connected GitHub index, so a complete repository-wide identifier scan remains a required step before renaming runtime identifiers.

## Phases

### Phase 0 — Baseline and constraints

- [x] Confirm repository rename to `xarvea/zivi`.
- [x] Confirm PR #1 is merged.
- [x] Establish Ubuntu/Linux as the primary target.
- [x] Set the rule: preserve required license and copyright notices.
- [ ] Complete a repository-wide scan on a full local checkout.

### Phase 1 — Public branding

- [x] Rewrite the root README around Zivi and Ubuntu/Linux learning.
- [x] Correct clone instructions to `https://github.com/xarvea/zivi.git`.
- [x] Update the project description in `pyproject.toml`.
- [ ] Review and merge the documentation PR after checks.

### Phase 2 — Runtime identity inventory

Before changing code:

1. Clone the repository on Ubuntu and record `git rev-parse HEAD` and `git status --short`.
2. Search tracked files for case-insensitive matches of `hermes`, `NousResearch`, `HERMES_`, `.hermes`, old repository URLs, product banners, and install paths.
3. Classify each match as public branding, compatibility contract, package/module identifier, license/attribution, test fixture, or third-party reference.
4. Map each runtime setting to its read/write locations and precedence rules.
5. Identify tests that freeze command names, environment variables, home-directory defaults, updater imports, package metadata, and generated entry points.
6. Publish the inventory and acceptance criteria before broad runtime edits.

**Gate:** no renaming of package/module names, data paths, or updater identifiers until this inventory is reviewed.

### Phase 3 — CLI transition

- Add a `zivi` console entry point while retaining current command aliases.
- Test `zivi --help`, version reporting, doctor/status commands, provider setup, and interactive startup.
- Check generated scripts in the development environment and Nix workflow.
- Keep the old entry points until usage and compatibility checks demonstrate they can safely be retired.

**Acceptance:** new Zivi command works in a clean Ubuntu environment; existing command aliases continue to work; no command-resolution collision with another installed copy.

### Phase 4 — Data-home transition

- Make `ZIVI_HOME` the canonical public setting.
- Preserve a documented compatibility fallback for `HERMES_HOME` during the transition.
- Define precedence when both variables are set; do not silently choose different directories in different components.
- Migrate the default data path only for new isolated Zivi installations.
- Never automatically move, delete, or overwrite existing user data.
- Add tests for unset variables, each variable independently set, both set, relative paths, tilde/environment expansion, permissions, and path containment.

**Acceptance:** all components resolve the same data home, and legacy data remains intact unless the user explicitly migrates it.

### Phase 5 — Installer, updater, package, and internal identifiers

- Introduce Zivi-specific repository/install variables with explicit precedence and safe defaults.
- Test fresh install, repeat install, update, interrupted update recovery, and rollback behavior.
- Audit distribution metadata, Python module imports, Nix package attributes, generated scripts, dependency references, and frozen updater surfaces.
- Rename internal modules or distribution metadata only when every consumer, lockfile, test, build recipe, and compatibility path is covered.
- Keep the license and required copyright notices unchanged.

**Acceptance:** clean install and update work on the supported Ubuntu target; compatibility tests pass; no data loss or accidental upstream installation occurs.

### Phase 6 — Verification and completion

Run, as applicable:

- Focused unit and behavioral tests for every changed surface.
- `scripts/run_tests.sh` for the broader test suite.
- Python lint/type checks and JS/Rust checks only when relevant files change.
- Nix checks when packaging or Nix files change.
- Clean-environment CLI smoke tests and installer/update checks.
- A final tracked-file scan for residual branding, with every remaining match explained.
- Diff review for secrets, unrelated changes, license notices, and accidental deletions.

Report each check as PASS, FAIL, BLOCKED, or NOT VERIFIED. Do not claim production readiness based only on CI.

## Non-goals

- No public release or package publication.
- No deployment.
- No blanket replacement of every `hermes` string.
- No removal of required license/copyright notices.
- No automatic destructive migration of existing user data.
- No claim that the agent is production-certified.

## Immediate next action

Complete Phase 2's full tracked-file scan from an Ubuntu checkout. The current GitHub connector can inspect known files but its code-search index is unavailable, so a complete rename inventory cannot be truthfully certified from connector search alone.
