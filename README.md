# Personal agent workflow

Portable behavior shared by Claude Code, Google Antigravity, Codex, and omp so
each follows the same visible approval, implementation, review, verification,
commit, and remote-action flow as the personal Pi setup.

The package intentionally does not emulate Pi-only tools. Each runtime uses its native question and subagent interfaces.

## Antigravity

```sh
./install.sh install agy
./install.sh check agy
```

The installer manages one marked block in `~/.gemini/GEMINI.md`, the global `workflow` skill, and the `architect` and `reviewer` agents. It removes the old marked Galdr block from `~/.gemini/AGENTS.md` while preserving unrelated content.

## Pi

Pi's `~/.pi/agent/AGENTS.md` is the hand-written master of the rules. Sentences that
only mean something inside Pi sit between `<!-- pi-only:start -->` and
`<!-- pi-only:end -->`. `policy.md` in this repository is generated from that file:

```sh
./install.sh render pi   # regenerate policy.md after editing the Pi file
./install.sh check pi    # fails when policy.md is stale
```

Nothing writes into `~/.pi/agent`. Claude Code, Codex, and Antigravity consume the
generated `policy.md`; re-run `install codex` after a change, since Codex holds a
rendered copy.

`policy.md` carries the contract every runtime shares. Detail that only one phase
needs lives in the shared `workflow` skill, the one skill linked into every
runtime: it owns entry selection, specification and plan ownership, schema and
migration design, implementation, review, verification, and finish. A phase that
needs the detail loads the skill; a runtime that cannot see the skill still
enforces the contract from the rendered policy.

## Codex

```sh
./install.sh install codex
./install.sh check codex
```

Codex documents no include directive for its instructions file, so the installer
renders `policy.md` inline into one marked block in `~/.codex/AGENTS.md`, keeping
everything outside the block. It also writes read-only `architect` and `reviewer`
agents to `~/.codex/agents/` (each starts with `# personal-workflow managed`) and
links the Codex skills into `~/.codex/skills/`. Re-run `install codex` after a
policy change; `check codex` reports a stale block.

The Codex adapter renders the current portable rules with one exception: it removes
the automatic prewalk handoff claim. Codex stays on the selected model. Regenerating
`policy.md` also refreshes rules consumed by Claude and Antigravity; their runtime
adapters and prewalk behavior are unchanged.

Codex-specific skills live in `adapters/codex/skills/`; the shared `skills/workflow`
remains the source for the other runtimes. The installer migrates only the known
previous Codex workflow link and refuses unrelated skill files or links before
writing. Pi remains the source for `go-engineering`, linked with its references;
`~/.pi/agent/skills/go-engineering/SKILL.md` must exist for installation and checks.

Installed skills:

- Engineering: `workflow`, `shape`, `plan`, `implement`, `investigate`, `review`,
  `verify`, `finish`, `go-engineering`, `no-comments`, and `domain-language`.
- Review and continuation: `plan-review`, `interactive-review`, `prepush`,
  `resume-plan`, `retry`, and `task-boundary`.
- Investigation and explanation: `project`, `feature-journey`, `research`, and `repo-fit`.

Invoke a skill with its name and context, for example `$resume-plan <plan-path>` or
`$prepush <base-ref>`. These are skills, not Pi slash-command templates. Required
decisions use the Codex adapter's user approval flow; subagent advice uses available
native roles. Planning consults at most one architect, and only when an
independent view materially improves the plan; the architect preserves inherited
decisions and reports drift while remaining read-only. Direct implementation never
waives independent review.
`no-comments` retains its explicit-only invocation; other reviews may read its keep
list without launching another reviewer. Private vocabulary uses
`~/.codex/context/<owner>/<repo>.md`; existing Pi vocabulary is not migrated.

No model router, first-edit model switching, capability loader, VCC/session import,
RDG tool extension, service integration, credentials, or hook migration is included.
Existing settings, MCP servers, plugins, hooks and unrelated skills are preserved.
Use a fresh Codex session after installation to check discovery. A successful local
installer check proves file/link parity, not discovery or execution in T3 Code.

## Claude Code

`~/Projects/personal/claude-config/bootstrap.sh --links-only` consumes the Claude adapter, workflow skill, and role definitions from this repository. Claude configuration remains owned by `claude-config`. `./install.sh install claude` also links Pi's `go-engineering` skill from `~/.pi/agent/skills` into `~/.claude/skills`, so Go work in Claude uses the same skill as Pi.

## omp

```sh
./install.sh install omp
./install.sh check omp
```

omp resolves `@path` imports inside context files, so the installer writes one
marked block into `~/.omp/agent/AGENTS.md` with the generated policy included by
path and keeps everything outside the block. That native file is omp's
highest-priority user context file, so the rules load with no configuration.
The adapter names only facilities omp exposes: the `ask` tool for required
decisions, `skill://<name>` for skills, `read`, `bash`, `grep`, and `glob`, and
the `task` tool with its `scout`, `reviewer`, and user-defined agents. `install
omp` also links `skills/task-review` into `~/.agents/skills`, the canonical
native skills root.

## Task review gate

