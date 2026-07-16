#!/usr/bin/env python3
"""corpus_resolve.py — the sync-protocol resolver.

Reads a corpus file of hooks, lints them against the schema, resolves each
POINTER against the tree, and reports whether the ground under each ruling
has moved.

    HOLDS    (+)  pointer resolves, GROUND matches. Ruling stands on same ground.
    STIRRED  ( )  pointer resolves, GROUND differs. Something moved underneath.
                  The claim MAY still be true; this tool cannot know. Re-rule.
    DEAD     (-)  pointer will not resolve. Loud, refused, never degraded.

STIRRED and DEAD are DERIVED, never authored. A hand-written one is a lint error.

This tool detects a symbol that vanished and ground that moved. It does NOT
detect a claim that was false when written, a claim nobody hooked, or code that
shipped with no doc. Those need eyes. It converts silent rot into a loud flag;
that is all it does.

Exit codes:  0 = all HOLDS   1 = STIRRED or DEAD present   2 = lint failure

Stdlib only. Draft — bench tooling, pending review circle + captain's gate.
CAI (chat seat), 2026-07-17.
"""

import argparse
import hashlib
import re
import sys
from pathlib import Path

VERDICTS = ("SETTLED", "OPEN", "STALE")
DERIVED = ("DEAD", "STIRRED", "HOLDS")
BUDGET = 500
DIGEST_LEN = 16  # 64 bits of sha256; accident-detection, not adversarial

FIELD_RE = re.compile(r"^([A-Z][A-Z-]*):\s*(.*)$")
TOPIC_RE = re.compile(r"^\[TOPIC\]\s+(\S+)\s*$")
LINENUM_RE = re.compile(r"(::.*?)(\bL\d+\b|:\d+\b)")


# ---------------------------------------------------------------- parsing

HOOKS_HEADING = re.compile(r"^#{1,6}\s+Hooks\s*$", re.I)


def parse_hooks(text):
    """Yield (topic, fields, raw, lineno). A hook is a [TOPIC] block; it ends
    at the next [TOPIC] or at a non-indented, non-blank line.

    Only the '## Hooks' section is parsed. The schema template in the header is
    structurally identical to a real hook — a machine cannot tell the example
    from the instance — so the section boundary is what distinguishes them.
    """
    all_lines = text.splitlines()
    start = None
    for i, l in enumerate(all_lines):
        if HOOKS_HEADING.match(l.strip()):
            start = i + 1
            break
    if start is None:
        return []
    lines = all_lines[start:]

    hooks, cur = [], None
    for i, raw in enumerate(lines, start + 1):
        stripped = raw.strip()
        m = TOPIC_RE.match(stripped)
        if m:
            if cur:
                hooks.append(cur)
            cur = {"topic": m.group(1), "fields": {}, "raw": [raw], "lineno": i}
            continue
        if cur is None:
            continue
        if stripped and not raw.startswith((" ", "\t")):
            hooks.append(cur)
            cur = None
            continue
        if not stripped:
            continue
        cur["raw"].append(raw)
        fm = FIELD_RE.match(stripped)
        if fm:
            cur["fields"][fm.group(1)] = fm.group(2).strip()
    if cur:
        hooks.append(cur)
    return hooks


def parse_pointer(ptr):
    """'path :: a, b ; path2 :: c'  ->  [(path, [syms])]. Symbols may glob with *."""
    out = []
    for clause in ptr.split(";"):
        clause = clause.strip()
        if not clause:
            continue
        if "::" not in clause:
            out.append((clause.strip(), []))
            continue
        path, syms = clause.split("::", 1)
        names = [s.strip() for s in syms.split(",") if s.strip()]
        out.append((path.strip(), names))
    return out


# ---------------------------------------------------------------- linting

