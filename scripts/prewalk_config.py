#!/usr/bin/env python3
"""Print effective prewalk defaults for a wrapper: `prewalk_config.py <runtime> <key>...`.

Each runtime keeps its own flat file: `claude` reads ~/.claude/prewalk.json (or
$CLAUDE_CONFIG_DIR/prewalk.json), `agy` reads ~/.gemini/prewalk.json. Prints one
`key=value` line per requested key that the file defines. A missing file prints
nothing; invalid JSON prints nothing and warns once on stderr, so the wrapper
keeps its shipped defaults either way.
"""
from __future__ import annotations

import json
import os
import sys


CONFIG_DIRS = {"claude": (".claude", "CLAUDE_CONFIG_DIR"), "agy": (".gemini", None)}


def config_path(runtime: str, env: dict[str, str] | None = None) -> str | None:
    env = os.environ if env is None else env
    entry = CONFIG_DIRS.get(runtime)
    if entry is None:
        return None
    default_dir, override = entry
    base = (env.get(override) if override else None) or os.path.join(env.get("HOME", ""), default_dir)
    return os.path.join(base, "prewalk.json")


def load(path: str) -> tuple[dict, str | None]:
    try:
        with open(path, encoding="utf-8") as handle:
            raw = handle.read()
    except OSError:
        return {}, None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as error:
        return {}, f"{path} is not valid JSON ({error.msg}); using defaults."
    if not isinstance(data, dict):
        return {}, f"{path} must contain a JSON object; using defaults."
    return data, None


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("usage: prewalk_config.py <runtime> <key>...", file=sys.stderr)
        return 64
    runtime, keys = argv[1], argv[2:]
    path = config_path(runtime)
    if path is None:
        print(f"prewalk_config.py: unknown runtime {runtime}", file=sys.stderr)
        return 64
    data, warning = load(path)
    if warning:
        print(f"prewalk: {warning}", file=sys.stderr)
    for key in keys:
        value = data.get(key)
        if isinstance(value, (str, int, float)) and not isinstance(value, bool):
            print(f"{key}={value}")
        elif isinstance(value, bool):
            print(f"{key}={'true' if value else 'false'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
