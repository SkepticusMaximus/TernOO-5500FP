"""professor_agent.py — the ship's local agent loop.

The Professor (a local model via ollama's OpenAI-compatible endpoint) wields the
FlowCode **macro Forge's own macros** as tools. Each `command` macro becomes a
callable tool whose parameters are *exactly* the macro's declared fields — so the
model can only **parameterise** macros the captain forged, never run arbitrary
shell. The loop: ask → model emits a tool-call → assemble the deterministic
command from the macro + the model's field values → run it → feed the output back
→ repeat until the Professor answers.

This is Mesh-Chat's engine, not a parallel harness: it reads the same
`5500fp/macros/*.json` library the Forge writes. Mesh-Chat calls `ask()`.
"""
import os
import re
import glob
import json
import time
import subprocess
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
MACRO_DIR = os.path.join(HERE, "macros")
OLLAMA = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")

SYSTEM = ("You are the Professor, the ship's assistant. You can read and reason "
          "about everything in this conversation — including the contents of any "
          "attached file — and answer directly. You ALSO have tools (the captain's "
          "forged macros) for things like listing or searching files; call a tool "
          "only when it genuinely helps. NEVER claim you cannot read content that "
          "is already present in the conversation. After a tool returns, use its "
          "output to answer.")


def _san(name):
    return re.sub(r"\W+", "_", (name or "tool")).strip("_") or "tool"


def load_macros(macro_dir=MACRO_DIR):
    """The Forge's `command` macros (the ones with something to run)."""
    out = []
    for fn in sorted(glob.glob(os.path.join(macro_dir, "*.json"))):
        try:
            spec = json.load(open(fn, encoding="utf-8"))
        except Exception:
            continue
        if spec.get("kind") == "command" and spec.get("command"):
            out.append(spec)
    return out


def _field_key(f):
    return f.get("flag") or f.get("arg")


def schema_for(spec):
    props = {}
    for f in spec.get("fields", []):
        key = _field_key(f)
        if not key:
            continue
        name = _san(key)
        t = f.get("type")
        if t == "check":
            props[name] = {"type": "boolean", "description": f.get("label", key)}
        elif t == "choice":
            opts = [o for o in f.get("options", []) if o != ""]
            props[name] = {"type": "string", "description": f.get("label", key)}
            if opts:
                props[name]["enum"] = opts
        else:   # path / text / default
            props[name] = {"type": "string", "description": f.get("label", key)}
    return {"type": "object", "properties": props}


def macros_as_tools(macros):
    tools = []
    for s in macros:
        tools.append({"type": "function", "function": {
            "name": _san(s["name"]),
            "description": (s.get("desc") or s["name"]) + "  (runs: %s)" % s["command"],
            "parameters": schema_for(s)}})
    return tools


def assemble(spec, values):
    """macro spec + the model's field values → a deterministic argv list.
    Base command is the macro's; only declared fields are honoured; NO shell."""
    values = values or {}
    cmd = [spec["command"]]
    for f in spec.get("fields", []):
        key = _field_key(f)
        if not key:
            continue
        v = values.get(_san(key))
        if f.get("type") == "check":
            if v in (True, "true", "True", 1, "1"):
                cmd.append(f["flag"])
        elif f.get("flag"):
            if v not in (None, "", False):
                cmd += [f["flag"], str(v)]
        else:   # positional arg
            if v not in (None, ""):
                cmd.append(os.path.expanduser(str(v)))
    return cmd


def run_macro(spec, values, timeout=30):
    cmd = assemble(spec, values)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        out = (r.stdout or "") + (r.stderr or "")
        return (out[:4000] or "(ran, no output)"), cmd
    except Exception as e:
        return ("(error running %s: %s)" % (cmd, e)), cmd


def _ollama_chat(messages, tools, model="Professor", timeout=900):
    body = json.dumps({"model": model, "messages": messages,
                       "tools": tools, "stream": False}).encode()
    last = None
    for _ in range(3):           # ollama can drop the connection while (re)loading a big model
        try:
            req = urllib.request.Request(OLLAMA + "/api/chat", body,
                                         {"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except Exception as e:   # RemoteDisconnected on reload / transient — give it time, retry
            last = e
            time.sleep(4)
    raise last


def ask(user_msg=None, model="Professor", max_steps=5, system=None, on_event=None,
        macro_dir=MACRO_DIR, messages=None):
    """Run the agent loop. Returns (final_answer, transcript).
    Pass either `user_msg` (one question) OR `messages` (a full conversation — e.g.
    Mesh-Chat's build_messages() with history AND any attached file). The system
    message is always the agent's, so the model knows it can read content and use
    tools. on_event(name, args, cmd, result) fires on each tool run."""
    macros = load_macros(macro_dir)
    tools = macros_as_tools(macros)
    by_name = {_san(s["name"]): s for s in macros}
    sysmsg = {"role": "system", "content": system or SYSTEM}
    if messages is not None:
        messages = [sysmsg] + [m for m in messages if m.get("role") != "system"]
    else:
        messages = [sysmsg, {"role": "user", "content": user_msg or ""}]
    transcript = []
    for _ in range(max_steps):
        resp = _ollama_chat(messages, tools, model=model)
        m = resp.get("message", {}) or {}
        messages.append(m)
        tcs = m.get("tool_calls") or []
        if not tcs:
            return (m.get("content", "") or ""), transcript
        for tc in tcs:
            fn = tc.get("function", {}).get("name", "")
            args = tc.get("function", {}).get("arguments") or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args or "{}")
                except Exception:
                    args = {}
            spec = by_name.get(fn)
            if not spec:
                result, cmd = ("(no such macro: %s)" % fn), []
            else:
                result, cmd = run_macro(spec, args)
            transcript.append({"tool": fn, "args": args, "cmd": cmd,
                               "result": result[:600]})
            if on_event:
                on_event(fn, args, cmd, result)
            messages.append({"role": "tool", "tool_name": fn, "content": result})
    return "(reached max tool-steps without a final answer)", transcript


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "List the files in /tmp, long listing."
    print("ASK:", q)
    ans, tr = ask(q)
    for t in tr:
        print("  ⚙ %s(%s) -> %s" % (t["tool"], t["args"], t["cmd"]))
        print("     out: %s" % (t["result"][:200].replace("\n", " ⏎ ")))
    print("ANSWER:", ans)
