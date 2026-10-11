#!/usr/bin/env python3
"""Embed data/press.json + web assets into dist/interest-press.html."""
import json
import os

R = os.path.dirname(os.path.abspath(__file__))


def rd(rel: str) -> str:
    return open(os.path.join(R, rel), encoding="utf-8").read()


def main() -> None:
    press_path = os.path.join(R, "data", "press.json")
    if not os.path.exists(press_path):
        raise SystemExit("missing data/press.json — run collect.py first")
    press_json = open(press_path, encoding="utf-8").read().strip()
    # Validate JSON
    json.loads(press_json)

    html = rd("web/index.html")
    html = html.replace("/*__CSS__*/", rd("web/app.css"))
    # Embed PRESS object: replace /*__PRESS__*/null with the JSON literal
    html = html.replace("/*__PRESS__*/null", press_json)
    app_js = rd("web/app.js").replace("</script", "<\\/script")
    html = html.replace("/*__APP__*/", app_js)

    out_dir = os.path.join(R, "dist")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "interest-press.html")
    open(out, "w", encoding="utf-8").write(html)
    print(f"built {out} ({len(html.encode())} bytes)")


if __name__ == "__main__":
    main()
