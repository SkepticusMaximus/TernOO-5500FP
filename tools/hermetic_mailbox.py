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

    INFRA = {"migration"}                                     # cards present only so ported sigs verify

    def contacts(self, account=None):
        return [{"display_name": c["display"], "handle": c["aid"]}
                for c in self.wire.directory().values()
                if c["aid"] != self.kh.aid and c["display"] not in self.INFRA]

    def publish_card(self):
        """Put this seat's signed card on the wire (spool if daemon-backed, else straight in)."""
        import json
        dest = os.path.join(self.spool, "directory") if self.spool else self.wire.dir
        open(os.path.join(dest, self.kh.aid + ".card"), "w").write(
            json.dumps(self.kh.card(), sort_keys=True))

    # ── send / receive ────────────────────────────────────────────────────────────────
    def send(self, from_account=None, to_contact=None, subject="", body=""):
        return self.send_group(from_account, [to_contact], subject, body)

    def send_group(self, from_account=None, to_contacts=(), subject="", body=""):
        """Seal ONE envelope to every recipient at once (+ a self-copy = Sent). The padding hides
        the count, so a crew letter and a one-to-one letter are indistinguishable on the wire, and
        the sender keeps a single Sent record instead of one per head. Returns the id + who it
        was sealed to (display names) so the GUI can confirm exactly who will be able to open it."""
        cards = self.wire.directory()
        rcpts, names = [], []
        for h in to_contacts:
            c = cards.get(h)
            if not c:
                raise ValueError("no key card on the wire for recipient %r" % h)
            rcpts.append(c)
            names.append(c["display"])
        if not rcpts:
            raise ValueError("no recipients")
        env, mid = self.kh.seal(rcpts, subject, body)
        dest = os.path.join(self.spool, "pool") if self.spool else self.wire.pool
        open(os.path.join(dest, secrets.token_hex(12) + ".age"), "wb").write(env)
        return {"message_id": mid, "recipients": names}

    def inbox(self, account=None):
        """Every letter this seat can open, as Tmail-shaped dicts. Sender/recipients are mapped
        back to display names via the directory; nothing unreadable is ever surfaced.

        Ported history (legacy=True) renders with its ORIGINAL sender/recipients/date — the
        migration key sealed it, but the letter is shown as the real correspondence it was."""
        who = {c["aid"]: c["display"] for c in self.wire.directory().values()}
        who[self.kh.aid] = self.kh.display
        seen, out = set(), []
        for m in self.wire.fetch(self.kh, seen):
            if m.get("legacy"):
                frm, to = m.get("orig_from", "?"), m.get("orig_to", "?")
                t, sent = m.get("time_posted") or 0, (m.get("orig_from", "") == self.kh.display)
            else:
                frm = who.get(m["from"], m["from"])
                to = ", ".join(who.get(a, a) for a in m["to"])
                t, sent = m.get("time") or 0, m["from"] == self.kh.aid
            out.append({
                "id": m["id"], "from": frm, "to": to,
                "subject": m["subject"], "body": m["body"],
                "time": int(t) if isinstance(t, (int, float)) or str(t).isdigit() else 0,
                "unread": False, "sent": sent, "legacy": bool(m.get("legacy"))})
        return out

    # ── facade no-ops / hermetic behaviours the GUI also calls ─────────────────────────
    def mark_read(self, account=None, message_id=None):
        return {"ok": True}                                   # read-state is local, not on the wire

    def create_account(self, display_name=None):
        return {"account_handle": self.kh.aid}                # one keyholder == one seat; no minting here

    def add_contact(self, account=None, invite=None):
        return {"contact_handle": None}                       # contacts come from the wire directory (cards)

    def create_invite(self, account=None, for_display_name=None):
        return {"invite": "share your published card from the wire directory"}

    def grants_on(self, object_handle=None):
        return []                                             # no admin, no grants — that's the point

    def grant(self, account=None, object_handle=None, holder_contact=None, rights=None, caveats=None):
        return {"grant_handle": None}

    def revoke(self, account=None, grant_handle=None):
        return {"ok": True}


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
