#!/usr/bin/env python3
"""Hermetic mailbox — Tmail's new backend (CF5 spec §11, "Tmail pointed at its own keyholder").

Exposes the same shape Tmail already uses against the old agent (account_display, list_accounts,
contacts, send, inbox), but every letter is SEALED by this seat's keyholder before it leaves and
OPENED by it on arrival. The shared side (the wire) only ever holds sealed envelopes + signed
cards. There is no admin, no shared keystore, no plaintext — the things §9 deletes are simply
absent here.

  contacts  = the wire directory (other seats' signed cards)
  send      = seal to the recipient's card -> drop in the spool (daemon pushes) or the pool
  inbox     = open every pool envelope addressed to this seat (self-copies = Sent)
"""
import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hermetic_wire import Wire


class HermeticMailbox:
    def __init__(self, keyholder, wire_path, spool_path=None):
        self.kh = keyholder
        self.wire = Wire(wire_path)
        self.spool = spool_path                               # if set, send drops here for the daemon
        if spool_path:
            os.makedirs(os.path.join(spool_path, "pool"), exist_ok=True)
            os.makedirs(os.path.join(spool_path, "directory"), exist_ok=True)

    # ── identity / roster ─────────────────────────────────────────────────────────────
    def account_display(self, account_handle=None):
        return self.kh.display

    def list_accounts(self):
        return [self.kh.aid]

    def contacts(self, account=None):
        return [{"display_name": c["display"], "handle": c["aid"]}
                for c in self.wire.directory().values() if c["aid"] != self.kh.aid]

    def publish_card(self):
        """Put this seat's signed card on the wire (spool if daemon-backed, else straight in)."""
        import json
        dest = os.path.join(self.spool, "directory") if self.spool else self.wire.dir
        open(os.path.join(dest, self.kh.aid + ".card"), "w").write(
            json.dumps(self.kh.card(), sort_keys=True))

    # ── send / receive ────────────────────────────────────────────────────────────────
    def send(self, from_account=None, to_contact=None, subject="", body=""):
        cards = self.wire.directory()
        rcpt = cards.get(to_contact)
        if not rcpt:
            raise ValueError("no key card on the wire for recipient %r" % to_contact)
        env, mid = self.kh.seal([rcpt], subject, body)
        dest = os.path.join(self.spool, "pool") if self.spool else self.wire.pool
        open(os.path.join(dest, secrets.token_hex(12) + ".age"), "wb").write(env)
        return {"message_id": mid}

    def inbox(self, account=None):
        """Every letter this seat can open, as Tmail-shaped dicts. Sender/recipients are mapped
        back to display names via the directory; nothing unreadable is ever surfaced."""
        who = {c["aid"]: c["display"] for c in self.wire.directory().values()}
        who[self.kh.aid] = self.kh.display
        seen, out = set(), []
        for m in self.wire.fetch(self.kh, seen):
            out.append({
                "id": m["id"],
                "from": who.get(m["from"], m["from"]),
                "to": ", ".join(who.get(a, a) for a in m["to"]),
                "subject": m["subject"], "body": m["body"], "time": m["time"],
                "unread": False, "sent": m["from"] == self.kh.aid})
        return out


def _selftest():
    import tempfile
    import keyholder as K
    print("Hermetic mailbox self-test — Tmail backend over a shared wire")
    wdir = tempfile.mkdtemp()
    cc = K.Keyholder("CC")
    ccc = K.Keyholder("CCC")
    stevo = K.Keyholder("Stevo")
    boxes = {k.display: HermeticMailbox(k, wdir) for k in (cc, ccc, stevo)}
    for b in boxes.values():
        b.publish_card()
    print("  CC's contacts:", [c["display_name"] for c in boxes["CC"].contacts()])
    boxes["CC"].send(to_contact=ccc.aid, subject="hi", body="CCC only — not the captain")
    for name, b in boxes.items():
        got = [(m["from"], m["body"], "SENT" if m["sent"] else "recv") for m in b.inbox()]
        print(f"    {name:6} inbox:", got if got else "(empty — correct)")
    assert any(m["body"] == "CCC only — not the captain" for m in boxes["CCC"].inbox())
    assert boxes["Stevo"].inbox() == [], "captain must NOT see a CC->CCC letter"
    print("ALL GREEN — Tmail backend seals/opens hermetically; captain sees nothing not his.")


if __name__ == "__main__":
    _selftest()
