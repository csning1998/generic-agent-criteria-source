"""Resolve a context docs_root from a contexts.toml file."""

from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path


_MISSING_CONFIG = "config file is absent"
_MISSING_DIR = "docs_root directory is absent"
_USAGE = (
    "usage: resolve-context-docs.py "
    "(--context ID | --socket ID) [--config PATH]"
)


def _fail(context_id: str, error: str) -> dict[str, object]:
    """Return a failed resolve result."""
    return {
        "ok": False,
        "context_id": context_id,
        "docs_root": None,
        "error": error,
    }


def _section(
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


def _required_names(
    section: dict[str, object], context_id: str
) -> tuple[str, ...] | str:
    """Return required file names, or an error string."""
    raw = section.get("required")
    if not isinstance(raw, list) or not raw:
        return f"context.{context_id}.required is absent"
    names: list[str] = []
    for item in raw:
        if not isinstance(item, str) or not item.strip():
            return f"context.{context_id}.required is absent"
        names.append(item)
    return tuple(names)


def resolve_context_docs_root(
    config_path: Path, context_id: str
) -> dict[str, object]:
    """Return ok, an absolute docs_root, and error for context_id."""
    if not config_path.is_file():
        return _fail(context_id, _MISSING_CONFIG)
    try:
        loaded = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return _fail(context_id, f"context.{context_id} is absent")
    if not isinstance(loaded, dict):
        return _fail(context_id, f"context.{context_id} is absent")
    section = _section(loaded, context_id)
    if isinstance(section, str):
        return _fail(context_id, section)
    raw = section.get("docs_root")
    if not isinstance(raw, str) or not raw.strip():
        return _fail(context_id, f"context.{context_id}.docs_root is absent")
    names = _required_names(section, context_id)
    if isinstance(names, str):
        return _fail(context_id, names)
    docs = Path(raw).expanduser().resolve()
    if not docs.is_dir():
        return _fail(context_id, _MISSING_DIR)
    for name in names:
        if not (docs / name).is_file():
            return _fail(context_id, f"required file is absent: {name}")
    return {
        "ok": True,
        "context_id": context_id,
        "docs_root": str(docs),
        "error": None,
    }


def _socket_fail(socket_id: str, error: str) -> dict[str, object]:
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
    if not config_path.is_file():
        return _socket_fail(socket_id, _MISSING_CONFIG)
    try:
        loaded = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return _socket_fail(socket_id, f"socket.{socket_id} is absent")
    if not isinstance(loaded, dict):
        return _socket_fail(socket_id, f"socket.{socket_id} is absent")
    sockets = loaded.get("socket")
    if not isinstance(sockets, dict):
        return _socket_fail(socket_id, f"socket.{socket_id} is absent")
    socket = sockets.get(socket_id)
    if not isinstance(socket, dict):
        return _socket_fail(socket_id, f"socket.{socket_id} is absent")
    pack = socket.get("pack")
    skill = socket.get("skill")
    if not isinstance(pack, str) or not pack.strip():
        return _socket_fail(socket_id, f"socket.{socket_id}.pack is absent")
    if not isinstance(skill, str) or not skill.strip():
        return _socket_fail(socket_id, f"socket.{socket_id}.skill is absent")
    section = _section(loaded, pack)
    if isinstance(section, str):
        return _socket_fail(socket_id, section)
    listed = section.get("skills")
    if not isinstance(listed, list) or skill not in listed:
        return _socket_fail(
            socket_id, f"socket.{socket_id}.skill is absent from the pack"
        )
    raw_path = section.get("skills_path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        return _socket_fail(
            socket_id, f"context.{pack}.skills_path is absent"
        )
    skills_path = Path(raw_path).expanduser().resolve()
    if not skills_path.is_dir():
        return _socket_fail(socket_id, "skills_path directory is absent")
    return {
        "ok": True,
        "socket_id": socket_id,
        "pack": pack,
        "skill": skill,
        "skills_path": str(skills_path),
        "error": None,
    }


def _arguments(args: list[str]) -> tuple[Path, str, str] | str:
    """Return config path, mode, and id, or a usage error."""
    config = Path.home() / ".grok" / "contexts.toml"
    context_id = ""
    socket_id = ""
    index = 0
    while index < len(args):
        flag = args[index]
        needs_value = flag in ("--config", "--context", "--socket")
        if needs_value and index + 1 >= len(args):
            return _USAGE
        if flag == "--config":
            config = Path(args[index + 1])
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
    if context_id.strip():
        return config, "context", context_id
    return config, "socket", socket_id


def main(argv: list[str] | None = None) -> int:
    """Print one JSON object and return 0 or 1."""
    args = list(sys.argv[1:] if argv is None else argv)
    parsed = _arguments(args)
    if isinstance(parsed, str):
        print(json.dumps(_fail("", parsed)))
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
