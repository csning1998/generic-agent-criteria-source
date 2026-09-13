---
name: skill-transcribe-youtube-video-to-notion-resources
effort: medium
description: >
    Sequence yt-dlp, Buzz, and Notion write for watch URLs the owner
    picked. Use when the user asks to download, transcribe, and file
    YouTube videos in one pass, or runs /skill-transcribe-youtube-video-to-notion-resources.
    Each write still needs an explicit ask in the current turn.
metadata:
    short-description: "Transcribe YouTube video to Notion Resources layer"
---

# Transcribe YouTube video to Notion Resources

Layer that sequences three modules. This file owns YouTube Resource fill.

## When to Use

The owner named one or more watch URLs and asked to transcribe and file them.

## Input Requirements

- Required: watch URLs from the owner in this turn.
- Optional: Topic and Area pages the owner named.

Read `~/.grok/skills/modules/shared/write-gate.md`.

## Process

1. For each watch URL, fill yt-dlp JSON and call `~/.grok/skills/skill-module-yt-dlp/SKILL.md`. Keep `media_path` and `watch_url` from `YtDlpResult`.

```json
{
    "mode": "download",
    "url": "<watch URL>",
    "outdir": "~/Videos",
    "playlist_end": null,
    "dateafter": null
}
```

1. Probe Buzz. Stop the file when `cuda_available` is false. Fill Buzz JSON from the language table in `skill-buzz-transcribe` and call `~/.grok/skills/skill-module-buzz-transcribe/SKILL.md`. Keep `transcript_path`.
2. Call `~/.grok/skills/skill-module-media-tags/SKILL.md` with `{"media_path":"<media_path>"}`. Fill `VideoResourcePayload` from `MediaTags` using the table below.
3. Locate Resources through `~/.grok/skills/skill-module-inspect-second-brain/SKILL.md` with `{"object":"Resources","docs_root":"<home>/.grok/docs/second-brain"}`.
4. Create `/tmp/skill-transcribe-youtube-video-to-notion-resources/<id>/` with mode `0700`. Write each module JSON and the filled `VideoResourcePayload` there. Do not paste a live title or transcript into this skill file. Do not delete the directory after the write.
5. Lookup then, when the write gate allows it, send `payload_path` to `~/.grok/skills/skill-module-file-notion-resources/SKILL.md`.

| Payload key            | Value                                                                       |
| ---------------------- | --------------------------------------------------------------------------- |
| `Title`                | `YYYYMMDD` from tag `date` (date digits only) plus a space plus tag `title` |
| `Type`                 | `Video`                                                                     |
| `userDefined:URL`      | tag `comment`                                                               |
| `Author`               | tag `artist`                                                                |
| `Publisher`            | empty                                                                       |
| `date:Published:start` | tag `date` rewritten as `YYYY-MM-DD`                                        |
| `Description`          | tag `description`, or `synopsis` when `description` is null                 |
| `content`              | full text of `transcript_path`                                              |
| `AI Summary`           | empty                                                                       |

`Created time` is Notion system time. Do not put the upload date there. Do not write this table into Second Brain.

## Output

Artifact `VideoResourcePayload` plus artifact `ResourceFiled`.

```json
{
    "Title": "YYYYMMDD video title",
    "Type": "Video",
    "userDefined:URL": "https://www.youtube.com/watch?v=ID",
    "Author": "channel",
    "Publisher": "",
    "date:Published:start": "YYYY-MM-DD",
    "Description": "youtube description",
    "content": "transcript text",
    "AI Summary": "",
    "media_path": "<media_path>",
    "transcript_path": "<transcript_path>"
}
```

## Validation Checklist

- [ ] Each module received JSON this layer filled
- [ ] Notion module received `payload_path` only
- [ ] yt-dlp and Buzz modules were not edited to know Notion keys

## Backtrack Triggers

- Any module `ok` false: stop that URL and keep going only when the owner asked to continue the list.
- CUDA false: do not transcribe on CPU.
- Lookup hit: skip create. When the owner asked to file in this turn, update that page with the payload.

## Example

Owner pastes four youtu.be URLs and says 「下載、轉譯、灌」. Layer runs download, Buzz, tags, then one Notion create per URL.
