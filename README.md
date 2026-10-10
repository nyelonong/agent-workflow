# agent-workflow

**A portable workflow and human-review harness for coding agents.**

Use **task-review** on its own to review a real Git working-tree diff or a
specification/plan in a local browser. Optionally install the shared engineering
workflow and native adapters for Claude Code, Google Antigravity, Codex and omp.
Agent runtimes still own model/tool execution; this package is not another agent
runtime and does not emulate Pi-only tools.

## Task-review quickstart

Requires Python 3.11 or 3.13, Git and a local browser. No pip/npm installation,
Node, agent runtime, workflow installation or editor is needed to run the gate.
Node is used only for the JavaScript tests. Linux verification is proposed in CI;
local verification has been performed on macOS. Windows is not a verified path.
If the GitHub repository is private, cloning requires access; these commands do
not publish it.

```sh
git clone https://github.com/nyelonong/agent-workflow.git
HARNESS="$(cd agent-workflow && pwd -P)"
TARGET="$(cd /path/to/your/git-repository && pwd -P)"

python3 "$HARNESS/scripts/task_review.py" review \
  --criterion "The approved change and its tests are correct" \
  --repo "$TARGET" --paths src/example.py,tests/test_example.py
```

Run the client from the **trusted harness checkout**, not a similarly named
script supplied by the repository being reviewed. Replace the criterion and
paths with the actual approved unit. Omit `--paths` only when the whole current
working-tree change belongs to that unit. Paths are repo-relative; directory
scopes include their descendants. `--repo` may be repeated for a multi-root
review.

The client collects the actual change and blocks while you inspect the default
bundled HTML page. Add line-anchored comments and choose **approve**, **request
changes**, **return to planning** or **cancelled**. Only approval of the captured
state authorizes proceeding. Do not edit reviewed inputs or start another review
in the same ledger context while a decision is pending.

After approval, verify immediately before staging. Stage only task-owned files,
inspect the staged paths, commit the same logical unit, then retire the approval:

```sh
python3 "$HARNESS/scripts/task_review.py" verify \
  --repo "$TARGET" --paths src/example.py,tests/test_example.py
git -C "$TARGET" add -- src/example.py tests/test_example.py
git -C "$TARGET" diff --cached --name-only
git -C "$TARGET" commit -m "Describe the verified change"
python3 "$HARNESS/scripts/task_review.py" consume --repo "$TARGET"
```

Stop if any step fails. Changed state requires a new review, not a waived
fingerprint check. A successful local review or commit grants **no push, merge,
deployment, recipient contact or publication authority**.

### Documents

```sh
python3 "$HARNESS/scripts/task_review.py" review-doc \
  --criterion "This specification settles the requested scope and contracts" \
  --doc /absolute/path/to/specification.md
python3 "$HARNESS/scripts/task_review.py" verify-doc \
  --doc /absolute/path/to/specification.md
python3 "$HARNESS/scripts/task_review.py" consume-doc \
  --doc /absolute/path/to/specification.md
```

The page renders headings, paragraphs, tables and code with a heading outline.
Comments retain source line ranges. Keep the document unchanged through approval
verification and its authorized use; consume its approval after using it for the
next phase. Specification approval permits planning; plan approval permits its
bounded implementation. Private planning documents may live under the ignored
`docs/` directory; they are not release content.

### Results, failure and reviewer choice

Exit 0 means approval (or a successful verify/consume operation), 1 means a
non-approving decision or verification mismatch, and 2 means an error. Successful
result commands emit JSON; help/usage/errors retain their own output conventions.
A failed reviewer, malformed result, timeout or mid-review state change provides
no approval. Inspect the actual command result before retrying. Read-only work
needs no approval gate.

| Surface | Selection | Boundary |
| --- | --- | --- |
| Bundled HTML | Default, or `TASK_REVIEW_REVIEWER=html` | Loopback browser; no external editor or asset CDN required |
| RDG | `TASK_REVIEW_REVIEWER=rdg` | Existing running RDG window with the target repository open; canonical absolute roots |
| Custom process | `TASK_REVIEW_REVIEWER` command | Trusted program taking one JSON request argument and returning one JSON result line |

`RDG_CONTROL_COMMAND` remains a fallback when `TASK_REVIEW_REVIEWER` is unset.
The previously observed RDG build opened reviews but failed to return results
with `io error: Bogus destination port`; use HTML unless your build is verified.
Changing a surface does not relax the protocol or fingerprint rules. Timeout and
parent-loss handling belong to the client/reviewer processes; any async waiting,
wake-up and cancellation integration is supplied by the invoking runtime, not
promised universally by this package.

### Privacy and trust

The default reviewer serves on 127.0.0.1 behind a per-session token, with bundled
JavaScript/fonts from the same origin. Treat its URL as sensitive. Review content
and comments are local, but an unrestricted local process can access local data;
custom reviewers may handle data differently and must be trusted.

Approvals and annotations are stored in `task-review-approval.jsonl` in the
reviewed repository's Git metadata directory (document reviews use their
resolved document context). Ledgers can contain criteria, paths and comments:
keep them private, do not commit or delete them as retry cleanup, and do not
include live token URLs, sessions or scanner reports in release files.

