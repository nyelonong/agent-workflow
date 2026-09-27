---
name: domain-language
description: "Maintain a repository's shared vocabulary in CONTEXT.md. Use before substantive work when that file exists, when a project term recurs unexplained, or when the user explains an abbreviation or internal name."
---

# Domain Language

A CONTEXT.md holds the project's shared vocabulary: terms, abbreviations, and internal names the code does not say. One line per term.

Read CONTEXT.md before substantive work in a repo that has one. When a term earns a line, identify the correct destination below and obtain the normal implementation approval before creating or changing durable vocabulary; an approved single-line update is a trivial local edit.

## When a term earns a line

- The user explains a term, or a term is explained a second time in one conversation.
- A name in code, config, or docs is opaque to someone new to the repo.
- Two names for the same thing compete in conversation or code.

## Rules

- Use one line per term in the canonical form `Term — definition`, written in the repo's own language. No paragraphs, examples, or rationale.
- Do not document what code, names, or the type system already say. The file holds vocabulary, not design.
- Use the term in conversation, code, and docs instead of its explanation. When an approved code change renames it, update the line in the same change.
- Remove a term only after a repository-wide search shows it is obsolete or an approved rename replaces it, and obtain approval for the removal. Keep the file short; a long file means the boundary slipped.
- Do not create CONTEXT.md speculatively. Create it only when a term has earned an approved line and no file exists.

Do not treat CONTEXT.md as a spec, ADR, or design doc. Design decisions live in `shape`'s specification and decision log.

## Where the file lives

Identify the repo by the origin remote of the files involved (owner and repository name), not by the nearest `.git` directory: a workspace can hold several repos, and its own top level may be a repo too.

| Repo | Location |
|---|---|
| Your private repo | repository root, committed |
| Your repo, shared or public | personal store |
| Repo you only contribute to | personal store; the repo stays untouched, never staged or committed |

Key the personal store by owner and repository name: `~/.codex/context/<owner>/<repo>.md`. Use the repository directory name when there is no origin, prefixed by its parent when the name would collide.
