"""Deterministic, local-first IndexGraph bootstrap without per-file model calls.

The provider reads bounded text files, never executes project code, and only emits
relationships that its built-in extractors can substantiate.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from agent.indexgraph import (
    Confidence,
    GraphEdge,
    GraphNode,
    IndexManifest,
    IndexStatus,
    project_id_for,
    stable_id,
    utc_now,
)

PROVIDER_ID = "builtin-deterministic"
PROVIDER_VERSION = "1"
MAX_FILES = 20_000
MAX_FILE_BYTES = 1_000_000
MAX_TOTAL_BYTES = 20_000_000
GIT_TIMEOUT_SECONDS = 5.0
SOURCE_SUFFIXES = frozenset({
    ".py", ".pyi", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx",
    ".rs", ".go", ".java", ".kt", ".c", ".h", ".cc", ".cpp", ".hpp",
    ".cs", ".rb", ".php", ".sh", ".bash", ".zsh", ".sql",
})
CONFIG_SUFFIXES = frozenset({".json", ".toml", ".yaml", ".yml", ".ini", ".cfg"})
TEXT_SUFFIXES = SOURCE_SUFFIXES | CONFIG_SUFFIXES | frozenset({".md", ".rst", ".txt"})
MANIFEST_NAMES = frozenset({
    "pyproject.toml", "package.json", "Cargo.toml", "go.mod",
    "pnpm-workspace.yaml", "requirements.txt", "uv.lock", "package-lock.json",
})
EXCLUDED_DIRS = frozenset({
    ".git", ".hg", ".svn", ".venv", "venv", "node_modules", "vendor",
    "dist", "build", "target", "coverage", ".next", ".turbo", "__pycache__",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox", ".engineering-agent",
})
SECRET_NAMES = frozenset({
    ".env", "id_rsa", "id_ed25519", "credentials", "secrets.json",
    "service-account.json",
})
_IMPORT_RE = re.compile(
    r"""(?:from\s+|import\s*\(?\s*|require\s*\(\s*)["']([^"']+)["']"""
)


@dataclass(frozen=True)
class BootstrapPolicy:
    max_files: int = MAX_FILES
    max_file_bytes: int = MAX_FILE_BYTES
    max_total_bytes: int = MAX_TOTAL_BYTES
    excluded_dirs: frozenset[str] = EXCLUDED_DIRS
    text_suffixes: frozenset[str] = TEXT_SUFFIXES


@dataclass(frozen=True)
class BootstrapReport:
    manifest: IndexManifest
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]
    indexed_paths: tuple[str, ...]
    excluded_paths: tuple[str, ...]
    unsupported_paths: tuple[str, ...]
    errors: tuple[str, ...] = ()


def _fingerprint(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _is_secret_path(path: str) -> bool:
    name = PurePosixPath(path).name.lower()
    if name in SECRET_NAMES or name.endswith((".pem", ".key", ".p12", ".pfx")):
        return True
    if name.startswith(".env.") and name not in {".env.example", ".env.template", ".env.sample"}:
        return True
    return name in {".env", ".npmrc", ".pypirc", ".netrc"}


def _excluded_by_policy(path: str, policy: BootstrapPolicy) -> bool:
    parts = PurePosixPath(path).parts
    return (
        not parts
        or any(part in policy.excluded_dirs for part in parts)
        or _is_secret_path(path)
    )


def _is_eligible(path: str, policy: BootstrapPolicy) -> bool:
    if _excluded_by_policy(path, policy):
        return False
    suffix = PurePosixPath(path).suffix.lower()
    name = PurePosixPath(path).name.lower()
    return suffix in policy.text_suffixes or name in MANIFEST_NAMES


def _git_paths(root: Path) -> list[str] | None:
    """Return tracked plus eligible untracked paths; None means not a Git worktree."""
    try:
        result = subprocess.run(
            [
                "git", "-C", str(root), "ls-files", "--cached", "--others",
                "--exclude-standard", "-z",
            ],
            check=False, capture_output=True, timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    paths = {
        item.decode("utf-8", errors="surrogateescape")
        for item in result.stdout.split(b"\0") if item
    }
    return sorted(paths)


def _walk_paths(root: Path, policy: BootstrapPolicy) -> list[str]:
    paths: list[str] = []
    for current, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(
            name for name in dirs
            if name not in policy.excluded_dirs and not (Path(current) / name).is_symlink()
        )
        for name in sorted(files):
            path = (Path(current) / name).relative_to(root).as_posix()
            if _is_eligible(path, policy):
                paths.append(path)
    return sorted(paths)


def _source_revision(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--verify", "HEAD"],
            check=False, capture_output=True, text=True, timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    revision = result.stdout.strip()
    valid = result.returncode == 0 and re.fullmatch(r"[0-9a-fA-F]{40,64}", revision)
    return revision if valid else None


def _node(project_id: str, kind: str, path: str, label: str, fingerprint: str,
          *, attributes: dict[str, Any] | None = None) -> GraphNode:
    return GraphNode(
        id=stable_id(project_id, kind, path, label),
        kind=kind,
        label=label[:512],
        path=path,
        source_fingerprint=fingerprint,
        extractor_id=PROVIDER_ID,
        extractor_version=PROVIDER_VERSION,
        confidence=Confidence.CONFIRMED,
        attributes=attributes or {},
    )


def _edge(project_id: str, source: GraphNode, relation: str, target: GraphNode,
          source_path: str, fingerprint: str) -> GraphEdge:
    return GraphEdge(
        id=stable_id(project_id, source.id, relation, target.id),
        from_id=source.id,
        relation=relation,
        to_id=target.id,
        source_path=source_path,
        source_fingerprint=fingerprint,
        extractor_id=PROVIDER_ID,
        extractor_version=PROVIDER_VERSION,
        confidence=Confidence.CONFIRMED,
    )


def _resolve_import(root: Path, source: str, specifier: str) -> str | None:
    """Resolve only project-local imports; external imports are not guessed."""
    if not specifier.startswith("."):
        return None
    base = (root / source).parent
    target = (base / specifier).resolve(strict=False)
    try:
        relative = target.relative_to(root).as_posix()
    except ValueError:
        return None
    candidates = [relative]
    if not Path(relative).suffix:
        suffixes = (".py", ".pyi", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx")
        candidates.extend(relative + suffix for suffix in suffixes)
        candidates.extend(f"{relative}/index{suffix}" for suffix in (".js", ".jsx", ".ts", ".tsx"))
        candidates.append(f"{relative}/__init__.py")
    for candidate in candidates:
        resolved = (root / candidate).resolve(strict=False)
        try:
            resolved.relative_to(root)
        except ValueError:
            continue
        if resolved.is_file():
            return candidate
    return None


def _python_imports(data: bytes, source: str) -> list[tuple[str, int]]:
    try:
        tree = ast.parse(data.decode("utf-8"), filename=source)
    except (UnicodeDecodeError, SyntaxError, ValueError, RecursionError):
        return []
    imports: list[tuple[str, int]] = []
    parent = PurePosixPath(source).parent
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level:
                base_parts = parent.parts[:max(0, len(parent.parts) - node.level + 1)]
                base = "/".join(base_parts)
                if node.module:
                    module_parts = (base, node.module.replace(".", "/"))
                    module = "/".join(part for part in module_parts if part)
                    if module:
                        imports.append((module, node.lineno))
                else:
                    imports.extend(
                        ("/".join(part for part in (base, alias.name) if part), node.lineno)
                        for alias in node.names
                    )
            elif node.module:
                imports.append((node.module.replace(".", "/"), node.lineno))
        elif isinstance(node, ast.Import):
            imports.extend((alias.name.replace(".", "/"), node.lineno) for alias in node.names)
    return imports


def _resolve_python_module(root: Path, module_path: str) -> str | None:
    normalized = module_path.strip("/")
    candidates = [normalized + ".py", normalized + ".pyi", normalized + "/__init__.py"]
    for candidate in candidates:
        resolved = (root / candidate).resolve(strict=False)
        try:
            resolved.relative_to(root)
        except ValueError:
            continue
        if resolved.is_file():
            return candidate
    return None


def _python_requirement_name(requirement: str) -> str:
    """Extract the normalized project-name token from a PEP 508 requirement."""
    match = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)", requirement)
    return match.group(1) if match else ''


def _dependency_declarations(path: str, data: bytes) -> list[tuple[str, str]]:
    name = PurePosixPath(path).name.lower()
    try:
        if name == "package.json":
            record = json.loads(data.decode("utf-8"))
            if not isinstance(record, dict):
                return []
            dependencies: list[tuple[str, str]] = []
            sections = (
                "dependencies", "devDependencies", "peerDependencies",
                "optionalDependencies",
            )
            for section in sections:
                values = record.get(section, {})
                if isinstance(values, dict):
                    dependencies.extend(
                        (str(package), str(spec)) for package, spec in values.items()
                        if isinstance(package, str) and isinstance(spec, (str, int, float))
                    )
            return sorted(set(dependencies))
        if name == "pyproject.toml":
            record = tomllib.loads(data.decode("utf-8"))
            project = record.get("project", {})
            deps = project.get("dependencies", []) if isinstance(project, dict) else []
            result = [
                (_python_requirement_name(item), item)
                for item in deps
                if isinstance(item, str)
            ]
            optional = project.get("optional-dependencies", {}) if isinstance(project, dict) else {}
            if isinstance(optional, dict):
                for values in optional.values():
                    if isinstance(values, list):
                        result.extend(
                            (_python_requirement_name(item), item)
                            for item in values
                            if isinstance(item, str)
                        )
            return sorted({
                (package, spec) for package, spec in result if package
            })
        if name == "cargo.toml":
            record = tomllib.loads(data.decode("utf-8"))
            result = []
            for section in ("dependencies", "dev-dependencies", "build-dependencies"):
                values = record.get(section, {})
                if isinstance(values, dict):
                    for package, spec in values.items():
                        result.append((str(package), json.dumps(spec, sort_keys=True)[:512]))
            return sorted(result)
        if name == "go.mod":
            text = data.decode("utf-8")
            result = []
            for block in re.findall(r"(?ms)^require\s*\((.*?)^\)", text):
                for line in block.splitlines():
                    fields = line.strip().split()
                    if len(fields) >= 2 and not line.strip().startswith("//"):
                        result.append((fields[0], fields[1]))
            for line in text.splitlines():
                if line.strip().startswith("require ") and "(" not in line:
                    fields = line.strip().split()
                    if len(fields) >= 3:
                        result.append((fields[1], fields[2]))
            return sorted(set(result))
    except (
        UnicodeDecodeError, json.JSONDecodeError, tomllib.TOMLDecodeError,
        TypeError, ValueError, RecursionError,
    ):
        return []
    return []


def build_index(project_root: str | Path, policy: BootstrapPolicy | None = None) -> BootstrapReport:
    """Build a deterministic snapshot using local parsers and bounded file reads only."""
    policy = policy or BootstrapPolicy()
    root = Path(project_root).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("project_root must be a directory")
    raw_paths = _git_paths(root)
    if raw_paths is None:
        raw_paths = _walk_paths(root, policy)

    excluded: list[str] = []
    eligible: list[str] = []
    unsupported: list[str] = []
    for path in raw_paths:
        if _excluded_by_policy(path, policy):
            excluded.append(path)
        elif not _is_eligible(path, policy):
            unsupported.append(path)
        else:
            eligible.append(path)
    if len(eligible) > policy.max_files:
        raise ValueError(f"project exceeds bootstrap file limit ({policy.max_files})")

    file_data: dict[str, bytes] = {}
    errors: list[str] = []
    total_bytes = 0
    for path in eligible:
        lexical_path = root / Path(*PurePosixPath(path).parts)
        if any(
            (root / Path(*PurePosixPath(path).parts[:index])).is_symlink()
            for index in range(1, len(PurePosixPath(path).parts) + 1)
        ):
            excluded.append(path)
            continue
        candidate = lexical_path.resolve(strict=False)
        try:
            candidate.relative_to(root)
        except ValueError:
            excluded.append(path)
            continue
        if not candidate.is_file():
            excluded.append(path)
            continue
        try:
            size = candidate.stat().st_size
            if size > policy.max_file_bytes:
                unsupported.append(path)
                continue
            if total_bytes + size > policy.max_total_bytes:
                errors.append("total byte budget reached; remaining files not read")
                break
            data = candidate.read_bytes()
        except OSError:
            errors.append(f"unreadable file: {path[:400]}")
            continue
        if b"\0" in data:
            unsupported.append(path)
            continue
        total_bytes += len(data)
        file_data[path] = data

    project_id = project_id_for(root)
    project_node = _node(
        project_id, "project", "", root.name or "project",
        _fingerprint(str(root).encode()),
    )
    nodes: list[GraphNode] = [project_node]
    edges: list[GraphEdge] = []
    path_nodes: dict[str, GraphNode] = {}
    fingerprints = {path: _fingerprint(data) for path, data in file_data.items()}
    directories: set[str] = set()
    for path in sorted(file_data):
        parts = PurePosixPath(path).parts
        for i in range(1, len(parts)):
            directories.add("/".join(parts[:i]))
    directory_nodes: dict[str, GraphNode] = {}
    for path in sorted(directories):
        node = _node(
            project_id, "directory", path, PurePosixPath(path).name,
            _fingerprint(path.encode()),
        )
        directory_nodes[path] = node
        nodes.append(node)
    for path, data in sorted(file_data.items()):
        is_manifest = PurePosixPath(path).name.lower() in MANIFEST_NAMES
        node = _node(
            project_id, "manifest" if is_manifest else "file", path,
            PurePosixPath(path).name, fingerprints[path],
            attributes={"size_bytes": len(data), "suffix": PurePosixPath(path).suffix.lower()},
        )
        path_nodes[path] = node
        nodes.append(node)
    for path, node in directory_nodes.items():
        parent_path = PurePosixPath(path).parent.as_posix()
        parent = directory_nodes.get(parent_path, project_node)
        edges.append(_edge(project_id, parent, "contains", node, path, node.source_fingerprint))
    for path, node in path_nodes.items():
        parent_path = PurePosixPath(path).parent.as_posix()
        parent = directory_nodes.get(parent_path, project_node)
        edges.append(_edge(project_id, parent, "contains", node, path, fingerprints[path]))

    for path, data in sorted(file_data.items()):
        source_node = path_nodes[path]
        suffix = PurePosixPath(path).suffix.lower()
        imports: list[tuple[str, int]] = []
        if suffix in {".py", ".pyi"}:
            for module_path, line in _python_imports(data, path):
                resolved = _resolve_python_module(root, module_path)
                if resolved:
                    imports.append((resolved, line))
        elif suffix in {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"}:
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                text = ""
            for match in _IMPORT_RE.finditer(text):
                specifier = match.group(1)
                target = _resolve_import(root, path, specifier)
                if target:
                    line = text.count("\n", 0, match.start()) + 1
                    imports.append((target, line))
        for target_path, line in sorted(set(imports)):
            target_node = path_nodes.get(target_path)
            if target_node:
                edge = _edge(
                    project_id, source_node, "imports", target_node, path,
                    fingerprints[path],
                )
                edges.append(GraphEdge(**{
                    **edge.__dict__,
                    "id": stable_id(
                        project_id, source_node.id, "imports", target_node.id, str(line),
                    ),
                    "start_line": line,
                    "end_line": line,
                }))

        dependency_manifests = {"pyproject.toml", "package.json", "cargo.toml", "go.mod"}
        if PurePosixPath(path).name.lower() in dependency_manifests:
            for package, specifier in _dependency_declarations(path, data):
                package_node = _node(
                    project_id, "package", path, package, fingerprints[path],
                    attributes={"specifier": specifier[:512], "declared_by": path},
                )
                package_node = GraphNode(
                    **{
                        **package_node.__dict__,
                        "id": stable_id(project_id, "package", path, package, specifier),
                    }
                )
                nodes.append(package_node)
                edges.append(_edge(
                    project_id, source_node, "declares_dependency", package_node,
                    path, fingerprints[path],
                ))

    revision = _source_revision(root)
    indexed_paths = tuple(sorted(file_data))
    unsupported_paths = tuple(sorted(set(unsupported)))
    errors = errors[:100]
    status = IndexStatus.PARTIAL if errors or unsupported_paths else IndexStatus.READY
    manifest = IndexManifest(
        project_id=project_id,
        canonical_root=str(root),
        source_revision=revision,
        provider_id=PROVIDER_ID,
        provider_version=PROVIDER_VERSION,
        status=status,
        discovered_files=len(eligible),
        indexed_files=len(indexed_paths),
        excluded_files=len(set(excluded)),
        unsupported_files=len(unsupported_paths),
        failed_files=len(errors),
        config_fingerprint=_fingerprint(json.dumps({
            "provider": PROVIDER_ID, "version": PROVIDER_VERSION,
            "max_files": policy.max_files, "max_file_bytes": policy.max_file_bytes,
            "max_total_bytes": policy.max_total_bytes,
            "excluded_dirs": sorted(policy.excluded_dirs),
            "text_suffixes": sorted(policy.text_suffixes),
        }, sort_keys=True).encode()),
        last_success_at=utc_now(),
        errors=tuple(errors),
    )
    return BootstrapReport(
        manifest=manifest,
        nodes=tuple(nodes),
        edges=tuple(edges),
        indexed_paths=indexed_paths,
        excluded_paths=tuple(sorted(set(excluded))),
        unsupported_paths=unsupported_paths,
        errors=tuple(errors),
    )
