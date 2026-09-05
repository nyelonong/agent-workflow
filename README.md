# Personal agent workflow

Portable behavior shared by Claude Code and Google Antigravity so both follow the same visible approval, implementation, review, verification, commit, and remote-action flow as the personal Pi setup.

The package intentionally does not emulate Pi-only tools. Each runtime uses its native question and subagent interfaces.

## Antigravity

```sh
./install.sh install agy
./install.sh check agy
```

The installer manages one marked block in `~/.gemini/GEMINI.md`, the global `workflow` skill, and the `oracle` and `reviewer` agents. It removes the old marked Galdr block from `~/.gemini/AGENTS.md` while preserving unrelated content.

## Claude Code

`~/Projects/personal/claude-config/bootstrap.sh --links-only` consumes the Claude adapter, workflow skill, and role definitions from this repository. Claude configuration remains owned by `claude-config`.

## Prewalk

`./install.sh install claude` adds the prewalk hooks to `~/.claude/settings.json`
beside existing hooks and links `~/.local/bin/claude-prewalk`. `claude-prewalk -- <task>`
runs a strong model until its first edit, then resumes the same session on a cheaper
model. The hooks are inert unless the wrapper armed them; subagents started during
phase 1 share the arming. Specification: `docs/specs/2026-09-05-prewalk.md`.

## Gate

```sh
python3 -m unittest discover -s tests -v
sh -n install.sh
python3 -m py_compile scripts/install.py
```
