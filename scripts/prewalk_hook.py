#!/usr/bin/env python3
"""Prewalk hooks. Inert unless the wrapper exported the state-file variable."""
from __future__ import annotations

import json
import os
import sys

CLAUDE_EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
CLAUDE_TODO_TOOL = "TodoWrite"
HANDOFF_REASON = "Prewalk handoff: stop editing now and end your turn with a short summary of the remaining todo items."


def read_state(path: str) -> set[str]:
    try:
        with open(path, encoding="utf-8") as handle:
            return {line.strip() for line in handle if line.strip()}
    except FileNotFoundError:
        return set()


def record(path: str, marker: str) -> None:
    if marker in read_state(path):
        return
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(marker + "\n")


def claude(state_path: str, event: dict) -> dict | None:
    name = event.get("hook_event_name")
    tool = event.get("tool_name")
    state = read_state(state_path)
    # Claude Code 2.1.261 ships no TodoWrite tool, so the todo gate is opt-in here.
    require_todo = os.environ.get("CLAUDE_PREWALK_REQUIRE_TODO", "0") == "1"
    if name == "PostToolUse":
        if tool == CLAUDE_TODO_TOOL:
            record(state_path, "todo")
        elif tool in CLAUDE_EDIT_TOOLS and ("todo" in state or not require_todo):
            record(state_path, "edit")
        return None
    if name == "PreToolUse" and tool in CLAUDE_EDIT_TOOLS and "edit" in state:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": HANDOFF_REASON,
            }
        }
    return None


def main(argv: list[str]) -> int:
    runtime = argv[1] if len(argv) > 1 else ""
    if runtime != "claude":
        print(f"prewalk_hook: unknown runtime {runtime!r}", file=sys.stderr)
        return 64
    state_path = os.environ.get("CLAUDE_PREWALK_STATE")
    if not state_path:
        return 0
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if not isinstance(event, dict):
        return 0
    try:
        output = claude(state_path, event)
    except OSError as error:
        # Fail open: an unwritable state file must never block an edit.
        print(f"prewalk_hook: {error}", file=sys.stderr)
        return 0
    if output is not None:
        print(json.dumps(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
