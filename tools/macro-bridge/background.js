// POBOX MacroBridge — background page.
// Relays an approved command line to the native host, which drops it into the
// POBOX Outbox as mail From: Stevo To: CC. The outbox watcher does the rest.
// One message in, one reply out (sendNativeMessage spawns the host per call).

browser.runtime.onMessage.addListener((msg) => {
  if (!msg || msg.cmd !== "relay") return;
  return browser.runtime.sendNativeMessage("pobox_macro_host", {
    line: msg.line, url: msg.url, ts: msg.ts
  }).then(
    resp => resp || { ok: false, error: "empty host reply" },
    err => ({ ok: false, error: String(err) })
  );
});
