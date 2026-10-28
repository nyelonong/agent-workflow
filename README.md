# agent-workflow

**A portable workflow and human-review harness for coding agents.**

```text
agent-workflow
├── task-review ──→ Git diff or document ──→ local browser ──→ human decision
└── workflow    ──→ policy + skills + adapters ──→ your agent runtime
                    (optional installation)
```

- **Task-review:** Python 3.11 or 3.13, Git and a local browser. No pip/npm install, Node, editor or agent runtime needed.
- **Optional workflow:** Claude Code, Antigravity, Codex or omp; existing prerequisites below. Runtimes own model/tool execution, not this package.
- **Repository:** currently private; cloning requires access and does not publish it.

## Task-review

### 1. Review

```sh
git clone https://github.com/nyelonong/agent-workflow.git
HARNESS="$(cd agent-workflow && pwd -P)"
TARGET="$(cd /path/to/your/git-repository && pwd -P)"

python3 "$HARNESS/scripts/task_review.py" review \
  --criterion "The approved change and its tests are correct" \
  --repo "$TARGET" --paths src/example.py,tests/test_example.py \
  --recovery-dir /absolute/private/new-review
```

| Input | Rule |
| --- | --- |
| Client | **Trusted harness's absolute path**, never a script supplied by the target |
| Criterion / paths | Replace with your approved unit; paths are repo-relative, directories include descendants |
| Whole change | Omit `--paths` only when **everything** belongs to the unit; repeat `--repo` for multiple roots |
| Pending review | Actual diff opens in the browser; client blocks. Add line-anchored comments; no edits or competing reviews in the same ledger context |

| Decision | Next step |
| --- | --- |
| **Approve** | Verify the captured state before staging |
| **Request changes** | Correct, check, review again |
| **Return to planning** | Stop; revisit scope/plan |
| **Cancelled** | Stop |

### Delegated launch and recovery

Invoke the canonical client in the native gate subagent's foreground command.
Do not generate launch scripts, PID files, shell redirection or detached commands.
The native async run supplies ownership, waiting and cancellation; optional
child-side progress messaging is not required. Set native run/tool deadlines
longer than the client timeout (default 1800 seconds) plus preparation time.

`--recovery-dir` works with both `review` and `review-doc`. It is optional for
manual callers and required by the delegated workflow. Supply a new or empty
private directory outside the reviewed inputs; the client creates it with mode
0700 and artifacts with mode 0600. Existing nonempty directories are refused.

| Artifact | Meaning |
| --- | --- |
| `request.json` | Exact canonical request, criterion, scope and review ID |
| `process.json` | Client/reviewer PIDs and reviewer argv; diagnostic ownership evidence, not permission to blindly kill a reused PID |
| `state.json` | `starting`, `reviewing`, `finished`, or `error`; finished state includes decision/exit code |
| `stderr.log` | Live reviewer diagnostics, including the browser URL |
| `browser-url.txt` | HTML page URL while waiting; withdrawn on normal completion |
| `result.json` | Validated decision after ledger recording; approval also requires unchanged reviewed inputs |

Reviewer stderr is forwarded immediately, independently of stdout's single
validated result line. An open native tool while the client is `reviewing` is
normally waiting for a human, not a launch failure. Exit 0 means approve; exit 1
with a decision means human non-approval; exit 2 means an error. Missing result or
an error never grants approval. Inspect native state and saved artifacts before
relaunching; recovery does not replace `verify`/`verify-doc` or `consume`.

### Guided tab (HTML)

**Diff** remains the default. **Guided** shows an overview, before/after cards,
optional flow labels, and explained chapters beside the same real diffs. Comments,
drafts, layout controls and approval checks are shared. Chapter checkboxes track
reading only, for this page session; they are not approval.

Guides are best-effort and written by the calling agent itself from the diff it
has already inspected; there is no separate preparation step or deadline. If a
guide fails preflight, the agent corrects it once, then skips it and opens the
complete actual diff without a guide, reporting why.

No model/network call is made by this harness. Store the guide outside reviewed
repositories and client recovery artifacts. Obtain the fingerprint using the
**same repo/path scope**:

```sh
python3 "$HARNESS/scripts/task_review.py" status --repo "$TARGET" --paths src/example.py,tests/test_example.py
# Exit 1 is normal when no approval exists; read the fingerprint in its JSON output.
python3 "$HARNESS/scripts/task_review.py" preflight \
  --criterion "The approved change and its tests are correct" \
  --repo "$TARGET" --paths src/example.py,tests/test_example.py \
  --guide /absolute/private/path/guide.json
python3 "$HARNESS/scripts/task_review.py" review \
  --criterion "The approved change and its tests are correct" \
  --repo "$TARGET" --paths src/example.py,tests/test_example.py \
  --guide /absolute/private/path/guide.json
```

`preflight` returns 0 only for valid scope/guide inputs; it opens no browser and
does not change any approval ledger. Duplicate, stale or out-of-scope guide
references fail. The best-effort runtime workflow skips a guide that still fails
after one correction and preflights the unchanged base request without one; it
does not weaken validation or retry a failed review. Manually supplied `--guide` requests still fail strictly.


