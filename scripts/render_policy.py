#!/usr/bin/env python3
"""Render the portable policy from Pi's global instructions.

    render_policy.py <pi-agents-md> [--output policy.md] [--check]

Pi's AGENTS.md is the hand-written master. Paragraphs between
`<!-- pi-only:start -->` and `<!-- pi-only:end -->` are Pi mechanics and are
dropped; everything else becomes policy.md under a fixed title.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

START = "<!-- pi-only:start -->"
END = "<!-- pi-only:end -->"
TITLE = "# Personal engineering workflow"


def render(source: str) -> str:
    out: list[str] = []
    inside = False
    for number, line in enumerate(source.splitlines(), start=1):
        stripped = line.strip()
        if stripped == START:
            if inside:
                raise ValueError(f"line {number}: nested {START}")
            inside = True
            continue
        if stripped == END:
            if not inside:
                raise ValueError(f"line {number}: {END} without a start")
            inside = False
            continue
        if START in line or END in line:
            raise ValueError(f"line {number}: marker must stand alone on its line")
        if not inside:
            out.append(line.rstrip())
    if inside:
        raise ValueError(f"unterminated {START}")
    body = re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip("\n")
    # Pi keeps hard-wrapped prose; the portable file uses one line per paragraph.
    paragraphs = [" ".join(part.split("\n")) if not part.startswith("#") else part for part in body.split("\n\n")]
    return f"{TITLE}\n\n" + "\n\n".join(paragraphs) + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "policy.md")
    parser.add_argument("--check", action="store_true", help="exit 1 when the output is stale instead of writing")
    args = parser.parse_args(argv[1:])
    try:
        rendered = render(args.source.read_text(encoding="utf-8"))
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
