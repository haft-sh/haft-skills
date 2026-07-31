# HTML artifact viewing and review-board pitfalls

Use this note when handling standalone HTML artifacts, review boards, or any request for a “Haft link” to an HTML file.

## Default expectation for a Haft link

When the user asks for a link to a file *in Haft*, the default expectation is usually:
- a **Haft URL**
- with the artifact shown **inside Haft context** when that mode exists
- not merely a raw standalone preview page
- and not a reader-text projection masquerading as a faithful rendered view

If the current app version cannot embed that artifact class in the shell, say so plainly and distinguish the fallback paths.

## Three distinct HTML experiences

1. **Reader/text document view**
   - chunked/indexed/document flow
   - suitable for Haft HTML-profile documents and markdown-like reading

2. **Standalone rendered HTML view**
   - browser renders the page as `text/html`
   - suitable for self-contained review boards, visual reports, mini-apps

3. **Shell-embedded rendered artifact view**
   - desired product direction when the user expects a Haft-native link
   - may not exist yet for every artifact class

Do not conflate these in user-facing language.

## Review-board pitfall: data URLs are fine for offline display, bad for click-through zoom

A self-contained review board with `data:` image URLs can be useful for offline portability, but it creates a UX trap:
- images may appear clickable
- clicking them navigates to a `data:` URL
- users expect a normal `http://...` or Haft-served asset URL for full-size inspection

When the user wants clickable images that open full-sized assets:
- do **not** point the anchor at the same `data:` URL
- point the anchor at a real served asset URL instead
- if no stable served asset URL exists yet, say so explicitly and choose a different delivery path rather than silently using `data:` links

## Operational rule for review boards

If an HTML review board is meant for real artifact inspection, prefer:
- rendered board served over HTTP, and
- clickable image links that resolve to HTTP-served full-size assets

Use fully self-contained `data:` embedding only when portability/offline use matters more than navigable full-size asset inspection.
