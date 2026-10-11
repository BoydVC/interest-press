#!/usr/bin/env python3
"""Interest Press the server (stdlib only). Serves on 127.0.0.1:4292."""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("PORT", 4292))


def page() -> str:
    press_path = os.path.join(HERE, "data", "press.json")
    press_json = open(press_path, encoding="utf-8").read().strip()
    rd = lambda p: open(os.path.join(HERE, p), encoding="utf-8").read()
    html = rd("web/index.html")
    html = html.replace("/*__CSS__*/", rd("web/app.css"))
    html = html.replace("/*__PRESS__*/null", press_json)
    html = html.replace("/*__APP__*/", rd("web/app.js").replace("</script", "<\\/script"))
    return html


class H(BaseHTTPRequestHandler):
    def send(self, code, body, ctype):
        b = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        path = self.path.split("?")[0]
        try:
            if path in ("/", "/index.html", "/interest-press.html"):
                self.send(200, page(), "text/html; charset=utf-8")
            elif path == "/data/press.json":
                raw = open(os.path.join(HERE, "data", "press.json"), "rb").read()
                self.send(200, raw, "application/json")
            elif path == "/health":
                self.send(
                    200,
                    json.dumps({"ok": True, "port": PORT, "app": "interest-press"}),
                    "application/json",
                )
            else:
                self.send(404, "not found", "text/plain")
        except Exception as ex:
            self.send(500, f"error: {ex}", "text/plain")

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer.allow_reuse_address = True
    print(f"Interest Press on http://127.0.0.1:{PORT}/", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
