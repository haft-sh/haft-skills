---
name: self-hosted-runner-provenance
description: Use when runner identity disagrees across GitHub and hosts.
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [ci, github-actions, runners, provenance, herdr]
    related_skills: [self-hosted-ci-operations, github-actions-run-diagnostics, herdr-agent-dispatch-orchestration]
---

# Self-Hosted Runner Provenance

## When to Use

Use this skill when GitHub runner identity, heartbeat, storage paths, or host-local listener evidence disagree; before runner cleanup, restart, relabeling, replacement, reruns, or incident routing.

## Purpose

Use this skill when GitHub reports a runner online but the suspected host, service, path, or storage evidence disagrees. Establish the physical execution domain before cleanup, restart, relabeling, reruns, or board routing.

A runner name, GitHub runner ID, SSH hostname, job machine name, service/listener identity, and runner-root path are separate identities until live evidence ties them together.

See `references/native-listener-and-quota-diagnosis.md` for the bounded host-local investigation recipe and the stale/stray registration pattern.

## Workflow

1. **Capture immutable job evidence.** Record repository, current head SHA, run/job URL, runner name and ID, labels, machine name when logged, failed path, and first host-level error. Reconcile notifications against live GitHub state.
2. **State the intended runner form.** Determine whether the runner should be a native listener under a Unix user, a system service, container, VM, or ephemeral autoscaled instance. Do not infer this from a human/runner name or `/home/runner` alone.
3. **Inventory the suspected host read-only.** For native runners, inspect `Runner.Listener` and `Runner.Worker` processes, owner, PID/PPID ancestry, executable/root/cwd, cgroup/unit, service definitions, runner directory, `_work`, `_diag`, and a non-secret `.runner` projection. For containers, inspect the runtime, namespace, mounts, and persistent volumes.
4. **Correlate identities.** Build an evidence row containing GitHub runner name/ID, machine hostname or machine ID, local listener/service name, Unix user, runner-root path, and physical host. Mark unknowns explicitly.
5. **Diagnose storage by domain.** Check block capacity, inodes, mount type/options, tmpfs headroom, user/project quota, deleted-open files, and a tiny disposable write. Keep `/tmp`, `/dev/shm`, home, runner `_work`, and runner `_diag` separate unless mount/process evidence joins them.
6. **Use a host-local agent when topology is ambiguous.** Through the established control channel, select an idle verified pane and send a bounded read-only brief. Ask for process ancestry, units/cgroups, non-secret registration metadata, filesystems/quotas, and bounded top-level sizes. Corroborate its report with direct reads or APIs.
7. **Interrupt unbounded diagnostics without losing context.** If a recursive search runs too broadly, interrupt only the command, keep the same agent session, ask it to synthesize collected evidence, and replace the search with targeted paths or `du --max-depth=1`.
8. **Correct ownership before acting.** Route incidents by exact runner or physical capacity domain, not generic “disk/capacity.” Update stale owner cards rather than creating duplicates. Record corrections on both the old and correct owners.
9. **Gate quarantine.** Before removing an approval label, enumerate every runner satisfying the workflow’s full selector. If no approved alternative is online, quarantine is fail-closed but halts the lane and requires an explicit operator decision.
10. **Mutate only after provenance is proven.** Restart, cleanup, re-registration, label changes, or reruns must target the proven execution domain. Never clean a healthy reachable host merely because its name resembles the runner.

## Interpretation Rules

- GitHub `online` proves heartbeat, not physical-host provenance or dispatch health.
- No matching intended native listener on the suspected host plus continued GitHub heartbeat suggests a stray/legacy runtime or another namespace/host; report this as an inference until located.
- Absence from `docker ps` does not disprove an intended native listener.
- A hex machine name or `/home/runner` path does not by itself prove Docker.
- `df` showing free blocks does not disprove tmpfs, inode, user, or project quota exhaustion.
- A tiny successful write disproves a total write outage, not a larger size/quota boundary.
- A failure under one runner-root path is not explained by pressure in another path or host without provenance evidence.

## Safety

- Never print `.credentials`, tokens, registration secrets, environment secrets, or private file contents.
- Use passwordless sudo only for bounded read-only inspection; never prompt for credentials.
- Do not restart active listeners, delete runner registrations, remove approval labels, or clean storage before alternate-capacity and ownership checks.
- Do not rerun a deterministic no-space job until capacity or quota in the actual execution domain is repaired.
- Keep build, browser, release, and deployment runner lanes separate unless physical-host evidence proves a shared capacity domain.

## Verification Checklist

- [ ] Current head and canonical job/run evidence captured.
- [ ] Intended execution model stated.
- [ ] GitHub runner ID/name mapped to a listener/service and physical host, or explicitly unresolved.
- [ ] Runner-root path and storage domain identified.
- [ ] Blocks, inodes, tmpfs, and quota checked separately.
- [ ] Existing board owner corrected by exact runner domain.
- [ ] Alternate approved capacity enumerated before quarantine.
- [ ] Proposed action targets the proven execution domain and preserves secrets.
