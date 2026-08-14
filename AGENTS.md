# Agent artifact policy

## Skill provenance invariant

Skills that encode Haft, Athabasca, Hypervault, DevSpace, GitHub-project, release, deployment, or other team/project operating behavior **must be authored and maintained in the appropriate version-controlled team skills repository**. Do not create or revise those skills only under `.hermes/`, `.codex/`, or another machine-local profile directory.

Use machine-local skill directories only for genuinely personal, experimental, provider-specific, or temporary workflows. If a local skill becomes reusable team behavior, migrate it into a repo-backed skills repository and submit a normal pull request before treating it as shared policy.

When a local skill and a repo-backed skill conflict, the version-controlled repository is authoritative. Do not silently fork or override it locally.

## Repository routing

- Haft operations, GitHub project workflows, deployment/release procedures, and shared development operations belong in `haft-skills`.
- Athabasca product, media, and creative workflows belong in `athabasca-skills`.
- Keep secrets, credentials, private host details, personal paths, and transient incident state out of public skill repositories.

Every skill change must leave a reviewable git history: branch/worktree, validation, commit, and pull request when it changes shared behavior.
