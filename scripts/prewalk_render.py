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


def render_agy(line: str) -> str | None:
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        return None
    kind = event.get("event")
    if kind == "init":
        return f"[init] model {(event.get('init') or {}).get('model', '?')}"
    if kind == "step_update":
        step = event.get("step_update") or {}
        if step.get("step_type") == "tool" and step.get("state") == "ACTIVE":
            params = (step.get("tool_info") or {}).get("parameters") or {}
            target = params.get("TargetFile") or params.get("CommandLine") or ""
            return f"  > {step.get('tool_name', '?')}{': ' + str(target)[:100] if target else ''}"
        error = (step.get("tool_info") or {}).get("error")
        if step.get("step_type") == "tool" and error:
            return f"  ! {step.get('tool_name', '?')}: {error.get('message', '')[:120]}"
        delta = step.get("text_delta")
        if step.get("step_type") == "agent_response" and delta and delta.strip():
            return delta.rstrip()
        return None
    if kind == "result":
        result = event.get("result") or {}
        return f"[result] {result.get('status', '?')} turns {result.get('num_turns', '?')}"
    return None


def conversation_id(line: str) -> str | None:
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        return None
    return event.get("conversation_id") if event.get("event") == "init" else None


def main(argv: list[str]) -> int:
    runtime = argv[1] if len(argv) > 1 else "claude"
    id_path = argv[2] if len(argv) > 2 else None
    renderer = render_agy if runtime == "agy" else render
    init_marker = '"event":"init"' if runtime == "agy" else '"subtype":"init"'
    started = False
    for line in sys.stdin:
        if init_marker in line or init_marker.replace(":", ": ") in line:
            started = True
            if id_path and runtime == "agy":
                cid = conversation_id(line)
                if cid:
                    with open(id_path, "w", encoding="utf-8") as handle:
                        handle.write(cid)
        text = renderer(line)
        if text:
            print(text, flush=True)
    # A stream with no init event means the agent never started (auth, bad model, missing binary).
    return 0 if started else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
