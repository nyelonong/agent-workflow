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

import render_policy


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
CLAUDE_START = "<!-- personal-workflow:claude:start -->"
CLAUDE_END = "<!-- personal-workflow:claude:end -->"
CLAUDE_LEGACY_START = "<!-- homie:baseline-golang"
CLAUDE_LEGACY_END = "<!-- agents:global-rules:end -->"
MANAGED_HEADER = "# personal-workflow managed"
PI_SKILL_ENTRY = str(ROOT / "skills/workflow")
PI_PROMPTS_ENTRY = str(ROOT / "adapters/pi/prompts")


def ensure_policy_fresh() -> None:
    """Reject consumers of policy.md when its generated copy is stale."""
    policy = ROOT / "policy.md"
    try:
        expected = render_policy.render(render_policy.read_source(ROOT / "policy/core.md"))
    except (OSError, ValueError) as error:
        fail(str(error))
    if not policy.is_file() or policy.read_text(encoding="utf-8") != expected:
        fail(f"portable policy is stale relative to canonical source: {policy}")


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


def atomic_write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o600
    with tempfile.NamedTemporaryFile("wb", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    os.chmod(temporary, mode)
    temporary.replace(path)


def atomic_write(path: Path, content: str) -> None:
    atomic_write_bytes(path, content.encode("utf-8"))


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
    return [
        (ROOT / "adapters/agy/bin/agy-prewalk", home / ".local/bin/agy-prewalk"),
        (ROOT / "adapters/agy/prewalk.json", home / ".gemini/prewalk.json"),
    ]


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
    ensure_policy_fresh()
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
    ensure_policy_fresh()
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


def claude_policy_path(home: Path) -> Path:
    path = home / ".claude/CLAUDE.md"
    # Write through an owner-managed link rather than replacing it.
    return path.resolve() if path.is_symlink() else path


def claude_block() -> str:
    adapter = (ROOT / "adapters/claude/CLAUDE.md").read_text(encoding="utf-8")
    placeholder = "@__POLICY_PATH__"
    if adapter.count(placeholder) != 1:
        fail("Claude adapter must contain exactly one policy placeholder")
    return adapter.replace(placeholder, f"@{ROOT / 'policy.md'}").rstrip()


def replace_claude_block_bytes(content: bytes, block: str) -> bytes:
    """Splice Claude's current or legacy block without changing unmanaged bytes."""
    start = CLAUDE_START.encode("ascii")
    end = CLAUDE_END.encode("ascii")
    legacy_start = CLAUDE_LEGACY_START.encode("ascii")
    legacy_end = CLAUDE_LEGACY_END.encode("ascii")
    legacy_starts = content.count(legacy_start)
    legacy_ends = content.count(legacy_end)
    if legacy_starts != legacy_ends:
        fail("~/.claude/CLAUDE.md contains an incomplete legacy managed block")
    if legacy_starts > 1:
        fail("~/.claude/CLAUDE.md contains duplicate legacy managed blocks")

    newline = b"\r\n" if b"\r\n" in content else b"\n"
    rendered = block.encode("utf-8").replace(b"\n", newline).rstrip(b"\r\n")
    if legacy_starts:
        if start in content or end in content:
            fail("~/.claude/CLAUDE.md mixes legacy and personal-workflow managed blocks")
        pattern = re.compile(
            rb"(?m)^" + re.escape(legacy_start) + rb".*?$.*?^" + re.escape(legacy_end) + rb"\r?$",
            re.DOTALL,
        )
    else:
        starts = content.count(start)
        ends = content.count(end)
        if starts != ends:
            fail("~/.claude/CLAUDE.md contains an incomplete personal-workflow block")
        if starts > 1:
            fail("~/.claude/CLAUDE.md must contain exactly one personal-workflow block")
        if starts:
            pattern = re.compile(
                rb"(?m)^" + re.escape(start) + rb"\r?$.*?^" + re.escape(end) + rb"\r?$",
                re.DOTALL,
            )
        else:
            if not content:
                return rendered + newline
            separator = b"" if content.endswith(newline * 2) else newline if content.endswith(newline) else newline * 2
            return content + separator + rendered + newline

    matches = list(pattern.finditer(content))
    if len(matches) != 1:
        label = "legacy managed" if legacy_starts else "personal-workflow"
        fail(f"~/.claude/CLAUDE.md contains a malformed {label} block")
    match = matches[0]
    # The newline after the end marker belongs to the unmanaged suffix. Multiline
    # matching consumes CR before LF, so retain it with that suffix.
    suffix_cr = b"\r" if content[match.end() - 1 : match.end()] == b"\r" else b""
    return content[: match.start()] + rendered + suffix_cr + content[match.end() :]


def replace_claude_block(text: str, block: str) -> str:
    """Text compatibility wrapper for Claude managed-block replacement."""
    return replace_claude_block_bytes(text.encode("utf-8"), block).decode("utf-8")


def claude_workflow_links(home: Path) -> list[tuple[Path, Path]]:
    return [
        (ROOT / "skills/workflow", home / ".claude/skills/workflow"),
        (ROOT / "adapters/claude/agents/architect.md", home / ".claude/agents/architect.md"),
        (ROOT / "adapters/claude/agents/reviewer.md", home / ".claude/agents/reviewer.md"),
    ]


def claude_links(home: Path) -> list[tuple[Path, Path]]:
    return [
        *claude_workflow_links(home),
        (ROOT / "adapters/claude/bin/claude-prewalk", home / ".local/bin/claude-prewalk"),
        (ROOT / "adapters/claude/prewalk.json", home / ".claude/prewalk.json"),
    ]


def preflight_link(source: Path, target: Path) -> None:
    if not source.exists():
        fail(f"managed source is missing: {source}")
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
    if not source.exists():
        fail(f"managed source is missing: {source}")
    if not target.is_symlink() or Path(os.readlink(target)) != source:
        fail(f"managed link is missing or points elsewhere: {target}")


def install_claude(home: Path) -> None:
    ensure_policy_fresh()
    for source, target in claude_links(home):
        preflight_link(source, target)
    policy_path = claude_policy_path(home)
    existing = policy_path.read_bytes() if policy_path.exists() else b""
    rendered = replace_claude_block_bytes(existing, claude_block())
    settings_path = home / ".claude/settings.json"
    if settings_path.is_symlink():
        # Write through the link so an owner repository keeps the file.
        settings_path = settings_path.resolve()
    settings = load_json(settings_path)
    merged = merge_claude_hooks(json.loads(json.dumps(settings)))

    if rendered != existing:
        atomic_write_bytes(policy_path, rendered)
    if merged != settings:
        atomic_write(settings_path, json.dumps(merged, indent=2) + "\n")
    for source, target in claude_links(home):
        install_link(source, target)


def check_claude(home: Path) -> None:
    ensure_policy_fresh()
    policy_path = claude_policy_path(home)
    if not policy_path.is_file():
        fail(f"managed file is missing: {policy_path}")
    existing = policy_path.read_bytes()
    if replace_claude_block_bytes(existing, claude_block()) != existing:
        fail(f"managed block differs from source: {policy_path}")
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
    ensure_policy_fresh()
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
    ensure_policy_fresh()
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


def pi_agents_path(home: Path) -> Path:
    path = home / ".pi/agent/AGENTS.md"
    # Write through an owner-managed link rather than replacing it.
    return path.resolve() if path.is_symlink() else path


def pi_settings_path(home: Path) -> Path:
    path = home / ".pi/agent/settings.json"
    # Write through an owner-managed link rather than replacing it.
    return path.resolve() if path.is_symlink() else path


def pi_block() -> str:
    try:
        return render_policy.pi_block(
            render_policy.read_source(ROOT / "policy/core.md"),
            render_policy.read_source(ROOT / "adapters/pi/AGENTS.md"),
        )
    except (OSError, ValueError) as error:
        fail(str(error))


def pi_configured_source(raw: object, home: Path, field: str) -> Path:
    if not isinstance(raw, str) or not raw:
        fail(f"Pi settings {field} contains a non-string configured source")
    if raw == "~":
        candidate = home
    elif raw.startswith("~/"):
        candidate = home / raw[2:]
    elif raw.startswith("~"):
        fail(f"cannot safely verify configured {field} source with an unsupported home alias: {raw}")
    else:
        candidate = Path(raw)
    if not candidate.is_absolute():
        fail(f"cannot safely verify cwd-relative configured {field} source: {raw}")
    try:
        return candidate.resolve(strict=True)
    except (OSError, RuntimeError):
        fail(f"cannot safely verify missing or unresolved configured {field} source: {raw}")


def pi_skill_name(path: Path) -> str | None:
    if path.suffix.lower() != ".md" or not path.is_file():
        return None
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        fail(f"cannot read configured skills source {path}: {error}")
    if not lines or lines[0] != "---":
        return None
    for line in lines[1:]:
        if line == "---":
            return None
        match = re.fullmatch(r"name:\s*(.+?)\s*", line)
        if match:
            return match.group(1).split(" #", 1)[0].strip().strip("\"'")
    return None


def pi_skill_files(source: Path) -> list[Path]:
    if source.is_file():
        return [source]
    if not source.is_dir():
        return []
    root_skill = source / "SKILL.md"
    if root_skill.is_file():
        return [root_skill]
    # Pi searches nested skill roots but only direct Markdown files in a source root.
    return sorted(
        [path for path in source.glob("*.md") if path.is_file()]
        + [path for path in source.rglob("SKILL.md") if path.is_file()]
    )


def pi_prompt_files(source: Path) -> list[Path]:
    if source.is_file():
        return [source] if source.suffix.lower() == ".md" else []
    if not source.is_dir():
        return []
    # Prompt directories are deliberately non-recursive in Pi.
    return [path for path in source.glob("*.md") if path.is_file()]


def pi_prompt_names(source: Path) -> set[str]:
    return {path.stem for path in pi_prompt_files(source)}


def pi_collisions(home: Path) -> list[Path]:
    """Find default-root resources Pi would discover under managed names."""
    root = home / ".pi/agent"
    skills = [
        path
        for path in pi_skill_files(root / "skills")
        if pi_skill_name(path) == "workflow"
    ]
    managed_prompt_names = {path.stem for path in pi_prompt_files(ROOT / "adapters/pi/prompts")}
    prompts = [
        path
        for path in pi_prompt_files(root / "prompts")
        if path.stem in managed_prompt_names
    ]
    return skills + prompts


def pi_configured_collisions(home: Path, settings: dict) -> None:
    managed = {
        "skills": (PI_SKILL_ENTRY, Path(PI_SKILL_ENTRY).resolve()),
        "prompts": (PI_PROMPTS_ENTRY, Path(PI_PROMPTS_ENTRY).resolve()),
    }
    managed_prompt_names = pi_prompt_names(Path(PI_PROMPTS_ENTRY))
    for field, (canonical_entry, canonical_source) in managed.items():
        entries = settings.get(field, [])
        if not isinstance(entries, list):
            fail(f"Pi settings has a non-array {field} field")
        canonical_count = 0
        for raw in entries:
            source = pi_configured_source(raw, home, field)
            if source == canonical_source:
                if raw != canonical_entry:
                    fail(f"Pi settings has a configured {field} source alias for the managed path: {raw}")
                canonical_count += 1
                if canonical_count > 1:
                    fail(f"Pi settings has duplicate managed {field} entries")
                continue
            if field == "skills":
                if any(pi_skill_name(path) == "workflow" for path in pi_skill_files(source)):
                    fail(f"Pi configured skills source exposes managed workflow skill: {raw}")
            elif pi_prompt_names(source) & managed_prompt_names:
                names = ", ".join(sorted(pi_prompt_names(source) & managed_prompt_names))
                fail(f"Pi configured prompts source exposes managed prompt names ({names}): {raw}")


def merge_pi_settings(settings: dict) -> dict:
    merged = json.loads(json.dumps(settings))
    for key, entry in (("skills", PI_SKILL_ENTRY), ("prompts", PI_PROMPTS_ENTRY)):
        value = merged.setdefault(key, [])
        if not isinstance(value, list):
            fail(f"Pi settings has a non-array {key} field")
        if value.count(entry) > 1:
            fail(f"Pi settings has duplicate managed {key} entries")
        if entry not in value:
            value.append(entry)
    return merged


def json_skip_whitespace(content: bytes, position: int) -> int:
    while position < len(content) and content[position] in b" \t\r\n":
        position += 1
    return position


def json_string_end(content: bytes, position: int) -> int:
    if position >= len(content) or content[position] != ord('"'):
        fail("Pi settings contains malformed JSON string")
    position += 1
    while position < len(content):
        if content[position] == ord("\\"):
            position += 2
        elif content[position] == ord('"'):
            return position + 1
        else:
            position += 1
    fail("Pi settings contains unterminated JSON string")


def json_value_end(content: bytes, position: int) -> int:
    if position >= len(content):
        fail("Pi settings contains malformed JSON value")
    if content[position] == ord('"'):
        return json_string_end(content, position)
    if content[position] not in (ord("["), ord("{")):
        end = position
        while end < len(content) and content[end] not in b",]} \t\r\n":
            end += 1
        return end
    opening = content[position]
    closing = ord("]") if opening == ord("[") else ord("}")
    depth = 1
    position += 1
    while position < len(content):
        if content[position] == ord('"'):
            position = json_string_end(content, position)
            continue
        if content[position] == opening:
            depth += 1
        elif content[position] == closing:
            depth -= 1
            if depth == 0:
                return position + 1
        position += 1
    fail("Pi settings contains unterminated JSON value")


def json_object_members(content: bytes) -> tuple[int, list[tuple[str, int, int]]]:
    """Return root-object close and key/value spans without reformatting JSON."""
    position = json_skip_whitespace(content, 0)
    if position >= len(content) or content[position] != ord("{"):
        fail("Pi settings must contain a JSON object")
    position += 1
    members: list[tuple[str, int, int]] = []
    while True:
        position = json_skip_whitespace(content, position)
        if position >= len(content):
            fail("Pi settings contains an unterminated JSON object")
        if content[position] == ord("}"):
            if content[json_skip_whitespace(content, position + 1) :]:
                fail("Pi settings contains data after its JSON object")
            return position, members
        key_start = position
        key_end = json_string_end(content, key_start)
        try:
            key = json.loads(content[key_start:key_end])
        except json.JSONDecodeError as error:
            fail(f"Pi settings contains malformed JSON key: {error}")
        position = json_skip_whitespace(content, key_end)
        if position >= len(content) or content[position] != ord(":"):
            fail("Pi settings contains a JSON key without a value")
        value_start = json_skip_whitespace(content, position + 1)
        value_end = json_value_end(content, value_start)
        members.append((key, value_start, value_end))
        position = json_skip_whitespace(content, value_end)
        if position >= len(content):
            fail("Pi settings contains an unterminated JSON object")
        if content[position] == ord("}"):
            continue
        if content[position] != ord(","):
            fail("Pi settings contains malformed JSON object separators")
        position += 1


def append_json_array_entry(content: bytes, start: int, end: int, entry: str) -> bytes:
    if content[start] != ord("[") or content[end - 1] != ord("]"):
        fail("Pi settings has a non-array managed field")
    item = json.dumps(entry, ensure_ascii=False).encode("utf-8")
    body_start = json_skip_whitespace(content, start + 1)
    if body_start == end - 1:
        return content[: end - 1] + item + content[end - 1 :]
    # The JSON parser already established that this is an array; append after its
    # final value so its original trailing whitespace remains byte-for-byte intact.
    last_end = start + 1
    position = start + 1
    while True:
        position = json_skip_whitespace(content, position)
        value_end = json_value_end(content, position)
        last_end = value_end
        position = json_skip_whitespace(content, value_end)
        if content[position] == ord("]"):
            break
        if content[position] != ord(","):
            fail("Pi settings contains malformed array separators")
        position += 1
    return content[:last_end] + b", " + item + content[last_end:]


def merge_pi_settings_bytes(content: bytes, settings: dict) -> bytes:
    """Add only owned Pi entries while retaining all existing JSON bytes."""
    merged = merge_pi_settings(settings)
    if merged == settings:
        return content
    close, members = json_object_members(content)
    updates: list[tuple[int, int, str]] = []
    existing = {key: (start, end) for key, start, end in members}
    additions: list[str] = []
    for key, entry in (("skills", PI_SKILL_ENTRY), ("prompts", PI_PROMPTS_ENTRY)):
        if entry in settings.get(key, []):
            continue
        if key in existing:
            start, end = existing[key]
            updates.append((start, end, entry))
        else:
            additions.append(f'{json.dumps(key)}: {json.dumps([entry], ensure_ascii=False)}')
    # Array spans cannot overlap. Apply them right-to-left to retain offsets.
    for start, end, entry in sorted(updates, reverse=True):
        content = append_json_array_entry(content, start, end, entry)
    if additions:
        # Recompute the close after any earlier array growth. Inserting after the
        # final value retains the existing object suffix (including CRLF) exactly.
        close, members = json_object_members(content)
        if members:
            insert_at = members[-1][2]
            prefix = b", "
        else:
            insert_at = close
            prefix = b""
        content = content[:insert_at] + prefix + ", ".join(additions).encode("utf-8") + content[insert_at:]
    return content


def load_pi_settings(path: Path) -> tuple[bytes, dict]:
    content = path.read_bytes() if path.exists() else b"{}\n"
    try:
        data = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        fail(f"{path} is not valid JSON: {error}")
    if not isinstance(data, dict):
        fail(f"{path} must contain a JSON object")
    return content, data


def pi_preflight(home: Path) -> tuple[Path, bytes, Path, bytes, dict, bytes, bytes]:
    for source in (ROOT / "policy/core.md", ROOT / "adapters/pi/AGENTS.md", ROOT / "skills/workflow/SKILL.md"):
        if not source.is_file():
            fail(f"managed Pi source is missing: {source}")
    prompts = ROOT / "adapters/pi/prompts"
    if not prompts.is_dir() or not list(prompts.glob("*.md")):
        fail(f"managed Pi prompts are missing: {prompts}")
    collisions = pi_collisions(home)
    if collisions:
        fail("Pi default-root resource collision: " + ", ".join(str(path) for path in collisions))
    agents = pi_agents_path(home)
    existing = agents.read_bytes() if agents.exists() else b""
    try:
        rendered = render_policy.replace_pi_block_bytes(existing, pi_block())
    except ValueError as error:
        fail(str(error))
    settings_path = pi_settings_path(home)
    settings_bytes, settings = load_pi_settings(settings_path)
    pi_configured_collisions(home, settings)
    merged = merge_pi_settings_bytes(settings_bytes, settings)
    return agents, existing, settings_path, settings_bytes, settings, rendered, merged


def install_pi(home: Path) -> None:
    ensure_policy_fresh()
    agents, existing, settings_path, settings_bytes, _settings, rendered, merged = pi_preflight(home)
    # pi_preflight validates the complete semantic update before either write.
    if rendered != existing:
        atomic_write_bytes(agents, rendered)
    if merged != settings_bytes:
        atomic_write_bytes(settings_path, merged)


def check_pi(home: Path) -> None:
    ensure_policy_fresh()
    agents, existing, settings_path, settings_bytes, settings, rendered, merged = pi_preflight(home)
    if not agents.is_file() or existing != rendered:
        fail(f"managed Pi policy block is missing or differs: {agents}")
    if merge_pi_settings(settings) != settings:
        fail(f"managed Pi resource entries are missing from {settings_path}")
    if merged != settings_bytes:
        fail(f"managed Pi resource entries are not byte-stable in {settings_path}")


def render_pi(home: Path) -> None:
    del home
    source = ROOT / "policy/core.md"
    rendered = render_policy.render(render_policy.read_source(source))
    target = ROOT / "policy.md"
    if not target.exists() or target.read_text(encoding="utf-8") != rendered:
        atomic_write(target, rendered)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install the personal workflow adapters")
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("action", choices=("install", "check", "render"))
    parser.add_argument("runtime", choices=("agy", "claude", "codex", "pi"))
    args = parser.parse_args()
    if args.action == "render" and args.runtime != "pi":
        parser.error("'render' applies to the pi runtime only")
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
            ("install", "pi"): install_pi,
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
