#!/usr/bin/env python3
"""prof_agent.py — give the local Professor hands: a minimal agentic tool loop.

The Professor (any OpenAI-compatible local server — the 30B on the HP at
:8090) is driven through a strict JSON tool protocol: each model turn must be
exactly one JSON object, either a tool call or a final answer. No server
flags, no template support needed — works with any backend llama-server can
front, Bonsai included.

Usage:
  prof_agent.py "find every test_*.py under the 5500fp tree and count them"
  prof_agent.py --yolo "..."            # skip the per-tool confirmation gate
  prof_agent.py --list-macros
  prof_agent.py --macro yt url=https://youtu.be/...
  PROF_BASE=http://127.0.0.1:8090      # the model endpoint (default; HP-local)

From Lenny (the Prof's API is bound to the HP's loopback), open a tunnel once:
  ssh -f -N -L 18090:127.0.0.1:8090 stevo@100.65.86.46
  PROF_BASE=http://127.0.0.1:18090 prof_agent.py "..."

Safety: every tool is allowlisted below; filesystem tools are confined to
$HOME and read-only (open_editor hands a file to your desktop, it never
writes); every call is shown and confirmed before it runs unless --yolo.
"""

import argparse
import fnmatch
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request

BASE = os.environ.get("PROF_BASE", "http://127.0.0.1:8090").rstrip("/")
HOME = os.path.realpath(os.path.expanduser("~"))
HERE = os.path.dirname(os.path.abspath(__file__))
MACROS_PATH = os.path.join(HERE, "prof_macros.json")
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".cache", ".venvs",
             "LOCAL_AI", ".local", ".mozilla", ".config"}
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) prof-agent/0.1"}


# ── confinement ──────────────────────────────────────────────────────────────
def _confined(path):
    """Resolve `path` and refuse anything outside $HOME."""
    p = os.path.realpath(os.path.expanduser(path))
    if p != HOME and not p.startswith(HOME + os.sep):
        raise ValueError(f"refused: {path} is outside your home directory")
    return p


# ── the tools ────────────────────────────────────────────────────────────────
def _ddg_decode(href):
    """DDG wraps result links as /l/?uddg=<real> — unwrap when present."""
    q = urllib.parse.urlparse(href).query
    return urllib.parse.parse_qs(q).get("uddg", [href])[0]


def _ddg_html(query):
    url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        page = r.read(300_000).decode("utf-8", "replace")
    out = []
    for m in re.finditer(
            r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
            page, re.S):
        title = html.unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip()
        out.append(f"- {title}\n  {_ddg_decode(m.group(1))}")
    return out


def _ddg_lite(query):
    """The bare-bones lite endpoint — different markup, often unblocked when
    the html one is bot-walled (airport WiFi taught us this)."""
    url = "https://lite.duckduckgo.com/lite/?q=" + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        page = r.read(300_000).decode("utf-8", "replace")
    out = []
    for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', page, re.S):
        href = _ddg_decode(m.group(1))
        title = html.unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip()
        if (not href.startswith("http") or "duckduckgo.com" in href
                or len(title) < 5):
            continue
        out.append(f"- {title}\n  {href}")
    return out


def web_search(query):
    """DuckDuckGo, two endpoints deep — and an HONEST failure when both dry up
    (an empty search must read as a failure, never as license to invent)."""
    for fetch in (_ddg_html, _ddg_lite):
        try:
            hits = fetch(query)
        except Exception:                              # noqa: BLE001
            hits = []
        if hits:
            return "\n".join(hits[:5])
    return ("SEARCH FAILED: no results from either endpoint (this network may "
            "be blocking the search engine). Report this failure to the user "
            "plainly — do NOT supply links or facts from memory as if they "
            "were search results.")


def fetch_url(url):
    """Fetch a page and strip it to readable text."""
    if not url.startswith(("http://", "https://")):
        raise ValueError("only http(s) URLs")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=45) as r:
        page = r.read(400_000).decode("utf-8", "replace")
    page = re.sub(r"(?is)<(script|style|noscript).*?</\1>", " ", page)
    text = html.unescape(re.sub(r"<[^>]+>", " ", page))
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()[:6000]


