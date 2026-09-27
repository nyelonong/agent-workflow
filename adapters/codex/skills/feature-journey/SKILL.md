---
name: feature-journey
description: Explain a feature's flow, state transitions, and component sequence
---

# Feature Journey

Use the feature or scenario named by the user or established in the active context. If it is missing or materially ambiguous, ask one plain numbered question with a concrete recommendation and stop until answered. Inspect the relevant code and documentation before explaining it. Do not propose implementation changes unless asked.

Explain the trigger, user-visible outcome and entry points, then the normal path, decisions, side effects and failure paths. Show control/data flow, meaningful state transitions and participant message order using readable diagrams when they add clarity. If no state machine exists, say so and describe the derived lifecycle. Use plain ASCII for terminal output; Mermaid is suitable when the surface supports it.

Cite the files supporting the explanation. Separate verified behavior, inferred behavior and evidence gaps; do not turn an illustrative diagram into a claim that a path was executed.
