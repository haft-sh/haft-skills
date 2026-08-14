---
name: herdr-ssh-identity-bootstrap
description: "Use when bootstrapping SSH identity for remote Herdr agents."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [herdr, ssh, remote, agents, identity, coordination]
    related_skills: [herdr-team-agent-automation]
---

# Herdr SSH Identity Bootstrap

## Overview

Use this class-level skill when a configured SSH target is required for Herdr remote-agent discovery or prompting, but the target's identity file is missing, unusable, or not accepted. This skill handles the SSH prerequisite; the Herdr team-agent workflow remains responsible for server discovery, pane selection, read-only prompting, and response capture.

## Safe workflow

1. Run the reachability preflight in `references/herdr-remote-reachability-preflight.md` before treating a failure as an identity problem. Classify alias/configuration, network reachability, SSH authentication, and Herdr availability separately; do not substitute another visible peer or alias without explicit target verification.
2. Inspect the configured alias with `ssh -G <target>` and verify the effective user, hostname, port, and `identityfile`. Do not guess hostnames or silently fall back to another target.
2. Check the SSH directory and referenced key path without printing private-key contents. Refuse to overwrite an existing private or public key.
3. If the intended identity is absent, create a target-specific Ed25519 pair such as `~/.ssh/id_ed25519_<target>` with restrictive permissions:
   - private key: `0600`
   - public key: `0644`
   - SSH directory: `0700`
4. Verify the public-key fingerprint locally. The public key can be given to the operator for installation; never expose the private key.
5. Install the public key in the remote account's `~/.ssh/authorized_keys` through an already-authorized access path or operator-controlled console. Generating the pair alone cannot repair remote authentication.
6. Only after installation, update the matching `Host` block to reference the dedicated key, or invoke SSH explicitly with `-i`. Preserve unrelated host blocks and existing file permissions.
7. Re-run the bounded connection test with `ssh -o BatchMode=yes -o ConnectTimeout=20 <target> ...`, then use the Herdr remote binary to verify server status and enumerate panes.
8. Select and verify the agent by pane ID, CWD, terminal title, and visible prompt; do not infer the target from pane order or a duplicate agent name.

## Verification and boundaries

- A generated key is not proof that the remote host accepts it; an actual SSH connection is required.
- Do not use a newly generated key or `ssh-keyscan` output as a substitute for installing the public key.
- Do not overwrite a missing generic `id_rsa` merely because an alias names it. Prefer a target-specific Ed25519 key and an explicit alias change.
- Treat SSH config and credential files as sensitive operational files. Make only the requested host-block change, and stop if a credential-file guard blocks an unrequested configuration edit.
- If SSH authentication fails because the private key is unavailable, report the exact alias, host, missing identity path, and required operator action. Do not ask for or print private keys.

## Reporting format

Report:
- generated private/public key paths;
- public-key fingerprint;
- whether the public key was installed remotely;
- whether the SSH connection was verified;
- the Herdr server/pane evidence if discovery proceeded;
- any config file left unchanged because remote installation or explicit config authorization is still required.

See `references/herdr-ssh-identity-bootstrap.md` for the concrete missing-identity failure shape and the observed safe recovery boundary.

## Common pitfalls

- Treating key generation as a completed connectivity repair.
- Treating a timeout or refused TCP connection as an SSH key failure; classify network reachability first.
- Switching to a visible Tailscale peer or alternate alias without verifying that it is the intended Herdr host and agent identity.
- Overwriting an existing key to satisfy a stale `IdentityFile` path.
- Updating every SSH alias when only one remote target needs repair.
- Printing private-key material, full SSH config secrets, or unrelated host data.
- Selecting a remote agent by name alone when multiple panes expose the same generic name.