def yt_transcript(url):
    """Pull a YouTube transcript via yt-dlp's subtitle download."""
    if not shutil.which("yt-dlp"):
        return "yt-dlp is not installed on this machine — tell the user."
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(
            ["yt-dlp", "--skip-download", "--write-auto-subs", "--write-subs",
             "--sub-langs", "en.*,en", "--sub-format", "vtt",
             "-o", os.path.join(td, "t"), url],
            capture_output=True, timeout=180)
        vtts = [f for f in os.listdir(td) if f.endswith(".vtt")]
        if not vtts:
            return "no transcript/captions available for that video"
        lines, last = [], None
        for raw in open(os.path.join(td, vtts[0]), encoding="utf-8",
                        errors="replace"):
            s = re.sub(r"<[^>]+>", "", raw).strip()
            if (not s or "-->" in s or s == "WEBVTT" or s.isdigit()
                    or s.startswith(("Kind:", "Language:"))):
                continue
            if s != last:                      # VTT repeats rolling lines
                lines.append(s)
                last = s
        return " ".join(lines)[:8000] or "empty transcript"


def find_files(pattern, root="~"):
    """Find files under `root` (within $HOME) whose NAME matches `pattern`."""
    top = _confined(root)
    hits = []
    for dirpath, dirnames, filenames in os.walk(top):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            if fnmatch.fnmatch(f, pattern):
                hits.append(os.path.join(dirpath, f))
                if len(hits) >= 80:
                    return "\n".join(hits) + "\n… (capped at 80)"
    return "\n".join(hits) if hits else "no matches"


def list_dir(path="~"):
    p = _confined(path)
    names = sorted(os.listdir(p))[:200]
    return "\n".join(n + ("/" if os.path.isdir(os.path.join(p, n)) else "")
                     for n in names) or "(empty)"


def read_file(path):
    p = _confined(path)
    with open(p, encoding="utf-8", errors="replace") as f:
        body = f.read(8000)
    return body + ("\n… (truncated)" if os.path.getsize(p) > 8000 else "")


def open_editor(path):
    """Open a file in the user's desktop editor (xdg-open)."""
    p = _confined(path)
    if not os.path.exists(p):
        raise ValueError(f"no such file: {p}")
    subprocess.Popen(["xdg-open", p], stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL)
    return f"opened {p} in the user's default application"


TOOLS = {
    "web_search":    (web_search,    "web_search(query) — DuckDuckGo, top 5 results"),
    "fetch_url":     (fetch_url,     "fetch_url(url) — fetch a page as readable text"),
    "yt_transcript": (yt_transcript, "yt_transcript(url) — YouTube transcript via yt-dlp"),
    "find_files":    (find_files,    "find_files(pattern, root='~') — filename glob under $HOME"),
    "list_dir":      (list_dir,      "list_dir(path='~') — directory listing"),
    "read_file":     (read_file,     "read_file(path) — first 8k chars of a file"),
    "open_editor":   (open_editor,   "open_editor(path) — open a file on the user's desktop"),
}

SYSTEM = """You are the Professor — a capable local AI with TOOLS. You are \
helping the user (they are not the Professor; never address them by that title).

Available tools:
%s

PROTOCOL — your every reply must be EXACTLY ONE JSON object, nothing else:
  to use a tool:   {"tool": "<name>", "args": {"<arg>": "<value>"}}
  to answer:       {"final": "<your complete answer to the user>"}
Rules: one tool per turn. After a tool runs, its output arrives in the next
message as [TOOL RESULT]. Use tools when they help; when you have what you
need, reply with "final". If a tool errors, adapt or report honestly in
"final". Never invent tool output. A URL may appear in "final" ONLY if it
appeared verbatim in a [TOOL RESULT] — if searches fail or return nothing,
say exactly that instead of answering from memory.""" % "\n".join(
    f"  - {d}" for _, d in TOOLS.values())