Guide format (replace the fingerprint and repository root):

```json
{
  "version": 1,
  "fingerprint": "<64-character scoped fingerprint from status>",
  "summary": "What this change achieves",
  "before": "The previous behavior",
  "after": "The new behavior",
  "flow": {"before": ["Input", "Old path"], "after": ["Input", "New path", "Result"]},
  "chapters": [
    {
      "title": "Core change",
      "summary": "Why these files belong together and what to inspect",
      "files": [{"repository": "/absolute/repository/root", "path": "src/example.py"}]
    }
  ]
}
```

- Only `flow` is optional. Guide version is integer `1`; total serialized size is
  at most 48 KiB. Text fields allow 8,000 characters, titles/flow labels 200;
  at most 128 chapters and 1–20 flow labels per side. Each chapter has at least one file.
- File references use canonical repository roots and current diff paths (rename
  destinations), never old paths. Unknown or duplicate references fail locally;
  unassigned scoped files appear under **Other changes**.
- Explanations are labeled **Agent-authored**, not verified behavior. A stale
  fingerprint fails; regenerate after code or scope changes. Narration is captured
  once and is advisory, not part of the existing code-approval fingerprint/ledger.
- Without a guide, Guided offers explicitly labeled directory groups, not invented
  behavior explanations. All existing guide-free callers continue working.
- `--guide` and `--json` cannot be combined; complete JSON review requests may carry
  an inline `guide` object. Guide-bearing reviews require the bundled `html` backend;
  other backends fail explicitly rather than silently ignoring it.
- Document reviews are unchanged.

### 2. Verify and commit

```text
review → approve → verify → stage owned files → inspect → commit → consume
                   ↑
          changed state? review again
```

```sh
python3 "$HARNESS/scripts/task_review.py" verify \
  --repo "$TARGET" --paths src/example.py,tests/test_example.py
git -C "$TARGET" add -- src/example.py tests/test_example.py
git -C "$TARGET" diff --cached --name-only
git -C "$TARGET" commit -m "Describe the verified change"
python3 "$HARNESS/scripts/task_review.py" consume --repo "$TARGET"
```

- **Stop on failure.** Verify immediately before staging; commit only the reviewed unit.
- Changed state requires another review, never a waived fingerprint check.
- Local approval grants **no push, merge, deployment, recipient contact or publication authority**.
- Read-only work needs no gate.

### Documents

```sh
python3 "$HARNESS/scripts/task_review.py" review-doc \
  --criterion "This technical plan settles the outcome, material design and executable tasks" \
  --doc /absolute/path/to/technical-plan.md
python3 "$HARNESS/scripts/task_review.py" verify-doc --doc /absolute/path/to/technical-plan.md
python3 "$HARNESS/scripts/task_review.py" consume-doc --doc /absolute/path/to/technical-plan.md
```

- Rendered headings/tables/code and outline; comments retain source line ranges.
- Keep unchanged through verification and authorized use; consume **after** use.
- One technical-plan approval → bounded implementation; no separate specification stage.
- Private planning files belong in ignored `docs/`, not releases.

The workflow uses one visual technical plan: relevant Mermaid architecture,
sequence, ownership/swimlane or ER diagrams; concise outcome and scope bullets;
a decisions/risks table; and ordered task checkboxes with concrete proof.
Omit irrelevant diagrams and sections rather than adding boilerplate. A routine,
already-authorized change needs only a short approach and tasks, not another
document or approval. Material changes to outcome, scope, authority or risk
require renewed approval; ordinary implementation choices and progress do not.

`plan` includes clarification and design. The retired `shape` entry point is
removed; its useful lenses live under `plan/references/`. Existing approved
requirements remain valid on resume. Commit review and external-action
authorization are unchanged.

### Results and reviewers

| Exit | Meaning |
| --- | --- |
| `0` | Approval, or successful verify/consume |
| `1` | Non-approving decision or verification mismatch |
| `2` | Error |

- Successful result commands emit JSON; help/usage/errors retain their conventions.
- Failed reviewer, malformed result, timeout or mid-review edits grant **no approval**; inspect before retrying.

| Reviewer | Selection / requirement |
| --- | --- |
| **HTML** | Default; `TASK_REVIEW_REVIEWER=html`; loopback browser and bundled assets, no editor/CDN |
| RDG | `TASK_REVIEW_REVIEWER=rdg`; running window with target repo open, canonical absolute roots |
| Custom | `TASK_REVIEW_REVIEWER` command; trusted process: one JSON request argument → one JSON result line |

- `RDG_CONTROL_COMMAND` is a fallback when `TASK_REVIEW_REVIEWER` is unset.
- Known RDG return failure: `io error: Bogus destination port`. Prefer HTML unless your build is verified.
- Surface choice never relaxes protocol/fingerprint rules. Client/reviewer own timeout/parent-loss handling; runtime owns async waiting/wake-up/cancellation integration.

### Privacy and trust

