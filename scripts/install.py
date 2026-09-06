#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shlex
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
        (ROOT / "adapters/agy/agents/architect", home / ".gemini/config/agents/architect"),
        (ROOT / "adapters/agy/agents/reviewer", home / ".gemini/config/agents/reviewer"),
    ]


def agy_links(home: Path) -> list[tuple[Path, Path]]:
    return [(ROOT / "adapters/agy/bin/agy-prewalk", home / ".local/bin/agy-prewalk")]


AGY_HOOKS_BLOCK = "prewalk"


def agy_hook_command(event: str) -> str:
    script = shlex.quote(str(CLAUDE_HOOK_SCRIPT))
    # Guarded so a moved repository fails open (empty stdout is Antigravity's neutral answer).
    return f"[ -f {script} ] && python3 {script} agy {event} || true"


def agy_hooks_block() -> dict:
    handler = lambda event: {"type": "command", "command": agy_hook_command(event), "timeout": 10}
    return {
        "PreInvocation": [handler("PreInvocation")],
        "Stop": [handler("Stop")],
        "PreToolUse": [{"matcher": ".*", "hooks": [handler("PreToolUse")]}],
        "PostToolUse": [{"matcher": ".*", "hooks": [handler("PostToolUse")]}],
    }


def agy_hooks_path(home: Path) -> Path:
    path = home / ".gemini/config/hooks.json"
    return path.resolve() if path.is_symlink() else path


def load_agy_hooks(home: Path) -> tuple[Path, dict]:
    path = agy_hooks_path(home)
    data = load_json(path)
    if AGY_HOOKS_BLOCK in data and not isinstance(data[AGY_HOOKS_BLOCK], dict):
        fail(f"{path} has a non-object {AGY_HOOKS_BLOCK} block")
    return path, data


def install_agy_hooks(home: Path) -> None:
    path, data = load_agy_hooks(home)
    if data.get(AGY_HOOKS_BLOCK) == agy_hooks_block():
        return
    data[AGY_HOOKS_BLOCK] = agy_hooks_block()
    atomic_write(path, json.dumps(data, indent=2) + "\n")


def check_agy_hooks(home: Path) -> None:
    path, data = load_agy_hooks(home)
    if data.get(AGY_HOOKS_BLOCK) != agy_hooks_block():
        fail(f"prewalk block is missing or differs in {path}")


def install_agy(home: Path) -> None:
    paths = agy_paths(home)
    for _, target in paths:
        preflight_directory(target)
    for source, target in agy_links(home):
        preflight_link(source, target)
    load_agy_hooks(home)

    gemini = home / ".gemini/GEMINI.md"
    existing = gemini.read_text(encoding="utf-8") if gemini.exists() else ""
    rendered = replace_marked_block(existing, managed_block())

    remove_galdr_block(home / ".gemini/AGENTS.md", check=False)
    atomic_write(gemini, rendered)
    for source, target in paths:
        install_directory(source, target)
    install_agy_hooks(home)
    for source, target in agy_links(home):
        install_link(source, target)


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
    check_agy_hooks(home)
    for source, target in agy_links(home):
        check_link(source, target)


CLAUDE_HOOK_SCRIPT = ROOT / "scripts/prewalk_hook.py"
# Guarded so a moved or deleted repository fails open instead of denying every edit.
CLAUDE_HOOK_COMMAND = (
    f"[ -f {shlex.quote(str(CLAUDE_HOOK_SCRIPT))} ] && python3 {shlex.quote(str(CLAUDE_HOOK_SCRIPT))} claude || true"
)
CLAUDE_EDIT_MATCHER = "Edit|Write|MultiEdit|NotebookEdit"
CLAUDE_TODO_MATCHER = "TodoWrite"


def claude_hook_groups() -> dict[str, list[str]]:
    return {"PreToolUse": [CLAUDE_EDIT_MATCHER], "PostToolUse": [CLAUDE_EDIT_MATCHER, CLAUDE_TODO_MATCHER]}


def claude_hook_entry(matcher: str) -> dict:
    return {"matcher": matcher, "hooks": [{"type": "command", "command": CLAUDE_HOOK_COMMAND, "timeout": 10}]}


