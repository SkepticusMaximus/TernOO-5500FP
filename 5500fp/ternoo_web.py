#!/usr/bin/env python3
"""ternoo_web.py — Road A: the ship's web face server.

Engine-sovereign and stdlib-only: a ThreadingHTTPServer on loopback that
serves ONE self-contained page (webface/app.html — no CDNs, no external
requests, ever) and a small JSON API over the TernDoc engine and the
POBOX. The browser contributes what host toolkits never could — real
typography, native selection, native spellcheck, IME — while every
decision that matters (document model, markdown canon, mail transport)
stays in the engine. The face remains disposable; this one just happens
to be pre-built by the entire web industry.

Fleet access later: front with `tailscale serve` exactly like the docs
site. Distribution later: this server is the seed of the "downloadable
TernOO" the captain named — swap the python engine calls for the C/NASM
core behind the same endpoints and nothing above the API notices.

API:
  GET  /                 the app
  GET  /api/status       engine + box info
  GET  /api/mail         letters, newest first (parsed headers)
  GET  /api/mail/<name>  one letter: {md, html}
  POST /api/send         {to, subject, html|md} -> Outbox drop-is-send
  POST /api/render       {md} -> {html}
  POST /api/convert      {html} -> {md}

Run:  python3 ternoo_web.py            (then http://127.0.0.1:8610)

Added: 22 Sep 2026 (Road A). Authors: Stevo + Claude.
"""

from __future__ import annotations

import json
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import terndoc as TD
import terndoc_html as TH
import pobox_store as TM

HOST, PORT = "127.0.0.1", 8610
APP_PATH = os.path.join(_HERE, "webface", "app.html")


def html_body(doc):
    """Body-only render for embedding in the app."""
    full = TD.to_html(doc)
    m = re.search(r"<body>\n(.*)\n</body>", full, re.S)
    return m.group(1) if m else full


class Handler(BaseHTTPRequestHandler):
    server_version = "TernOOWeb/0.1"

    # — plumbing —
    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else \
            json.dumps(body).encode() if not isinstance(body, str) else \
            body.encode()
        self.send_response(code)
        self.send_header("Content-Type", f"{ctype}; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _body_json(self):
        n = int(self.headers.get("Content-Length", 0))
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            return {}

    def log_message(self, fmt, *args):          # quiet; the box logs enough
        pass

    # — routes —
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            try:
                with open(APP_PATH, "rb") as f:
                    self._send(200, f.read(), "text/html")
            except FileNotFoundError:
                self._send(500, {"error": "webface/app.html missing"})
        elif self.path == "/api/status":
            self._send(200, {"engine": "terndoc", "mailbox": TM.POBOX,
                             "letters": len(TM.list_mail())})
        elif self.path == "/api/mail":
            out = []
            for f in TM.list_mail():
                try:
                    with open(os.path.join(TM.POBOX, f),
                              encoding="utf-8") as fh:
                        h = TM.parse_headers(fh.read(2000))
                except Exception:
                    h = {"from": "?", "to": "?", "subject": ""}
                out.append({"file": f, **h})
            self._send(200, out)
        elif self.path.startswith("/api/mail/"):
            from urllib.parse import unquote
            name = os.path.basename(unquote(self.path[len("/api/mail/"):]))
            p = os.path.join(TM.POBOX, name)
            if not os.path.isfile(p):
                self._send(404, {"error": "no such letter"})
                return
            with open(p, encoding="utf-8") as f:
                md = f.read()
            self._send(200, {"file": name, "md": md,
                             "html": html_body(TD.from_markdown(md))})
        else:
            self._send(404, {"error": "no such route"})

    def do_POST(self):
        req = self._body_json()
        if self.path == "/api/render":
            doc = TD.from_markdown(req.get("md", ""))
            self._send(200, {"html": html_body(doc)})
        elif self.path == "/api/convert":
            doc = TH.from_html(req.get("html", ""))
            self._send(200, {"md": TD.to_markdown(doc)})
        elif self.path == "/api/send":
            to = (req.get("to") or "crew").strip()
            subject = (req.get("subject") or "no subject").strip()
            if req.get("html"):
                body_md = TD.to_markdown(TH.from_html(req["html"]))
            else:
                body_md = req.get("md", "")
            if not body_md.strip():
                self._send(400, {"error": "refusing an empty letter"})
                return
            path = TM.drop_letter(to, subject, body_md,
                                   sender="CC (via TernOO web face)")
            self._send(200, {"dropped": os.path.basename(path),
                             "note": "the drop IS the send"})
        else:
            self._send(404, {"error": "no such route"})


def serve(host=HOST, port=PORT):
    httpd = ThreadingHTTPServer((host, port), Handler)
    return httpd


def main():
    httpd = serve()
    print(f"TernOO web face: http://{HOST}:{PORT}   (Ctrl+C stops)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
