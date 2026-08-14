---
name: github-public-request-intake
description: Route and file sanitized public GitHub requests.
version: 0.1.0
author: JP (jplew), Hermes Agent
license: Proprietary
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [github, issues, discussions, privacy, feature-requests]
    related_skills: [github-issues, github-repo-management]
---

# GitHub Public Request Intake Skill

Use this for filing a public GitHub bug report, feature request, idea, or proposal on behalf of JP. It complements repository-specific GitHub issue tooling by adding a policy-first intake pass: inspect the target repository's instructions and automation, route the request to the channel the project actually supports, sanitize identifying details, and verify the public artifact after creation.

## When to Use

- JP asks to file a feature request, idea, proposal, or bug report in a GitHub repository.
- A workflow produced a reusable product improvement worth communicating upstream.
- The request contains operational details that must be reduced to a generic public scenario.

Do not use this for private internal tickets, code changes, or a repository whose issue/discussion policy has not been inspected.

## Intake Principles

1. Repository policy outranks generic GitHub habits. A request called an “issue” by the user may need to become a Discussion.
2. Public text contains only the minimum reproducible/useful facts. Remove names, usernames, SSH aliases, hostnames, IPs, private URLs, repository/task names, credentials, paths, and private document bodies unless each is explicitly public and necessary.
3. Verify before claiming success: check the canonical repository, created URL, title, category/state, and body content.
4. Prefer a strong problem statement and bounded proposal over a speculative root-cause essay or over-specified implementation.

## Procedure

1. **Inspect the repository.** Read its `AGENTS.md`, contribution guidance, issue templates, discussion templates, and issue-gate/triage workflows. Check the canonical upstream remote and default branch. Look for explicit rules such as “feature requests belong in Discussions” or maintainer-only issue creation.
2. **Search for overlap.** Search open and closed issues/discussions using several concrete phrases from the proposed behavior. Treat adjacent results as context, not duplicates, and link only genuinely related items.
3. **Verify authority.** Check the authenticated GitHub account and, when repository policy distinguishes maintainers, verify permission against the canonical upstream. A user request is authorization to act, not evidence that the account can bypass repository policy.
4. **Choose the channel.** Use the issue template only for a reproducible bug or an allowed maintainer work item. Use the repository's documented discussion category for ideas/features when required. If neither channel is appropriate, report the exact policy conflict instead of filing a doomed artifact.
5. **Write the case.** Describe the generic workflow and observed gap, expected capability, practical impact, and a bounded backward-compatible direction. Explain why the improvement reduces ambiguity, polling, duplicate work, or operator effort. Keep related issue references precise.
6. **Sanitize.** Replace people with roles such as “remote coding agent” and infrastructure with generic terms such as “configured SSH target” or “remote pane.” Remove personal names, machine names, IPs, private task links, credential-bearing evidence, private documents, and unrelated operational history. Re-read the final title/body as public text before submitting.
7. **Create through the supported API.** Prefer `gh` for ordinary issue operations. For Discussions, query category IDs and repository node ID with the GitHub GraphQL API and create the discussion in the documented category. Do not guess global IDs.
8. **Verify the artifact.** Fetch the created issue/discussion and check URL, number, title, state/category, author, and body. Confirm the public body contains no PII or secrets and matches the intended proposal. Report the canonical URL and any routing caveat.

## Feature-Request Case Pattern

Use this compact shape for a feature/idea:

- **Problem:** What happens now, including the exact observable ambiguity or manual workaround.
- **Requested capability:** What durable API/CLI/event/result contract would remove it.
- **Impact:** Why the gap causes extra round trips, duplicate work, unsafe retries, or poor automation.
- **Design latitude:** Offer one or two compatible directions without dictating internal architecture.
- **Boundary:** Name related issues that are adjacent but distinct.

For asynchronous agent operations, distinguish submission acknowledgement from settled completion. A useful request may ask for a durable operation ID, accepted/running/rejected/stalled/settled states, and a follow-up wait/result query or event subscription.

## Public-Text Checklist

Before submission, search the draft for:

- personal names, usernames, email addresses, task IDs, organization-private links;
- hostnames, SSH aliases, IP addresses, filesystem paths, terminal titles;
- tokens, API keys, secret names/values, private logs, or document bodies;
- unique project/repository names that are not needed to understand the general problem;
- claims based only on an unverified agent self-report.

Replace identifying details with roles and generic nouns while retaining the behavior and evidence needed for maintainers to evaluate the request.

## Pitfalls

- Do not file a feature request as a bug merely to satisfy an issue form.
- Do not create a non-template issue in a repository whose gate automatically closes it.
- Do not assume `gh issue create` can create Discussions; use GraphQL for Discussions when needed.
- Do not guess a repository node ID or discussion category ID; query both first.
- Do not expose PII to make a request sound more credible. Generic, verifiable behavior is sufficient.
- Do not claim an issue was filed when a create call returned an error; retry only after diagnosing the error.
- Do not silently convert a user-requested issue into a Discussion: explain the repository policy and the resulting URL.

## Verification

A successful intake has:

- live repository policy and routing checked;
- overlap search completed;
- channel and category selected from repository state;
- sanitized public title/body reviewed before submission;
- creation response with a canonical URL/number;
- post-creation fetch confirming the intended content and no sensitive details;
- final report that clearly says Issue or Discussion and why.

Session-specific examples and API payload patterns are kept in `references/remote-agent-completion-request.md`.