def is_prewalk_hook(hook: object) -> bool:
    return isinstance(hook, dict) and "prewalk_hook.py" in str(hook.get("command", ""))


def prewalk_groups(groups: object, matcher: str) -> list[dict]:
    if not isinstance(groups, list):
        return []
    return [
        group
        for group in groups
        if isinstance(group, dict)
        and group.get("matcher") == matcher
        and isinstance(group.get("hooks"), list)
        and any(is_prewalk_hook(hook) for hook in group["hooks"])
    ]


def has_claude_hook(groups: object, matcher: str) -> bool:
    return any(
        hook.get("command") == CLAUDE_HOOK_COMMAND
        for group in prewalk_groups(groups, matcher)
        for hook in group["hooks"]
        if is_prewalk_hook(hook)
    )


def merge_claude_hooks(settings: dict) -> dict:
    """Return settings with the prewalk hook groups added or converged; other content is untouched."""
    hooks = settings.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        fail("~/.claude/settings.json has a non-object hooks field")
    for event, matchers in claude_hook_groups().items():
        groups = hooks.setdefault(event, [])
        if not isinstance(groups, list):
            fail(f"~/.claude/settings.json hooks.{event} is not a list")
        for matcher in matchers:
            existing = prewalk_groups(groups, matcher)
            if not existing:
                groups.append(claude_hook_entry(matcher))
                continue
            for group in existing:
                for hook in group["hooks"]:
                    if is_prewalk_hook(hook):
                        hook["command"] = CLAUDE_HOOK_COMMAND
                        hook["timeout"] = 10
    return settings


def claude_hooks_present(settings: dict) -> bool:
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return False
    return all(
        has_claude_hook(hooks.get(event), matcher)
        for event, matchers in claude_hook_groups().items()
        for matcher in matchers
    )


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        fail(f"{path} is not valid JSON: {error}")
    if not isinstance(data, dict):
        fail(f"{path} must contain a JSON object")
    return data


def claude_links(home: Path) -> list[tuple[Path, Path]]:
    return [(ROOT / "adapters/claude/bin/claude-prewalk", home / ".local/bin/claude-prewalk")]


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
        preflight_link(source, target)
    settings_path = home / ".claude/settings.json"
    if settings_path.is_symlink():
        # Write through the link so an owner repository keeps the file.
        settings_path = settings_path.resolve()
    settings = load_json(settings_path)
    merged = merge_claude_hooks(json.loads(json.dumps(settings)))
    if merged != settings:
        atomic_write(settings_path, json.dumps(merged, indent=2) + "\n")
    for source, target in claude_links(home):
        install_link(source, target)


def check_claude(home: Path) -> None:
    settings_path = home / ".claude/settings.json"
    if not claude_hooks_present(load_json(settings_path)):
        fail(f"prewalk hooks are missing from {settings_path}")
    for source, target in claude_links(home):
        check_link(source, target)


def codex_agent_files(home: Path) -> list[tuple[Path, Path]]:
    return [
        (ROOT / "adapters/codex/agents/architect.toml", home / ".codex/agents/architect.toml"),
        (ROOT / "adapters/codex/agents/reviewer.toml", home / ".codex/agents/reviewer.toml"),
    ]


def codex_links(home: Path) -> list[tuple[Path, Path]]:
    return [(ROOT / "skills/workflow", home / ".codex/skills/workflow")]


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
        preflight_link(source, target)

    if rendered != existing:
        atomic_write(agents_path, rendered)
    for source, target in codex_agent_files(home):
        install_managed_file(source, target)
    for source, target in codex_links(home):
        install_link(source, target)


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
        check_link(source, target)


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
    parser.add_argument("action", choices=("install", "check", "render"))
    parser.add_argument("runtime", choices=("agy", "claude", "codex", "pi"))
    args = parser.parse_args()
    if (args.action == "render" and args.runtime != "pi") or (args.action == "install" and args.runtime == "pi"):
        parser.error("'render' applies to the pi runtime only; pi supports 'render' and 'check'")
    return args


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
        }
        actions[(args.action, args.runtime)](args.home)
    except RuntimeError as error:
        print(f"install.py: {error}", file=sys.stderr)
        return 1
    print(f"{args.runtime} personal workflow: {args.action} ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
