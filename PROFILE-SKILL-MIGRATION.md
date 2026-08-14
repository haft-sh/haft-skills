# Profile skill migration audit

Date: 2026-08-15

## Scope

Audited the Orchestrator profile skill tree under the machine-local Hermes profile. The profile exposes 260 `SKILL.md` files, including upstream/general-purpose skills, plugin skills, archived material, and team-specific operational skills.

## Routing decision

- **Already repo-backed:** 6 Haft skills were already present in this repository and were not duplicated.
- **Migrated in this PR:** the 61 clearly Haft/shared-engineering/Hypervault/DevSpace/GitHub-project `SKILL.md` files copied from the profile tree into this repository, plus the reusable Herdr dispatch lessons reference. Historical incident references and machine-specific templates remain in the local audit set for a separate sanitization pass rather than being bulk-published.
- **Athabasca:** Athabasca-specific skills remain in the profile for a separate migration to `athabasca-skills`; this PR does not mix the two repositories.
- **Not migrated:** upstream/general-purpose provider, creative, productivity, research, Apple, and machine-local utility skills. They are not team Haft skills and need no move to this repository.

## Migrated skill directories

The migrated directories are:

- `haft-agent-dogfooding`, `haft-release-operations`, `haft-release-procedure`, `haft-product-dogfooding`, `haft-remote-publish-operations`, `haft-remote-import-verification`, `remote-media-artifact-operations`, `haft-auth-and-claim-operations`, `haft-hq-deploy-verification`, `transactional-email-provider-cutovers`, `haft-html-document-authoring`, `haft-operator-health-checks`, `haft-artifact-catalog-reconciliation`, `haft-document-retrieval`, `haft-cli-auth-and-remotes`, `haft-observability-monitoring-health-check`
- `github-herdr-project-dispatch`, `haft-orchestrator-workflows`, `deployed-media-pipeline-debugging`, `pr-handoff-reconciliation`, `pr-review-reconciliation`, `automated-ci-notification-containment`, `pr-ci-triage`, `ci-supersession-reconciliation`, `haft-ready-worktree-cards`, `kanban-external-worker-worktree-claimability`, `kanban-orchestrator-operations`, `kanban-dependency-integrity`, `kanban-board-inventory-triage`, `haft-sprint-planner-orchestration`, `haft-central-projection-auth`, `haft-codebase-audit`, `repo-backed-specification-publication`, `delivery-finish-line-orchestration`, `hypervault-artifact-planning-and-publication`, `hypervault-epic11-sprint-planner-refill`
- `github-pr-governance`, `pr-provenance-policy`, `haft-pr-review-guidelines`, `github-cross-repo-project-operations`, `pr-review-gate`, `github-project-board-reconciler`, `hypervault-pr-reconciliation`, `workflow-alert-board-reconciliation`, `github-actions-run-triage`, `github-actions-run-diagnostics`, `github-public-request-intake`
- `self-hosted-ci-operations`, `self-hosted-runner-provenance`, `herdr-ssh-identity-bootstrap`, `devspace-mcp-operations`, `hermes-operational-integrations`, `sdlc-review`, `dev-host-disk-reclamation`, `deployment-drift-repair`, `release-deployment-readiness`, `branch-integration-safety`, `multi-host-runtime-verification`, `protected-dev-app-reverse-proxying`, `transactional-email-incident-operations`, `hypervault-dogfooding-workflows`

## Sanitization

The migrated files replace machine-specific home paths, instance identifiers, private addresses, mailbox identities, and host-specific origins with placeholders. No credentials, tokens, cookies, OTPs, invitation material, or private message bodies are included.

## Follow-up

After this PR is merged, configure the team profiles to load the repository-backed directory and remove local forks of migrated skills. Athabasca-specific profile skills should be audited and migrated separately to `athabasca-skills` using the same invariant.
