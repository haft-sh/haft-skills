# Portable Repo Skill Boundary

Use this note when maintaining Haft's repo-shared skills under `.hermes/skills/haft-ops/`.

## Rule of thumb

Repo skills should explain how Haft behaves for **the user** of the product.
They should not encode one developer's machine layout, service manager, hostnames, ports, tailnet addresses, or personal vault paths.

## Put these in repo-shared skills

- API routes and when to use them
- expected request/response shapes
- verification patterns that apply across installs
- product-level pitfalls such as route selection, CORS vs allowlisting, or canonical-path verification
- stable operational semantics that a user or agent would need on any installation

## Keep these out of repo-shared skills

- `systemctl --user` commands for one developer's service
- personal vault roots such as `/home/...`
- Tailscale IPs or local hostnames
- one user's preferred vault names or batches unless they are product defaults
- instructions that only make sense in one workstation setup

## Where machine-specific instructions belong

Use one of these instead:
- profile-local skills under `~/.hermes/profiles/<profile>/skills/`
- workspace docs such as `~/Sites/AGENTS.md`
- project-local operational notes that are explicitly marked as install-specific

## Multi-profile loading convention

If multiple Hermes profiles should see the repo-shared Haft skills, each profile should load the repo root via:

```yaml
skills:
  external_dirs:
    - /path/to/haft/.hermes/skills
```

When updating an existing profile config, append this directory to `skills.external_dirs`; do not overwrite other configured external skill roots.
