#!/usr/bin/env python3
"""Per-seat local mail store (M2, CF5 re-audit 18-11).

The wire is authoritative for DELIVERY but not for RETENTION: anyone with write access to it
could delete envelopes (or a seat's card) and silently empty an inbox. So each seat keeps its own
append-only copy of every message it has opened, plus the set of wire filenames it has seen. Then:

  * a wiped or force-pushed wire cannot erase a seat's mail — the local store still has it;
  * if an envelope the seat had seen disappears from the wire, or the seat's own card does,
    that is an ALARM (loud, recoverable), not a silent loss.

Storage (mode 0700), keyed by the seat's AID:
    <root>/<aid>/messages.jsonl   one opened message per line, deduped by (signer, id)
    <root>/<aid>/seen.json        {wire_filename: [signer, id]} — the disappearance tripwire
"""
import json
import os

def _root():                                                 # resolved per-call so tests can override
    return os.path.expanduser(os.environ.get("TERNOO_MAIL_STORE", "~/.local/state/ternoo/mail-store"))


class LocalStore:
    def __init__(self, aid, root=None):
        self.dir = os.path.join(root or _root(), aid)
        os.makedirs(self.dir, mode=0o700, exist_ok=True)
        self.msgs_path = os.path.join(self.dir, "messages.jsonl")
        self.seen_path = os.path.join(self.dir, "seen.json")

    def _load_msgs(self):
        out = {}
        if os.path.exists(self.msgs_path):
            for line in open(self.msgs_path, encoding="utf-8"):
                line = line.strip()
                if not line:
                    continue
                try:
                    m = json.loads(line)
                    out[(m.get("from"), m.get("id"))] = m
                except Exception:
                    pass
        return out

    def _load_seen(self):
        try:
            return json.load(open(self.seen_path))
        except Exception:
            return {}

    def record(self, opened):
        """opened = iterable of (wire_filename, msg). Append messages new to this store (by
        signer+id) and remember every filename seen. Returns the count newly stored."""
        have = self._load_msgs()
        seen = self._load_seen()
        new = 0
        with open(self.msgs_path, "a", encoding="utf-8") as f:
            for fname, m in opened:
                k = (m.get("from"), m.get("id"))
                seen[fname] = list(k)
                if k not in have:
                    f.write(json.dumps(m, ensure_ascii=False) + "\n")
                    have[k] = m
                    new += 1
        tmp = self.seen_path + ".tmp"
        json.dump(seen, open(tmp, "w"))
        os.replace(tmp, self.seen_path)
        return new

    def messages(self):
        """Every message this seat has ever opened — the retention-safe inbox source."""
        return list(self._load_msgs().values())

    def disappeared(self, current_filenames):
        """Wire filenames we had seen that are no longer present — i.e. deleted from the wire."""
        current = set(current_filenames)
        return sorted(f for f in self._load_seen() if f not in current)


def _selftest():
    import tempfile
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    print("LocalStore self-test (M2)")
    root = tempfile.mkdtemp()
    s = LocalStore("aid_cc", root)
    s.record([("a.age", {"from": "aid_x", "id": "1", "body": "one"}),
              ("b.age", {"from": "aid_y", "id": "2", "body": "two"})])
    assert len(s.messages()) == 2
    s.record([("a.age", {"from": "aid_x", "id": "1", "body": "one"})])      # dup -> no growth
    assert len(s.messages()) == 2, "duplicate stored twice"
    # the wire now only shows a.age; b.age vanished -> alarm, but the message is retained
    gone = s.disappeared(["a.age"])
    assert gone == ["b.age"], gone
    assert any(m["body"] == "two" for m in s.messages()), "retention failed — lost the vanished letter"
    print("  stored 2, dedup holds, b.age disappearance caught, letter retained ✓")
    print("ALL GREEN — a wiped wire cannot erase mail; deletion is a loud alarm.")


if __name__ == "__main__":
    _selftest()
