#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
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


CODEX_START = "<!-- personal-workflow:codex:start -->"
CODEX_END = "<!-- personal-workflow:codex:end -->"
MANAGED_HEADER = "# personal-workflow managed"


def managed_block() -> str:
    adapter = (ROOT / "adapters/agy/GEMINI.md").read_text(encoding="utf-8").strip()
    return f"{GEMINI_START}\n@{ROOT / 'policy.md'}\n\n{adapter}\n{GEMINI_END}"


def codex_block() -> str:
    # Codex documents no include directive, so the policy is rendered inline.
    policy = (ROOT / "policy.md").read_text(encoding="utf-8").strip()
    adapter = (ROOT / "adapters/codex/AGENTS.md").read_text(encoding="utf-8").strip()
    return f"{CODEX_START}\n{policy}\n\n{adapter}\n{CODEX_END}"


def replace_marked_block(
    text: str,
    block: str,
    *,
    start: str = GEMINI_START,
    end: str = GEMINI_END,
    label: str = "GEMINI.md",
) -> str:
    has_start = start in text
    has_end = end in text
    if has_start != has_end:
        fail(f"{label} contains an incomplete personal-workflow block")
    if has_start:
        pattern = re.compile(
            rf"(?m)^{re.escape(start)}$.*?^{re.escape(end)}$",
            re.DOTALL,
        )
        if len(pattern.findall(text)) != 1:
            fail(f"{label} must contain exactly one personal-workflow block")
        return pattern.sub(lambda _match: block, text)
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
        (ROOT / "skills/task-review", home / ".gemini/config/skills/task-review"),
        (ROOT / "adapters/agy/agents/architect", home / ".gemini/config/agents/architect"),
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


OMP_START = "<!-- personal-workflow:omp:start -->"
OMP_END = "<!-- personal-workflow:omp:end -->"


def omp_path(home: Path) -> Path:
    return home / ".omp/agent/AGENTS.md"


def omp_block() -> str:
    adapter = (ROOT / "adapters/omp/AGENTS.md").read_text(encoding="utf-8").strip()
    return f"{OMP_START}\n@{ROOT / 'policy.md'}\n\n{adapter}\n{OMP_END}"


def omp_links(home: Path) -> list[tuple[Path, Path]]:
    return [(ROOT / "skills/task-review", home / ".agents/skills/task-review")]


def install_omp(home: Path) -> None:
    agents_path = omp_path(home)
    existing = agents_path.read_text(encoding="utf-8") if agents_path.exists() else ""
    rendered = replace_marked_block(existing, omp_block(), start=OMP_START, end=OMP_END, label="~/.omp/agent/AGENTS.md")
    for source, target in omp_links(home):
        preflight_link(source, target)

    if rendered != existing:
        atomic_write(agents_path, rendered)
    for source, target in omp_links(home):
        install_link(source, target)


def check_omp(home: Path) -> None:
    agents_path = omp_path(home)
    if not agents_path.is_file():
        fail(f"managed file is missing: {agents_path}")
    text = agents_path.read_text(encoding="utf-8")
    if replace_marked_block(text, omp_block(), start=OMP_START, end=OMP_END, label="~/.omp/agent/AGENTS.md") != text:
        fail(f"managed block differs from source: {agents_path}")
    for source, target in omp_links(home):
        if not (source / "SKILL.md").is_file():
            fail(f"skill source is missing: {source / 'SKILL.md'}")
        check_link(source, target)


def claude_links(home: Path) -> list[tuple[Path, Path]]:
    return [
        # Pi owns the Go skill; Claude consumes it read-only through this link.
        (home / ".pi/agent/skills/go-engineering", home / ".claude/skills/go-engineering"),
    ]


def preflight_link(source: Path, target: Path) -> None:
    if target.is_symlink():
        if Path(os.readlink(target)) != source:
            fail(f"refusing to replace a link that points elsewhere: {target}")
    elif target.exists():
        fail(f"refusing to replace unmanaged path: {target}")


