---
name: skill-module-update-antigravity
effort: low
description: >
    Execute Antigravity probe, download, stop, and replace from JSON
    a layer already filled. Use when skill-layer-update-antigravity hands
    off that JSON, or when the user runs /skill-module-update-antigravity.
metadata:
    short-description: "Execute Antigravity replace from JSON"
---

# Module update Antigravity

## When to Use

A layer already chose products, URLs, and install roots.

## Input Requirements

```json
{
    "op": "replace",
    "products": ["ide", "hub"],
    "ide_url": "https://storage.googleapis.com/...",
    "hub_url": "https://storage.googleapis.com/...",
    "ide_root": "~/.local/share/antigravity-ide",
    "hub_root": "~/.local/share/antigravity/Antigravity-x64",
    "old_ide_version": "1.0.0",
    "old_hub_version": "2.0.0",
    "extract_hub_icon": false
}
```

`op` is `probe` or `replace`. For `probe`, the URL and root keys may be omitted.

Optional `ide_sha256` and `hub_sha256` carry a 64-hex digest. The archive is rejected on mismatch. The upstream download page and release index publish no checksum or signature (checked 2026-10-31). The digest must come from the owner.
Every `old_*_version` MUST match `[A-Za-z0-9][A-Za-z0-9._+-]*` without `..`.
Every `*_root` MUST resolve under `/opt` or at least two levels below the home directory.

## Process

1. For `probe`, run `scripts/probe.py` and return official URLs plus detected installs.
2. For `replace`, run `scripts/replace.py --payload '<json>'` (or pass the JSON via stdin / file).
3. Stage each product tree in the same filesystem under `.<root_name>.staging` to guarantee atomic moves without cross-device link errors.
4. Stop the main PID from `ps -eo pid,ppid,args`. Never use `pgrep -f`.
5. `mv` each live root to a `.bak.<old_version>` suffix, then `mv` the staged tree onto that root.
6. Restore desktop icons. For IDE, copy `code.png` to `antigravity.png` under `resources/app/resources/linux/` if absent. For Hub, extract `icon.png` from `resources/app.asar` when `extract_hub_icon` is true.
7. Set `chrome-sandbox` permissions. Try `4755` with `755` fallback for IDE, and use `755` for Hub.

```bash
python3 scripts/probe.py
python3 scripts/replace.py --payload payload.json
```

## Output

Artifact `AntigravityResult`.

```json
{
    "ok": true,
    "error": null,
    "op": "replace",
    "probe": {},
    "backups": ["~/.local/share/antigravity-ide.bak.1.0.0"]
}
```

## Validation Checklist

- [ ] Product list matches the input JSON
- [ ] User data under `~/.antigravity-ide` was not touched

## Backtrack Triggers

- curl to a non-Google host, including a redirect hop to one: `ok` false. The layer must send an official URL.
- Any product failing validation or download: no live root is touched, because all products are validated and staged before the first replacement.
- Move failure after backup: the backup is renamed back to the live root.
- sudo required for `/opt` and unavailable: `ok` false. The layer switches `hub_root`.

## Example

Layer sends `{"op":"probe"}`, then a filled `replace` object.
