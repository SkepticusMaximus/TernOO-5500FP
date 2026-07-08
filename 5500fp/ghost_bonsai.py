"""ghost_bonsai.py — the Bonsai delegation harness (UI-free, testable).

The Professor behind the seam. GHOST (the Student) stays the conscience;
Bonsai is the optional local back-end brain GHOST may consult ONLY when it
is honest about needing to. Everything the classroom tab does with Bonsai, minus
pixels — so the plumbing is unit-testable without a display.

Five invariants held structurally here (CAI Two-Mind arch; CF5 Spec B):
  * Bonsai runs as a LOCAL SUBPROCESS, JSON-lines over stdin/stdout — no
    sockets, no network surface at all (stronger than an allow-list hole).
  * The gate is a CONSISTENCY gate, NOT a truth gate: it checks provenance,
    contract form, and class-agreement with GHOST's own routing — never facts.
  * Delegation is CONSENT-gated: nothing crosses to Bonsai without an explicit
    yes. No automatic delegation, ever.
  * The 81-trit GHOST feature vector rides every request (Component-3 door
    kept open — the embedding field is reserved now, unused).
  * The FULL delegated-humility gate is PARKED design-first; only the interim
    consistency gate lives here. Do not build past it.

Date: 2026-07-07, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

from __future__ import annotations

import json
import shutil
import threading

# Contract version — bump only with a matching parser change.
CONTRACT_VERSION = 1

# The GHOST feature vector length — 3^4, must equal ghost_train.NFEAT.
GHOST_FEATURES_LEN = 81

# The humility-gate margin floor — must equal ghost_train.MARGIN. GHOST is
# "confident" only at or above this argmax lead.
GHOST_MARGIN_FLOOR = 3

# ── subprocess status (drives the Professor pose + placard presence) ─────────
NOT_RUNNING = 'not_running'
LOADING = 'loading'
READY = 'ready'
GENERATING = 'generating'


class BonsaiProtocolError(ValueError):
    """A line off Bonsai's stdout was not a well-formed Contract v1 response."""


# ═══════════════════════════════════════════════════════════════════════════
# Contract v1 — request/response (round-trip pinned in tests)
# ═══════════════════════════════════════════════════════════════════════════

def build_request(text: str, ghost_features, ghost_route: str,
                  ghost_margin: int, major: str = 'commands') -> dict:
    """Assemble a Contract v1 request. The 81-trit GHOST feature vector rides
    every request (the representation-resonance door, kept open, unused)."""
    feats = list(ghost_features)
    if len(feats) != GHOST_FEATURES_LEN:
        raise BonsaiProtocolError(
            f"ghost_features must be {GHOST_FEATURES_LEN} trits, "
            f"got {len(feats)}")
    return {
        'version': CONTRACT_VERSION,
        'text': text,
        'ghost_features': feats,
        'ghost_route': ghost_route,
        'ghost_margin': int(ghost_margin),
        'major': major,
    }


def encode_request(req: dict) -> str:
    """One JSON line, newline-terminated — the only thing written to stdin."""
    return json.dumps(req) + '\n'


def validate_response(resp) -> tuple:
    """(ok, reason). A well-formed Contract v1 response is a dict with:
    version == 1; text:str; claimed_intent_class:str non-empty;
    self_confidence in [0,1] OR the literal 'unknown' (explicit unknown is
    honored, never coerced); optional bonsai_embedding:list (reserved)."""
    if not isinstance(resp, dict):
        return False, 'not a JSON object'
    if resp.get('version') != CONTRACT_VERSION:
        return False, f"version != {CONTRACT_VERSION}"
    if not isinstance(resp.get('text'), str):
        return False, 'text missing or not a string'
    cls = resp.get('claimed_intent_class')
    if not isinstance(cls, str) or not cls:
        return False, 'claimed_intent_class missing or empty'
    conf = resp.get('self_confidence')
    if conf == 'unknown':
        pass                                   # explicit unknown, honored
    elif isinstance(conf, (int, float)) and not isinstance(conf, bool) \
            and 0.0 <= float(conf) <= 1.0:
        pass
    else:
        return False, "self_confidence must be 0..1 or 'unknown'"
    if 'bonsai_embedding' in resp and not isinstance(
            resp['bonsai_embedding'], list):
        return False, 'bonsai_embedding present but not a list'
    return True, ''


def parse_response(line: str) -> dict:
    """Strict parse: raises BonsaiProtocolError on bad JSON or bad contract."""
    try:
        resp = json.loads(line)
    except (ValueError, TypeError) as e:
        raise BonsaiProtocolError(f"not JSON: {e}")
    ok, reason = validate_response(resp)
    if not ok:
        raise BonsaiProtocolError(reason)
    return resp


def safe_parse_response(line: str) -> tuple:
    """(resp, err). Never raises — malformed lines return (None, reason) so
    the tab can log-and-drop them without crashing (acceptance #1/#2)."""
    try:
        return parse_response(line), None
    except BonsaiProtocolError as e:
        return None, str(e)


# ═══════════════════════════════════════════════════════════════════════════
# The interim CONSISTENCY gate (NOT a truth gate — full gate parked)
# ═══════════════════════════════════════════════════════════════════════════

class GateResult:
    """accepted: may the reply reach the board? reason: why. caveat: present
    it, but flagged (unknown/low confidence) — honesty about what we gate."""

    __slots__ = ('accepted', 'reason', 'caveat')

    def __init__(self, accepted, reason, caveat=None):
        self.accepted = accepted
        self.reason = reason
        self.caveat = caveat

    def __repr__(self):
        return (f"GateResult(accepted={self.accepted}, "
                f"reason={self.reason!r}, caveat={self.caveat!r})")


