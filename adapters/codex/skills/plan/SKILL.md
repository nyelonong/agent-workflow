---
name: plan
description: Clarify the outcome and produce one visual technical plan before implementation, with relevant diagrams, concise decisions and an ordered task checklist.
---

# Plan

Apply the shared workflow's one-technical-plan contract. Clarification, design and task breakdown belong together; no approved specification or second document is required.

- Inspect the relevant repository, behavior and callers before proposing a change.
- Resolve only material unknowns with a plain numbered question and concrete options. Recommend one option and explain its trade-off; stop until answered. Batch independent questions and sequence dependent decisions.
- Separate intended outcome and activation behavior from authority to transmit data or affect external systems. Preserve settled scope and approval.
- Check assumptions and failure paths against evidence. Missing evidence or authority is a blocker, not an implementation assumption.

Use the shared contract's diagrams, tables, bullets and tasks, not another template or design-coverage matrix. Load only applicable guidance: [graph lens](references/graph-lens.md) for complex structure/data flow, [interface flow](references/interface-flow.md) for changed user interactions, and [delegation planning](references/delegation-planning.md) for nontrivial dependencies or approved parallel work.

Present a technical-plan document through `task-review` using `review-doc`. Follow the native Codex waiting/recovery mechanics and keep the pending document unchanged. Apply annotations and re-review revisions. Do not add a separate specification gate or competing chat approval. Approval authorizes the listed implementation scope directly; external actions and commits retain their own authority boundaries.

After approval, implement and apply shared continuous closeout. Keep task status, actual evidence, review outcomes and one `next:` in the plan; classify consequence and independent-review necessity separately. Reuse valid evidence rather than rerunning it at phase boundaries. Keep reviewed inputs unchanged through approval verification and use/consumption.

Use [context recovery](references/context-recovery.md) for interrupted work or an unconsumed checkpoint. Compaction alone requires no checkpoint or extra approval. Preserve existing approved requirements on resume, including older source documents, and finish against the integrated outcome.
