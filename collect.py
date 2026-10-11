#!/usr/bin/env python3
"""Collect Interest Journal / bookmark research into data/press.json for Interest Press."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORKSPACE = Path("/workspace")
OUT = ROOT / "data" / "press.json"

# Skip firm-private / KPD ops material
KPD_RE = re.compile(
    r"\b(KPD|Klima|kpdlaw|BlueCubed|KPD04|collections\s+law|firm\s+ops|law[\s-]?firm)\b",
    re.I,
)
KPD_SECTION_RE = re.compile(r"(?i)^(#+)\s*.*\b(KPD|Chrome\s*/?\s*ops|firm)\b")

SPORTS_KEYS = {
    "ravens": re.compile(r"\bravens?\b|\blamar\b|\bhuntley\b", re.I),
    "orioles": re.compile(r"\borioles?\b|\bbirds?\b.*\bmlb\b|\bmlb\b.*\borioles?\b", re.I),
    "chelsea": re.compile(r"\bchelsea\b|\bpalmer\b|\bstamford\b", re.I),
    "terps": re.compile(r"\bterps?\b|\bmaryland\b.*\b(football|hoops|basketball)\b|\blocksley\b", re.I),
}
SPORTS_SECTION = re.compile(
    r"(?i)(sports|household\s*/\s*sports|ravens|orioles|chelsea|terps|football|mlb|premier)",
)
SPACE_SECTION = re.compile(
    r"(?i)(spacex|starlink|starship|starmind|musk|xai|grok\s*bot|tesla|neuralink|boring|"
    r"agent\s*tool|personal[- ]?ai|elon)",
)
BOOKMARK_SECTION = re.compile(r"(?i)(bookmark|agent\s*army|ai[- ]?ops)",)

DATE_IN_NAME = re.compile(r"ij_(\d{4}-\d{2}-\d{2})")
H_RE = re.compile(r"^(#{1,4})\s+(.+?)\s*$", re.M)
MD_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
URL_RE = re.compile(r"https?://[^\s\)\]\>\"']+")
BULLET = re.compile(r"^[\-\*]\s+")


def et_now_iso() -> str:
    # Box is America/New_York; stamp as local-ish ISO without forcing zone math
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def file_mtime_iso(p: Path) -> str:
    ts = p.stat().st_mtime
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%dT%H:%M:%S")


def date_from_path(p: Path) -> str | None:
    m = DATE_IN_NAME.search(p.name)
    return m.group(1) if m else None


def clean_text(s: str) -> str:
    s = MD_LINK.sub(r"\1", s)
    s = re.sub(r"[*`_~]{1,3}", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def excerpt(s: str, n: int = 400) -> str:
    t = clean_text(s)
    if len(t) <= n:
        return t
    cut = t[: n - 1]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut + "…"


def is_kpd_block(title: str, body: str) -> bool:
    if KPD_SECTION_RE.search("# " + title):
        return True
    # Whole-section KPD ops / Chrome offline notes
    head = (title + "\n" + body[:500]).lower()
    if "kpd ops" in head or "kpd04" in head or "bluecubed" in head:
        return True
    # Skip if body is mostly KPD and short sports-free
    if KPD_RE.search(title) and not SPORTS_SECTION.search(title):
        return True
    return False


def strip_kpd_paragraphs(body: str) -> str:
    keep = []
    for para in re.split(r"\n\s*\n", body):
        if KPD_RE.search(para) and not SPORTS_KEYS["ravens"].search(para):
            # Drop pure KPD paras; keep if also sports/space
            if not (SPACE_SECTION.search(para) or any(r.search(para) for r in SPORTS_KEYS.values())):
                continue
        keep.append(para)
    return "\n\n".join(keep).strip()


def split_sections(text: str) -> list[dict]:
    """Split markdown into heading blocks (## and ### preferred)."""
    lines = text.splitlines()
    blocks: list[dict] = []
    cur_level = 0
    cur_title = ""
    cur_lines: list[str] = []
    file_title = ""

    def flush():
        nonlocal cur_title, cur_lines, cur_level
        body = "\n".join(cur_lines).strip()
        if cur_title or body:
            blocks.append({"level": cur_level, "title": cur_title or file_title or "Untitled", "body": body})
        cur_title, cur_lines, cur_level = "", [], 0

    for line in lines:
        m = re.match(r"^(#{1,4})\s+(.+?)\s*$", line)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            if level == 1 and not file_title:
                file_title = title
                # Don't flush yet — H1 is file masthead
                continue
            if level <= 3:
                flush()
                cur_level = level
                cur_title = title
                continue
        cur_lines.append(line)
    flush()
    return blocks


def classify(title: str, body: str) -> str:
    blob = title + "\n" + body[:800]
    tl = title.lower()
    # Explicit title lanes first
    if re.search(r"(?i)bookmark", tl) or re.search(r"(?i)agent\s*army|ai[- ]?ops", tl):
        if SPACE_SECTION.search(body[:400]) and not SPORTS_SECTION.search(tl):
            # agent/AI tooling often overlaps space/xAI — keep as space when Grok/xAI heavy
            if re.search(r"(?i)grok|x\.ai|xai|spacex|agent", body[:500]):
                return "space"
        return "bookmarks"
    if re.search(r"(?i)^quiet elsewhere", tl):
        # Day digests mention every beat — park as general, not sports
        return "general"
    if SPORTS_SECTION.search(title) or any(r.search(title) for r in SPORTS_KEYS.values()):
        return "sports"
    if SPACE_SECTION.search(title):
        return "space"
    # body heuristics: sports only when a team keyword hits AND sports framing
    sports_hits = sum(1 for r in SPORTS_KEYS.values() if r.search(blob))
    if sports_hits >= 1 and re.search(r"(?i)\b(sports|ravens|orioles|chelsea|terps|nfl|mlb|epl|premier league)\b", blob):
        return "sports"
    if SPACE_SECTION.search(blob) and sports_hits == 0:
        return "space"
    if re.search(r"(?i)bookmark", blob[:200]):
        return "bookmarks"
    return "general"


def sports_team(title: str, body: str) -> str | None:
    blob = title + "\n" + body[:600]
    for team, rx in SPORTS_KEYS.items():
        if rx.search(blob):
            return team
    return None


def slug(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.lower()).strip("-")
    return (s[:48] or "item")


def parse_ij_file(path: Path) -> tuple[list[dict], dict]:
    text = path.read_text(encoding="utf-8", errors="replace")
    date = date_from_path(path) or file_mtime_iso(path)[:10]
    mtime = file_mtime_iso(path)
    meta = {
        "path": str(path),
        "name": path.name,
        "date": date,
        "mtime": mtime,
        "bytes": path.stat().st_size,
        "kind": kind_from_name(path.name),
    }
    articles = []
    # Skip pure chrome A11Y dumps with no research content
    if path.name.endswith("_chrome.md") and "Household" not in text and "Sports" not in text:
        # Still archive the file but no articles
        return articles, meta
    # Skip raw X a11y dumps that are mostly UI chrome
    if path.name.endswith("_x.md") and text.lstrip().startswith("- generic"):
        return articles, meta

    blocks = split_sections(text)
    # If no ## sections, treat whole body as one article under H1
    if not blocks:
        body = strip_kpd_paragraphs(text)
        if body and not is_kpd_block(path.name, body):
            articles.append(make_article(
                title=path.stem.replace("_", " "),
                body=body,
                section="general",
                source=meta,
                date=date,
            ))
        return articles, meta

    # Merge tiny ### under parent ## when helpful: keep each ##/### as card if substantial
    for b in blocks:
        title = b["title"]
        body = strip_kpd_paragraphs(b["body"])
        if is_kpd_block(title, body):
            continue
        if len(clean_text(body)) < 40 and b["level"] >= 3:
            continue
        if not body.strip() and b["level"] >= 2:
            continue
        section = classify(title, body)
        # Drop leftover KPD-heavy general chrome notes
        if section == "general" and KPD_RE.search(body) and len(clean_text(body)) < 200:
            continue
        art = make_article(title=title, body=body or title, section=section, source=meta, date=date)
        if section == "sports":
            art["team"] = sports_team(title, body)
            # Drop carry/quiet stubs that aren't real team clips
            if re.match(r"(?i)^(quiet|highlight bullets|cut guidance)\b", title.strip()):
                continue
            if re.match(r"(?i)^b\.\s*sports\b", title.strip()) and len(clean_text(body)) > 600:
                # Split umbrella "B. Sports" into team subclips when ### missing — keep as sports
                pass
        articles.append(art)
    return articles, meta


def kind_from_name(name: str) -> str:
    if "_research" in name:
        return "research"
    if "_content" in name:
        return "content"
    if "_bookmarks" in name:
        return "bookmarks"
    if "_x" in name:
        return "x"
    if "_chrome" in name:
        return "chrome"
    if "_body" in name:
        return "body"
    return "journal"


def make_article(title: str, body: str, section: str, source: dict, date: str) -> dict:
    aid = f"{source['date']}-{slug(title)}-{source['name'][:12]}"
    return {
        "id": aid,
        "title": clean_text(title)[:180],
        "section": section,
        "date": date,
        "excerpt": excerpt(body, 400),
        "body": body.strip()[:12000],
        "source_path": source["path"],
        "source_name": source["name"],
        "source_kind": source["kind"],
        "team": None,
        "urls": URL_RE.findall(body)[:8],
    }


def collect_bookmarks_from_atlas() -> list[dict]:
    atlas = WORKSPACE / "tokenmax" / "bookmark-atlas" / "data" / "posts.json"
    out = []
    if not atlas.exists():
        return out
    try:
        data = json.loads(atlas.read_text(encoding="utf-8"))
        posts = data.get("posts") or []
    except Exception:
        return out
    for p in posts[:40]:
        title = (p.get("notes") or [None])[0] if isinstance(p.get("notes"), list) else None
        if not title:
            handle = p.get("handle") or p.get("name") or "bookmark"
            raw = p.get("text") or p.get("quote") or ""
            if isinstance(raw, dict):
                raw = raw.get("text") or raw.get("title") or str(raw)
            text = str(raw).strip()
            title = f"@{handle}" + (f" — {text[:120]}" if text else "")
        title = clean_text(str(title))[:180]
        url = p.get("url") or ""
        if not url and p.get("id"):
            handle = p.get("handle") or "i"
            url = f"https://x.com/{handle}/status/{p['id']}"
        if KPD_RE.search(title):
            continue
        out.append({
            "id": f"bm-{p.get('id') or slug(title)}",
            "title": title,
            "url": url,
            "handle": p.get("handle"),
            "sources": p.get("sources") or [],
        })
    return out


def collect_bookmarks_from_yml() -> list[dict]:
    """Best-effort parse of X a11y YAML dumps for status URLs + nearby text."""
    found: dict[str, dict] = {}
    paths = sorted(WORKSPACE.glob("bookmarks*.yml"))[:8]
    paths += sorted(WORKSPACE.glob("bm*.yml"))[:4]
    text_re = re.compile(r"- text:\s*(.+)$")
    url_re = re.compile(r"/url:\s*(/(?:[A-Za-z0-9_]+)/status/\d+)")
    article_re = re.compile(r"article\s+\"([^\"]{20,200})")
    for path in paths:
        try:
            raw = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        lines = raw.splitlines()
        pending_text: list[str] = []
        for i, line in enumerate(lines):
            tm = text_re.search(line)
            if tm:
                t = tm.group(1).strip().strip("'\"")
                if len(t) > 20 and not t.startswith("To view keyboard"):
                    pending_text.append(t)
                    if len(pending_text) > 6:
                        pending_text.pop(0)
            um = url_re.search(line)
            if um:
                path_url = um.group(1)
                if "/analytics" in path_url:
                    continue
                full = "https://x.com" + path_url
                sid = path_url.rstrip("/").split("/")[-1]
                if sid in found:
                    continue
                title = pending_text[-1] if pending_text else None
                # Look ahead for article label
                window = "\n".join(lines[max(0, i - 3) : i + 8])
                am = article_re.search(window)
                if am and (not title or len(title) < 40):
                    title = am.group(1)
                if not title:
                    continue
                title = clean_text(title)[:180]
                if KPD_RE.search(title):
                    continue
                handle = path_url.strip("/").split("/")[0]
                found[sid] = {
                    "id": f"yml-{sid}",
                    "title": title,
                    "url": full,
                    "handle": handle,
                    "sources": [path.name],
                }
            if len(found) >= 30:
                break
        if len(found) >= 30:
            break
    return list(found.values())[:25]


def pick_leads(articles: list[dict], n: int = 6) -> list[str]:
    """Mix newest sports + space research cards for the front page."""
    skip_title = re.compile(
        r"(?i)^(quiet|highlight bullets|cut guidance|e\)|b\.\s*sports|household)"
    )

    def score(a: dict) -> float:
        if len(a["excerpt"]) < 80:
            return -1.0
        if skip_title.search(a["title"]):
            return -1.0
        s = 0.0
        if a["source_kind"] in ("research", "content"):
            s += 5
        if a["section"] in ("sports", "space"):
            s += 3
        s += min(len(a["excerpt"]), 400) / 100.0
        try:
            s += (int(a["date"].replace("-", "")) - 20260901) * 2.0
        except Exception:
            pass
        if a.get("team") or re.search(
            r"(?i)spacex|starlink|starship|ravens|orioles|chelsea|terps|xai|grok",
            a["title"],
        ):
            s += 4
        return s

    sports = sorted(
        [a for a in articles if a["section"] == "sports" and score(a) > 0],
        key=score,
        reverse=True,
    )
    space = sorted(
        [a for a in articles if a["section"] == "space" and score(a) > 0],
        key=score,
        reverse=True,
    )
    other = sorted(
        [a for a in articles if a["section"] == "general" and score(a) > 0],
        key=score,
        reverse=True,
    )
    leads: list[str] = []
    seen: set[str] = set()

    def take(pool: list[dict], k: int) -> None:
        added = 0
        for a in pool:
            if len(leads) >= n or added >= k:
                return
            key = a["title"].lower()[:40]
            if key in seen or a["id"] in leads:
                continue
            seen.add(key)
            leads.append(a["id"])
            added += 1

    take(sports, 2)
    take(space, 3)
    take(other, 2)
    take(sports, 2)
    take(space, 2)
    return leads[:n]


def main() -> None:
    ij_files = sorted(WORKSPACE.glob("ij_*.md"))
    articles: list[dict] = []
    sources: list[dict] = []
    seen_ids: set[str] = set()

    for path in ij_files:
        arts, meta = parse_ij_file(path)
        sources.append(meta)
        for a in arts:
            # uniquify ids
            base = a["id"]
            i = 2
            while a["id"] in seen_ids:
                a["id"] = f"{base}-{i}"
                i += 1
            seen_ids.add(a["id"])
            articles.append(a)

    bookmarks = collect_bookmarks_from_atlas()
    if len(bookmarks) < 5:
        yml_bms = collect_bookmarks_from_yml()
        have = {b.get("url") for b in bookmarks}
        for b in yml_bms:
            if b["url"] not in have:
                bookmarks.append(b)
                have.add(b["url"])

    # Also pull bookmark-ish bullets from ij_*_bookmarks.md already in articles
    leads = pick_leads(articles, 6)

    # Newest source mtime for masthead date
    newest_mtime = max((s["mtime"] for s in sources), default=et_now_iso())
    newest_date = max((s["date"] for s in sources if s.get("date")), default=newest_mtime[:10])

    sports = [a for a in articles if a["section"] == "sports"]
    space = [a for a in articles if a["section"] == "space"]

    press = {
        "generated": et_now_iso(),
        "masthead": {
            "title": "Interest Press",
            "tagline": "Morning edition from Boyd's Interest Journal",
            "date": newest_date,
            "mtime": newest_mtime,
        },
        "counts": {
            "sources": len(sources),
            "articles": len(articles),
            "sports": len(sports),
            "space": len(space),
            "bookmarks": len(bookmarks),
            "leads": len(leads),
        },
        "leads": leads,
        "articles": articles,
        "bookmarks": bookmarks,
        "sources": sources,
        "thin": {
            "sports": len(sports) == 0,
            "space": len(space) == 0,
            "bookmarks": len(bookmarks) == 0,
        },
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(press, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"wrote {OUT} · sources={len(sources)} articles={len(articles)} "
        f"sports={len(sports)} space={len(space)} bookmarks={len(bookmarks)} leads={len(leads)}"
    )


if __name__ == "__main__":
    main()
