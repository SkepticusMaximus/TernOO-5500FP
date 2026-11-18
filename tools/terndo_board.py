#!/usr/bin/env python3
"""Append a task to the TernDO board (~/.config/ternoo/todo.json) safely from other tools.

TernDO's own Store.save() calls _merge_external(), which folds in items appended to the file
by "CC's scripts" (by id) instead of clobbering them — so an ATOMIC APPEND here is the
sanctioned, one-writer-safe way for Tmail (and any CC tool) to contribute a task. We only ever
ADD new items (fresh id); we never rewrite or delete existing ones, so we can't race a GUI edit.
"""
import datetime
import json
import os
import re
import tempfile

STORE = os.environ.get("TERNDO_STORE", os.path.expanduser("~/.config/ternoo/todo.json"))
STATUSES = ("pending", "progress", "complete")       # must match terndo_qt STATUSES


def _now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _load(path):
    try:
        d = json.load(open(path, encoding="utf-8"))
        if isinstance(d, dict) and d.get("version") == 2:
            d.setdefault("items", [])
            d.setdefault("seq", len(d["items"]))
            return d
    except Exception:
        pass
    return {"version": 2, "seq": 0, "items": []}


def _next_id(d):
    n = max((int(re.sub(r"\D", "", it.get("id", "")) or 0) for it in d["items"]), default=0)
    return "g%d" % (n + 1)


def add_task(text, notes="", area="", priority=0, status="pending", parent=None,
             origin="", store=STORE):
    """Atomically append one task to the board; returns its new id. `origin` is a short
    provenance note (e.g. 'from mail: <subject>'). Status must be a TernDO status."""
    if status not in STATUSES:
        status = "pending"
    d = _load(store)
    tid = _next_id(d)
    hist = [{"ts": _now(), "status": "pending", "note": origin or "added"}]
    if status != "pending":
        hist.append({"ts": _now(), "status": status, "note": origin or "added"})
    d["items"].append({"id": tid, "text": text, "status": status, "parent": parent,
                       "history": hist, "notes": notes, "staging": "", "assignees": [],
                       "grants": [], "priority": priority, "area": area})
    d["seq"] = d.get("seq", 0) + 1
    os.makedirs(os.path.dirname(os.path.abspath(store)), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(store)))
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
    os.replace(tmp, store)                            # atomic: readers see old or new, never partial
    return tid


if __name__ == "__main__":
    import sys
    tmp = os.path.join(tempfile.mkdtemp(), "todo.json")
    a = add_task("first", notes="n1", area="test", store=tmp)
    b = add_task("second", status="progress", origin="from mail: hello", store=tmp)
    d = json.load(open(tmp))
    assert [it["id"] for it in d["items"]] == [a, b], d
    assert d["items"][1]["status"] == "progress" and d["seq"] == 2
    print("terndo_board OK —", a, b, "seq", d["seq"])