def lint(hook, all_topics):
    """Return list of error strings. Empty == clean."""
    errs = []
    f = hook["fields"]
    body = "\n".join(hook["raw"])
    size = len(body)

    if size > BUDGET:
        errs.append(f"over budget: {size} chars > {BUDGET}")

    v = f.get("VERDICT")
    if not v:
        errs.append("missing VERDICT")
    elif v in DERIVED:
        errs.append(f"VERDICT: {v} is DERIVED, never authored — "
                    "a hand-authored one masks a live break as an intended state")
    elif v not in VERDICTS:
        errs.append(f"unknown VERDICT: {v!r} (expected one of {'/'.join(VERDICTS)})")

    ptr = f.get("POINTER")
    if not ptr:
        errs.append("missing POINTER — there is no hook without a pointer")
    elif LINENUM_RE.search(ptr):
        errs.append("POINTER carries a line number — lines drift; name a symbol "
                    "or heading. A line-numbered pointer is a rot vector")

    if not f.get("RULING"):
        errs.append("missing RULING (provenance)")
    if not f.get("TRIGGER"):
        errs.append("missing TRIGGER")

    if v == "SETTLED":
        if "BEHAVIOUR" in f:
            errs.append("SETTLED must not carry BEHAVIOUR — the pointer is the behaviour")
        if not f.get("GROUND"):
            errs.append("SETTLED requires GROUND (digest at ruling time) — "
                        "without it, a moved claim cannot be detected")
    if v == "OPEN":
        if not f.get("OWNER"):
            errs.append("OPEN requires OWNER — who can close it")
        if not f.get("BEHAVIOUR"):
            errs.append("OPEN requires BEHAVIOUR — what to do instead of stating")
    if v == "STALE":
        sb = f.get("SUPERSEDED-BY")
        if not sb:
            errs.append("STALE requires SUPERSEDED-BY")
        elif sb not in all_topics:
            errs.append(f"SUPERSEDED-BY: {sb!r} does not resolve to a live TOPIC — "
                        "a STALE redirecting to nothing is as broken as a dangling SETTLED")
        if not f.get("BEHAVIOUR"):
            errs.append("STALE requires BEHAVIOUR — what to cite instead")

    return errs


# ---------------------------------------------------------------- regions

def norm(text):
    """Deterministic normalisation: line endings + trailing whitespace only.
    Nothing cleverer. Indentation and blank lines are content."""
    return "\n".join(l.rstrip() for l in text.replace("\r\n", "\n").split("\n"))


def py_region(lines, name):
    """Definition of `name` through to the next line at same-or-lower indent.
    Matches `def name`, `class name`, or `name =`."""
    pat = re.compile(rf"^(\s*)(?:def\s+{re.escape(name)}\b"
                     rf"|class\s+{re.escape(name)}\b"
                     rf"|{re.escape(name)}\s*[:=])")
    for i, line in enumerate(lines):
        m = pat.match(line)
        if not m:
            continue
        indent = len(m.group(1))
        out = [line]
        for nxt in lines[i + 1:]:
            if not nxt.strip():
                out.append(nxt)
                continue
            cur = len(nxt) - len(nxt.lstrip())
            if cur <= indent:
                break
            out.append(nxt)
        while out and not out[-1].strip():
            out.pop()
        return "\n".join(out)
    return None


def md_region(lines, heading):
    """A markdown heading through to the next heading of same-or-higher level.
    `heading` may be the text ('The law') or a section number ('15.1')."""
    want = heading.strip().lower()
    for i, line in enumerate(lines):
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if not m:
            continue
        level, text = len(m.group(1)), m.group(2).strip().lower()
        if want not in text:
            continue
        out = [line]
        for nxt in lines[i + 1:]:
            m2 = re.match(r"^(#{1,6})\s+", nxt)
            if m2 and len(m2.group(1)) <= level:
                break
            out.append(nxt)
        while out and not out[-1].strip():
            out.pop()
        return "\n".join(out)
    return None


