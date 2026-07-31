# UI reference lock before implementation

Use this when Haft is about to restart, rebuild, or significantly redesign app-shell UI after architecture planning.

## Durable lesson

Do not send workers into UI implementation from architecture docs alone. JP explicitly called out that the previous app build got messy because work started before there was a clear picture of the finished product. Before dispatching app-shell work, lock visual references into the roadmap or equivalent product doc so workers have a concrete north star.

## Workflow

1. **Freeze implementation flow first** when architecture/UI direction is being reset.
   - Pause orchestrator/cron dispatch if active.
   - Keep implementation cards blocked or scheduled until references are captured.
2. **Collect the reference screens** from the user.
   - If they are ChatGPT shared images, open the share, extract the real image `src`, download the bytes, and verify the saved image dimensions/signature.
   - Avoid relying on ephemeral ChatGPT/backend URLs in docs.
3. **Persist references durably.**
   - Save a repo-local source copy under a product-doc asset directory such as `content/assets/ui-mockups/`.
   - Upload shareable copies to durable object storage/R2 using stable keys.
   - Verify public URLs with a ranged GET and content type, not just successful upload output.
4. **Insert references into the roadmap/product doc near the top.**
   - Add a clear section like `Visual direction lock`.
   - State that these images are product direction, not decoration.
   - Include captions describing each screen/state and local source path.
5. **Make adherence operational.**
   - Add explicit acceptance language: UI cards must cite the visual-lock section and include screenshot-based verification against it.
   - Comment on existing UI Kanban cards so workers see the requirement even if they do not re-read the whole roadmap.
6. **Only then resume implementation or migration work.**

## Acceptance language to reuse

For desktop shell cards:

> Implementation must adhere to the roadmap's desktop visual direction lock. Verify with screenshots showing the rebuilt shell against the locked desktop reference: browse-first left navigation, reader-centered canvas, and metadata/actions on the right.

For mobile/responsive cards:

> Implementation must show both mobile states before it is treated as done: (1) a browse-first vault drawer with import/create/search/recent/library affordances, and (2) a clean reader-first state with bottom navigation and accessible metadata/actions. Do not ship a merely shrunken desktop layout.

## Pitfalls

- Do not treat visual references as loose inspiration once the user says to lock them.
- Do not leave references only in chat history or temporary local files.
- Do not store ChatGPT CDN/backend URLs as canonical references; mirror them to durable storage.
- Do not resume a broad implementation queue while the UI reference set is still incomplete.
- Do not forget Kanban/worker handoff comments; roadmap docs alone are easy for autonomous workers to miss.