# ── model wire ───────────────────────────────────────────────────────────────
def chat(messages):
    payload = {"model": "prof", "messages": messages,
               "max_tokens": 1800, "temperature": 0.2}
    req = urllib.request.Request(
        BASE + "/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=420) as r:
            return json.load(r)["choices"][0]["message"]["content"]
    except urllib.error.URLError as e:
        sys.exit(f"can't reach the Professor at {BASE} ({e.reason}).\n"
                 "On Lenny, tunnel first:\n"
                 "  ssh -f -N -L 18090:127.0.0.1:8090 stevo@100.65.86.46\n"
                 "  PROF_BASE=http://127.0.0.1:18090 " + " ".join(sys.argv))


def first_json(text):
    """The first balanced JSON object in `text` (models love to add prose)."""
    dec = json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch == "{":
            try:
                obj, _ = dec.raw_decode(text[i:])
                return obj
            except ValueError:
                continue
    return None


# ── the loop ─────────────────────────────────────────────────────────────────
def run(task, yolo=False, rounds=8, show=False):
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": task}]
    nudged = False
    for _ in range(rounds):
        out = chat(messages)
        if show:
            print(f"\n─ model ─\n{out.strip()}\n─────────", file=sys.stderr)
        obj = first_json(out)
        if obj is None:
            if nudged:
                print(out.strip())          # twice off-protocol: show as-is
                return
            nudged = True
            messages += [{"role": "assistant", "content": out},
                         {"role": "user", "content":
                          "Protocol reminder: reply with ONE JSON object only "
                          '({"tool":…} or {"final":…}).'}]
            continue
        if "final" in obj:
            print(obj["final"])
            return
        name = obj.get("tool")
        args = obj.get("args") or {}
        if name not in TOOLS:
            messages += [{"role": "assistant", "content": out},
                         {"role": "user", "content":
                          f"[TOOL RESULT] error: no tool named {name!r}"}]
            continue
        print(f"⚙ {name}({', '.join(f'{k}={v!r}' for k, v in args.items())})",
              file=sys.stderr)
        if not yolo:
            ok = input("  run it? [Y/n] ").strip().lower() if sys.stdin.isatty() else "n"
            if ok not in ("", "y", "yes"):
                messages += [{"role": "assistant", "content": out},
                             {"role": "user", "content":
                              "[TOOL RESULT] the user declined this tool call. "
                              "Answer with what you have, or try another way."}]
                continue
        try:
            result = TOOLS[name][0](**args)
        except Exception as e:                       # noqa: BLE001 — to the model
            result = f"error: {e}"
        if show:
            print(f"─ tool result ─\n{str(result)[:400]}\n───────────────",
                  file=sys.stderr)
        messages += [{"role": "assistant", "content": out},
                     {"role": "user",
                      "content": f"[TOOL RESULT {name}]\n{str(result)[:6000]}"}]
    print("(round limit reached without a final answer — try a tighter ask)")


# ── macros: named prompts with {slots} — the GUI buttons' CLI ancestor ───────
def load_macros():
    try:
        return json.load(open(MACROS_PATH, encoding="utf-8"))
    except FileNotFoundError:
        return {}


def main():
    ap = argparse.ArgumentParser(description="give the local Professor hands")
    ap.add_argument("task", nargs="*", help="what you want done")
    ap.add_argument("--yolo", action="store_true",
                    help="run tools without per-call confirmation")
    ap.add_argument("--macro", help="run a saved macro from prof_macros.json")
    ap.add_argument("--list-macros", action="store_true")
    ap.add_argument("--rounds", type=int, default=8)
    ap.add_argument("--show", action="store_true",
                    help="print each raw model turn to stderr")
    ap.add_argument("--base", help="model endpoint (else $PROF_BASE)")
    a = ap.parse_args()
    global BASE
    if a.base:
        BASE = a.base.rstrip("/")
    macros = load_macros()
    if a.list_macros:
        for k, v in macros.items():
            print(f"{k}: {v.get('desc', '')}\n    {v['template']}")
        return
    if a.macro:
        if a.macro not in macros:
            sys.exit(f"no macro {a.macro!r} — try --list-macros")
        slots = dict(kv.split("=", 1) for kv in a.task if "=" in kv)
        try:
            task = macros[a.macro]["template"].format(**slots)
        except KeyError as e:
            sys.exit(f"macro {a.macro!r} needs a value for {e}")
    else:
        task = " ".join(a.task).strip()
    if not task:
        ap.print_help()
        return
    run(task, yolo=a.yolo, rounds=a.rounds, show=a.show)


if __name__ == "__main__":
    main()
