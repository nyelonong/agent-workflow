---
name: repo-fit
description: Assess whether a GitHub repository is useful for Zaki
---
Assess the GitHub URL or owner/repository supplied by the user. If no valid reference can be established, ask one plain numbered question with a recommendation and stop until answered. Resolve owner/repository input to its GitHub URL when needed.

Inspect the repository's README, documentation, source layout, recent activity, releases, license, dependencies, issues, and discussions when available. Use web research and repository inspection. Do not run untrusted repository code or installation scripts.

Produce a concise report with these sections:

## Summary
One paragraph describing the repository and its current maturity.

## 5W+1H
- **What:** What it provides and its main capabilities.
- **Who:** Maintainers, intended users, and notable adopters when verifiable.
- **Why:** The problem it solves and why it exists.
- **When:** Release cadence, recent activity, maturity, and appropriate adoption stage.
- **Where:** Primary ecosystem, platforms, integrations, and deployment context.
- **How:** Architecture, workflow, installation or integration path, and important dependencies.

## Assessment
State strengths, risks, maintenance signals, security or licensing concerns, and credible alternatives when relevant. Clearly separate verified facts from inferences.

## Recommendation for Zaki
Give a direct verdict: **beneficial**, **possibly beneficial**, or **not beneficial**. Explain the reasoning against Zaki's likely needs: personal software projects, personal agent workflows, Go where applicable, maintainable tooling, and practical automation. If those assumptions are insufficient, name the specific missing context that could change the verdict.

## Next step
Recommend exactly one action: adopt, trial, watch, or skip. Include a short, concrete first step.
