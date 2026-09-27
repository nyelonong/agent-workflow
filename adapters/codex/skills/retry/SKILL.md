---
name: retry
description: Resume the current task without replaying a tool operation
---

# Retry

Resume the interrupted task from the current conversation and repository state. Briefly state that work resumed, then take the next safe necessary action.

Do not automatically replay a prior tool operation or infer that it succeeded or failed. First inspect available results and read-only state to determine its outcome, especially for commits, file writes and external mutations. If the outcome of a consequential operation remains unknown, stop for a required decision rather than risking a duplicate action. A safe read-only inspection or fresh verification may be repeated when needed. Preserve the existing scope and approval boundaries.