def install_link(source: Path, target: Path) -> None:
    preflight_link(source, target)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_symlink():
        return
    target.symlink_to(source)


def check_link(source: Path, target: Path) -> None:
    if not target.is_symlink() or Path(os.readlink(target)) != source:
        fail(f"managed link is missing or points elsewhere: {target}")


def install_claude(home: Path) -> None:
    for source, target in claude_links(home):
        install_link(source, target)


def check_claude(home: Path) -> None:
    for source, target in claude_links(home):
        check_link(source, target)


def codex_agent_files(home: Path) -> list[tuple[Path, Path]]:
    return [
        (ROOT / "adapters/codex/agents/architect.toml", home / ".codex/agents/architect.toml"),
        (ROOT / "adapters/codex/agents/reviewer.toml", home / ".codex/agents/reviewer.toml"),
    ]


def codex_links(home: Path) -> list[tuple[Path, Path]]:
    names = (
        "plan", "implement", "investigate", "review", "verify", "finish",
        "no-comments", "domain-language", "plan-review", "interactive-review", "prepush",
        "resume-plan", "project", "feature-journey", "research", "repo-fit", "retry", "task-boundary",
        "task-review",
    )
    return [
        (ROOT / "adapters/codex/skills" / name, home / ".codex/skills" / name)
        for name in names
    ] + [
        (ROOT / "skills/workflow", home / ".codex/skills/workflow"),
        (home / ".pi/agent/skills/go-engineering", home / ".codex/skills/go-engineering"),
    ]


def legacy_codex_workflow(source: Path, target: Path) -> bool:
    return (
        source == ROOT / "skills/workflow"
        and target.is_symlink()
        and Path(os.readlink(target)) == ROOT / "adapters/codex/skills/workflow"
    )


def preflight_codex_skill(source: Path, target: Path) -> None:
    if not (source / "SKILL.md").is_file():
        fail(f"skill source is missing: {source / 'SKILL.md'}")
    if not legacy_codex_workflow(source, target):
        preflight_link(source, target)


def install_codex_skill(source: Path, target: Path) -> None:
    preflight_codex_skill(source, target)
    if legacy_codex_workflow(source, target):
        with tempfile.TemporaryDirectory(dir=target.parent) as tmp:
            replacement = Path(tmp) / "workflow"
            replacement.symlink_to(source)
            os.replace(replacement, target)
    else:
        install_link(source, target)


def preflight_managed_file(target: Path) -> None:
    if not target.exists() or target.is_symlink():
        if target.is_symlink():
            fail(f"refusing to replace a link with a managed file: {target}")
        return
    first_line = target.read_text(encoding="utf-8").splitlines()[:1]
    if first_line != [MANAGED_HEADER]:
        fail(f"refusing to replace unmanaged path: {target}")


def install_managed_file(source: Path, target: Path) -> None:
    preflight_managed_file(target)
    content = source.read_text(encoding="utf-8")
    if not content.startswith(MANAGED_HEADER + "\n"):
        fail(f"managed source lacks the header line: {source}")
    if target.exists() and target.read_text(encoding="utf-8") == content:
        return
    atomic_write(target, content)


def check_managed_file(source: Path, target: Path) -> None:
    if not target.is_file() or target.read_text(encoding="utf-8") != source.read_text(encoding="utf-8"):
        fail(f"managed file is missing or differs from source: {target}")


def install_codex(home: Path) -> None:
    agents_path = home / ".codex/AGENTS.md"
    existing = agents_path.read_text(encoding="utf-8") if agents_path.exists() else ""
    rendered = replace_marked_block(existing, codex_block(), start=CODEX_START, end=CODEX_END, label="~/.codex/AGENTS.md")
    for _, target in codex_agent_files(home):
        preflight_managed_file(target)
    for source, target in codex_links(home):
        preflight_codex_skill(source, target)

    if rendered != existing:
        atomic_write(agents_path, rendered)
    for source, target in codex_agent_files(home):
        install_managed_file(source, target)
    for source, target in codex_links(home):
        install_codex_skill(source, target)
    retired = home / ".codex/skills/shape"
    if retired.is_symlink() and Path(os.readlink(retired)) == ROOT / "adapters/codex/skills/shape":
        retired.unlink()


