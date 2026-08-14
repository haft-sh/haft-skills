---
name: haft-document-retrieval
description: Retrieve and validate private Haft documents through the installed CLI, including canonical Reader URLs and bounded artifact-to-page resolution.
version: 1.0.0
---

# Haft Document Retrieval

## When to use

Use this for a request to read, inspect, summarize, or derive work from one existing Haft document hosted locally or on a managed remote destination.

Use before filing implementation tickets from a linked private Haft document. Ground ticket scope in the retrieved body, not an opaque shell URL or a guessed feature name.

## Primary path: canonical document locators

Use the installed CLI and the intended CLI home. First resolve the **configured remote slug** (not merely its HTTPS origin):

```bash
HOME=<dev-host-home> haft --json remotes
```

Match the supplied URL origin to `apiOrigin`, then pass the matching `slug` (for example `dev`) to `--remote`. Use the current top-level `query` command (not the retired `agent query-documents` spelling) to discover a document when its canonical locator is unknown. Prefer the document's canonical Reader URL, page ID, slug, chunk ID, or durable handle for retrieval:

```bash
haft query '<distinctive title terms>' --remote <configured-remote-slug> --json
haft get <reader-url-or-slug> --remote <configured-remote-slug> --json
# or
haft get --page <page-id> --remote <configured-remote-slug> --json
haft get --handle 'haft://artifact/<artifact-id>' --remote <configured-remote-slug> --json
`

Do not pass an HTTPS origin as `--remote`: that selector expects a configured local target slug. A client-side Reader URL may still be supplied as the document locator when its origin exactly matches the configured remote. Record only bounded facts needed for the next task: title, canonical page ID/slug, content hash, and the document text. Never put credentials, grants, session IDs, private paths, or full document text into durable Kanban comments unless the user explicitly asks for an attachment.

## UI-artifact route workaround

A shell URL such as `https://<remote>/#/artifact/<artifact-id>` may be a client-side route rather than a Reader URL that `haft get` can parse. If the user authorizes access to that exact private document and needs its text before a canonical Reader URL is available, resolve it without altering canonical content:

```bash
haft --json agent-session start --remote <target> --artifact <artifact-id>
# Extract `attachment.pageId` from the receipt.
haft --json get --page <resolved-page-id> --remote <target>
```

### Safety gate

Before continuing, verify the start/attach receipt says:

- `canonicalEffect: "none"`
- `copyCreated: false`

This creates or attaches isolated private draft-session state only. Do **not** run a turn, preview, diff, Apply, import, overwrite, or direct patch merely to read the document. Do not expose session IDs, draft contents, mirror paths, credentials, or grants in tickets/comments.

## Ticket intake after retrieval

1. Search live board and current source for existing or already-delivered work.
2. Separate features already delivered from the remaining product gap.
3. Cite the document title and stable page/artifact reference in the card, but summarize requirements rather than duplicating its full private body.
4. Make security boundaries, test expectations, non-goals, and Review handoff explicit.
5. For cross-cutting release/runtime/authorization changes, prefer one coherent implementation card over concurrent slices that could ship an unusable or unsafe partial contract.

## Pitfalls

- Do not treat a browser shell route as evidence that the CLI can retrieve the document.
- Do not guess a page ID from an artifact ID.
- Do not use direct vault/database access as the normal read path when the managed product path can resolve the identity.
- Do not mistake an isolated AgentSession start for authorization to mutate canonical content.
- Do not add broad artifact-URL parsing to `haft get` as an ad hoc workaround; that needs a reviewed URL/identity contract.

## Reference

- `references/ui-artifact-route-resolution.md` — bounded artifact-route-to-page resolution recipe and evidence shape.
