# Context recovery

Load this reference only when resuming a plan with an unconsumed checkpoint, or when an interruption leaves the current task without a durable checkpoint. Automatic context compaction never by itself requires a checkpoint. Recover dropped detail from durable artifacts and supported session history; ask if a material approval or constraint remains unavailable. The plan is the sole durable continuation artifact. Replace its checkpoint in place and create no separate handoff.

## Normal checkpoint

Write a normal checkpoint only after all of these are true:

- The current task's implementation is complete, the parent review has no unresolved P0/P1 finding, and fresh focused evidence passed. Optional P2 findings need not be eliminated, but each accepted P2 note is recorded under residual risks.
- The task's code and tests are in a parent-created task commit, then the plan's `next:` line is advanced to the next dependency.
- There is no active task-owned child, and all task-owned results and handoffs have been consumed.
- Every dirty path, including unrelated pre-existing user files, is enumerated with its reason. Preserve all of them untouched except for authorized task changes.

If the completed task was the last task, set `next: finish`.

Keep exactly one replaceable section with the following heading in the plan. Replace its contents on later rollovers instead of appending history.

## Continuation checkpoint

- State: `ready`, `partial`, or `consumed`.
- Reason: runtime state and the event requiring rollover.
- Repository: repository identity or root path.
- Checkout: absolute checkout path.
- Branch: branch name.
- Current commit: `<SHA> — <plain-English description>`.
- Task commit: `<SHA> — <plain-English description>`, or `none — partial task is not committed`.
- Completed task or current partial phase: task name and status.
- Evidence: exact fresh commands and results.
- Evidence gaps: known checks not run or coverage not provided.
- Authoritative next: the plan's unchanged or advanced `next:` value.
- Expected dirty files: every dirty path, including unrelated pre-existing user files, and the reason for each, or `none`; preserve all untouched except for authorized task changes.
- Child state: every task-owned child and consumed handoff, normally `none`.
- Review state, when applicable: pending phase, criterion, exact repository/path scope or document, private command-artifact directory and first recovery action. Its private operational record holds the review ID, expected fingerprint, URL, supported command/session handle when available and recorded outcome or `pending`. Missing handles or results remain explicit evidence gaps. Follow [task-review recovery](../../task-review/SKILL.md#recover-an-interrupted-review) before relaunching a review or committing.
- Learned execution decisions: settled implementation facts that do not change the specification.
- Blockers: current blockers, or `none`.
- Residual risks: accepted P2 notes and other residual risks, or `none`.
- Ordered resume steps: validation, recovery when needed, checkpoint consumption, and execution.

## Partial checkpoint

Use a partial checkpoint only when interruption prevents the normal checkpoint. Do not advance `next:`, do not claim completion, and do not create a misleading commit. Record the exact dirty-file state, exact active or interrupted child state, every command and result so far, remaining evidence gaps, and the first recovery action. Worker reports and dirty code remain untrusted until the replacement session inspects and reviews the diff and validates evidence under the shared freshness contract, rerunning missing, stale, invalidated or uncertain proof; only then may it commit or advance.

Before entering an HTML review wait, record the pending review and its private artifact location so an abrupt interruption can be recovered. Do not advance the plan's `next:`; record review recovery as the first resume action. Write this checkpoint before capturing the reviewed state, then store its expected fingerprint externally. Keep a reviewed document or checkpoint within the diff scope unchanged through verification and approval use/consumption, including the diff commit. Put later command handles, URL information and interim checkpoint-consumption state in the private operational record and supported session history instead. This deferral takes precedence over the normal checkpoint-consumption order in `resume-plan`; update the embedded checkpoint only after the review approval has been used and consumed. Recovery records are not human approval.

## Fresh-session bootstrap

1. Read `AGENTS.md`, the approved specification, the plan, and its continuation checkpoint.
2. Before any operation that changes HEAD or the worktree, inspect remotes and validate the repository identity, checkout, branch, HEAD, and exact dirty set against the checkpoint. Confirm there is no inherited writer or other mutation-capable task-owned child.
3. Only after that validation, fetch from an existing upstream. Update only when safe, without discarding checkpointed work or creating or forcing a conflict, then revalidate the repository identity, checkout, branch, HEAD, exact dirty set, and absence of inherited writers. If no upstream exists, report it once and continue locally.
4. Validate the last completed task's recorded evidence under the shared freshness contract; rerun missing, stale, invalidated or uncertain proof. For a partial checkpoint, first inspect and review the dirty diff and follow its first recovery action.
5. Route any unexplained state mismatch or command failure to `investigate`; do not execute forward.
6. After validation and evidence pass, mark the checkpoint state `consumed` before continuing, except when it is within a pending or approved review scope. In that case, record checkpoint consumption externally and defer the embedded edit as described above.
7. Preserve the existing implementation approval unless validation reveals a material scope change. When authoritative next is `next: finish`, load `finish`; otherwise execute only the named task.

End the old session with: “Start a new session in the same checkout, validate the continuation checkpoint in `<absolute plan path>`, then execute its `next:`.”
