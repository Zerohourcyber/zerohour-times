# Screenshots

`newspaper.png` is referenced from the project README and is **not generated
automatically** — it is a real screenshot of a real edition, taken by a human.

To produce it:

1. Run the demo so the page is populated with the bundled sample data:
   ```bash
   docker compose run --rm --no-deps --service-ports zerohour-times demo
   ```
2. Open <http://localhost:8099> at roughly 1400px wide.
3. Capture the full page (Firefox: right-click → *Take Screenshot* → *Save full
   page*; Chrome: DevTools → ⌘/Ctrl-Shift-P → *Capture full size screenshot*).
4. Save it here as `newspaper.png`.

Use the **demo data**, not your own edition — a screenshot of a real run would
publish your job search and your assessments.
