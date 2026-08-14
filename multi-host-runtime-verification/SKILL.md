---
name: multi-host-runtime-verification
description: Verify you are operating the intended deployed runtime in multi-host environments before claim/bootstrap/recovery/debug actions.
version: 1.0.0
author: Hermes Agent
license: MIT
---

# Multi-Host Runtime Verification

## When to use

Use this before any operator action against a deployed environment when a project has more than one relevant machine or runtime, for example:
- canonical checkout on one host, public app on another
- CI runner on one host, deployed service on another
- local listener and public hostname that may not map to the same runtime
- Dev / prod / HQ split across separate instances
- SSH/SSM/operator recovery tasks such as claim, bootstrap, revoke, reset, hotfix, migration, or direct API mutation

## Why this exists

A common failure mode is inferring target identity from convenient local evidence:
- the repo checkout is on the current host
- the GitHub runner is on the current host
- `127.0.0.1` returns a plausible app response
- an old architecture note still describes a prior topology

That can lead to mutating the wrong vault, claiming the wrong instance, or reporting success against the wrong environment.

## Required verification sequence

1. **Read the current source of truth first**
   - Prefer the current repo `README.md` deployment/environment table and active runbooks over memory or historical diagrams.
   - If two docs disagree, prefer the newer operational doc and then verify live state.

2. **Identify the exact target tuple**
   Record all of:
   - hostname
   - instance id / host id
   - service name
   - app directory
   - vault root or data root
   - access lane (local shell, SSH, SSM, dashboard, reverse proxy, public URL)

3. **Compare local and public state explicitly**
   - Query the local listener on the machine you are currently on.
   - Query the public target hostname.
   - Compare key state such as auth/app status.
   - If they diverge, treat that as proof you are not touching the same runtime.

4. **Use the lane that matches the target**
   - If the real target is remote, switch to the documented remote lane (for example SSM) before mutating anything.
   - Do not mutate the local checkout, local vault, or local service just because it is accessible.

5. **Only then take the operator action**
   Examples:
   - claim/bootstrap first owner
   - revoke/reset auth state
   - restart service
   - inspect vault files
   - apply migrations
   - run local-only recovery scripts

6. **Verify on the real target after the action**
   - Re-check the public hostname or the target host's own local listener, depending on the task.
   - Do not treat success on an intermediate host as proof the public environment changed.

### Live proxy/config changes require separate authorization

Ticket ownership or authorization to investigate does not automatically authorize a deployed configuration change. Before changing reverse-proxy, TLS, compression, DNS, firewall, or systemd configuration:

1. complete read-only target verification and capture the minimal current configuration;
2. state the exact mutation, service reload/restart, and rollback artifact;
3. obtain explicit confirmation when the execution surface presents a dangerous-action gate; and
4. if confirmation is withheld or times out, do not retry through another command path. Preserve local code and evidence, record the precise blocker, and leave the live target unchanged.

Keep this distinct from source-code review: a locally verified patch does not itself authorize a deployed-runtime mutation.

## Practical heuristics

- A matching JSON shape is not proof of shared runtime identity.
- A successful `curl http://127.0.0.1:...` only proves something about the current machine.
- A canonical repo checkout often lives somewhere other than the deployed service.
- CI and deployment may run from one host while the public app lives on another.

## Pitfalls

### Mistaking orchestration host for public app host
If the dashboard, gateway, repo checkout, or runner live on DevSpace/orchestrator, do not assume the public app also lives there.

### Trusting stale diagrams over current deployment docs
Historical architecture docs can remain useful background, but they are not enough for live operator actions.

### Treating a hostname label as proof of its origin
A hostname such as `gly.example.com` can temporarily resolve to a disposable E2E or test instance while an older instance still carries a similar service name, vault, or deployment role. Before claim, enrollment, vault repair, or DNS work:

1. Resolve the public hostname and record its IP/CNAME.
2. Map that address to the cloud instance and record tags, instance type, lifecycle/purpose markers, service, app directory, and vault root.
3. Compare the hostname's no-cache status response with the candidate host's loopback status.
4. If the public target is temporary or differs from the candidate, do not mutate either runtime as if it were the other. Establish the intended durable target first.

A successful repair on an old host is not a public recovery unless the hostname's actual origin is verified afterwards.

### Verifying only the local side
If you claim, reset, or hotfix a runtime, always re-check the public target or actual remote host afterwards.

### Mistaking a host-header guard for a dead service
A public dashboard or admin surface can look "down" even when the service is healthy if the listener bind and the public Host header no longer match.

Probe this class explicitly:
1. confirm which unit is actually active (user vs system systemd units, and whether a stale duplicate unit still exists);
2. record the listener bind (`127.0.0.1`/`localhost` vs `0.0.0.0`/specific hostname) and port;
3. compare a plain local request with an explicit `Host:` request that matches the public hostname;
4. inspect the reverse-proxy layer separately (Caddy, Tailscale Serve/Funnel, cloud redirect, etc.) and capture any redirect chain.

Interpretation:
- local request succeeds but explicit `Host:` request returns a host-header error -> service is up; the bind/proxy contract is wrong;
- public hostname redirects to another origin before the app -> diagnose the redirect target separately; a healthy local listener is not proof the public path works.

For Hermes dashboard specifically, a loopback bind accepts only loopback Host headers. Public hostname access through Caddy/Tailscale/cloud redirects needs `--host 0.0.0.0` or another bind/hostname arrangement that matches the incoming Host header. After repair, remove or archive stale duplicate units so the next operator does not debug the wrong service.

Reference: `references/hermes-dashboard-host-header-mismatch.md`.

## Session Manager client-side endpoint timeouts

If `aws ssm start-session` reports `Connect timeout on endpoint URL` while the target is running and SSM reports `Online`, classify that as a client-to-AWS-control-plane failure—not a target or agent failure.

1. Resolve both `ssm.<region>.amazonaws.com` and `ssmmessages.<region>.amazonaws.com` on the client.
2. If a laptop connected through VPN/Tailscale/split DNS receives RFC1918 addresses for those names, it may be seeing VPC interface-endpoint private DNS without a working route or endpoint-security-group admission.
3. Prefer correcting the split-DNS/routing policy. Do not hardcode interface-endpoint IPs.
4. A bounded bypass is the regional FIPS API endpoint:
   ```bash
   aws ssm start-session \
     --region <region> \
     --endpoint-url https://ssm-fips.<region>.amazonaws.com \
     --target <instance-id>
   ```
   Verify first that `StartSession` returns a stream URL on `ssmmessages-fips.<region>.amazonaws.com`; that keeps both the API and data-channel paths off the unreachable private-DNS names.
5. If the FIPS path also times out, test HTTPS reachability and local proxy/firewall policy before changing the EC2 instance, SSM agent, IAM profile, or VPC endpoints.

See `references/ssm-split-dns-fips-bypass.md` for the exact DNS probes, safe `StartSession`/`StreamUrl` verification, immediate test-session cleanup, and durable repair options.

## Output discipline

When reporting completion, separate:
- what host you actually touched
- how you verified it was the intended target
- what public endpoint or remote status confirmed success

If you discover you touched the wrong runtime, say so directly, repair the real target, and clearly distinguish the accidental local mutation from the intended remote change.
