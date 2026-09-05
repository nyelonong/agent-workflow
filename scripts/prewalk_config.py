#!/usr/bin/env python3
"""Print effective prewalk defaults for a wrapper: `prewalk_config.py <runtime> <key>...`.

Reads ~/.config/prewalk/config.json (or $XDG_CONFIG_HOME/prewalk/config.json).
Prints one `key=value` line per requested key that the file defines. A missing
file prints nothing; invalid JSON prints nothing and warns once on stderr, so
the wrapper keeps its shipped defaults either way.
"""
from __future__ import annotations

import json
import os
import sys


def config_path(env: dict[str, str] | None = None) -> str:
    env = os.environ if env is None else env
    base = env.get("XDG_CONFIG_HOME") or os.path.join(env.get("HOME", ""), ".config")
    return os.path.join(base, "prewalk", "config.json")


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
    data, warning = load(config_path())
    if warning:
        print(f"prewalk: {warning}", file=sys.stderr)
    section = data.get(runtime)
    if not isinstance(section, dict):
        return 0
    for key in keys:
        value = section.get(key)
        if isinstance(value, (str, int, float)) and not isinstance(value, bool):
            print(f"{key}={value}")
        elif isinstance(value, bool):
            print(f"{key}={'true' if value else 'false'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