# below this self_confidence, a numeric answer is presented WITH a caveat
CAVEAT_CONFIDENCE = 0.5


def consistency_gate(resp, ghost_route: str, ghost_margin: int,
                     *, provenance_ok: bool = True,
                     margin_floor: int = GHOST_MARGIN_FLOOR) -> GateResult:
    """Accept a Bonsai reply only if (a) provenance = our subprocess,
    (b) the contract is well-formed with explicit-unknown honored, and
    (c) claimed_intent_class does not CONTRADICT a CONFIDENT GHOST.

    Interpretation of (c) — DESIGN JUDGEMENT, flag for CF5/CAI: delegation
    only fires on GHOST `none`, so there is usually no confident class to
    contradict; the gate rejects Bonsai only when GHOST *was* confident
    (route != none AND margin >= floor) yet Bonsai claims a different class.
    This keeps the gate a consistency check, never a fact check — GHOST does
    not validate what it cannot itself route.
    """
    if not provenance_ok:
        return GateResult(False, 'provenance: reply not from our subprocess')
    ok, reason = validate_response(resp)
    if not ok:
        return GateResult(False, f'malformed: {reason}')
    ghost_confident = ghost_route != 'none' and ghost_margin >= margin_floor
    if ghost_confident and resp['claimed_intent_class'] != ghost_route:
        return GateResult(
            False,
            f"disagreement: bonsai claims {resp['claimed_intent_class']!r} "
            f"but GHOST is confident it is {ghost_route!r}")
    conf = resp.get('self_confidence')
    caveat = None
    if conf == 'unknown':
        caveat = 'bonsai declared unknown confidence — presented with caveat'
    elif isinstance(conf, (int, float)) and float(conf) < CAVEAT_CONFIDENCE:
        caveat = (f'bonsai low confidence ({float(conf):.2f}) — '
                  f'presented with caveat')
    return GateResult(True, 'consistent', caveat)


# ═══════════════════════════════════════════════════════════════════════════
# Consent-gated delegation (no automatic delegation, ever)
# ═══════════════════════════════════════════════════════════════════════════

CONSENT_PROMPT = 'beyond my competence — ask the professor? [y/n]'


def should_delegate(ghost_route: str, consent: bool) -> bool:
    """Cross to Bonsai ONLY on a GHOST `none` AND an explicit yes. A confident
    GHOST never delegates; a `none` without consent never delegates."""
    return ghost_route == 'none' and consent is True


# ═══════════════════════════════════════════════════════════════════════════
# B1 — subprocess lifecycle (JSON-lines over stdin/stdout; no sockets)
# ═══════════════════════════════════════════════════════════════════════════

class BonsaiProcess:
    """Owns spawn / timeout / kill of the local Bonsai runner. If no binary
    is configured or present, stays NOT_RUNNING — the classroom degrades to
    GHOST-only and the Professor zone shows `professor not present`."""

    def __init__(self, cmd=None):
        self.cmd = list(cmd) if cmd else None
        self.status = NOT_RUNNING
        self._proc = None

    def available(self) -> bool:
        if not self.cmd:
            return False
        exe = self.cmd[0]
        return bool(shutil.which(exe)) or __import__('os').path.exists(exe)

    def start(self) -> bool:
        """Spawn the runner. Returns True if running. Missing binary → False,
        status NOT_RUNNING (graceful, never raises to the tab)."""
        if not self.available():
            self.status = NOT_RUNNING
            return False
        import subprocess
        try:
            self._proc = subprocess.Popen(
                self.cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                text=True, bufsize=1)
        except OSError:
            self.status = NOT_RUNNING
            self._proc = None
            return False
        self.status = LOADING           # READY on first successful round-trip
        return True

    def ask(self, request: dict, timeout: float = 60.0) -> tuple:
        """Write one request line, read one response line within `timeout`.
        Returns (resp, err); never raises. Drives status GENERATING→READY."""
        if self.status == NOT_RUNNING or self._proc is None:
            return None, 'bonsai not running'
        try:
            self._proc.stdin.write(encode_request(request))
            self._proc.stdin.flush()
        except (BrokenPipeError, OSError) as e:
            self.status = NOT_RUNNING
            return None, f'write failed: {e}'
        self.status = GENERATING
        box = {}

        def _reader():
            try:
                box['line'] = self._proc.stdout.readline()
            except Exception as e:                       # pragma: no cover
                box['err'] = str(e)

        t = threading.Thread(target=_reader, daemon=True)
        t.start()
        t.join(timeout)
        if t.is_alive():
            self.status = READY
            return None, 'timeout'
        if 'err' in box:
            self.status = READY
            return None, box['err']
        raw = box.get('line', '')
        if not raw:
            self.status = NOT_RUNNING
            return None, 'bonsai closed the pipe'
        resp, err = safe_parse_response(raw)
        self.status = READY
        return resp, err

    def stop(self) -> None:
        """Clean shutdown on tab/app close."""
        if self._proc is not None:
            try:
                if self._proc.stdin:
                    self._proc.stdin.close()
                self._proc.terminate()
                self._proc.wait(timeout=2)
            except Exception:                            # pragma: no cover
                try:
                    self._proc.kill()
                except Exception:
                    pass
            finally:
                if self._proc.stdout:
                    try:
                        self._proc.stdout.close()
                    except Exception:                    # pragma: no cover
                        pass
            self._proc = None
        self.status = NOT_RUNNING