| Boundary | Rule |
| --- | --- |
| Browser | `127.0.0.1`, session token, same-origin JS/fonts; **keep the URL private** |
| Data | Local by default, accessible to unrestricted local processes; custom reviewers must be trusted |
| Ledger | `task-review-approval.jsonl` in Git metadata; document reviews use their resolved context; contains criteria, paths, comments/decisions |
| Private files | Never commit ledgers, live URLs, sessions or scanner reports; never delete ledgers as retry cleanup |
| Security | **Not a sandbox or tamper-proof barrier** against unrestricted shell/write access |
| Fingerprint | State identity—not correctness, ownership or external-action permission |

## Optional workflow installation

- Contract: `policy.md`, `skills/`, `adapters/`; native runtime questions/subagents, no Pi-tool emulation.
- Local/non-networked, but **writes selected-home configuration and links/copies**.
- Replaces only owned marked content, preserves unrelated content, refuses unowned collisions. Review existing config first; `personal-workflow` markers stay intact.

### Prerequisites

| Dependency | Requirement |
| --- | --- |
| Pi policy | Unbundled `~/.pi/agent/AGENTS.md` master; `<!-- pi-only:start -->` / `<!-- pi-only:end -->` delimit Pi mechanics. Pi skill uses an explicit link; installer never writes into `~/.pi/agent` |
| Go skill | Codex install/check requires `~/.pi/agent/skills/go-engineering/SKILL.md`; Claude links it too; not bundled/downloaded |
| Claude config | External `claude-config/bootstrap.sh --links-only` consumes policy/workflow/roles; this installer handles the Go skill link, not full bootstrap |

Task-review needs **none** of these. Workflow installation retains the existing personal-policy setup, not a self-contained bootstrap for every user.

Explicit regeneration **writes this checkout's `policy.md`**:

```sh
./install.sh render pi
./install.sh check pi
```

### Commands

| Command | Effect |
| --- | --- |
| `./install.sh install RUNTIME` | Install owned artifacts; `RUNTIME`: `agy`, `codex`, `claude`, `omp` |
| `./install.sh check RUNTIME` | Read-only managed-artifact check; same runtime names |
| `./install.sh install-all` | Render Pi → install/check Codex, Claude, Antigravity, omp → check Pi |
| `./install.sh check-all` | Read-only policy/runtime checks; missing/stale inputs fail without repair |

- `check pi` / `check-all` validate Pi-derived policy; include-only adapters' individual checks do **not** independently validate imported policy.
- Reinstall consuming copies after shared-skill edits. Checks prove file/link parity, **not live discovery**; verify that in a fresh runtime session.

| Runtime | Managed files |
| --- | --- |
| Antigravity | Marked GEMINI.md, skill/role copies; only old marked Galdr block removed |
| Codex | Marked AGENTS.md with inline policy, read-only roles, native skill links; Go stays Pi-owned |
| Claude | Go skill link; full config stays external |
| omp | Marked AGENTS.md `@path` import, task-review link in `~/.agents/skills` |

- Codex keeps the selected model. Phase skills: `adapters/codex/skills/`; shared workflow: `skills/workflow`.
- Task-review uses native skill roots: Codex `$task-review`, omp `skill://task-review`.
- Task-review is optional and runs only when the user requests it. Every coding-agent runtime then delegates plan and diff gate preparation/invocation to one bounded native subagent. Use the fixed task-review model within the current provider's available runtime scope: GPT-6 Luna (`gpt-6-luna`) by default, `haiku` for Claude Code, or `gemini-3.8-flash-low` for Antigravity as specified by their adapters. Do not compare prices, substitute another model/version or silently fall back. If the fixed model is unavailable or disallowed, stop and ask the user. The parent retains its model, exact-state verification, corrections, consumption and commits. Missing native delegation/model-selection/waiting support blocks the gate. This is an instruction-level rule, not runtime enforcement.
- No credentials, MCP/model-router configuration, VCC/session migration, unrelated settings or remote-action authority supplied.

## Verification

```sh
python3 -m unittest discover -s tests -v
node --test tests/test_diff_view.js
sh -n install.sh
python3 -m py_compile scripts/install.py
```

| Coverage | Status |
| --- | --- |
| Local | macOS, Python 3.11/3.13, Node 26 |
| Linux / Windows / live runtime discovery | Not verified |
| Tests | Unit + isolated integration: temporary Git repos, synthetic homes/config, stub reviewers, loopback HTTP; no real-home install, credentials, RDG or live upstream |
| Optional host checks | Pi/Claude parity skips when absent; not proof of live compatibility |

No GitHub Actions workflow is provided; run the checks locally.

## License and assets

- Owner-controlled code/workflow: [MIT](LICENSE).
- Vendors retain their own MIT, ISC, BSD, Apache, dual MPL/Apache and OFL terms: [NOTICE](NOTICE).
- Builds, hashes, existing modifications and version limits: [asset provenance](assets/PROVENANCE.md).
- Bundled assets, Reserved Font Names and embedded legal notices remain unchanged.
