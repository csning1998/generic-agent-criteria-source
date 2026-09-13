#!/usr/bin/env python3
"""Cursor stop hook: scan the last assistant turn for assistant-output bans."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


EM_DASH = "\u2014"
EMOJI_PATTERN = re.compile(
    "[\U0001f300-\U0001faff\U00002700-\U000027bf\U0001f600-\U0001f64f]+",
)
SYCOPHANCY_PATTERNS = (
    "非常榮幸為您服務",
    "非常荣幸为您服务",
)


def _is_assistant_event(event: dict) -> bool:
    """Return True when the transcript event is an assistant turn."""
    role = event.get("role") or event.get("type")
    if role in ("assistant", "assistant_message"):
        return True
    if event.get("type") == "assistant":
        return True
    message = event.get("message")
    return isinstance(message, dict) and message.get("role") == "assistant"


def _content_text(content: object) -> str:
    """Flatten assistant content blocks into one string."""
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for block in content:
        if isinstance(block, dict):
            text = block.get("text")
            if isinstance(text, str):
                parts.append(text)
        elif isinstance(block, str):
            parts.append(block)
    return "".join(parts)


def last_assistant_text(transcript_path: str) -> str:
    """Return the last assistant message text from a Cursor transcript."""
    if not transcript_path:
        return ""
    path = Path(transcript_path)
    if not path.is_file():
        return ""
    last = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not _is_assistant_event(event):
            continue
        message = event.get("message", event)
        if isinstance(message, dict):
            content = message.get("content", event.get("text"))
        else:
            content = event.get("text")
        text = _content_text(content)
        if text.strip():
            last = text
    return last


def finding(text: str) -> str | None:
    """Return a short ban reason when text hits assistant-output rules."""
    if EM_DASH in text:
        return "em dash (U+2014)"
    if EMOJI_PATTERN.search(text):
        return "emoji"
    for phrase in SYCOPHANCY_PATTERNS:
        if phrase in text:
            return f"sycophancy phrase {phrase!r}"
    return None


def main() -> None:
    """Emit a stop followup_message when the last assistant turn is banned."""
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        print("{}")
        return
    if payload.get("status") not in (None, "completed"):
        print("{}")
        return
    loop_count = int(payload.get("loop_count") or 0)
    if loop_count >= 3:
        print("{}")
        return
    transcript = str(
        payload.get("transcript_path") or payload.get("transcriptPath") or ""
    )
    text = last_assistant_text(transcript)
    hit = finding(text)
    if hit is None:
        print("{}")
        return
    print(
        json.dumps(
            {
                "followup_message": (
                    "assistant-output.md: rewrite the last assistant reply. "
                    f"Remove the banned span ({hit}) and resend a clean reply."
                )
            }
        )
    )


if __name__ == "__main__":
    main()
