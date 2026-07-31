# Shared image-page import note

Use this when the user provides a shared page that visually contains generated images and wants those images persisted into Haft.

## Reliable pattern

1. Resolve the share page.
2. Extract the underlying image URL from the page content when available.
3. If normal extraction omits the image URL, inspect the page's image list in the browser and capture the direct image source there.
4. Download the resolved image locally.
5. Import the binary through `POST /api/import/media`.
6. Preserve provenance separately through document upload.

## Concrete example: ChatGPT share pages

ChatGPT share pages are one concrete case and may expose the image in one of two practical ways:
- directly in extracted markdown as a `![Image](https://chatgpt.com/backend-api/estuary/public_content/enc/...)` link
- indirectly only through browser image inspection

If one path fails, try the other. The durable lesson is the fallback extraction pattern, not that either tool path is universally unavailable.

## Provenance guidance

- For final named assets, prefer one provenance note per image.
- For looser brainstorming/reference batches, a single batch provenance note with source URLs/titles is acceptable when the user says prompts are not important.
