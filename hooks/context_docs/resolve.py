"""Resolve a context docs_root from a contexts.toml file."""

from __future__ import annotations

import json
import os
import sys
import tomllib
from pathlib import Path


_AGENTS_DIR = ".agents"
_CONTEXTS_FILE = "contexts.toml"
_MISSING_CONFIG = "config file is absent"
_MISSING_DIR = "docs_root directory is absent"
_MISSING_SKILLS_PATH = "skills_path directory is absent"
_USAGE = (
    "usage: resolve-context-docs.py "
    "(--context ID | --socket ID) [--config PATH] [--workspace-root PATH]"
)


def _derive_failure(context_id: str, error: str) -> dict[str, object]:
    """Return a failed resolve result."""
    return {
        "ok": False,
        "context_id": context_id,
        "docs_root": None,
        "error": error,
    }


def _load_toml_config(config_path: Path) -> dict[str, object] | None:
    """Return parsed TOML mapping, or None if missing or invalid."""
    if not config_path.is_file():
        return None
    try:
        loaded = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return None
    if not isinstance(loaded, dict):
        return None
    return loaded


def _extract_context_section(
    loaded: dict[str, object], context_id: str
) -> dict[str, object] | str:
    """Return the context table, or an error string."""
    context = loaded.get("context")
    if not isinstance(context, dict):
        return f"context.{context_id} is absent"
    section = context.get(context_id)
    if not isinstance(section, dict):
        return f"context.{context_id} is absent"
    return section


def _extract_required_names(
    section: dict[str, object], context_id: str
) -> tuple[str, ...] | str:
    """Return required file names, or an error string."""
    raw = section.get("required")
    if not isinstance(raw, list):
        return f"context.{context_id}.required is absent"
    names: list[str] = []
    for item in raw:
        if not isinstance(item, str) or not item.strip():
            return f"context.{context_id}.required is absent"
        names.append(item)
    return tuple(names)


def _validate_required_files(docs: Path, names: tuple[str, ...]) -> str | None:
    """Return missing file error if any required file is absent."""
    for name in names:
        if not (docs / name).is_file():
            return f"required file is absent: {name}"
    return None


def _extract_socket_binding(
    loaded: dict[str, object], socket_id: str
) -> tuple[str, str] | str:
    """Return (pack, skill), or an error string for socket_id."""
    sockets = loaded.get("socket")
    if not isinstance(sockets, dict):
        return f"socket.{socket_id} is absent"
    socket = sockets.get(socket_id)
    if not isinstance(socket, dict):
        return f"socket.{socket_id} is absent"
    pack = socket.get("pack")
    skill = socket.get("skill")
    if not isinstance(pack, str) or not pack.strip():
        return f"socket.{socket_id}.pack is absent"
    if not isinstance(skill, str) or not skill.strip():
        return f"socket.{socket_id}.skill is absent"
    return pack, skill


def _resolve_contained_directory(
    config_path: Path, raw_path: str
) -> Path | None:
    """Return an absolute directory resolved within base, or None."""
    path_raw = Path(raw_path).expanduser()
    if not path_raw.is_absolute():
        base = config_path.parent
        if base.name == _AGENTS_DIR:
            base = base.parent
        resolved = (base / path_raw).resolve()
        if not resolved.is_relative_to(base.resolve()):
            return None
    else:
        resolved = path_raw.resolve()
    if not resolved.is_dir():
        return None
    return resolved


def resolve_context_docs_root(
    config_path: Path, context_id: str
) -> dict[str, object]:
    """Return ok, an absolute docs_root, and error for context_id."""
    loaded = _load_toml_config(config_path)
    if loaded is None:
        err = (
            _MISSING_CONFIG
            if not config_path.is_file()
            else f"context.{context_id} is absent"
        )
        return _derive_failure(context_id, err)
    section = _extract_context_section(loaded, context_id)
    if isinstance(section, str):
        return _derive_failure(context_id, section)
    raw = section.get("docs_root")
    if not isinstance(raw, str) or not raw.strip():
        return _derive_failure(
            context_id, f"context.{context_id}.docs_root is absent"
        )
    names = _extract_required_names(section, context_id)
    if isinstance(names, str):
        return _derive_failure(context_id, names)
    docs = _resolve_contained_directory(config_path, raw)
    if docs is None:
        return _derive_failure(context_id, _MISSING_DIR)
    file_err = _validate_required_files(docs, names)
    if file_err is not None:
        return _derive_failure(context_id, file_err)
    return {
        "ok": True,
        "context_id": context_id,
        "docs_root": str(docs),
        "error": None,
    }


def _derive_socket_failure(socket_id: str, error: str) -> dict[str, object]:
    """Return a failed catalog socket result."""
    return {
        "ok": False,
        "socket_id": socket_id,
        "pack": None,
        "skill": None,
        "skills_path": None,
        "error": error,
    }


