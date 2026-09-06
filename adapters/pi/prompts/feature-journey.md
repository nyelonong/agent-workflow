---
description: Explain a feature's flow, state transitions, and component sequence
argument-hint: "<feature or scenario>"
---
Analyze the flow and user journey for this feature or scenario:

$@

If `$@` is empty, use `ask_decision` to obtain the feature or scenario, include a recommendation, and stop. Inspect the relevant code and documentation before answering. If the feature or scenario is ambiguous, use `ask_decision` with a recommended option rather than assume its scope. Do not propose implementation changes unless asked.

Structure the explanation as:

1. **Scope** — the trigger, user-visible outcome, and main entry points.
2. **Narrative** — the normal path, decisions, side effects, and relevant failure paths.
3. **Flow diagram** — a plain-ASCII diagram showing the control and data flow.
4. **State diagram** — a plain-ASCII diagram of persistent or meaningful lifecycle states
   and their transitions. If no state machine exists, state that explicitly and show the
   derived lifecycle instead.
5. **Sequence diagram** — a plain-ASCII diagram of the participating users, services,
   queues, databases, and external systems in message order.
6. **Evidence and gaps** — the files that support the explanation, plus any assumptions
   or unknown behavior.

Keep diagrams readable in a terminal. Use only plain ASCII characters such as `+`, `-`,
`|`, `[`, `]`, and `->`.