def extract(root, path, syms):
    """Return (region_text, [missing_syms]). Region is the concatenation of each
    named symbol's region, in the order named. No symbols == the whole file."""
    fp = root / path
    if not fp.is_file():
        return None, [f"path not found: {path}"]
    text = norm(fp.read_text(encoding="utf-8", errors="replace"))
    if not syms:
        return text, []
    lines = text.split("\n")
    chunks, missing = [], []
    is_py = fp.suffix == ".py"
    for sym in syms:
        if sym.endswith("*"):
            prefix = sym[:-1]
            hits = [l for l in lines if re.match(rf"^\s*{re.escape(prefix)}\w*\s*[:=]", l)]
            if not hits:
                missing.append(sym)
            else:
                chunks.append("\n".join(hits))
            continue
        r = py_region(lines, sym) if is_py else md_region(lines, sym)
        if r is None and not is_py:
            r = py_region(lines, sym)
        if r is None:
            missing.append(sym)
        else:
            chunks.append(r)
    return "\n".join(chunks), missing


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:DIGEST_LEN]


# ---------------------------------------------------------------- resolving

def resolve(root, hook):
    """Return (status, detail, computed_digest_or_None)."""
    f = hook["fields"]
    ptr = f.get("POINTER")
    if not ptr:
        return "DEAD", "no POINTER", None
    parts, missing_all, chunks = parse_pointer(ptr), [], []
    for path, syms in parts:
        region, missing = extract(root, path, syms)
        if region is None:
            return "DEAD", missing[0], None
        missing_all += missing
        chunks.append(region)
    if missing_all:
        return "DEAD", "symbol(s) not found: " + ", ".join(missing_all), None
    got = digest("\n".join(chunks))
    ground = f.get("GROUND")
    if not ground:
        return "UNGROUNDED", f"no GROUND recorded; current is {got}", got
    if ground.strip() == got:
        return "HOLDS", "", got
    return "STIRRED", f"GROUND {ground.strip()} -> {got}", got


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="Resolve corpus hooks against the tree.")
    ap.add_argument("--root", default=".", help="repo root (default: cwd)")
    ap.add_argument("--corpus", default="docs/CORPUS.md", help="corpus file, relative to root")
    ap.add_argument("--ground", action="store_true",
                    help="print the digest each hook's pointer currently yields "
                         "(for a human ruling a hook — never for a worker clearing a flag)")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    cpath = root / args.corpus
    if not cpath.is_file():
        print(f"FATAL: corpus not found: {cpath}", file=sys.stderr)
        return 2

    hooks = parse_hooks(cpath.read_text(encoding="utf-8"))
    if not hooks:
        print(f"FATAL: no hooks parsed from {args.corpus}", file=sys.stderr)
        return 2

    topics = {h["topic"] for h in hooks}
    dupes = [t for t in topics if sum(1 for h in hooks if h["topic"] == t) > 1]

    lint_fail = False
    counts = {"HOLDS": 0, "STIRRED": 0, "DEAD": 0, "UNGROUNDED": 0}
    print(f"corpus: {args.corpus}   hooks: {len(hooks)}\n")

    for t in sorted(dupes):
        print(f"  LINT  [{t}] duplicate TOPIC id")
        lint_fail = True

    for h in hooks:
        errs = lint(h, topics)
        if errs:
            lint_fail = True
            for e in errs:
                print(f"  LINT  [{h['topic']}] {e}")

    print()
    for h in hooks:
        status, detail, got = resolve(root, h)
        counts[status] = counts.get(status, 0) + 1
        mark = {"HOLDS": "+", "STIRRED": " ", "DEAD": "-", "UNGROUNDED": "?"}[status]
        line = f"  [{mark}] {status:<10} {h['topic']}"
        if detail:
            line += f"   — {detail}"
        print(line)
        if args.ground and got:
            print(f"        GROUND: {got}")

    print("\n  " + "  ".join(f"{k}={v}" for k, v in counts.items() if v))

    if lint_fail:
        print("\nLINT FAILED — the schema is the mechanism; fix before trusting the run.")
        return 2
    if counts["DEAD"] or counts["STIRRED"]:
        print("\nGround moved. These need re-ruling by a chat seat or the review circle.")
        print("A worker may report this. A worker may never clear it.")
        return 1
    if counts["UNGROUNDED"]:
        print("\nUngrounded hooks present — rule them and record GROUND.")
        return 1
    print("\nAll hooks hold.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
