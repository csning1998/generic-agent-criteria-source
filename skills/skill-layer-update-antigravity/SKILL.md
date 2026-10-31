---
name: skill-layer-update-antigravity
effort: low
description: >
    Update Google Antigravity IDE and Antigravity 2.0 Agent Manager on Linux
    from official tarballs on antigravity.google/download. Use when the user
    asks to update Antigravity, upgrade Antigravity IDE, update Agent Manager,
    refresh the Antigravity hub, or runs /skill-layer-update-antigravity.
metadata:
    short-description: "Update Antigravity IDE and Agent Manager"
---

# Update Antigravity

Layer for tooling.

## When to Use

The owner asked to update Antigravity IDE, Agent Manager, or both.

## Input Requirements

- Required: the product names from the owner. Bare 「Antigravity」 means both.

Read `modules/shared/write-gate.md`.

## Process

1. Send `{"op":"probe"}` to `skills/skill-module-update-antigravity/SKILL.md`.
2. Fill replace JSON from this probe. Use `ideVersion` in `product.json` as the IDE version. Do not use `antigravity-ide --version`.
3. Skip a product whose live version matches the official version.
4. Official hosts only: `storage.googleapis.com`, `dl.google.com`, `edgedl.me.gvt1.com`.
5. If `/opt` needs sudo and sudo is blocked, set `hub_root` to `~/.local/share/antigravity/Antigravity-x64`.
6. Call the module with `op` `replace` via `scripts/replace.py`. Then restore desktop icons (copying `code.png` to `antigravity.png` for IDE, extracting icon from `app.asar` for Hub), keep existing symlink paths, and match previous `chrome-sandbox` mode (`4755` for IDE, `755` for Hub).

Typical IDE root is `~/.local/share/antigravity-ide`. Typical hub roots are `~/.local/share/antigravity/Antigravity-x64` or `/opt/antigravity/Antigravity-x64`.

Do not touch `~/.antigravity-ide` or the config directories. Do not update CLI or SDK unless asked.

## Output

Artifact `AntigravityResult` plus a short report of old version, new version, live path, and backup path.

## Validation Checklist

- [ ] URLs came from this probe
- [ ] User data directories were not modified
- [ ] Replace ran only after an ask in this turn

## Backtrack Triggers

- Probe `ok` false: stop.
- `/opt` sudo denied: switch `hub_root` and retry replace.

## Example

Owner says 「更新 Antigravity」. Layer probes, fills both products, then replaces through the module.
