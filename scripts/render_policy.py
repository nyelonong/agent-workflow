#!/usr/bin/env python3
"""Render portable policy and compose the managed Pi policy block from canonical sources."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PI_START = "<!-- personal-workflow:pi:start -->"
PI_END = "<!-- personal-workflow:pi:end -->"


def read_source(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError(f"{path} is empty")
    return text.rstrip() + "\n"


def render(source: str) -> str:
    """Return canonical portable policy with a stable trailing newline."""
    if "<!-- pi-only:" in source:
        raise ValueError("portable policy must not contain Pi-only markers")
    return source.rstrip() + "\n"


def pi_block(policy: str, adapter: str) -> str:
    if PI_START in policy or PI_END in policy or PI_START in adapter or PI_END in adapter:
        raise ValueError("Pi managed markers belong to the renderer, not a source")
    return f"{PI_START}\n{render(policy).rstrip()}\n\n{adapter.rstrip()}\n{PI_END}\n"


def replace_pi_block_bytes(content: bytes, block: str) -> bytes:
    """Splice a Pi block without normalizing unmanaged bytes or line endings."""
    start = PI_START.encode("ascii")
    end = PI_END.encode("ascii")
    starts = content.count(start)
    ends = content.count(end)
    if starts != ends:
        raise ValueError("Pi instructions contain incomplete managed markers")
    if starts > 1:
        raise ValueError("Pi instructions contain duplicate managed blocks")

    newline = b"\r\n" if b"\r\n" in content else b"\n"
    rendered = block.encode("utf-8").replace(b"\n", newline)
    if starts:
        pattern = re.compile(
            rb"(?m)^" + re.escape(start) + rb"\r?$.*?^" + re.escape(end) + rb"\r?$",
            re.DOTALL,
        )
        matches = list(pattern.finditer(content))
        if len(matches) != 1:
            raise ValueError("Pi instructions contain malformed managed block")
        match = matches[0]
        # The newline after the end marker belongs to the unmanaged suffix. The
        # regex consumes CR before LF under multiline matching, so restore it.
        suffix_cr = b"\r" if content[match.end() - 1 : match.end()] == b"\r" else b""
        return content[: match.start()] + rendered.rstrip(b"\r\n") + suffix_cr + content[match.end() :]
    if not content:
        return rendered
    # Preserve markerless instructions exactly, including trailing whitespace.
    separator = b"" if content.endswith(newline * 2) else newline if content.endswith(newline) else newline * 2
    return content + separator + rendered


def replace_pi_block(text: str, block: str) -> str:
    """Text compatibility wrapper for callers that do not require byte preservation."""
    return replace_pi_block_bytes(text.encode("utf-8"), block).decode("utf-8")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", type=Path, nargs="?", default=ROOT / "policy/core.md")
    parser.add_argument("--output", type=Path, default=ROOT / "policy.md")
    parser.add_argument("--check", action="store_true", help="exit 1 when output is stale instead of writing")
    args = parser.parse_args(argv[1:])
    try:
        rendered = render(read_source(args.source))
    except (OSError, ValueError) as error:
        print(f"render_policy: {error}", file=sys.stderr)
        return 1
    current = args.output.read_text(encoding="utf-8") if args.output.exists() else None
    if args.check:
        if current != rendered:
            print(f"render_policy: {args.output} is stale relative to {args.source}", file=sys.stderr)
            return 1
        return 0
    if current != rendered:
        args.output.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
