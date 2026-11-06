# ML offline design — compiled PDF

Renders `design_docs/00_overview.md` through `09_monitoring.md` into
one PDF, with `DISCOVERY_SUMMARY.md` and the ADRs as an annex. Source
text is never modified — this just prints it.

```
make install   # once — pulls mermaid + a local Chromium (playwright)
make pdf       # builds ml-offline-design.pdf in this folder
```

Requires `pandoc` on PATH (`brew install pandoc`). No LaTeX needed —
rendering goes markdown → HTML (mermaid diagrams rendered in-browser)
→ PDF via a local headless Chromium.

Includes, in order: a title page, a clickable table of contents, Part
I (the ten design docs, one chapter each, in file order), Part II —
Annex (discovery summary, then ADR 0000–0006).

## Changing what's included

Edit the `MAIN_FILES` / `ANNEX_FILES` lists at the top of
`build/render.mjs` — e.g. to add `OPEN_QUESTIONS.md`,
`CLIENT_QUESTIONS.md`, or `PLAN.md` to the annex.

## Other

```
make clean   # removes build/out/ and the PDF
```
