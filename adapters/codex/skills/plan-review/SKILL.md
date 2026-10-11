---
name: plan-review
description: Review one visual technical plan against the requested outcome and repository evidence
---

Review the supplied technical plan. Resolve its path from context; ask only if it cannot be identified. This is an optional user-requested review, not another mandatory implementation stage.

- Compare outcome, scope and acceptance criteria with the user's decisions and source requirements. No separate specification is required.
- Check relevant diagrams for real participants, ownership, data/trust boundaries and important failure paths.
- Check tasks for concrete changes, affected files/components, dependencies and meaningful proof.
- Surface unresolved material decisions and unsupported safety assumptions. Do not mistake ordinary implementation discretion for missing design.
- Report findings once in a compact table: location, issue, impact and smallest correction. No coverage matrix, separate ledger or compulsory task-by-task walkthrough.

Read-only by default; change the plan only with user authorization. Use a plain numbered question for unresolved material decisions and stop until answered. Do not edit production code.

If the user requests approval, present the final document through `task-review` using `review-doc` and follow native waiting/recovery. Do not add another approval when the current plan is already approved and its outcome, scope, authority and material risk are unchanged. Walkthrough acknowledgements are not approval; revisions to a pending document require re-review.
