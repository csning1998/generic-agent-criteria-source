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

## Process

1. For `probe`, run `scripts/probe.py` and return official URLs plus detected installs.
2. For `replace`, curl and tar only the URLs present in the JSON.
3. Stop the main PID from `ps -eo pid,ppid,args`. Never use `pgrep -f`.
4. `mv` each live root to a `.bak.<old_version>` suffix, then `mv` the staged tree onto that root.
5. Extract the hub icon only when `extract_hub_icon` is true.

```bash
python3 scripts/probe.py
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

- curl to a non-Google host: `ok` false. The layer must send an official URL.
- sudo required for `/opt` and unavailable: `ok` false. The layer switches `hub_root`.

## Example

Layer sends `{"op":"probe"}`, then a filled `replace` object.
