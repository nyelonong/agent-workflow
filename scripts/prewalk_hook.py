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


AGY_EDIT_TOOLS = {"edit", "replace", "write_to_file", "create_file"}
AGY_PLAN_NUDGE = (
    "Prewalk phase 1. Before any further exploration, write the complete plan for this task in your next reply: "
    "every remaining step in order with exact files, symbols, commands and checks; the risks and how each step is "
    "verified; what is already done. Restate it as a numbered checklist of 5-9 concrete items, each naming its target "
    "and its verification, then continue into implementation. Do not ask for approval: implementation of this exact "
    "scope is already approved. When a tool call is denied with a prewalk handoff reason, stop editing immediately and "
    "end your turn with a short summary of the remaining checklist items."
)


def agy(state_path: str, event_name: str, event: dict) -> dict | None:
    """Antigravity hooks while armed. Empty stdout is the neutral answer on every
    event and "{}" denies a tool call, so only a denial, an injection, or a
    continue decision is ever printed; permissions otherwise follow the user's mode."""
    tool = (event.get("toolCall") or {}).get("name") if isinstance(event.get("toolCall"), dict) else None
    state = read_state(state_path)
    if event_name == "PreInvocation":
        if "edit" in state or "nudged" in state:
            return None
        record(state_path, "nudged")
        return {"injectSteps": [{"ephemeralMessage": AGY_PLAN_NUDGE}]}
    if event_name == "Stop":
        # A plan-only run would end before any edit; push on once, like Pi's continue nudge.
        if "edit" in state or "continued" in state or "nudged" not in state:
            return None
        record(state_path, "continued")
        return {"decision": "continue", "reason": "Continue the task now — do not end on the plan alone."}
    if event_name == "PreToolUse":
        if tool in AGY_EDIT_TOOLS and "edit" in state:
            return {"decision": "deny", "reason": HANDOFF_REASON}
        return None
    if event_name == "PostToolUse":
        if tool in AGY_EDIT_TOOLS and not event.get("error"):
            record(state_path, "edit")
        return None
    return None


def read_event() -> dict | None:
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return None
    return event if isinstance(event, dict) else None


def main(argv: list[str]) -> int:
    runtime = argv[1] if len(argv) > 1 else ""
    if runtime == "claude":
        state_path = os.environ.get("CLAUDE_PREWALK_STATE")
        if not state_path:
            return 0
        event = read_event()
        if event is None:
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
    if runtime == "agy":
        event_name = argv[2] if len(argv) > 2 else ""
        state_path = os.environ.get("AGY_PREWALK_STATE")
        event = read_event() or {}
        if not state_path:
            # Not armed: print nothing. Empty stdout leaves the normal permission
            # flow untouched, whereas "{}" is treated as a denial.
            return 0
        try:
            output = agy(state_path, event_name, event)
        except OSError as error:
            print(f"prewalk_hook: {error}", file=sys.stderr)
            output = None
        if output is not None:
            print(json.dumps(output))
        return 0
    print(f"prewalk_hook: unknown runtime {runtime!r}", file=sys.stderr)
    return 64


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
