# Haft Skills

Public operational skills for any AI agent operating [Haft](https://github.com/jplew/haft).

These skills follow the [agentskills.io](https://agentskills.io) open standard and are compatible with Hermes Agent, Codex, Claude Code, and other skill-aware tools.

## Skills

| Skill | Purpose |
|---|---|
| `daily-notes` | Deterministic daily-note creation and update workflow via the Haft CLI |
| `haft-agent-api` | Creating Haft HTML artifacts through the agent API |
| `haft-agent-session-operations` | Editing existing Haft documents through isolated agent sessions |
| `haft-import-operations` | Importing files into Haft and testing CLI-managed remote paths |
| `haft-pr-reconciliation` | Reconciling Haft PRs against the live Kanban board |
| `haft-vault-operations` | Deciding which Haft product seam to use for vault operations |

## Usage

### Hermes Agent

Clone this repo, then register it as an external skill directory:

```bash
hermes config edit
```

In the active config, declare `external_dirs` as a YAML list using absolute paths:

```yaml
skills:
  external_dirs:
    - /home/<user>/Sites/haft-skills
```

Preserve any existing external skill directories in the same list. Do not use `hermes config set skills.external_dirs '[...]'`: Hermes currently persists the bracketed value as a YAML string rather than a YAML list, which prevents external skills from being discovered.

All skills will appear in the agent's skill index, `skills_list()`, and as `/skill-name` slash commands.

### Other tools

Each skill is a directory containing a `SKILL.md` file (plus optional `references/`). Load them however your tool consumes agentskills.io-compatible skills.

## Sanitization policy

This is a **public** repository. Skills must contain only:
- Operational guidance and reusable procedures
- Generic CLI commands with placeholder paths (`<repo-root>`, `<github-org>`)
- Environment variable references (never values)
- Architecture patterns and design principles

Skills must **never** contain:
- Machine hostnames, IPs, or user-specific paths
- Credentials, tokens, API keys, or secrets
- Agent identities tied to personal infrastructure
- Personal workflow details or project-specific state

## Contributing

PRs welcome. All changes are reviewed for sanitization compliance before merge.

## License

MIT
