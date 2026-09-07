# Named Haft Instance Resolution Guide

## Instance Nicknames

This host runs multiple Haft instances. When the user refers to an instance by nickname, resolve it to the canonical path before writing.

| Nickname | URL | Canonical checkout |
|---|---|---|
| **<instance-name>** | https://dev.haft.sh | `<repo-root>` |

Add new instances here as they become known. Always verify the path exists before writing.

## Common mistakes

1. **Confusing Hermes profile paths with instance paths**: `/home/ubuntu/.hermes/profiles/orchestrator/` is the Hermes orchestrator profile, not the Haft instance. Documents go in the instance's `docs/` directory.
2. **Saving to profile path instead of instance path**: The user says "save to <instance-name>" → correct path is `<repo-root>/docs/YYYY-MM-DD-<topic>.md`, NOT `~/.hermes/profiles/orchestrator/<instance-name>-<topic>.md`.
3. **Skipping verification**: Always `ls` the target path after writing to confirm the file is in the right vault, not just that the write tool returned success.

## Verification pattern

```bash
ls -la <repo-root>/docs/YYYY-MM-DD-<topic>.md
```

The response must show the file exists in the correct Haft instance docs directory.
