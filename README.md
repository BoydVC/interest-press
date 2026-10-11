# Interest Press

A multi-section morning newspaper rendered from Boyd's local Interest Journal / bookmark research files.

## Quick start

```bash
cd /workspace/tokenmax/interest-press
./run.sh          # collect → build → serve http://127.0.0.1:4292/
./run.sh --shots  # also write screenshots/
```

Offline single file: `dist/interest-press.html`

## Pipeline

1. `collect.py` — scans `/workspace/ij_*.md` (+ bookmark atlas / yml), writes `data/press.json`
2. `build.py` — embeds `press.json` + CSS/JS into `dist/interest-press.html`
3. `server.py` — stdlib HTTP on **127.0.0.1:4292**

## Sections

- **Front Page** — masthead + lead cards from real headings/excerpts
- **Sports Desk** — Ravens / Orioles / Chelsea / Terps
- **Space & xAI** — SpaceX / Starlink / Elon / agent tooling
- **Bookmark Radar** — titles/URLs when readable
- **Reader** — full article (sanitized markdown→HTML); ←/→ keyboard
- **Archive** — source file list

KPD / firm-private sections are skipped. Thin beats show a banner instead of inventing copy.

## Stack

Python stdlib + vanilla HTML/CSS/JS. No npm.


---
## Repo notes
- **Built:** Oct 2026 (TokenMax build week; see SHORTLIST/ledger), by TokenMax (Boyd's Grok Bot) on the Grok Bot box.
- **Run:** `./run.sh` (then open the localhost URL it prints).
- Imported from `/workspace/tokenmax/interest-press` on Oct 23, 2026. node_modules, virtualenvs, logs and files over 20 MB were left out.
