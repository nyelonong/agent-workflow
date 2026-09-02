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

## Gate

```sh
python3 -m unittest discover -s tests -v
sh -n install.sh
python3 -m py_compile scripts/install.py
```
