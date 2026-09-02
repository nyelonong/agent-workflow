#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
MANAGED = ".personal-workflow-managed"
GEMINI_START = "<!-- personal-workflow:agy:start -->"
GEMINI_END = "<!-- personal-workflow:agy:end -->"
GALDR_START = "<!-- galdr:start -->"
GALDR_END = "<!-- galdr:end -->"


def fail(message: str) -> None:
    raise RuntimeError(message)


def managed_block() -> str:
    adapter = (ROOT / "adapters/agy/GEMINI.md").read_text(encoding="utf-8").strip()
    return f"{GEMINI_START}\n@{ROOT / 'policy.md'}\n\n{adapter}\n{GEMINI_END}"


def replace_marked_block(text: str, block: str) -> str:
    has_start = GEMINI_START in text
    has_end = GEMINI_END in text
    if has_start != has_end:
        fail("GEMINI.md contains an incomplete personal-workflow block")
    if has_start:
        pattern = re.compile(
            rf"(?m)^{re.escape(GEMINI_START)}$.*?^{re.escape(GEMINI_END)}$",
            re.DOTALL,
        )
        if len(pattern.findall(text)) != 1:
            fail("GEMINI.md must contain exactly one personal-workflow block")
        return pattern.sub(block, text)
    if not text:
        return block + "\n"
    return text.rstrip() + "\n\n" + block + "\n"


def remove_galdr_block(path: Path, *, check: bool) -> None:
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    has_start = GALDR_START in text
    has_end = GALDR_END in text
    if has_start != has_end:
        fail(f"{path} contains an incomplete Galdr block")
    if not has_start:
        return
    if check:
        fail(f"{path} still contains the old Galdr block")
    pattern = re.compile(
        rf"(?m)^{re.escape(GALDR_START)}$.*?^{re.escape(GALDR_END)}$\n?",
        re.DOTALL,
    )
    if len(pattern.findall(text)) != 1:
        fail(f"{path} must contain exactly one Galdr block")
    updated = pattern.sub("", text)
    if not updated.strip():
        path.unlink()
    else:
        atomic_write(path, updated)


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o600
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    os.chmod(temporary, mode)
    temporary.replace(path)


def preflight_directory(target: Path) -> None:
    if target.exists() and not (target / MANAGED).is_file():
        fail(f"refusing to replace unmanaged path: {target}")


def install_directory(source: Path, target: Path) -> None:
    preflight_directory(target)
    if target.exists():
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target)
    (target / MANAGED).write_text(f"source={source}\n", encoding="utf-8")


def check_directory(source: Path, target: Path) -> None:
    if not (target / MANAGED).is_file():
        fail(f"managed path is missing: {target}")
    expected = {
        path.relative_to(source): path.read_bytes()
        for path in source.rglob("*")
        if path.is_file()
    }
    actual = {
        path.relative_to(target): path.read_bytes()
        for path in target.rglob("*")
        if path.is_file() and path.name != MANAGED
    }
    if actual != expected:
        fail(f"managed path differs from source: {target}")


def agy_paths(home: Path) -> list[tuple[Path, Path]]:
    return [
        (ROOT / "skills/workflow", home / ".gemini/config/skills/workflow"),
        (ROOT / "adapters/agy/agents/oracle", home / ".gemini/config/agents/oracle"),
        (ROOT / "adapters/agy/agents/reviewer", home / ".gemini/config/agents/reviewer"),
    ]


def install_agy(home: Path) -> None:
    paths = agy_paths(home)
    for _, target in paths:
        preflight_directory(target)

    gemini = home / ".gemini/GEMINI.md"
    existing = gemini.read_text(encoding="utf-8") if gemini.exists() else ""
    rendered = replace_marked_block(existing, managed_block())

    remove_galdr_block(home / ".gemini/AGENTS.md", check=False)
    atomic_write(gemini, rendered)
    for source, target in paths:
        install_directory(source, target)


def check_agy(home: Path) -> None:
    gemini = home / ".gemini/GEMINI.md"
    if not gemini.is_file():
        fail(f"managed file is missing: {gemini}")
    text = gemini.read_text(encoding="utf-8")
    if replace_marked_block(text, managed_block()) != text:
        fail(f"managed block differs from source: {gemini}")
    remove_galdr_block(home / ".gemini/AGENTS.md", check=True)
    for source, target in agy_paths(home):
        check_directory(source, target)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install the personal workflow adapters")
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("action", choices=("install", "check"))
    parser.add_argument("runtime", choices=("agy",))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.action == "install":
            install_agy(args.home)
        else:
            check_agy(args.home)
    except RuntimeError as error:
        print(f"install.py: {error}", file=sys.stderr)
        return 1
    print(f"{args.runtime} personal workflow: {args.action} ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
