# omp adapter

Use the `ask` tool for required decisions: give concrete options, mark the recommended index, and stop until the user answers. It is interactive-only and a cancelled `ask` is a refusal, not a decision. Never treat an edit, command, or sandbox permission prompt as product or implementation approval.

Load the personal `workflow` skill with `read` at `skill://workflow` when the user asks for the workflow, or let them invoke `/skill:workflow`; load `skill://task-review` only when the user requests a task review. The task-review client is the trusted workflow harness's `scripts/task_review.py`: resolve the physical `skill://task-review` directory (`<harness>/skills/task-review`) and use `<harness>/scripts/task_review.py`, never a path in the repository under review. Inspect with `read`, `bash`, `grep`, and `glob`. For approved multi-task planning, dispatch the `task` tool at most once with an `architect` agent, when one is defined in `~/.omp/agent/agents/`, and only when an independent view materially improves the plan; its output is advisory. Dispatch `reviewer` only when the global independent-review boundary applies, the user requests it, or credible uncertainty justifies optional review, and use `scout` for read-only codebase research. Ordinary parent work dispatches no subagent. Task-review is optional; when the user requests it, delegate plan/diff gate preparation and invocation under the shared task-review skill, using native child model controls to always use GPT-6 Luna (`gpt-6-luna`) within the current provider and runtime scope; if unavailable or disallowed, stop rather than substituting another model. Keep the parent model unchanged; unavailable delegation/model selection/waiting blocks rather than falling back to the parent. The parent retains verification, corrections, consumption and commits.

For best-effort task-review guides, supervise a **preparation-only** native phase
before authorizing reviewer invocation. Its packet forbids `review`/`review-doc`
and approval metadata. The verified fixed-model role, criterion, scope, private
guide path and cancellation ownership are retained in that packet. In Python
Eval, use the supported native handle/barrier, not `functions.wait` (which has no
deadline argument), a sleep loop, or a global task timeout:

```python
import time

deadline = time.monotonic() + 120
guide_handle = agent(preparation_packet, agent=gate_role)
try:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("guide preparation deadline expired")
    guide_result = wait([guide_handle], timeout=remaining, raise_errors=False)[0]
    if time.monotonic() >= deadline:
        guide_result = None
except TimeoutError:
    guide_handle.cancel()
    wait([guide_handle], raise_errors=False)
    guide_result = None
```

Native failure, missing/invalid output or rejected guide preflight means no guide;
never repair/retry the optional phase. Explicit user cancellation stops the task.
Before accepting completed output, finish its actual validation/preflight within
the same absolute deadline; do not start a new budget for result processing.
On timeout, settle the cancelled native handle and ignore late output before any
handoff. Confirm preparation did not invoke the canonical reviewer; an existing or
unknown gate must be recovered rather than replaced. Plain preflight must pass
with the same criterion/scope and no guide. Then resume a successfully completed
preparer where supported, or launch a fresh fixed-model **launch-only** runner.
The real review still runs once in a native subagent, with its normal human-wait
deadline and no guide generation in that phase. If supported bounded preparation
or cancellation/settlement is unavailable, skip the optional phase immediately.

omp-specific settings, hooks, extensions, MCP servers, and repository `.omp/` or standalone `AGENTS.md` files remain authoritative within their narrower scope.
