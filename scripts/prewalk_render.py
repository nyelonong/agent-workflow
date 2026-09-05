#!/usr/bin/env python3
"""Render Claude Code stream-json to a terminal: model, text, tool names, result."""
from __future__ import annotations

import json
import sys


def describe_tool(block: dict) -> str:
    name = block.get("name", "?")
    tool_input = block.get("input") or {}
    for key in ("file_path", "command", "pattern", "description"):
        value = tool_input.get(key)
        if isinstance(value, str) and value:
            return f"{name}: {value[:100]}"
    return name


def render(line: str) -> str | None:
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        return None
    kind = event.get("type")
    if kind == "system" and event.get("subtype") == "init":
        return f"[init] model {event.get('model', '?')}"
    if kind == "assistant":
        parts = []
        for block in (event.get("message") or {}).get("content") or []:
            if block.get("type") == "text" and block.get("text", "").strip():
                parts.append(block["text"].rstrip())
            elif block.get("type") == "tool_use":
                parts.append(f"  > {describe_tool(block)}")
        return "\n".join(parts) if parts else None
    if kind == "result":
        cost = event.get("total_cost_usd")
        cost_text = f" cost ${cost:.4f}" if isinstance(cost, (int, float)) else ""
        return f"[result] {event.get('subtype', '?')} turns {event.get('num_turns', '?')}{cost_text}"
    return None


def main() -> int:
    started = False
    for line in sys.stdin:
        if '"subtype": "init"' in line or '"subtype":"init"' in line:
            started = True
        text = render(line)
        if text:
            print(text, flush=True)
    # A stream with no init event means claude never started (auth, bad model, missing binary).
    return 0 if started else 1


if __name__ == "__main__":
    raise SystemExit(main())
