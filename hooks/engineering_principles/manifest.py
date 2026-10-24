"""Planning manifest that declares the adjudication record and its specs."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from pathlib import PurePosixPath


MANIFEST_NAME = "planning.manifest.toml"
DEFAULT_GOVERNED_DIRS = ("terraform", "ansible", "packer")


class ManifestError(ValueError):
    """Raised when a planning manifest is missing fields or names."""


@dataclass(frozen=True)
class Specification:
    """One specification file and the repository paths it governs."""

    path: Path
    governs: tuple[Path, ...]
    governs_text: tuple[str, ...]


@dataclass(frozen=True)
class PlanningManifest:
    """Parsed manifest with paths resolved against its directory."""

    file: Path
    root: Path
    workspace: Path
    adjudication: Path
    governed_dirs: tuple[str, ...]
    specifications: tuple[Specification, ...]


def find_planning_manifest(start: Path) -> Path | None:
    """Return the nearest manifest in a child directory of an ancestor."""
    cursor = start.expanduser()
    for ancestor in [cursor, *cursor.parents]:
        try:
            hits = sorted(ancestor.glob(f"*/{MANIFEST_NAME}"))
        except OSError:
            continue
        if len(hits) > 1:
            raise ManifestError(
                f"more than one {MANIFEST_NAME} under {ancestor}"
            )
        if hits:
            return hits[0]
    return None


def _require_relative(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ManifestError(f"{field} must be a non-empty string")
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts:
        raise ManifestError(f"{field} must stay inside the workspace: {value}")
    return value


def load_planning_manifest(file: Path) -> PlanningManifest:
    """Read and validate a manifest; every named file MUST exist."""
    try:
        data = tomllib.loads(file.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ManifestError(f"{file}: {error}") from error
    if data.get("version") != 1:
        raise ManifestError(f"{file}: version must be 1")
    root = file.parent
    workspace = root.parent
    adjudication = root / _require_relative(
        data.get("adjudication"), "adjudication"
    )
    if not adjudication.is_file():
        raise ManifestError(f"{file}: adjudication {adjudication} is missing")
    governed_dirs = tuple(data.get("governed_dirs", DEFAULT_GOVERNED_DIRS))
    raw_specs = data.get("specifications")
    if not isinstance(raw_specs, list) or not raw_specs:
        raise ManifestError(f"{file}: specifications must be a non-empty list")
    specs: list[Specification] = []
    for index, raw in enumerate(raw_specs):
        field = f"specifications[{index}]"
        path = root / _require_relative(raw.get("path"), f"{field}.path")
        if not path.is_file():
            raise ManifestError(f"{file}: {field}.path {path} is missing")
        governs = raw.get("governs")
        if not isinstance(governs, list) or not governs:
            raise ManifestError(f"{file}: {field}.governs must be a list")
        texts = tuple(
            _require_relative(item, f"{field}.governs") for item in governs
        )
        specs.append(
            Specification(
                path=path,
                governs=tuple(workspace / item for item in texts),
                governs_text=texts,
            )
        )
    return PlanningManifest(
        file=file,
        root=root,
        workspace=workspace,
        adjudication=adjudication,
        governed_dirs=governed_dirs,
        specifications=tuple(specs),
    )


def _is_within(path: Path, base: Path) -> bool:
    return path == base or base in path.parents


def resolve_absolute(path: str, workspace: Path) -> Path:
    """Return an absolute path, joining relative input to the workspace."""
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = workspace / candidate
    try:
        return candidate.resolve()
    except OSError:
        return candidate


def find_governing_specifications(
    manifest: PlanningManifest, path: str
) -> list[Specification] | None:
    """Return the specs that govern a path, or None when no gate applies."""
    target = resolve_absolute(path, manifest.workspace)
    if _is_within(target, manifest.root.resolve()):
        return []
    if not any(part in manifest.governed_dirs for part in target.parts):
        return None
    hits = [
        spec
        for spec in manifest.specifications
        if any(_is_within(target, base.resolve()) for base in spec.governs)
    ]
    return hits or None


def find_specifications_in_command(
    manifest: PlanningManifest, command: str
) -> list[Specification] | None:
    """Return the specs whose governed paths a shell command names."""
    if str(manifest.root) in command:
        return []
    if not any(name in command for name in manifest.governed_dirs):
        return None
    hits = []
    for spec in manifest.specifications:
        names = [str(base) + "/" for base in spec.governs] + [
            text.rstrip("/") + "/" for text in spec.governs_text
        ]
        if any(name in command for name in names):
            hits.append(spec)
    return hits or None
