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
  GET  /api/flows        .fc flow files
  GET  /api/flow/<name>  one flow (JSON) — code is readable, MAIL IS NOT
                         (captain's privacy ruling: send-only until
                         per-seat identity exists)
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

import importlib.util as _ilu
_wkspec = _ilu.spec_from_file_location(
    "flowcode_walker", os.path.join(_HERE, "flowcode_walker.py"))
WALKER = _ilu.module_from_spec(_wkspec)
_wkspec.loader.exec_module(WALKER)
_sfspec = _ilu.spec_from_file_location(
    "sheet_formula", os.path.join(_HERE, "sheet_formula.py"))
SHEETF = _ilu.module_from_spec(_sfspec)
_sfspec.loader.exec_module(SHEETF)
_FCDIR = FLOWDIR if 'FLOWDIR' in dir() else None
try:
    _fcspec = _ilu.spec_from_file_location(
        "flowcode_commands", os.path.join(_HERE, "flowcode_commands.py"))
    FCMD = _ilu.module_from_spec(_fcspec)
    _fcspec.loader.exec_module(FCMD)
except Exception:                               # noqa: BLE001
    FCMD = None

HOST, PORT = "127.0.0.1", 8610
APP_PATH = os.path.join(_HERE, "webface", "app.html")
FLOWDIR = os.path.join(os.path.dirname(_HERE), "FlowCode")


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
        elif self.path == "/app.js":
            try:
                with open(os.path.join(os.path.dirname(APP_PATH),
                                       "app.js"), "rb") as f:
                    self._send(200, f.read(), "text/javascript")
            except FileNotFoundError:
                self._send(404, {"error": "app.js missing"})
        elif self.path == "/api/status":
            self._send(200, {"engine": "terndoc",
                             "flows": len([f for f in os.listdir(FLOWDIR)
                                           if f.endswith(".fc")])})
        elif self.path == "/api/commands":
            names = []
            if FCMD is not None:
                try:
                    names = list(FCMD.command_names())
                except Exception:               # noqa: BLE001
                    names = []
            self._send(200, names)
        elif self.path == "/api/guis":
            out = sorted(f for f in os.listdir(FLOWDIR)
                         if f.endswith(".gui"))
            self._send(200, out)
        elif self.path.startswith("/api/gui/"):
            from urllib.parse import unquote
            name = os.path.basename(unquote(self.path[len("/api/gui/"):]))
            p = os.path.join(FLOWDIR, name)
            if not (name.endswith(".gui") and os.path.isfile(p)):
                self._send(404, {"error": "no such gui design"})
                return
            with open(p, encoding="utf-8") as f:
                self._send(200, f.read().encode(), "application/json")
        elif self.path == "/api/sheets":
            out = sorted(f for f in os.listdir(FLOWDIR)
                         if f.endswith(".sheet"))
            self._send(200, out)
        elif self.path.startswith("/api/sheet/") and not \
                self.path.endswith("/eval"):
            from urllib.parse import unquote
            name = os.path.basename(unquote(self.path[len("/api/sheet/"):]))
            p = os.path.join(FLOWDIR, name)
            if not (name.endswith(".sheet") and os.path.isfile(p)):
                self._send(404, {"error": "no such sheet"})
                return
            with open(p, encoding="utf-8") as f:
                self._send(200, f.read().encode(), "application/json")
        elif self.path == "/api/flows":
            # captain's privacy ruling 22-09: the web face may SEND letters
            # but never READ the box until per-seat identity exists. Flow
            # files are code, not correspondence — those it may read.
            out = sorted(f for f in os.listdir(FLOWDIR)
                         if f.endswith(".fc"))
            self._send(200, out)
        elif self.path.startswith("/api/flow/"):
            from urllib.parse import unquote
            name = os.path.basename(unquote(self.path[len("/api/flow/"):]))
            p = os.path.join(FLOWDIR, name)
            if not (name.endswith(".fc") and os.path.isfile(p)):
                self._send(404, {"error": "no such flow"})
                return
            with open(p, encoding="utf-8") as f:
                self._send(200, f.read().encode(), "application/json")
        else:
            self._send(404, {"error": "no such route"})

    def do_POST(self):
        from urllib.parse import unquote
        req = self._body_json()
        if self.path == "/api/sheet/eval":
            cells = {}
            for c in req.get("cells", []):
                text = str(c.get("value", ""))
                kind = "cell_formula" if text.startswith("=") else "cell_value"
                cells[(int(c["row"]), int(c["col"]))] = {
                    "kind": kind, "value": text,
                    "row": int(c["row"]), "col": int(c["col"])}
            try:
                results, errors = SHEETF.evaluate_sheet(cells)
            except Exception as e:              # noqa: BLE001
                self._send(200, {"values": {}, "errors":
                                 {"0,0": f"eval failed: {e}"}})
                return
            self._send(200, {
                "values": {f"{r},{c}": ("" if v is None else v)
                           for (r, c), v in results.items()},
                "errors": {f"{r},{c}": e for (r, c), e in errors.items()}})
            return
        if self.path.startswith("/api/sheet/") and self.path.endswith("/save"):
            name = os.path.basename(
                unquote(self.path[len("/api/sheet/"):-len("/save")]))
            if not name.endswith(".sheet"):
                self._send(400, {"error": "sheets are .sheet files"})
                return
            doc = req.get("sheet")
            if not (isinstance(doc, dict) and isinstance(doc.get("c"), list)):
                self._send(400, {"error": "malformed sheet document"})
                return
            doc.setdefault("r", []); doc.setdefault("f", [])
            doc.setdefault("n", len(doc["c"]) + 1)
            with open(os.path.join(FLOWDIR, name), "w",
                      encoding="utf-8") as f:
                json.dump(doc, f, indent=2)
            self._send(200, {"saved": name})
            return
        if self.path.startswith("/api/gui/") and self.path.endswith("/save"):
            name = os.path.basename(
                unquote(self.path[len("/api/gui/"):-len("/save")]))
            if not name.endswith(".gui"):
                self._send(400, {"error": "gui designs are .gui files"})
                return
            doc = req.get("design")
            if not (isinstance(doc, dict)
                    and isinstance(doc.get("symbols"), list)):
                self._send(400, {"error": "malformed design document"})
                return
            with open(os.path.join(FLOWDIR, name), "w",
                      encoding="utf-8") as f:
                json.dump(doc, f, indent=1)
            self._send(200, {"saved": name})
            return
        if self.path.startswith("/api/flow/") and self.path.endswith("/run"):
            name = os.path.basename(
                unquote(self.path[len("/api/flow/"):-len("/run")]))
            p = os.path.join(FLOWDIR, name)
            if not (name.endswith(".fc") and os.path.isfile(p)):
                self._send(404, {"error": "no such flow"})
                return
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
            syms = {s["id"]: s for s in d.get("flow_symbols", [])}
            edges = d.get("flow_edges", d.get("edges", []))
            try:
                rep = WALKER.walk(syms, edges, resolver=None,
                                  variables=req.get("variables") or {})
                self._send(200, {"steps": rep["steps"],
                                 "lines": rep["lines"],
                                 "vars": rep["vars"]})
            except Exception as e:              # noqa: BLE001
                self._send(200, {"steps": 0, "vars": {},
                                 "lines": [f"run failed: {e}"]})
            return
        if self.path.startswith("/api/flow/") and self.path.endswith("/save"):
            name = os.path.basename(
                unquote(self.path[len("/api/flow/"):-len("/save")]))
            if not name.endswith(".fc"):
                self._send(400, {"error": "flows are .fc files"})
                return
            doc = req.get("flow")
            if not (isinstance(doc, dict)
                    and isinstance(doc.get("flow_symbols"), list)):
                self._send(400, {"error": "malformed flow document"})
                return
            with open(os.path.join(FLOWDIR, name), "w",
                      encoding="utf-8") as f:
                json.dump(doc, f, indent=2)
            self._send(200, {"saved": name,
                             "note": "git is the safety net"})
            return
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
