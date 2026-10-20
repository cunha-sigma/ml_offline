# ML offline design deck

Source: `slides.md` (Slidev). Edit this file only — `deck/slides.md` is a symlink to it.

## Presenting (what you actually need)

```
make install   # once
make dev       # starts the Slidev server
```

Two browser tabs open:
- **Audience view** — `http://localhost:3030` (share this screen / projector)
- **Presenter view** — `http://localhost:3030/presenter` (your screen: notes, next slide, timer)

Or just press **`p`** in the audience tab to pop open the presenter view.

## PDF export (optional)

```
make pdf
```

Outputs `ml-offline-design-deck.pdf` in this folder.

## Other

```
make build   # validates slides/diagrams, builds to deck/dist/
make clean   # removes dist/ and the PDF
```