def check_codex(home: Path) -> None:
    agents_path = home / ".codex/AGENTS.md"
    if not agents_path.is_file():
        fail(f"managed file is missing: {agents_path}")
    text = agents_path.read_text(encoding="utf-8")
    if CODEX_START not in text:
        fail(f"personal-workflow block is missing from {agents_path}")
    if replace_marked_block(text, codex_block(), start=CODEX_START, end=CODEX_END, label="~/.codex/AGENTS.md") != text:
        fail(f"managed block differs from source: {agents_path}")
    for source, target in codex_agent_files(home):
        check_managed_file(source, target)
    for source, target in codex_links(home):
        if not (source / "SKILL.md").is_file():
            fail(f"skill source is missing: {source / 'SKILL.md'}")
        check_link(source, target)
    retired = home / ".codex/skills/shape"
    if retired.is_symlink() and Path(os.readlink(retired)) == ROOT / "adapters/codex/skills/shape":
        fail(f"retired managed skill remains: {retired}; run install codex")


def pi_source(home: Path) -> Path:
    return home / ".pi/agent/AGENTS.md"


def run_render_policy(home: Path, *, check: bool) -> None:
    source = pi_source(home)
    if not source.is_file():
        fail(f"Pi instructions are missing: {source}")
    command = [sys.executable, str(ROOT / "scripts/render_policy.py"), str(source), "--output", str(ROOT / "policy.md")]
    if check:
        command.append("--check")
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode != 0:
        fail(result.stderr.strip() or "render_policy failed")


def render_pi(home: Path) -> None:
    run_render_policy(home, check=False)


def check_pi(home: Path) -> None:
    run_render_policy(home, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install the personal workflow adapters")
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("action", choices=("install", "check", "render", "install-all", "check-all"))
    parser.add_argument("runtime", choices=("agy", "claude", "codex", "omp", "pi"), nargs="?")
    args = parser.parse_args()
    if args.action in ("install-all", "check-all"):
        return args
    if args.runtime is None:
        parser.error("a runtime is required for this action")
    if (args.action == "render" and args.runtime != "pi") or (args.action == "install" and args.runtime == "pi"):
        parser.error("'render' applies to the pi runtime only; pi supports 'render' and 'check'")
    return args


def run_everything(home: Path, *, installing: bool) -> int:
    if installing:
        render_pi(home)
    else:
        check_pi(home)
    for install, check, name in (
        (install_codex, check_codex, "codex"),
        (install_claude, check_claude, "claude"),
        (install_agy, check_agy, "agy"),
        (install_omp, check_omp, "omp"),
    ):
        if installing:
            install(home)
        check(home)
        print(f"{name} personal workflow: {'install' if installing else 'check'} ok")
    check_pi(home)
    print(f"pi personal workflow: {'render' if installing else 'check'} ok")
    return 0


def main() -> int:
    args = parse_args()
    try:
        actions = {
            ("install", "agy"): install_agy,
            ("check", "agy"): check_agy,
            ("install", "claude"): install_claude,
            ("check", "claude"): check_claude,
            ("install", "codex"): install_codex,
            ("check", "codex"): check_codex,
            ("render", "pi"): render_pi,
            ("check", "pi"): check_pi,
            ("install", "omp"): install_omp,
            ("check", "omp"): check_omp,
        }
        if args.action in ("install-all", "check-all"):
            return run_everything(args.home, installing=args.action == "install-all")
        actions[(args.action, args.runtime)](args.home)
    except RuntimeError as error:
        print(f"install.py: {error}", file=sys.stderr)
        return 1
    print(f"{args.runtime} personal workflow: {args.action} ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
