# Named Haft Instance Resolution Guide

## Instance Nicknames

This host runs multiple Haft instances. When the user refers to an instance by nickname, resolve it to the canonical path before writing.

| Nickname | URL | Canonical checkout |
|---|---|---|
| **indraloka** | https://dev.haft.sh | `/home/ubuntu/Sites/haft` |

Add new instances here as they become known. Always verify the path exists before writing.

## Common mistakes

1. **Confusing Hermes profile paths with instance paths**: `/home/ubuntu/.hermes/profiles/orchestrator/` is the Hermes orchestrator profile, not the Haft instance. Documents go in the instance's `docs/` directory.
2. **Saving to profile path instead of instance path**: The user says "save to indraloka" → correct path is `/home/ubuntu/Sites/haft/docs/YYYY-MM-DD-<topic>.md`, NOT `/home/ubuntu/.hermes/profiles/orchestrator/indraloka-<topic>.md`.
3. **Skipping verification**: Always `ls` the target path after writing to confirm the file is in the right vault, not just that the write tool returned success.

## Verification pattern

```bash
ls -la /home/ubuntu/Sites/haft/docs/YYYY-MM-DD-<topic>.md
```

The response must show the file exists in the correct Haft instance docs directory.
