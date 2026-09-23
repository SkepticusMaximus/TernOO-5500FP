/* ternwords.js — the JS word decoder: third sibling of the python
 * (meccano_to_model) and C (ternui_words.c) decoders, same grammar.
 * Decodes canonical 24-trit balanced-ternary words into widget dicts —
 * the web face renders FROM these (CF5 23-09: the stream is the
 * interface; the face keeps no model of its own).
 * JS numbers are exact here: |word| < 3^24/2 ≈ 1.4e11 << 2^53. */
"use strict";

function twTrits(v) {
  const t = new Array(24);
  for (let i = 0; i < 24; i++) {
    let r = v % 3;
    if (r > 1) r -= 3;
    if (r < -1) r += 3;
    t[i] = r;
    v = (v - r) / 3;
  }
  return t;
}

function twField(t, lsb, width) {
  let v = 0, p = 1;
  for (let i = 0; i < width; i++) { v += t[lsb + i] * p; p *= 3; }
  return v;
}

function twIsString(t) {          /* DATA primary, STRING qualifier */
  return t[23] === -1 && t[22] === 1 && t[21] === 1 && t[20] === -1;
}

function twChars(pay) {
  let out = "";
  for (const c of [pay % 128, Math.floor(pay / 128) % 128,
                   Math.floor(pay / 16384) % 128])
    if (c) out += String.fromCharCode(c);
  return out;
}

function twStrings(words, i0, n) {
  let out = "";
  for (let i = 0; i < n; i++) {
    const t = twTrits(words[i0 + i]);
    if (twIsString(t)) out += twChars(twField(t, 0, 18));
  }
  return out;
}

/* decode a word stream → widget list (pixel coords, top-left);
 * GRID = FC_GRID_TO_MECCANO */
function twDecode(words, GRID = 10) {
  const nodes = [];
  let last = null;                 /* [node, attr] MMORE target */
  for (let i = 0; i < words.length; i++) {
    const t = twTrits(words[i]);
    if (twField(t, 22, 2) !== 2) continue;      /* OPCODE only */
    const family = twField(t, 20, 2);
    const arity = twField(t, 18, 2) + 4;
    const op = twField(t, 12, 6);
    const n = Math.min(arity, words.length - i - 1);
    if (family === -1 && op === 40 && n >= 2) { /* PIGART RNODE */
      const tm = twTrits(words[i + 1]), td = twTrits(words[i + 2]);
      const nd = {kind: "", name: "", scope: "",
                  x: twField(tm, 9, 9) * GRID,
                  y: twField(tm, 0, 9) * GRID,
                  w: twField(td, 6, 6) * GRID,
                  h: twField(td, 0, 6) * GRID,
                  label: twStrings(words, i + 3, n - 2)};
      nodes.push(nd);
      last = [nd, "label"];
    } else if (family === 1 && nodes.length) {  /* MODEL */
      const nd = nodes[nodes.length - 1];
      const txt = twStrings(words, i + 1, n);
      if (op === 0)      { nd.kind = txt;  last = [nd, "kind"]; }
      else if (op === 1) { nd.name = txt;  last = [nd, "name"]; }
      else if (op === 6) { nd.scope = txt; last = [nd, "scope"]; }
      else if (op === 9) {                      /* MFLAG key=value */
        if (txt.startsWith("label=")) {
          nd.label = txt.slice(6);
          last = [nd, "label"];
        } else last = null;
      } else if (op === 11) {                   /* MPROP name=value */
        const eq = txt.indexOf("=");
        (nd.properties = nd.properties || []).push(
          {name: txt.slice(0, eq), value: txt.slice(eq + 1)});
        last = null;
      } else if (op === 12) {                   /* MBIND signal=target */
        const eq = txt.indexOf("=");
        (nd.bindings = nd.bindings || {})[txt.slice(0, eq)] =
          txt.slice(eq + 1);
        last = null;
      } else if (op === 13 && n >= 1) {         /* MVALUE: DATA word */
        nd.value = twField(twTrits(words[i + 1]), 0, 18);
        last = null;
      } else if (op === 7 && last) {            /* MMORE continues */
        last[0][last[1]] += txt;
      } else if (op !== 7) {
        last = null;                            /* unknown op: no bleed */
      }
    }
    i += n;
  }
  return nodes;
}
