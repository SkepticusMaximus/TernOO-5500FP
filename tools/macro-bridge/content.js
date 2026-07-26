// POBOX MacroBridge — content script.
// Scans the page for sentinel command lines and offers them for relay to CC.
//
// THE LAW OF THE SENTINEL (captain's spec, 27-07-2026):
//   - a command line begins with  !#   (optionally  !#_Verb ...)
//   - a line beginning with ## is a COMMENT: the sentinel is VOID there, so
//     docs and chat can discuss/show examples (## !# rm -rf /) without firing.
//   - nothing is ever sent without an explicit click on [Send to CC].

const SENTINEL_RE = /^\s*!#/;
const COMMENT_VOID_RE = /^\s*##/;      // a line that begins with ## is a comment
const MAX_LINE = 2000;
const SCAN_MS = 2500;

let seen = new Set();       // lines already sent or dismissed (persisted)
let offered = new Set();    // lines currently sitting in the panel
let panel = null;

browser.storage.local.get("mb_seen").then(r => {
  if (Array.isArray(r.mb_seen)) seen = new Set(r.mb_seen);
});

function persistSeen() {
  browser.storage.local.set({ mb_seen: Array.from(seen).slice(-500) });
}

// THE GUARD — applied in this exact order: comment check BEFORE sentinel check,
// so a line beginning with ## can never be read as a command, whatever follows.
function isCommand(line) {
  if (!line || line.length > MAX_LINE) return false;
  if (COMMENT_VOID_RE.test(line)) return false;   // ## voids the sentinel
  return SENTINEL_RE.test(line);
}

function ensurePanel() {
  if (panel && document.body.contains(panel)) return panel;
  panel = document.createElement("div");
  panel.id = "pobox-macrobridge-panel";
  panel.style.cssText =
    "position:fixed;bottom:14px;right:14px;z-index:2147483647;max-width:460px;" +
    "background:#1c1e26;color:#e8e8e8;font:12px monospace;border:1px solid #555;" +
    "border-radius:8px;padding:8px 10px;box-shadow:0 4px 18px rgba(0,0,0,.5);";
  panel.innerHTML =
    "<div style='font-weight:bold;margin-bottom:4px'>✉ MacroBridge</div>";
  document.body.appendChild(panel);
  return panel;
}

function toast(text, ok) {
  const p = ensurePanel();
  const d = document.createElement("div");
  d.style.cssText = "margin:4px 0;color:" + (ok ? "#8fd18f" : "#e88");
  d.textContent = text;
  p.appendChild(d);
  setTimeout(() => { d.remove(); trimPanel(); }, 6000);
}

function trimPanel() {
  if (panel && panel.children.length <= 1 && offered.size === 0) {
    panel.remove();
    panel = null;
  }
}

function offer(line) {
  offered.add(line);
  const p = ensurePanel();
  const row = document.createElement("div");
  row.style.cssText = "margin:6px 0;border-top:1px solid #444;padding-top:6px;";
  const cmd = document.createElement("div");
  cmd.style.cssText = "white-space:pre-wrap;word-break:break-all;color:#ffd479;";
  cmd.textContent = line.length > 300 ? line.slice(0, 300) + "…" : line;
  const btns = document.createElement("div");
  btns.style.cssText = "margin-top:4px;display:flex;gap:8px;";
  const send = document.createElement("button");
  send.textContent = "Send to CC ✉";
  send.style.cssText = "cursor:pointer;background:#2d6a4f;color:#fff;border:0;" +
                       "border-radius:4px;padding:3px 10px;font:12px monospace;";
  const dismiss = document.createElement("button");
  dismiss.textContent = "Dismiss";
  dismiss.style.cssText = "cursor:pointer;background:#555;color:#ddd;border:0;" +
                          "border-radius:4px;padding:3px 10px;font:12px monospace;";
  send.onclick = () => {
    send.disabled = true;
    send.textContent = "sending…";
    browser.runtime.sendMessage({
      cmd: "relay", line: line, url: location.href, ts: new Date().toISOString()
    }).then(resp => {
      seen.add(line); offered.delete(line); persistSeen();
      row.remove();
      toast(resp && resp.ok ? "sent: " + (resp.file || "mailed to CC")
                            : "FAILED: " + ((resp && resp.error) || "no host reply"),
            !!(resp && resp.ok));
      trimPanel();
    });
  };
  dismiss.onclick = () => {
    seen.add(line); offered.delete(line); persistSeen();
    row.remove(); trimPanel();
  };
  btns.appendChild(send); btns.appendChild(dismiss);
  row.appendChild(cmd); row.appendChild(btns);
  p.appendChild(row);
}

function scan() {
  let text = "";
  try { text = document.body ? document.body.innerText : ""; } catch (e) { return; }
  for (const raw of text.split("\n")) {
    const line = raw.replace(/\s+$/, "");
    if (!isCommand(line)) continue;                 // comment + sentinel guard
    if (seen.has(line) || offered.has(line)) continue;
    offer(line);
  }
}

setInterval(scan, SCAN_MS);
scan();
