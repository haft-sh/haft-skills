---
name: skill-provenance-policy
description: Keep shared project skills in version-controlled repositories.
version: 0.1.0
author: JP (jplew), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [skills, provenance, version-control, Haft, Athabasca]
    related_skills: []
---

# Skill Provenance Policy

Use this policy whenever creating, editing, or saving a reusable skill for Haft, Athabasca, Hypervault, DevSpace, GitHub project operations, deployment, release, or other team/project work.

## Invariant

Shared project behavior belongs in a version-controlled team skills repository. Do not create or revise it only under `.hermes/`, `.codex/`, or another machine-local profile directory.

Route the skill to `haft-skills` for Haft and shared engineering operations, or to `athabasca-skills` for Athabasca product, media, and creative operations. Local skill directories are reserved for personal, experimental, provider-specific, or temporary workflows.

## Procedure

1. Classify the skill as personal/local or reusable team behavior before writing it.
2. For reusable behavior, create or edit the skill in a repository worktree.
3. Keep secrets, credentials, private host details, personal paths, and transient incident state out of the repository.
4. Validate the skill, commit it, and open a pull request when it changes shared behavior.
5. When local and repo-backed versions conflict, treat the version-controlled repository as authoritative and remove or disable the local fork after the replacement is available.

## Verification

A shared skill is complete only when its repository path, branch/commit, validation result, and pull request are recorded. A local copy alone is not a shared implementation.