`scripts/task_review.py` is the runtime-agnostic client for one pre-commit human
review. `review` hands the real working-tree change to the reviewer, blocks until
a human decides, and records an approval bound to a fingerprint of the reviewed
state. `verify` recomputes that fingerprint and fails if anything changed, and
`consume` retires the approval after the commit. The gate is fail-closed: a
failed reviewer, a malformed result, a timeout, or a state that changed while
the human was reviewing all yield no approval.

The reviewer is a choice, not a branch: the gate speaks one protocol and either
surface can serve it.

| Reviewer | How to select it | Notes |
| --- | --- | --- |
| Bundled HTML page | default | no editor, no network, works anywhere |
| RDG | `TASK_REVIEW_REVIEWER=rdg` | reviews inside a running RDG window; the repository must be open there and the root must be canonical |

An approval from either is the same kind of approval: fingerprint-bound, single-decision, recorded in the same ledger.

After editing a shared skill, run `./install.sh install-all`: some runtimes
receive a link and one receives a copy, so installing one leaves the others
behind. `./install.sh check-all` fails when any runtime has drifted.

The reviewer is pluggable. `TASK_REVIEW_REVIEWER` selects it and defaults to
`html`, the bundled `scripts/html_review.py`: a token-gated `http.server` on
127.0.0.1 serving a self-contained page with line-anchored comment threads and the
four decisions. `TASK_REVIEW_REVIEWER=rdg` selects the `rdg` binary instead, a Zed
fork that reviews inside a running window. Any process that takes one JSON request
argument and prints one JSON result line can serve as a reviewer, so adding a
surface leaves the client unchanged. When `rdg` is the reviewer the repository must
already be open in the running application, and each root must be a canonical
absolute path, which the client derives by realpath.

`RDG_CONTROL_COMMAND` is still honored when `TASK_REVIEW_REVIEWER` is unset. RDG's
current build cannot complete a review: it opens the session and then fails to write
the result back to the caller, logging `io error: Bogus destination port` at
`crates/rdg/src/rdg/task_review_coordinator.rs:68` and `:71`. Until that is fixed,
keep the default HTML reviewer.

```sh
scripts/task_review.py review --criterion "..." --repo /path/to/repo --paths a,b
scripts/task_review.py verify --repo /path/to/repo --paths a,b
scripts/task_review.py consume --repo /path/to/repo
```

Exit 0 is `approve`, 1 is any other decision or a verify mismatch, and 2 is an
error. Read-only work needs no gate. The `task-review` skill teaches this flow
to every runtime:

| Runtime | Skill location |
| --- | --- |
| Claude Code | `~/.claude/skills/task-review`, linked by `claude-config/bootstrap.sh` |
| Antigravity | `~/.gemini/config/skills/task-review` |
| Codex | `~/.codex/skills/task-review`, invoked as `$task-review` |
| omp | `~/.agents/skills/task-review`, read at `skill://task-review` |

## Reviewing a specification or a plan

The same gate reviews a document, not only a diff:

```sh
scripts/task_review.py review-doc --criterion "<the question this document must answer>" --doc <path>
scripts/task_review.py verify-doc --doc <path>
scripts/task_review.py consume-doc --doc <path>
```

The page renders the document as a document — headings, paragraphs, tables,
tokenized code — with a heading outline in the sidebar that marks the section you
are reading. Each block remembers the source line range it came from, so a
comment on a paragraph spanning lines 5–7 comes back as `start_line: 5,
end_line: 7` and reaches the agent as an exact place to edit. The approval is
bound to a fingerprint of the document's bytes, so editing the plan after
approving it invalidates the approval.

`scripts/markdown_doc.py` groups the source into one block per construct, with
the ranges computed by the same pass, and the page renders each block with
vendored markdown-it. Fenced code is tokenized by vendored highlight.js only when
the fence names a language it knows; an unknown language stays plain monospace
rather than guessing.

## Prewalk

`./install.sh install claude` adds the prewalk hooks to `~/.claude/settings.json`
beside existing hooks and links `~/.local/bin/claude-prewalk`. `./install.sh install agy`
adds a `prewalk` block to `~/.gemini/config/hooks.json` beside other blocks and links
`~/.local/bin/agy-prewalk`. `claude-prewalk -- <task>` and `agy-prewalk -- <task>` run a
strong model until its first edit, then resume the same session on a cheaper model. The
hooks are inert unless the wrapper armed them; subagents started during phase 1 share
the arming. Defaults for each wrapper come from flags, then that agent's own flat
config file, then shipped values. `install claude` links `adapters/claude/prewalk.json`
to `~/.claude/prewalk.json` (or `$CLAUDE_CONFIG_DIR/prewalk.json`) and `install agy`
links `adapters/agy/prewalk.json` to `~/.gemini/prewalk.json`:

```json
{ "from": "fable", "into": "sonnet", "permissionMode": "acceptEdits" }
{ "from": "claude-opus-4-6-thinking", "into": "gemini-3.8-flash-low", "mode": "accept-edits" }
```

The Pi prewalk extension reads its own `~/.pi/agent/prewalk.json` (`autoArm`,
per-provider `starts`, per-provider `targets`), hand-written in the Pi repository like
its rules. A missing file means shipped defaults; invalid JSON warns once and means
shipped defaults. Specifications and plans are kept locally under `docs/`, which is not
tracked.

## Gate

```sh
python3 -m unittest discover -s tests -v
sh -n install.sh
python3 -m py_compile scripts/install.py
```
