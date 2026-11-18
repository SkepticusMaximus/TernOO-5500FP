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
from hermetic_store import LocalStore
from ternid_pins import classify, fingerprint, load_pins


MIGRATION_AID_FILE = os.path.join(                        # same dir the ceremony pins it in
    os.path.expanduser(os.environ.get("TERNOO_KEYS", "~/.config/ternoo/keys")), "migration.aid")


def _pinned_migration_aid():
    try:
        return open(MIGRATION_AID_FILE).read().strip() or None
    except Exception:
        return None


class HermeticMailbox:
    def __init__(self, keyholder, wire_path, spool_path=None, migration_aid=None, pins=None, store=None):
        self.kh = keyholder
        self.wire = Wire(wire_path)
        self.spool = spool_path                               # if set, send drops here for the daemon
        # H2: legacy (ported) mail is honoured ONLY when signed by this pinned migration AID;
        # any other signer that sets `legacy` is shown with its REAL identity, never the spoof.
        self.migration_aid = migration_aid or _pinned_migration_aid()
        # H3: pinned display->AID bindings. An impostor card (pinned name, wrong AID) is refused.
        self.pins = pins if pins is not None else load_pins()
        # M2: a retention-safe local copy, so a wiped wire can't empty the inbox.
        self.store = store if store is not None else LocalStore(keyholder.aid)
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
        """Roster from the wire, with pinning (H3): an IMPOSTOR (pinned name, wrong AID) is never
        offered; unpinned cards are flagged unverified; each carries a short AID fingerprint."""
        out = []
        for c in self.wire.directory().values():
            if c["aid"] == self.kh.aid or c["display"] in self.INFRA:
                continue
            cls = classify(c, self.pins)
            if cls == "impostor":
                continue                                      # never present an impostor by name
            out.append({"display_name": c["display"], "handle": c["aid"],
                        "verified": cls == "verified", "fingerprint": fingerprint(c["aid"])})
        return out

    def own_card_ok(self):
        """H3: confirm MY card on the wire still matches my key (unchanged, present). (ok, detail)."""
        on_wire = self.wire.directory().get(self.kh.aid)
        if on_wire is None:
            return (False, "your card is MISSING from the wire")
        if on_wire != self.kh.card():
            return (False, "your card on the wire does NOT match your key")
        return (True, "")

    def alarms(self):
        """M2 + H3: loud, recoverable warnings for the GUI — mail deleted from the wire (still
        held locally), or this seat's own card missing/changed. Empty list = all well."""
        out = []
        gone = self.store.disappeared(self.wire.pool_files())
        if gone:
            out.append("%d message(s) you had were DELETED from the wire — kept in your local store." % len(gone))
        ok, detail = self.own_card_ok()
        if not ok:
            out.append("YOUR CARD: " + detail)
        return out

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
        self.store.record(self.wire.open_pool(self.kh))      # M2: pull new mail, persist it locally
        dir_cards = self.wire.directory()
        who = {c["aid"]: c["display"] for c in dir_cards.values()}
        who[self.kh.aid] = self.kh.display
        out = []
        for m in self.store.messages():                      # render from the RETENTION-safe store
            is_legacy = bool(m.get("legacy")) and m.get("from") == self.migration_aid   # H2
            if is_legacy:
                frm, to = m.get("orig_from", "?"), m.get("orig_to", "?")
                t, sent = m.get("time_posted") or 0, (m.get("orig_from", "") == self.kh.display)
                verified, fp = True, ""                      # migration-signed: the ported record
            else:
                frm = who.get(m["from"], m["from"])          # a spoofed `legacy` shows its REAL signer
                to = ", ".join(who.get(a, a) for a in m["to"])
                t, sent = m.get("time") or 0, m["from"] == self.kh.aid
                # H3: is this sender's card pinned to this name? mark it so the GUI can warn.
                scard = dir_cards.get(m["from"])
                verified = sent or (scard is not None and classify(scard, self.pins) == "verified")
                fp = fingerprint(m["from"])
            out.append({
                "id": m["id"], "from": frm, "to": to,
                "subject": m["subject"], "body": m["body"],
                "time": int(t) if isinstance(t, (int, float)) or str(t).isdigit() else 0,
                "unread": False, "sent": sent, "legacy": is_legacy,
                "verified": verified, "fingerprint": fp})
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
    os.environ["TERNOO_MAIL_STORE"] = tempfile.mkdtemp()      # isolate the local store
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

    # M2: wipe the wire pool; CCC still has the letter locally, and an alarm fires
    import glob as _glob
    for f in _glob.glob(os.path.join(boxes["CCC"].wire.pool, "*.age")):
        os.remove(f)
    assert any(m["body"] == "CCC only — not the captain" for m in boxes["CCC"].inbox()), "wipe lost the mail"
    assert boxes["CCC"].alarms(), "no alarm raised for a wiped wire"
    print("  wire wiped -> CCC still holds the letter + alarms:", boxes["CCC"].alarms()[0][:48], "…")
    print("ALL GREEN — hermetic + retention-safe; a wiped wire alarms and loses nothing.")


if __name__ == "__main__":
    _selftest()
