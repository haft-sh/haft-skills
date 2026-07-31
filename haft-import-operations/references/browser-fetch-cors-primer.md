# Browser fetch vs normal navigation (CORS primer)

Use this note when a user says some version of:
- "I can open the URL in the browser, so why can't Haft fetch it?"
- "Does Haft need to whitelist the domain?"
- "I thought 'Fetch in browser' meant the browser downloads the file to the machine."

## The core distinction

There are three different browser behaviors that are easy to confuse:

1. **Top-level navigation**
   - The user opens a URL directly in a tab.
   - The browser is allowed to render the destination page.
   - This does **not** require CORS permission for some other app/page to read the response body.

2. **Download to local device storage**
   - The browser saves a file to the phone/computer Downloads area.
   - Haft does not automatically gain access to that saved file.
   - A separate upload/file-picker step would still be required.

3. **Browser-mediated import inside Haft**
   - Haft's page JavaScript calls `fetch(url)`.
   - If the browser allows cross-origin read access, the page gets the bytes in memory.
   - The page wraps them as a `Blob`/`File` and uploads them through Haft's import route.
   - This path depends on **CORS / cross-origin readability**.

## Practical operator explanation

When the active page is Haft and it tries to fetch a remote URL, the browser asks:

> Is this remote origin allowing the Haft origin to read the response body?

If the remote source does not return a suitable `Access-Control-Allow-Origin` header, the request may still happen on the network, but Haft's page JavaScript will not be allowed to read the body. That is why the user can often open the URL in a normal tab but still see a browser-fetch failure inside Haft.

## What to check

1. **App-side trust/allowlist** — is the host permitted by Haft's browser-fetch policy?
2. **Source-side CORS** — does the remote response include the right `Access-Control-Allow-Origin` header for the Haft app origin?
3. **Redirect behavior** — did the request redirect somewhere unexpected or off-policy?
4. **Content type / response shape** — is the fetched resource actually usable as the intended import input?

## How to explain the current product behavior

For the browser-fetch import path, say this plainly:

- Haft is **not** asking the backend to fetch the URL from the server side.
- The browser is trying to read the remote bytes in memory.
- If readable, Haft uploads those bytes through the normal import flow.
- This lowers SSRF exposure compared with a generic server-side URL fetcher, but it means CORS matters.

## Pitfall to avoid

Do not tell the user that "Fetch in browser" downloads the file to the host machine. That is the wrong mental model, especially on mobile. The current behavior is in-browser memory fetch plus upload, not a device-download handoff to the server.
