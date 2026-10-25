---
name: skill-layer-yt-dlp
effort: low
description: >
    List YouTube videos with yt-dlp and download only the URLs the
    owner picked. Use when the user names a video or channel URL,
    asks to list new uploads, asks to download a picked video, or
    runs /skill-layer-yt-dlp. Default is list-only. Download requires an
    explicit ask in the current turn.
metadata:
    short-description: "List and download picked YouTube videos"
---

# yt-dlp

Layer for media ingest download.

## When to Use

The owner named a watch URL, a channel URL, or asked what is new.

## Input Requirements

- Required: a URL from the owner in this turn.
- Optional artifact: none.

Read `~/.grok/skills/modules/shared/write-gate.md`.

User config at `~/.config/yt-dlp/config` also sets `-P` to `YouTube_cached`. This layer always fills `outdir`.

## Process

1. Fill the module JSON below.
2. Call `~/.grok/skills/skill-module-yt-dlp/SKILL.md`.
3. Report `YtDlpResult`. Do not assemble a Resource payload.

| Key            | Value                                                                                                   |
| -------------- | ------------------------------------------------------------------------------------------------------- |
| `outdir`       | `~/Videos` unless the owner named another directory                                                     |
| `mode`         | `list` by default. `download` only when the write gate allows it and the owner named rows, ids, or URLs |
| `url`          | The owner named watch, id, or channel URL                                                               |
| `playlist_end` | `20` for a channel or `/videos` list. `null` for a single watch URL                                     |
| `dateafter`    | `now-14days` when the owner asked for recent uploads only, otherwise `null`                             |
| `archive_path` | `~/.config/yt-dlp/archive.txt` on download. `null` on list                                              |

Do not pass a channel URL when `mode` is `download`.

## Output

Artifact `WatchMedia` on download. Artifact `YtDlpResult` on list (same JSON as the module).

```json
{
    "media_path": "~/Videos/file.mp4",
    "watch_url": "https://www.youtube.com/watch?v=ID"
}
```

## Validation Checklist

- [ ] `outdir` is explicit
- [ ] Download ran only after an ask in this turn
- [ ] Resource Title was not filled here

## Backtrack Triggers

- Module `ok` false: stop and report `error`.
- Channel URL with download: ask the owner to pick watch URLs.

## Example

`/skill-layer-yt-dlp` plus a `/videos` URL lists twenty rows. `/skill-layer-yt-dlp` plus 「下載第一支」 fills `mode` `download`.