This is a human judgment and exact-state workflow, **not a sandbox or a
tamper-proof security barrier** against an agent/process with unrestricted shell
or write access. A fingerprint establishes identity, not correctness, ownership
or permission for an external action.

## Optional workflow installation

The shipped `policy.md`, `skills/` and `adapters/` carry the shared engineering
contract. Each runtime uses native question/subagent facilities. Installation is
local and non-networked, but intentionally changes marked configuration and
links/copies in the selected home. It preserves unrelated content and refuses
unowned collisions; review your existing configuration before invoking it.
Internal `personal-workflow` markers remain ownership identifiers.

### Prerequisites and Pi policy source

Pi's `~/.pi/agent/AGENTS.md` remains the hand-written policy master; it is not
included here. Pi-only mechanics are bracketed by `<!-- pi-only:start -->` and
`<!-- pi-only:end -->`. Regeneration changes this checkout's `policy.md`:

```sh
./install.sh render pi
./install.sh check pi
```

The installer never writes into `~/.pi/agent`. Pi consumes the shared skill through
an explicitly configured link. This is the existing personal-policy setup, not
an automatically self-contained installer for every new user. Task-review does
not need that setup.

Codex installation/checking requires an existing
`~/.pi/agent/skills/go-engineering/SKILL.md`; Claude links that external skill too.
The external Go skill and `claude-config` repository are not bundled or downloaded.
The separate `claude-config/bootstrap.sh --links-only` consumes this repository's
Claude policy/workflow/roles; this package's Claude installer manages prewalk
hooks and links, not the complete external Claude bootstrap.

### Commands and effects

```sh
./install.sh install agy
./install.sh check agy
./install.sh install codex
./install.sh check codex
./install.sh install claude
./install.sh check claude
./install.sh install omp
./install.sh check omp
./install.sh install-all
./install.sh check-all
```

`install-all` explicitly renders Pi policy, installs/checks Codex, Claude,
Antigravity and omp, then checks Pi. It can replace owned copies and rendered
blocks. After changing shared skills, install all consuming copies explicitly.
All check commands are read-only. `check-all` and `check pi` reject missing/stale
Pi-derived policy **without repair**. Individual runtime checks validate their own
managed artifacts; include-only adapters do not independently validate imported
policy. Checks prove file/link parity, not live agent discovery/execution. Use a
fresh runtime session to verify discovery separately.

| Runtime | Managed boundary |
| --- | --- |
| Antigravity | Marked GEMINI.md block; workflow/task-review and role copies; prewalk hooks/links; removes only the old marked Galdr block |
| Codex | Marked AGENTS.md block with policy inline, managed read-only role files and native skill links; Go source remains Pi-owned |
| Claude Code | Prewalk hooks alongside unrelated settings and wrapper/config/Go links; external bootstrap owns full Claude configuration |
| omp | Marked AGENTS.md `@path` policy import and task-review link in `~/.agents/skills` |

Codex keeps the selected model rather than promising an automatic prewalk
handoff. Its phase skills live in `adapters/codex/skills/`; the shared workflow
contract is `skills/workflow`. No credentials, MCP service configuration, model
router, VCC/session migration or unrelated plugin/settings changes are supplied.

Claude/Antigravity prewalk wrappers are optional: their hooks are inert unless
armed by the wrapper. They run a stronger model until the first edit, then resume
on the configured target. Wrapper flags, each runtime's flat prewalk config and
shipped defaults control that behavior; existing permission modes are not
changed by this release preparation. Inspect those configurations before using
a wrapper that executes real agent/model work.

The `task-review` skill is installed in each runtime's native skills root; Codex
uses `$task-review`, omp uses `skill://task-review`. Workflow phase skills teach
the local approval/review/verification/commit boundaries; they do not supply
remote-action authorization.

## Verification

The repository gate includes unit tests plus explicitly isolated integration
using temporary Git repositories, synthetic homes/config, stub reviewers and
loopback HTTP. It does not install into your real home or require credentials,
RDG or a live upstream. Optional host Pi/Claude parity checks skip when absent;
those skips are not claims of live-runtime compatibility.

```sh
python3 -m unittest discover -s tests -v
node --test tests/test_diff_view.js
sh -n install.sh
python3 -m py_compile scripts/install.py
```

Local checks have used macOS, Python 3.13/3.11 test runners and Node 26. The proposed
GitHub Actions matrix is Linux/macOS with Python 3.11/3.13 and Node 22; adding its
workflow does not establish a successful remote run. CI has isolated HOME/Git
configuration, pinned official actions, read-only contents permission, no
repository secrets and no deployment/publishing steps. Private CI execution/cost
and pushes still require their own authorization.

## License and assets

Owner-controlled code and workflow text are MIT: see [LICENSE](LICENSE).
Vendored software/fonts retain their own MIT, ISC, BSD, Apache, dual MPL/Apache
and OFL terms; the project MIT grant does not replace them. See [NOTICE](NOTICE)
for full bundled-component attribution and
[asset provenance](assets/PROVENANCE.md) for matching source builds, hashes,
existing modifications and version-evidence limits. No bundled assets are
upgraded by this preparation. Reserved Font Names and embedded legal notices
remain intact.