def resolve_catalog_socket(
    config_path: Path, socket_id: str
) -> dict[str, object]:
    """Return the pack skill declared for socket_id."""
    loaded = _load_toml_config(config_path)
    if loaded is None:
        err = (
            _MISSING_CONFIG
            if not config_path.is_file()
            else f"socket.{socket_id} is absent"
        )
        return _derive_socket_failure(socket_id, err)
    binding = _extract_socket_binding(loaded, socket_id)
    if isinstance(binding, str):
        return _derive_socket_failure(socket_id, binding)
    pack, skill = binding
    section = _extract_context_section(loaded, pack)
    if isinstance(section, str):
        return _derive_socket_failure(socket_id, section)
    listed = section.get("skills")
    if not isinstance(listed, list) or skill not in listed:
        return _derive_socket_failure(
            socket_id, f"socket.{socket_id}.skill is absent from the pack"
        )
    raw_path = section.get("skills_path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        return _derive_socket_failure(
            socket_id, f"context.{pack}.skills_path is absent"
        )
    skills_path = _resolve_contained_directory(config_path, raw_path)
    if skills_path is None:
        return _derive_socket_failure(socket_id, _MISSING_SKILLS_PATH)
    return {
        "ok": True,
        "socket_id": socket_id,
        "pack": pack,
        "skill": skill,
        "skills_path": str(skills_path),
        "error": None,
    }


def resolve_catalog_skill_sources(config_path: Path) -> dict[str, Path] | str:
    """Return declared skill name to source path, or an error string."""
    if not config_path.is_file():
        return {}
    try:
        loaded = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return "config file is absent"
    if not isinstance(loaded, dict):
        return {}
    context = loaded.get("context")
    if not isinstance(context, dict):
        return {}
    sources: dict[str, Path] = {}
    for pack_id, section in context.items():
        if not isinstance(section, dict):
            continue
        listed = section.get("skills")
        if not listed:
            continue
        if not isinstance(listed, list):
            return f"context.{pack_id}.skills is absent"
        raw_path = section.get("skills_path")
        if not isinstance(raw_path, str) or not raw_path.strip():
            return f"context.{pack_id}.skills_path is absent"
        root = _resolve_contained_directory(config_path, raw_path)
        if root is None:
            return _MISSING_SKILLS_PATH
        for name in listed:
            if (
                not isinstance(name, str)
                or not name.strip()
                or name in {".", ".."}
                or "/" in name
            ):
                return f"context.{pack_id}.skills is absent"
            source = (root / name).resolve()
            if not source.exists():
                return "source-missing"
            previous = sources.get(name)
            if previous is not None and previous != source:
                return f"skill name collision: {name}"
            sources[name] = source
    return sources


def resolve_catalog_path(
    criteria_root: Path,
    workspace_root: Path | None = None,
    home_root: Path | None = None,
) -> Path:
    """Return the catalog file in workspace, user home, or criteria repo."""
    opt_in = workspace_root
    if opt_in is None:
        raw_env = (
            os.environ.get("AGENT_WORKSPACE_ROOT")
            or os.environ.get("ANTIGRAVITY_WORKSPACE_ROOT")
            or os.environ.get("GROK_WORKSPACE_ROOT")
        )
        if raw_env and raw_env.strip():
            opt_in = Path(raw_env).expanduser().resolve()
    if opt_in is not None:
        candidate_agents = opt_in / _AGENTS_DIR / _CONTEXTS_FILE
        if candidate_agents.is_file():
            return candidate_agents
    home = home_root if home_root is not None else Path.home()
    for candidate in (
        home / _AGENTS_DIR / _CONTEXTS_FILE,
        home / ".gemini" / _CONTEXTS_FILE,
        home / ".claude" / _CONTEXTS_FILE,
        home / ".grok" / _CONTEXTS_FILE,
    ):
        if candidate.is_file():
            return candidate
    return criteria_root / "config" / _CONTEXTS_FILE


def _parse_cli_arguments(args: list[str]) -> tuple[Path, str, str] | str:
    """Return config path, mode, and id, or a usage error."""
    criteria_root = Path(__file__).resolve().parents[2]
    config: Path | None = None
    workspace_root: Path | None = None
    context_id = ""
    socket_id = ""
    index = 0
    while index < len(args):
        flag = args[index]
        needs_value = flag in (
            "--config",
            "--context",
            "--socket",
            "--workspace-root",
        )
        if needs_value and index + 1 >= len(args):
            return _USAGE
        if flag == "--config":
            config = Path(args[index + 1])
            index += 2
            continue
        if flag == "--workspace-root":
            workspace_root = Path(args[index + 1]).expanduser().resolve()
            index += 2
            continue
        if flag == "--context":
            context_id = args[index + 1]
            index += 2
            continue
        if flag == "--socket":
            socket_id = args[index + 1]
            index += 2
            continue
        return _USAGE
    if bool(context_id.strip()) == bool(socket_id.strip()):
        return _USAGE
    if config is None:
        config = resolve_catalog_path(criteria_root, workspace_root)
    if context_id.strip():
        return config, "context", context_id
    return config, "socket", socket_id


def main(argv: list[str] | None = None) -> int:
    """Print one JSON object and return 0 or 1."""
    args = list(sys.argv[1:] if argv is None else argv)
    parsed = _parse_cli_arguments(args)
    if isinstance(parsed, str):
        print(json.dumps(_derive_failure("", parsed)))
        return 1
    config, mode, name = parsed
    if mode == "socket":
        result = resolve_catalog_socket(config, name)
    else:
        result = resolve_context_docs_root(config, name)
    print(json.dumps(result))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
