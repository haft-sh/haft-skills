# Haft CLI credential path under Hermes profiles

## Problem

The Haft CLI resolves credentials at `$HOME/.haft/cli-credentials.json`. When running under a Hermes profile with a non-default `HOME` (e.g. `~/.hermes/profiles/orchestrator/home`), the CLI finds no credentials even though they exist at the real user home (`~/.haft/cli-credentials.json`).

## Symptom

```
$ haft auth status
No CLI central credentials found. Run `haft auth login` first.

$ haft remotes list
No remotes configured.
Diagnostics:
  - cli-remote.central-wallet-missing: No CLI central wallet found at
    /home/ubuntu/.hermes/profiles/orchestrator/home/.haft/cli-credentials.json
```

## Fix

Symlink the credentials from the real home into the profile home:

```bash
ln -sf ~/.haft/cli-credentials.json \
  ~/.hermes/profiles/<profile>/home/.haft/cli-credentials.json
```

After symlink:
```
$ haft auth status
Signed in to Haft HQ.
Email: jplew108@gmail.com
...

$ haft remotes list
Slug    Source    Label    API origin         ...
dev     central   dev      https://dev.haft.sh ...
```

## Why this happens

Hermes profiles set `HOME` to the profile directory for session isolation. The Haft CLI uses `$HOME` for credential discovery. The two conventions conflict: Hermes wants `HOME` isolated, Haft wants `HOME` to be the real user home.

## Long-term fix candidates

1. `haft auth` checks `~/.haft/` as a fallback regardless of `$HOME`
2. `haft` supports `HAFT_HOME` env var for explicit credential path
3. Hermes profiles export `HAFT_HOME` pointing to the real `~/.haft/`

## Verified

2026-08-17: confirmed working on orchestrator profile after symlink.
`haft auth status`, `haft remotes list`, and `haft get --remote dev` all functional.
