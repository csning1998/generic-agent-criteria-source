---
name: skill-layer-buzz-transcribe
effort: medium
description: >
    Transcribe local audio or video files with the Buzz Flatpak CLI
    and write a .txt beside each input. Use when the user asks to
    transcribe, run Buzz CLI, or runs /skill-layer-buzz-transcribe.
    Default is list-only. Transcription requires an explicit ask
    in the current turn.
metadata:
    short-description: "Transcribe picked local media with Buzz"
---

# Buzz transcribe

Layer for media ingest transcription.

## When to Use

The owner named local media, or `WatchMedia` just returned from `skill-layer-yt-dlp`.

## Input Requirements

- Required for transcribe: `WatchMedia` from `skill-layer-yt-dlp`, or a local path the owner named.
- Optional: watch URL language field.

Read `~/.grok/skills/modules/shared/write-gate.md`.

## Process

1. When the owner did not name files and no `WatchMedia` is present, list `*.mp4` `*.mkv` `*.webm` `*.m4a` `*.mp3` under `~/Videos` at depth 1. Mark a sibling `[Transcript]*.txt` as already done. Report and stop.
2. Send `{"op":"probe"}` to `~/.grok/skills/skill-module-buzz-transcribe/SKILL.md`. If `cuda_available` is false, stop. Install the Flatpak NVIDIA GL extension that matches `nvidia-smi` driver version, then probe again.
3. After model load, `nvidia-smi --query-compute-apps` MUST show a Python process. If VRAM stays at compositor idle, stop.
4. Fill language from the watch URL language field, else CJK in the title as Chinese, else English. If still unclear, ask the owner.
5. Call the Buzz module once per file with the JSON below. Wait for each `BuzzResult`.
6. Record every `transcript_path`. Do not fill Resource Title here.

| Language | `model_type` | `model_size` | `language` |
| -------- | ------------ | ------------ | ---------- |
| Chinese  | `whisper`    | `medium`     | `zh`       |
| English  | `whisper`    | `medium.en`  | `en`       |

```json
{
    "op": "add",
    "media_path": "<WatchMedia.media_path>",
    "model_type": "whisper",
    "model_size": "medium",
    "language": "zh",
    "extract_speech": "no"
}
```

`extract_speech` is `yes` only when the owner asked in this turn.

## Output

Artifact `TranscriptDone`.

```json
{
    "media_path": "~/Videos/file.mp4",
    "watch_url": "https://www.youtube.com/watch?v=ID",
    "transcript_path": "~/Videos/[Transcript] file.txt",
    "exit_code": 0
}
```

## Validation Checklist

- [ ] CUDA was true before `add`
- [ ] One media path per module call
- [ ] Resource payload was not assembled

## Backtrack Triggers

- `cuda_available` false: do not finish on CPU.
- `exit_code` 134: retry once with the same JSON. Do not close the Buzz window.
- VRAM idle after model load: stop.

## Example

Owner says 「轉譯這支」 after a download. Layer sends probe then add, reports `TranscriptDone`.
