# Delegation planning

Use this method when dependencies or safe parallel execution are not obvious.

Build the execution graph:

1. Create task nodes that reference the technical plan's acceptance criteria rather than restating them.
2. Add dependency edges and name the predecessor inputs each task consumes.
3. Name each task's source seams, change authority, required evidence, and handoff.
4. Group independent nodes into waves and put gates where review or verification must complete first.

Parallelism depends on dependency independence, shared-context needs, and write isolation, not task size alone. Keep tasks sequential when they compete for the same files, require an unresolved predecessor decision, or need shared learning that has not yet been captured.

State what a worker may decide and what remains with the parent. A worker handoff is a claim, not evidence; parent diff review and fresh verification remain authoritative. The parent may supervise or steer during execution when ambiguity, drift, or new evidence makes that necessary.

Keep design decisions and execution tasks in the same technical plan without duplication. Renew approval only when the outcome, scope, authority or material risk changes; task sequencing within the approved scope is implementation discretion.
