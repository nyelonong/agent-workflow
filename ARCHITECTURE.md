# Control-plane ownership

| Layer | Canonical owner | Deployed form | Precedence |
| --- | --- | --- | --- |
| Portable policy | `policy/core.md` | `policy.md` and runtime blocks | Universal rules |
| Pi mechanics | `adapters/pi/AGENTS.md` | marked Pi `AGENTS.md` block | Runtime translation only |
| Other runtime mechanics | `adapters/<runtime>/` | runtime-managed blocks | Runtime translation only |
| Installer | `scripts/install.py` | owned marked blocks, links, and settings entries | Deploys only owned paths |
| Shared workflow | `skills/workflow/` | linked or configured skill | Executes policy |
| Pi prompts | `adapters/pi/prompts/` | configured prompt directory | User-invoked procedures |
| Project instructions | each project | project `AGENTS.md` | Local facts and stricter constraints |
| Pi extensions | Pi repository | `~/.pi/agent/extensions/` | Pi runtime behavior |

Canonical policy wins over weaker instructions. Runtime adapters only translate
mechanics. Project instructions may add repository facts, commands, and stricter
constraints; they do not redefine global approval or safety rules. Skills execute
policy, and prompts invoke procedures; neither is a policy source. For Claude,
`install claude` and `check claude` are the direct workflow owner; `claude-config`
only delegates to those commands and does not own the workflow content.

The Pi installer owns exactly one `personal-workflow:pi` block in Pi global
instructions plus its configured workflow and prompt entries. It rejects malformed
markers, active default-root duplicates, and other configured skill or prompt
sources that expose managed names. It resolves absolute and `~/` configured sources
through links; missing or cwd-relative sources fail because they cannot be safely
verified. Package and extension resources are a fresh-discovery migration check,
not evidence the local settings updater can enumerate. After complete semantic
preflight, each Pi file is written atomically, but `AGENTS.md` and `settings.json`
are not transactionally atomic together; Git-backed migration/re-run is recovery.
