"use strict";
/* TernOO-FlowCode web face — mechanics for all tabs.
   Engine-sovereign: every computation happens server-side in the real
   organs (walker, sheet_formula, command registry, TernDoc). */

const $ = id => document.getElementById(id);
function fatal(msg) {
  let b = $("fatalbar");
  if (!b) {
    b = document.createElement("div");
    b.id = "fatalbar";
    b.onclick = () => b.remove();
    document.body.appendChild(b);
  }
  b.textContent = "✗ " + msg + "   (click to dismiss)";
}
window.addEventListener("error", e =>
  fatal(e.message + " @ " + (e.filename || "").split("/").pop() + ":" +
        e.lineno));
window.addEventListener("unhandledrejection", e =>
  fatal(String((e.reason && (e.reason.message || e.reason)) ||
               "promise rejected")));
const toast = m => { const t = $("toast"); t.textContent = m;
  t.style.opacity = 1; setTimeout(() => t.style.opacity = 0, 2600); };
async function api(path, body) {
  const opts = body === undefined ? {} :
    {method: "POST", headers: {"Content-Type": "application/json"},
     body: JSON.stringify(body)};
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const r = await fetch(path, opts);
      return await r.json();
    } catch (e) {
      if (attempt) throw new Error(
        `the engine did not answer ${path} — is the server aboard? (` +
        (e.message || e) + ")");
      await new Promise(res => setTimeout(res, 400));
    }
  }
}
document.querySelectorAll(".navbtn").forEach(b => b.onclick = () => {
  document.querySelectorAll(".navbtn").forEach(x =>
    x.classList.toggle("active", x === b));
  for (const t of ["flow", "gui", "sheet", "conn", "author"])
    $("tab-" + t).classList.toggle("hidden", t !== b.dataset.tab);
});
function togglePanel(h) {
  h.classList.toggle("open");
  const b = h.nextElementSibling;
  if (b) b.style.display = h.classList.contains("open") ? "" : "none";
}

/* ══════════════════ FLOW ══════════════════ */
const SVGNS = "http://www.w3.org/2000/svg";
let view = {x: 0, y: 0, k: 1}, flowBounds = null;
let FLOW = null, SEL = null, SELEDGE = null, WIRE = null, drag = null;
let wpdrag = null;
function worldXY(e) {
  const r = $("flowwrap").getBoundingClientRect();
  return [(e.clientX - r.left - view.x) / view.k,
          (e.clientY - r.top - view.y) / view.k];
}
function distToSeg(p, a, b) {
  const dx = b[0] - a[0], dy = b[1] - a[1];
  const L2 = dx * dx + dy * dy;
  const t = L2 ? Math.max(0, Math.min(1,
    ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2)) : 0;
  const qx = a[0] + t * dx - p[0], qy = a[1] + t * dy - p[1];
  return Math.hypot(qx, qy);
}
let TOOL = "select";

function setTool(t) {
  TOOL = t; WIRE = (t === "wire") ? {src: null} : null;
  for (const id of ["t-select", "t-delete", "t-wire"])
    $(id).classList.toggle("arm", id === "t-" + t);
  $("toolname").textContent = {select: "Select", delete: "Delete",
                               wire: "Edge"}[t];
}
function applyView() {
  $("world").setAttribute("transform",
    `translate(${view.x},${view.y}) scale(${view.k})`);
}
function zoomBy(f) { view.k = Math.max(.2, Math.min(3, view.k * f));
  applyView(); }
function fitView() {
  if (!flowBounds) return;
  const w = $("flowwrap").clientWidth, h = $("flowwrap").clientHeight;
  const bw = flowBounds.x1 - flowBounds.x0 + 120,
        bh = flowBounds.y1 - flowBounds.y0 + 120;
  view.k = Math.min(w / bw, h / bh, 1.6);
  view.x = (w - (flowBounds.x0 + flowBounds.x1) * view.k) / 2;
  view.y = (h - (flowBounds.y0 + flowBounds.y1) * view.k) / 2;
  applyView();
}
(() => {
  let pan = null;
  $("flowwrap").addEventListener("mousedown", e => {
    if (e.target.closest(".zoomctl")) return;
    pan = {mx: e.clientX, my: e.clientY, vx: view.x, vy: view.y};
    $("flowwrap").classList.add("panning");
  });
  window.addEventListener("mousemove", e => {
    if (wpdrag && FLOW) {
      const wp = (FLOW.edges[wpdrag.ei].waypoints || [])[wpdrag.wi];
      if (wp) {
        wp.x = Math.round(wpdrag.sx + (e.clientX - wpdrag.mx) / view.k);
        wp.y = Math.round(wpdrag.sy + (e.clientY - wpdrag.my) / view.k);
        render();
      }
      return;
    }
    if (drag && FLOW) {
      const s = FLOW.syms.get(drag.id);
      s.x = Math.round(drag.sx + (e.clientX - drag.mx) / view.k);
      s.y = Math.round(drag.sy + (e.clientY - drag.my) / view.k);
      render(); showProps();
      return;
    }
    if (!pan) return;
    view.x = pan.vx + e.clientX - pan.mx;
    view.y = pan.vy + e.clientY - pan.my; applyView();
  });
  window.addEventListener("mouseup", () => { pan = null; drag = null;
    wpdrag = null;
    $("flowwrap").classList.remove("panning"); });
  $("flowwrap").addEventListener("wheel", e => {
    e.preventDefault(); zoomBy(e.deltaY < 0 ? 1.12 : 1 / 1.12);
  }, {passive: false});
})();
function el(tag, attrs, parent) {
  const n = document.createElementNS(SVGNS, tag);
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
  (parent || $("world")).appendChild(n);
  return n;
}
function symbolShape(s) {
  const {x, y, w, h, kind} = s;
  const common = {filter: "url(#shadow)", stroke: "#0d0d14",
                  "stroke-width": 1.5, class: "sym-hit"};
  let node;
  if (kind === "flow_decision") {
    const cx = x + w / 2, cy = y + h / 2;
    node = el("polygon", {...common,
      points: `${cx},${y - 6} ${x + w + 10},${cy} ${cx},${y + h + 6} ${x - 10},${cy}`,
      fill: "url(#g-dec)"});
  } else if (kind === "flow_io") {
    node = el("polygon", {...common,
      points: `${x + 14},${y} ${x + w},${y} ${x + w - 14},${y + h} ${x},${y + h}`,
      fill: "url(#g-io)"});
  } else if (kind === "flow_terminator") {
    node = el("rect", {...common, x, y, width: w, height: h,
      rx: h / 2, fill: "url(#g-term)"});
  } else if (kind === "flow_loop") {
    const c = 14;
    node = el("polygon", {...common,
      points: `${x + c},${y} ${x + w - c},${y} ${x + w},${y + h / 2} ` +
              `${x + w - c},${y + h} ${x + c},${y + h} ${x},${y + h / 2}`,
      fill: "url(#g-loop)"});
  } else {
    node = el("rect", {...common, x, y, width: w, height: h, rx: 7,
      fill: "url(#g-proc)"});
  }
  if (SEL === s.id) node.classList.add("sym-sel");
  node.addEventListener("mousedown", e => {
    e.stopPropagation();
    if (TOOL === "wire") { wireClick(s.id); return; }
    if (TOOL === "delete") { SEL = s.id; delSel(); return; }
    SEL = s.id; SELEDGE = null;
    drag = {id: s.id, mx: e.clientX, my: e.clientY, sx: s.x, sy: s.y};
    render(); showProps();
  });
  node.addEventListener("dblclick", e => {
    e.stopPropagation();
    const nl = prompt("Label:", s.label || "");
    if (nl !== null) { s.label = nl; render(); showProps(); }
  });
  return node;
}
function centerOf(s) { return [s.x + s.w / 2, s.y + s.h / 2]; }
function edgePath(a, b, waypoints) {
  const [ax, ay] = centerOf(a), [bx, by] = centerOf(b);
  const pts = [[ax, ay],
    ...(waypoints || []).map(p => [p.x ?? p[0], p.y ?? p[1]]), [bx, by]];
  if (pts.length === 2) {
    const mx = (ax + bx) / 2, my = (ay + by) / 2;
    const dy = Math.abs(by - ay) > Math.abs(bx - ax);
    return dy ? `M ${ax} ${ay} C ${ax} ${my}, ${bx} ${my}, ${bx} ${by}`
              : `M ${ax} ${ay} C ${mx} ${ay}, ${mx} ${by}, ${bx} ${by}`;
  }
  return "M " + pts.map(p => p.join(" ")).join(" L ");
}
function render() {
  const world = $("world"); world.innerHTML = "";
  if (!FLOW) return;
  FLOW.edges.forEach((e, i) => {
    const a = FLOW.syms.get(e.src), b = FLOW.syms.get(e.dst);
    if (!a || !b) return;
    const p = el("path", {d: edgePath(a, b, e.waypoints), fill: "none",
      stroke: SELEDGE === i ? "#ffffff" : "#8fa8d0",
      "stroke-width": SELEDGE === i ? 3 : 2.2,
      "marker-end": "url(#arrow)", style: "cursor:pointer"});
    p.addEventListener("mousedown", ev => { ev.stopPropagation();
      if (TOOL === "delete") { FLOW.edges.splice(i, 1); render(); return; }
      SELEDGE = i; SEL = null; render(); showProps(); });
    p.addEventListener("dblclick", ev => {
      ev.stopPropagation();               // dbl-click bends the edge here
      const [wx, wy] = worldXY(ev);
      e.waypoints = e.waypoints || [];
      const pts = [centerOf(a),
        ...e.waypoints.map(w => [w.x ?? w[0], w.y ?? w[1]]), centerOf(b)];
      let best = 0, bestD = Infinity;
      for (let k = 0; k < pts.length - 1; k++) {
        const dd = distToSeg([wx, wy], pts[k], pts[k + 1]);
        if (dd < bestD) { bestD = dd; best = k; }
      }
      e.waypoints.splice(best, 0, {x: Math.round(wx), y: Math.round(wy)});
      SELEDGE = i; SEL = null; render(); showProps();
    });
    if (SELEDGE === i) (e.waypoints || []).forEach((wp, wi) => {
      const h = el("circle", {cx: wp.x ?? wp[0], cy: wp.y ?? wp[1], r: 6,
        fill: "#ffffff", stroke: "#0d0d14", "stroke-width": 1.5,
        style: "cursor:move"});
      h.addEventListener("mousedown", ev => {
        ev.stopPropagation();
        if (TOOL === "delete") { e.waypoints.splice(wi, 1); render();
          return; }
        wpdrag = {ei: i, wi, mx: ev.clientX, my: ev.clientY,
                  sx: wp.x ?? wp[0], sy: wp.y ?? wp[1]};
      });
    });
    if (e.condition) {
      const [ax, ay] = centerOf(a), [bx, by] = centerOf(b);
      const t = el("text", {x: (ax + bx) / 2, y: (ay + by) / 2 - 8,
                            class: "edge-label"});
      t.textContent = e.condition;
    }
  });
  let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
  for (const s of FLOW.syms.values()) {
    symbolShape(s);
    const lbl = el("text", {x: s.x + s.w / 2, y: s.y + s.h / 2,
                            class: "sym-label"});
    lbl.textContent = s.label || s.kind.replace("flow_", "");
    x0 = Math.min(x0, s.x); y0 = Math.min(y0, s.y);
    x1 = Math.max(x1, s.x + s.w); y1 = Math.max(y1, s.y + s.h);
  }
  flowBounds = FLOW.syms.size ? {x0, y0, x1, y1} : null;
  $("flowtitle").textContent = FLOW.name +
    ` — ${FLOW.syms.size} symbols, ${FLOW.edges.length} edges`;
}
function showProps() {
  const pb = $("propbody");
  if (SELEDGE !== null && FLOW) {
    const e = FLOW.edges[SELEDGE];
    if (!e) { pb.innerHTML = '<div class="hint">select a symbol or an edge</div>'; return; }
    pb.innerHTML = "";
    pb.appendChild(propRow("kind", "edge", null, true));
    pb.appendChild(propRow("cond", e.condition || "", v => {
      e.condition = v; render(); }));
    pb.appendChild(propRow("bends",
      `${(e.waypoints || []).length} — dbl-click edge adds · drag` +
      ` moves · Delete tool on a handle removes`, null, true));
    return;
  }
  if (!FLOW || SEL === null || !FLOW.syms.has(SEL)) {
    pb.innerHTML = '<div class="hint">select a symbol or an edge</div>';
    return;
  }
  const s = FLOW.syms.get(SEL);
  pb.innerHTML = "";
  pb.appendChild(propRow("kind", s.kind.replace("flow_", ""), null, true));
  pb.appendChild(propRow("label", s.label || "", v => {
    s.label = v; render(); }));
  pb.appendChild(propRow("name", s.name || "", v => { s.name = v; }));
  for (const f of ["x", "y", "w", "h"])
    pb.appendChild(propRow(f, s[f], v => {
      const n = parseInt(v, 10);
      if (!isNaN(n)) { s[f] = n; render(); } }));
  propListEditor(pb, s, () => { render(); showProps(); });
}
function propListEditor(pb, holder, refresh) {
  // the symbol's own property words (direction / channel / address …)
  const props = holder.properties = holder.properties || [];
  props.forEach((pr, pi) => {
    const d = document.createElement("div");
    d.className = "prop-row";
    const l = document.createElement("label");
    l.textContent = "· " + pr.name;
    const i2 = document.createElement("input");
    i2.value = pr.value ?? "";
    i2.addEventListener("change", () => { pr.value = i2.value; });
    const x = document.createElement("button");
    x.textContent = "✕"; x.title = "remove property";
    x.className = "prop-del";
    x.onclick = () => { props.splice(pi, 1); refresh(); };
    d.appendChild(l); d.appendChild(i2); d.appendChild(x);
    pb.appendChild(d);
  });
  const add = document.createElement("button");
  add.className = "tool"; add.textContent = "＋ property";
  add.onclick = () => {
    const n = prompt("Property name (e.g. direction, channel, address):");
    if (!n || !n.trim()) return;
    props.push({name: n.trim(), value: ""});
    refresh();
  };
  pb.appendChild(add);
}
function propRow(label, value, onchange, ro) {
  const d = document.createElement("div");
  d.className = "prop-row";
  const l = document.createElement("label"); l.textContent = label;
  const i = document.createElement("input"); i.value = value;
  if (ro) i.disabled = true;
  else i.addEventListener("change", () => onchange(i.value));
  d.appendChild(l); d.appendChild(i);
  return d;
}
function addVarRow(name, init) {
  const d = document.createElement("div");
  d.className = "var-row";
  d.innerHTML = `<input placeholder="name" value="${name}">
    <input placeholder="init (one tongue)" value="${init}">
    <button title="remove">✕</button>`;
  d.querySelector("button").onclick = () => d.remove();
  $("varrows").appendChild(d);
}
function collectVars() {
  const out = {};
  for (const row of $("varrows").children) {
    const [n, v] = row.querySelectorAll("input");
    if (n.value.trim()) {
      const t = v.value.trim();
      out[n.value.trim()] =
        t === "" ? null : (isNaN(Number(t)) ? t : Number(t));
    }
  }
  return out;
}
let DOC = null;   // the unified open document — one file, all tabs
async function loadFlowList() {
  const designs = await api("/api/designs");
  if (!Array.isArray(designs) || !designs.length) {
    setTimeout(loadFlowList, 1500);       // server booting — keep trying
    return;
  }
  for (const pick of document.querySelectorAll("select.designpick")) {
    const kept = pick.value;
    pick.innerHTML = '<option value="">— designs aboard —</option>' +
      designs.map(n => `<option>${n}</option>`).join("");
    if (kept) pick.value = kept;
  }
  $("statusline").textContent =
    `on TernOO · ${designs.length} designs aboard` +
    (window.__BUILD ? ` · build ${window.__BUILD}` : "");
}
async function openDesign(name) {
  if (!name) {
    // no scolding: Open with nothing picked PRESENTS the choices
    const pick = $("designpick");
    if (pick.options.length <= 1) await loadFlowList();
    if (pick.showPicker) { try { pick.showPicker(); } catch (e) {} }
    pick.focus();
    return;
  }
  const raw = await api("/api/design/" + encodeURIComponent(name));
  if (raw.error) { toast(raw.error); return; }
  DOC = {name, raw};
  // THE STREAM IS THE INTERFACE (CF5 23-09): fetch the canonical
  // words; what the GUI tab SHOWS derives from decoding them — any
  // private-model drift loses to the stream.
  let wordWidgets = null;
  try {
    const ws = await api("/api/words/" + encodeURIComponent(name));
    if (ws.words && ws.words.length) wordWidgets = twDecode(ws.words);
  } catch (e) { wordWidgets = null; }
  const syms = new Map();
  for (const s of raw.flow_symbols || []) syms.set(s.id, s);
  FLOW = {name, raw, syms,
          edges: raw.flow_edges || raw.edges || [],
          edgeKey: raw.flow_edges ? "flow_edges" : "edges"};
  SEL = null; SELEDGE = null; render(); fitView(); showProps();
  GUI.widgets = new Map(); let maxid = 0;
  for (const s of raw.symbols || []) {
    if ((s.kind || "").startsWith("gui_")) {
      GUI.widgets.set(s.id, {...s}); maxid = Math.max(maxid, s.id);
    }
  }
  relToAbs();
  if (wordWidgets && wordWidgets.length) {
    // marry the decoded stream onto the edit model BY NAME: geometry,
    // label, kind and containment come from the WORDS (properties /
    // signal_ids stay JSON-side until the vocabulary carries them —
    // flagged); stream order becomes the stacking sequence.
    const byName = new Map(
      [...GUI.widgets.values()].map(w => [w.name, w]));
    const order = [];
    for (const d of wordWidgets) {
      const w = byName.get(d.name);
      if (!w) continue;
      w.kind = d.kind || w.kind;
      w.label = d.label;
      w.x = d.x; w.y = d.y; w.w = d.w; w.h = d.h;
      const par = byName.get(d.scope);
      w.parent_id = par ? par.id : null;
      order.push(w.id);
    }
    if (order.length === GUI.widgets.size) GUI.zorder = order;
    else GUI.zorder = (raw.sequence || []).map(Number)
      .filter(i => GUI.widgets.has(i));
    $("guititle").dataset.source = "words";
  } else {
    GUI.zorder = (raw.sequence || []).map(Number)
      .filter(i => GUI.widgets.has(i));
    $("guititle").dataset.source = "json";
  }
  zorderSeq();
  GUI.next = maxid + 1; GUI.name = name; GUI.raw = raw;
  GSEL = null; guiRender(); guiProps(); guiScrollHome();
  SHEET = {name, raw: new Map()};
  for (const c of raw.cell_symbols || raw.c || [])
    SHEET.raw.set(`${c.row},${c.col}`, String(c.value ?? ""));
  buildGrid(); if (SHEET.raw.size) evalSheet();
  CONN = {name, syms: new Map(), edges: raw.cmd_edges || [], next: 1};
  for (const s of raw.cmd_symbols || []) {
    CONN.syms.set(s.id, s);
    CONN.next = Math.max(CONN.next, s.id + 1);
  }
  connRender(); connProps();
  for (const pick of document.querySelectorAll("select.designpick"))
    pick.value = name;
  toast(`opened ${name} — families distributed to every tab`);
}
function closeDesign() {
  DOC = null;
  FLOW = null; SEL = null; SELEDGE = null;
  $("world").innerHTML = "";
  $("flowtitle").textContent = "no design open — File ▸ Open";
  showProps();
  GUI.widgets.clear(); GUI.zorder = []; GUI.name = null; GSEL = null;
  guiRender(); guiProps();
  SHEET = {name: null, raw: new Map()}; buildGrid();
  CONN = {name: "pipeline.fc", syms: new Map(), edges: [], next: 1};
  connRender(); connProps();
  $("runlines").textContent = "";
  WATCHVALS = {}; $("watchbody").textContent = "";
  $("connlines").textContent = "";
  for (const pick of document.querySelectorAll("select.designpick"))
    pick.value = "";
  toast("closed across all tabs");
}
async function saveDesign() {
  const name = prompt("Save design as (.fc / .flow / .gui / .sheet):",
                      (DOC && DOC.name) || "untitled.fc");
  if (!name) return;
  const doc = Object.assign({ternoo_version: "0.3",
    source_type: "ternoo_design", word_stream: [], symbols: [],
    edges: [], flow_symbols: [], flow_edges: [], cmd_symbols: [],
    cmd_edges: [], cell_symbols: [], sheet_regions: [], free_cells: [],
    sequence: [], groups: {}}, (DOC && DOC.raw) || {});
  doc.source_file = name;
  if (FLOW) { doc.flow_symbols = [...FLOW.syms.values()];
              doc[FLOW.edgeKey || "flow_edges"] = FLOW.edges; }
  doc.symbols = guiSymbolsOut();
  doc.sequence = zorderSeq().slice();
  doc.cell_symbols = cellSymbolsOut();
  doc.cmd_symbols = [...CONN.syms.values()];
  doc.cmd_edges = CONN.edges;
  const res = await api("/api/design/" + encodeURIComponent(name) +
                        "/save", {design: doc});
  if (res.saved) { toast(`saved ${res.saved}`);
    DOC = {name: res.saved, raw: doc}; loadFlowList(); }
  else toast(res.error || "save failed");
}
async function openFlow(name) {
  const raw = await api("/api/flow/" + encodeURIComponent(name));
  const syms = new Map();
  for (const s of raw.flow_symbols || []) syms.set(s.id, s);
  FLOW = {name, raw, syms,
          edges: raw.flow_edges || raw.edges || [],
          edgeKey: raw.flow_edges ? "flow_edges" : "edges"};
  SEL = null; SELEDGE = null;
  render(); fitView(); showProps();
}
function addSym(kind) {
  if (!FLOW)
    FLOW = {name: "untitled.fc",
            raw: {ternoo_version: "0.3", source_type: "ternoo_design",
                  symbols: [], edges: []},
            syms: new Map(), edges: [], edgeKey: "flow_edges"};
  const id = Math.max(0, ...FLOW.syms.keys()) + 1;
  const w = $("flowwrap").clientWidth, h = $("flowwrap").clientHeight;
  const cx = (w / 2 - view.x) / view.k, cy = (h / 2 - view.y) / view.k;
  const s = {id, kind, x: Math.round(cx - 60), y: Math.round(cy - 30),
             w: 120, h: 60,
             label: kind.replace("flow_", "").toUpperCase(),
             properties: []};
  FLOW.syms.set(id, s); SEL = id; render(); showProps();
}
function delSel() {
  if (!FLOW) return;
  if (SELEDGE !== null) { FLOW.edges.splice(SELEDGE, 1);
    SELEDGE = null; render(); showProps(); return; }
  if (SEL === null) return;
  FLOW.syms.delete(SEL);
  FLOW.edges = FLOW.edges.filter(e => e.src !== SEL && e.dst !== SEL);
  SEL = null; render(); showProps();
}
function wireClick(id) {
  if (!WIRE.src) { WIRE.src = id;
    $("flowtitle").textContent += "  ·  source set, click target";
    return; }
  if (WIRE.src !== id) {
    const srcSym = FLOW.syms.get(WIRE.src);
    let condition = "";
    if (srcSym.kind === "flow_decision")
      condition = prompt(
        "Condition for this branch (blank = dunno door):", "") || "";
    FLOW.edges.push({src: WIRE.src, dst: id, privilege: 0,
                     call_style: 0, return_type: 1, seg_idx: 0,
                     offset: 0, waypoints: [], condition});
  }
  WIRE = {src: null}; render();
}
function propOf(s, name, dflt) {
  for (const p of s.properties || [])
    if (p.name === name) return p.value;
  return dflt;
}
let WATCHVALS = {};
function liveDesignDoc() {
  // run-what-you-see: assemble the design from LIVE tab state
  const doc = Object.assign({ternoo_version: "0.3",
    source_type: "ternoo_design", word_stream: [], symbols: [],
    edges: [], flow_symbols: [], flow_edges: [], cmd_symbols: [],
    cmd_edges: [], cell_symbols: [], sheet_regions: [], free_cells: [],
    sequence: [], groups: {}}, (DOC && DOC.raw) || {});
  if (FLOW) { doc.flow_symbols = [...FLOW.syms.values()];
              doc[FLOW.edgeKey || "flow_edges"] = FLOW.edges; }
  doc.symbols = guiSymbolsOut();
  doc.sequence = zorderSeq().slice();
  doc.cell_symbols = cellSymbolsOut();
  doc.cmd_symbols = [...CONN.syms.values()];
  doc.cmd_edges = CONN.edges;
  return doc;
}
function cellKind(value) {
  // Tk-face auto-detect: = → formula, number/bool → value, else text
  if (value.startsWith("=")) return "cell_formula";
  const s = value.trim().toLowerCase();
  if (s === "true" || s === "false") return "cell_value";
  return (s !== "" && !isNaN(Number(s))) ? "cell_value" : "cell_text";
}
function cellSymbolsOut() {
  return [...SHEET.raw.entries()].map(([rc, value], i) => {
    const [row, col] = rc.split(",").map(Number);
    return {id: i + 1, row, col, value, kind: cellKind(value),
            label: colName(col) + (row + 1), properties: []};
  });
}
function showAppPreview() {
  // run = the app appears: the designed GUI, rendered clean, live values
  const old = $("apppreview");
  if (old) old.remove();
  if (!GUI.widgets.size) return;
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const w of GUI.widgets.values()) {
    x0 = Math.min(x0, w.x); y0 = Math.min(y0, w.y);
    x1 = Math.max(x1, w.x + w.w); y1 = Math.max(y1, w.y + w.h);
  }
  const ov = document.createElement("div");
  ov.id = "apppreview";
  ov.addEventListener("mousedown", e => {
    if (e.target === ov) ov.remove(); });
  const stage = document.createElement("div");
  stage.className = "appstage";
  const bar = document.createElement("div");
  bar.className = "appbar";
  const ttl = document.createElement("span");
  ttl.textContent = `▶ ${GUI.name || "app"} — running on TernOO`;
  const x = document.createElement("button");
  x.textContent = "✕ close";
  x.onclick = () => ov.remove();
  bar.appendChild(ttl); bar.appendChild(x);
  const cv = document.createElement("div");
  cv.className = "appcanvas";
  cv.style.width = (x1 - x0 + 40) + "px";
  cv.style.height = (y1 - y0 + 40) + "px";
  for (const src of $("guicanvas").children) {
    const c = src.cloneNode(true);
    c.classList.remove("sel");
    c.style.left = (parseInt(c.style.left, 10) - x0 + 20) + "px";
    c.style.top = (parseInt(c.style.top, 10) - y0 + 20) + "px";
    cv.appendChild(c);
  }
  stage.appendChild(bar); stage.appendChild(cv);
  ov.appendChild(stage);
  document.body.appendChild(ov);
}
function applyWidgetWrite(name, value) {
  // walk write-back parity with the DPG face: a watch write whose name
  // matches a widget's name lands on that widget's label, live
  for (const w of GUI.widgets.values())
    if (w.name === String(name)) { w.label = String(value); return true; }
  return false;
}
function watchRefresh() {
  $("watchbody").textContent = Object.entries(WATCHVALS)
    .map(([k, v]) => `${k} = ${JSON.stringify(v)}`).join("\n");
}
async function runFlow() {
  if (!FLOW || !FLOW.syms.size) {
    toast("nothing on the canvas to run"); return; }
  const vars = collectVars();
  for (const s of FLOW.syms.values()) {
    if (s.kind !== "flow_io") continue;
    if (propOf(s, "direction", "in") === "out") continue;
    if (propOf(s, "channel", "variable") !== "variable") continue;
    const addr = String(propOf(s, "address", "") || "").trim();
    if (!addr || vars[addr] !== undefined) continue;
    const v = prompt(`${s.label || "input"} — value for "${addr}":`, "");
    if (v !== null && v !== "") {
      vars[addr] = isNaN(Number(v)) ? v : Number(v);
      addVarRow(addr, v);
    }
  }
  const rep = await api("/api/run",
                        {design: liveDesignDoc(), variables: vars});
  if (rep.error || !rep.lines) {
    $("runlines").textContent = "✗ run failed: " +
      (rep.error || "no report from the engine");
    return;
  }
  WATCHVALS = {};
  for (const [k, v] of Object.entries(vars)) WATCHVALS[k] = v;
  let painted = 0;
  for (const ev of rep.events || []) {
    if (ev[0] === "watch") {
      WATCHVALS[ev[1]] = ev[2];
      if (applyWidgetWrite(ev[1], ev[2])) painted++;
    }
  }
  if (painted) { guiRender(); guiProps(); showAppPreview(); }
  watchRefresh();
  $("runlines").textContent = rep.lines.join("\n") +
    `\n■ RUN complete — ${rep.steps} step(s) · ${painted} ` +
    "GUI widget(s) painted" +
    (painted ? " — the GUI tab wears the result" : "");
}
async function saveFlow() {
  if (!FLOW) return;
  const name = prompt("Save as (.fc):", FLOW.name);
  if (!name) return;
  const doc = {...FLOW.raw};
  doc.flow_symbols = [...FLOW.syms.values()];
  doc[FLOW.edgeKey] = FLOW.edges;
  const res = await api("/api/flow/" + encodeURIComponent(name) +
                        "/save", {flow: doc});
  if (res.saved) { toast(`saved ${res.saved}`); FLOW.name = res.saved;
    loadFlowList(); }
  else toast(res.error || "save failed");
}
document.addEventListener("keydown", ev => {
  if (ev.key === "Delete"
      && !$("tab-flow").classList.contains("hidden")
      && !ev.target.closest("input, [contenteditable]")) delSel();
});

/* ══════════════════ GUI ══════════════════ */
const GUI_CONTAINERS = ["gui_window", "gui_dialog", "gui_box",
  "gui_frame", "gui_notebook", "gui_toolbar", "gui_statusbar",
  "gui_menubar", "gui_headerbar"];
const GUI_WIDGETS = ["gui_button", "gui_label", "gui_entry",
  "gui_checkbox", "gui_tritoggle", "gui_trifilter", "gui_tritstrip"];
const GUI_SIZE = {gui_window: [220, 170], gui_dialog: [200, 160],
  gui_box: [200, 120], gui_frame: [200, 120], gui_notebook: [200, 120],
  gui_toolbar: [240, 34], gui_statusbar: [240, 26],
  gui_menubar: [240, 26], gui_headerbar: [240, 44],
  gui_button: [96, 34], gui_label: [110, 26], gui_entry: [150, 30],
  gui_checkbox: [120, 26], gui_tritoggle: [96, 30],
  gui_trifilter: [120, 30], gui_tritstrip: [260, 34]};
let GUI = {name: null,
           raw: {ternoo_version: "0.3", source_type: "ternoo_design",
                 word_stream: [], symbols: [], edges: [],
                 flow_symbols: [], flow_edges: [], cmd_symbols: [],
                 cmd_edges: [], cell_symbols: [], sheet_regions: [],
                 free_cells: [], sequence: [], groups: {}},
           widgets: new Map(), next: 1};
GUI.zorder = [];
// full adopter set — parity with the DPG organ's CONTAINER_KINDS
const GUI_ADOPTERS = new Set([...GUI_CONTAINERS, "gui_grid", "gui_paned",
  "gui_scrolled", "gui_stack", "gui_expander", "gui_revealer",
  "gui_overlay", "gui_flowbox", "gui_listbox"]);
const GUI_TOPLEVEL = ["gui_window", "gui_dialog"];
const esc = s => String(s).replace(/[<>&]/g,
  m => ({"<": "&lt;", ">": "&gt;", "&": "&amp;"}[m]));
let GSEL = null, gdrag = null;
function gDepth(id, seen) {
  const w = GUI.widgets.get(id);
  if (!w || w.parent_id == null || !GUI.widgets.has(w.parent_id)
      || (seen || []).includes(id)) return 0;
  return 1 + gDepth(w.parent_id, [...(seen || []), id]);
}
function relToAbs() {
  // Tk schema: parented widgets carry centre-offsets from the parent's
  // centre — convert to absolute, parents first
  const ids = [...GUI.widgets.keys()].sort((a, b) => gDepth(a) - gDepth(b));
  for (const id of ids) {
    const w = GUI.widgets.get(id);
    const p = GUI.widgets.get(w.parent_id);
    if (p) {
      w.x = Math.round(p.x + p.w / 2 + w.x - w.w / 2);
      w.y = Math.round(p.y + p.h / 2 + w.y - w.h / 2);
    } else if (w.parent_id != null) w.parent_id = null;
  }
}
function guiSymbolsOut() {
  // inverse transform on the way out — the file keeps the Tk schema
  return [...GUI.widgets.values()].map(w => {
    const out = {...w};
    const p = GUI.widgets.get(w.parent_id);
    if (p) {
      out.x = Math.round(w.x + w.w / 2 - (p.x + p.w / 2));
      out.y = Math.round(w.y + w.h / 2 - (p.y + p.h / 2));
    }
    return out;
  });
}
function zorderSeq() {
  GUI.zorder = (GUI.zorder || []).filter(i => GUI.widgets.has(i));
  for (const i of GUI.widgets.keys())
    if (!GUI.zorder.includes(i)) GUI.zorder.push(i);
  return GUI.zorder;
}
function renderOrder() {
  // roots in stacking sequence, each followed by its children — a child
  // can never be buried under its own container
  const seq = zorderSeq(), kids = new Map();
  for (const i of seq) {
    const p = GUI.widgets.get(i).parent_id;
    const key = (p != null && GUI.widgets.has(p)) ? p : null;
    if (!kids.has(key)) kids.set(key, []);
    kids.get(key).push(i);
  }
  const out = [];
  const walk = i => { out.push(i);
    for (const c of kids.get(i) || []) walk(c); };
  for (const r of kids.get(null) || []) walk(r);
  for (const i of seq) if (!out.includes(i)) out.push(i);
  return out;
}
function descendantsOf(id) {
  const out = [];
  for (const [i, w] of GUI.widgets)
    if (w.parent_id === id) out.push(i, ...descendantsOf(i));
  return out;
}
function adopt(id) {
  // containment by geometry: centre inside a container → child of it;
  // smallest container wins; windows/dialogs adopt, never get adopted
  const w = GUI.widgets.get(id);
  if (GUI_TOPLEVEL.includes(w.kind)) { w.parent_id = null; return; }
  const cx = w.x + w.w / 2, cy = w.y + w.h / 2;
  const kin = new Set([id, ...descendantsOf(id)]);
  let best = null, bestArea = Infinity;
  for (const [oid, o] of GUI.widgets) {
    if (kin.has(oid) || !GUI_ADOPTERS.has(o.kind)) continue;
    if (o.x <= cx && cx <= o.x + o.w && o.y <= cy && cy <= o.y + o.h) {
      const area = o.w * o.h;
      if (area < bestArea) { best = oid; bestArea = area; }
    }
  }
  w.parent_id = best;
}
function buildGuiPalettes() {
  const GLYPH = {gui_window: "▣", gui_dialog: "◳", gui_box: "▢",
    gui_frame: "⬚", gui_notebook: "⧉", gui_toolbar: "▬",
    gui_statusbar: "▁", gui_menubar: "☰", gui_headerbar: "▀",
    gui_button: "▮", gui_label: "𝖠", gui_entry: "⌨",
    gui_checkbox: "☑", gui_tritoggle: "±", gui_trifilter: "⫷",
    gui_tritstrip: "▤"};
  const mk = (kinds, host) => {
    const box = $(host); box.innerHTML = "";
    for (const k of kinds) {
      const b = document.createElement("button");
      b.className = "tool";
        GLYPH.gui_tritoggle = "\u00b1"; GLYPH.gui_trifilter = "\u2af7";
      GLYPH.gui_tritstrip = "\u25a4";
      b.innerHTML = `<span class="glyph">${GLYPH[k] || "▢"}</span> ` +
        k.replace("gui_", "");
      b.onclick = () => guiPlace(k);
      box.appendChild(b);
    }
  };
  mk(GUI_CONTAINERS, "guipal-containers");
  mk(GUI_WIDGETS, "guipal-widgets");
}
function guiPlace(kind) {
  const [w, h] = GUI_SIZE[kind] || [120, 40];
  const id = GUI.next++;
  const wrap = $("guiwrap");
  const x = 60 + (id * 24) % Math.max(80, wrap.clientWidth - w - 120);
  const y = 50 + (id * 18) % Math.max(60, wrap.clientHeight - h - 100);
  GUI.widgets.set(id, {id, kind, x, y, w, h,
    label: kind.replace("gui_", ""), name: `${kind.replace("gui_", "")}_${id}`,
    parent_id: null, layout_mode: "absolute", properties: [],
    signal_ids: {}});
  GUI.zorder.push(id);
  adopt(id);
  GSEL = id; guiRender(); guiProps();
}
function guiScrollHome() {
  let mx = Infinity, my = Infinity;
  for (const w of GUI.widgets.values()) {
    mx = Math.min(mx, w.x); my = Math.min(my, w.y);
  }
  if (mx < Infinity)
    $("guiwrap").scrollTo({left: Math.max(0, mx - 40),
                           top: Math.max(0, my - 40)});
}
function guiRender() {
  const c = $("guicanvas"); c.innerHTML = "";
  let maxx = 900, maxy = 600;
  for (const id of renderOrder()) {
    const w = GUI.widgets.get(id);
    maxx = Math.max(maxx, w.x + w.w + 80);
    maxy = Math.max(maxy, w.y + w.h + 80);
    const d = document.createElement("div");
    d.className = "gw gw-" + w.kind +
      (GUI_ADOPTERS.has(w.kind) ? "" : " gw-leaf") +
      (GSEL === w.id ? " sel" : "");
    d.style.cssText =
      `left:${w.x}px;top:${w.y}px;width:${w.w}px;height:${w.h}px`;
    if (["gui_window", "gui_dialog", "gui_frame", "gui_notebook",
         "gui_box"].includes(w.kind)) {
      d.innerHTML = `<div class="ttl">${esc(w.label)}</div>`;
    } else if (w.kind === "gui_tritoggle" || w.kind === "gui_trifilter") {
      const v = w.value ?? 0;
      d.innerHTML = ["\u2212", "0", "+"].map((g, k) =>
        `<span class="tseg${k - 1 === v ? " on" : ""}">${g}</span>`)
        .join("") + "&nbsp;" + esc(w.label);
    } else if (w.kind === "gui_radio" || w.kind === "gui_checkbox") {
      d.innerHTML = `<span class="mark">` +
        (w.kind === "gui_radio" ? "◉" : "☐") + `</span>&nbsp;` +
        esc(w.label);
    } else {
      d.textContent = w.label;
    }
    d.addEventListener("mousedown", e => {
      e.stopPropagation(); e.preventDefault();
      GSEL = w.id;
      const fam = [w.id, ...descendantsOf(w.id)];
      gdrag = {id: w.id, mx: e.clientX, my: e.clientY,
               starts: new Map(fam.map(i => {
                 const f = GUI.widgets.get(i); return [i, [f.x, f.y]]; }))};
      guiRender(); guiProps();
    });
    d.addEventListener("dblclick", () => {
      const nl = prompt("Label:", w.label);
      if (nl !== null) { w.label = nl; guiRender(); guiProps(); }
    });
    c.appendChild(d);
  }
  c.style.width = maxx + "px"; c.style.height = maxy + "px";
  $("guititle").textContent = (GUI.name || "new design") +
    ` — ${GUI.widgets.size} widget(s)` +
    ($("guititle").dataset.source === "words"
      ? " · rendered from the word stream" : "");
}
window.addEventListener("mousemove", e => {
  if (!gdrag) return;
  const dx = e.clientX - gdrag.mx, dy = e.clientY - gdrag.my;
  for (const [i, [sx, sy]] of gdrag.starts) {
    const f = GUI.widgets.get(i);
    if (f) { f.x = sx + dx; f.y = sy + dy; }
  }
  guiRender();
});
window.addEventListener("mouseup", () => {
  if (gdrag) {                          // adoption happens on the DROP
    const moved = GUI.widgets.get(gdrag.id);
    if (moved) { adopt(gdrag.id); guiRender(); guiProps(); }
  }
  gdrag = null;
});
function guiProps() {
  const pb = $("guiprops");
  if (GSEL === null || !GUI.widgets.has(GSEL)) {
    pb.innerHTML = '<div class="hint">select a widget</div>'; return;
  }
  const w = GUI.widgets.get(GSEL);
  pb.innerHTML = "";
  pb.appendChild(propRow("kind", w.kind.replace("gui_", ""), null, true));
  pb.appendChild(propRow("name", w.name, v => { w.name = v; }));
  pb.appendChild(propRow("label", w.label, v => {
    w.label = v; guiRender(); }));
  for (const f of ["x", "y", "w", "h"])
    pb.appendChild(propRow(f, w[f], v => {
      const n = parseInt(v, 10);
      if (!isNaN(n)) { w[f] = n; guiRender(); } }));
  const par = GUI.widgets.get(w.parent_id);
  pb.appendChild(propRow("parent",
    par ? (par.name || par.label) : "(top level)", null, true));
  propListEditor(pb, w, () => { guiRender(); guiProps(); });
}
function guiDelete() {
  if (GSEL === null) return;
  const w = GUI.widgets.get(GSEL);
  for (const c of GUI.widgets.values())      // children go to grandparent
    if (c.parent_id === GSEL) c.parent_id = w ? w.parent_id : null;
  GUI.widgets.delete(GSEL); GSEL = null; guiRender(); guiProps();
}
function guiNew() {
  GUI.widgets.clear(); GUI.name = null; GUI.next = 1; GSEL = null;
  guiRender(); guiProps();
}
async function guiLoadList() {
  const names = await api("/api/guis");
  const tree = $("guitree");
  tree.innerHTML = names.length ? "" :
    '<div class="hint">no .gui designs aboard yet — build the first</div>';
  for (const n of names) {
    const d = document.createElement("div");
    d.className = "treeitem"; d.textContent = n;
    d.onclick = () => guiOpen(n);
    tree.appendChild(d);
  }
}
async function guiOpen(name) {
  const raw = await api("/api/gui/" + encodeURIComponent(name));
  GUI.raw = raw; GUI.name = name; GUI.widgets = new Map();
  let maxid = 0;
  for (const s of raw.symbols || []) {
    GUI.widgets.set(s.id, {...s});
    maxid = Math.max(maxid, s.id);
  }
  relToAbs();
  GUI.zorder = (raw.sequence || []).map(Number)
    .filter(i => GUI.widgets.has(i));
  zorderSeq();
  GUI.next = maxid + 1; GSEL = null;
  guiRender(); guiProps(); guiScrollHome();
}
async function guiSave() {
  const name = prompt("Save as (.gui):", GUI.name || "untitled.gui");
  if (!name) return;
  const doc = {...GUI.raw};
  doc.source_file = name;
  doc.symbols = guiSymbolsOut();
  doc.edges = doc.edges || [];
  doc.sequence = zorderSeq().slice();
  doc.tgui_meta = {widget_count: GUI.widgets.size,
                   edge_count: (doc.edges || []).length,
                   flow_symbol_count: 0, flow_edge_count: 0};
  const res = await api("/api/gui/" + encodeURIComponent(name) + "/save",
                        {design: doc});
  if (res.saved) { toast(`saved ${res.saved}`); GUI.name = res.saved;
    guiLoadList(); }
  else toast(res.error || "save failed");
}

/* ══════════════════ SHEET ══════════════════ */
let NROWS = 24, NCOLS = 10;
let SHEET = {name: null, raw: new Map()};
let FOCUS = null;
function colName(c) {
  return c < 26 ? String.fromCharCode(65 + c)
    : String.fromCharCode(64 + Math.floor(c / 26)) +
      String.fromCharCode(65 + (c % 26));
}
function buildGrid() {
  let mr = 0, mc = 0;                    // the grid grows to fit the data
  for (const rc of SHEET.raw.keys()) {
    const [r, c2] = rc.split(",").map(Number);
    mr = Math.max(mr, r); mc = Math.max(mc, c2);
  }
  NROWS = Math.max(24, mr + 4); NCOLS = Math.max(10, mc + 2);
  const g = $("grid"); g.innerHTML = "";
  const thead = document.createElement("thead");
  let hr = "<tr><th></th>";
  for (let c = 0; c < NCOLS; c++) hr += `<th>${colName(c)}</th>`;
  thead.innerHTML = hr + "</tr>"; g.appendChild(thead);
  const tb = document.createElement("tbody");
  for (let r = 0; r < NROWS; r++) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<th>${r + 1}</th>`;
    for (let c = 0; c < NCOLS; c++) {
      const td = document.createElement("td");
      const inp = document.createElement("input");
      inp.dataset.rc = `${r},${c}`;
      inp.addEventListener("focus", () => { FOCUS = inp.dataset.rc;
        inp.value = SHEET.raw.get(FOCUS) || "";
        $("fxbar").value = inp.value; });
      inp.addEventListener("blur", () => commitCell(inp));
      inp.addEventListener("keydown", ev => {
        if (ev.key === "Enter") { commitCell(inp);
          const [r2, c2] = inp.dataset.rc.split(",").map(Number);
          document.querySelector(
            `input[data-rc="${Math.min(r2 + 1, NROWS - 1)},${c2}"]`)
            ?.focus();
        }});
      td.appendChild(inp); tr.appendChild(td);
    }
    tb.appendChild(tr);
  }
  g.appendChild(tb);
}
function commitCell(inp) {
  const rc = inp.dataset.rc, text = inp.value.trim();
  if (text) SHEET.raw.set(rc, text); else SHEET.raw.delete(rc);
  evalSheet();
}
function fxCommit() {
  if (!FOCUS) return;
  const inp = document.querySelector(`input[data-rc="${FOCUS}"]`);
  inp.value = $("fxbar").value; commitCell(inp);
}
async function evalSheet() {
  const cells = [...SHEET.raw.entries()].map(([rc, value]) => {
    const [row, col] = rc.split(",").map(Number);
    return {row, col, value};
  });
  const rep = await api("/api/sheet/eval", {cells});
  document.querySelectorAll("#grid td").forEach(td =>
    td.classList.remove("fx", "err"));
  for (const inp of document.querySelectorAll("#grid td input")) {
    const rc = inp.dataset.rc;
    if (rc === FOCUS && document.activeElement === inp) continue;
    const raw = SHEET.raw.get(rc);
    if (!raw) { inp.value = ""; continue; }
    const isFx = raw.startsWith("=");
    if (isFx) inp.parentElement.classList.add("fx");
    if (rep.errors[rc] !== undefined) {
      inp.parentElement.classList.add("err");
      inp.value = rep.errors[rc];
    } else if (isFx) {
      inp.value = rep.values[rc] !== undefined ? rep.values[rc] : raw;
    } else inp.value = raw;
  }
  $("sheetstatus").textContent =
    `${SHEET.raw.size} cells · engine: sheet_formula (live)`;
}
async function loadSheetList() {
  const names = await api("/api/sheets");
  const pick = $("sheetpick");
  pick.innerHTML = '<option value="">— sheets aboard —</option>' +
    names.map(n => `<option>${n}</option>`).join("");
}
function newSheet() { SHEET = {name: null, raw: new Map()}; buildGrid();
  $("sheetstatus").textContent = "new sheet"; }
async function openSheet(name) {
  if (!name) return;
  const d = await api("/api/sheet/" + encodeURIComponent(name));
  SHEET = {name, raw: new Map()};
  for (const c of d.c || [])
    SHEET.raw.set(`${c.row},${c.col}`, String(c.value ?? ""));
  buildGrid(); evalSheet();
}
async function saveSheet() {
  const name = prompt("Save as (.sheet):", SHEET.name || "untitled.sheet");
  if (!name) return;
  const c = cellSymbolsOut();
  const res = await api("/api/sheet/" + encodeURIComponent(name) +
                        "/save", {sheet: {c, r: [], f: [], n: c.length + 1}});
  if (res.saved) { toast(`saved ${res.saved}`); SHEET.name = res.saved;
    loadSheetList(); }
  else toast(res.error || "save failed");
}

/* ══════════════════ CONNECTORS ══════════════════ */
let cview = {x: 0, y: 0, k: 1};
let CONN = {name: "pipeline.fc", syms: new Map(), edges: [], next: 1};
let CSEL = null, CWIRE = null, cdrag = null, CTOOL = "select";
function cApply() {
  $("cworld").setAttribute("transform",
    `translate(${cview.x},${cview.y}) scale(${cview.k})`);
}
function czoomBy(f) { cview.k = Math.max(.3, Math.min(3, cview.k * f));
  cApply(); }
function connTool(t) {
  CTOOL = t; CWIRE = (t === "wire") ? {src: null} : null;
  for (const id of ["c-select", "c-wire", "c-delete"])
    $(id).classList.toggle("arm", id === "c-" + t);
}
(() => {
  let pan = null;
  $("connwrap").addEventListener("mousedown", e => {
    if (e.target.closest(".zoomctl")) return;
    pan = {mx: e.clientX, my: e.clientY, vx: cview.x, vy: cview.y};
  });
  window.addEventListener("mousemove", e => {
    if (cdrag) {
      const s = CONN.syms.get(cdrag.id);
      s.x = Math.round(cdrag.sx + (e.clientX - cdrag.mx) / cview.k);
      s.y = Math.round(cdrag.sy + (e.clientY - cdrag.my) / cview.k);
      connRender(); return;
    }
    if (!pan) return;
    cview.x = pan.vx + e.clientX - pan.mx;
    cview.y = pan.vy + e.clientY - pan.my; cApply();
  });
  window.addEventListener("mouseup", () => { pan = null; cdrag = null; });
  $("connwrap").addEventListener("wheel", e => {
    e.preventDefault(); czoomBy(e.deltaY < 0 ? 1.12 : 1 / 1.12);
  }, {passive: false});
})();
let CMDSPECS = {};
async function buildCmdPalette() {
  const specs = await api("/api/commands");
  CMDSPECS = {};
  const names = [];
  for (const sp of specs || []) {
    if (typeof sp === "string") { names.push(sp); continue; }
    CMDSPECS[sp.name] = sp; names.push(sp.name);
  }
  const fams = {};
  for (const n of names) {
    const fam = n.split("_")[1] || "misc";
    (fams[fam] = fams[fam] || []).push(n);
  }
  const pal = $("cmdpal"); pal.innerHTML = "";
  for (const fam of Object.keys(fams).sort()) {
    const h = document.createElement("div");
    h.className = "phead" +
      (["text", "math"].includes(fam) ? " open" : "");
    h.innerHTML = `<span class="chev">▶</span> ${fam.toUpperCase()}`;
    h.onclick = () => togglePanel(h);
    const b = document.createElement("div");
    b.className = "pbody";
    if (!h.classList.contains("open")) b.style.display = "none";
    for (const k of fams[fam]) {
      const btn = document.createElement("button");
      btn.className = "tool";
      btn.innerHTML =
        `<span class="glyph">⚙</span> ${k.replace("cmd_", "")}`;
      btn.onclick = () => connPlace(k);
      b.appendChild(btn);
    }
    pal.appendChild(h); pal.appendChild(b);
  }
}
function connPlace(kind) {
  const id = CONN.next++;
  const w = $("connwrap").clientWidth, h = $("connwrap").clientHeight;
  const cx = (w / 2 - cview.x) / cview.k, cy = (h / 2 - cview.y) / cview.k;
  CONN.syms.set(id, {id, kind, x: Math.round(cx - 70 + (id % 5) * 16),
    y: Math.round(cy - 24 + (id % 7) * 12), w: 140, h: 44,
    label: kind.replace("cmd_", ""), name: `${kind}_${id}`,
    properties: []});
  CSEL = id; connRender(); connProps();
}
function cel(tag, attrs) {
  const n = document.createElementNS(SVGNS, tag);
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
  $("cworld").appendChild(n);
  return n;
}
function connRender() {
  $("cworld").innerHTML = "";
  CONN.edges.forEach((e, i) => {
    const a = CONN.syms.get(e.src), b = CONN.syms.get(e.dst);
    if (!a || !b) return;
    const p = cel("path", {d: edgePath(a, b, []), fill: "none",
      stroke: "#8fa8d0", "stroke-width": 2.2,
      "marker-end": "url(#arrow)", style: "cursor:pointer"});
    p.addEventListener("mousedown", ev => { ev.stopPropagation();
      if (CTOOL === "delete") { CONN.edges.splice(i, 1); connRender(); }});
  });
  for (const s of CONN.syms.values()) {
    const famRaw = (s.kind || "").split("_")[1];
    const fam = ["text", "math", "list"].includes(famRaw) ? famRaw
              : "misc";
    const r = cel("rect", {x: s.x, y: s.y, width: s.w, height: s.h,
      rx: 12, fill: `url(#g-cmd-${fam})`, stroke: "#0d0d14",
      "stroke-width": 1.5, filter: "url(#shadow)", class: "sym-hit" +
        (CSEL === s.id ? " sym-sel" : "")});
    r.addEventListener("mousedown", e => {
      e.stopPropagation();
      if (CTOOL === "wire") { connWireClick(s.id); return; }
      if (CTOOL === "delete") {
        CONN.syms.delete(s.id);
        CONN.edges = CONN.edges.filter(x =>
          x.src !== s.id && x.dst !== s.id);
        connRender(); connProps(); return;
      }
      CSEL = s.id;
      cdrag = {id: s.id, mx: e.clientX, my: e.clientY,
               sx: s.x, sy: s.y};
      connRender(); connProps();
    });
    const t = cel("text", {x: s.x + s.w / 2, y: s.y + s.h / 2 - 3,
                           class: "sym-label"});
    t.textContent = s.label;
    const ot = (CMDSPECS[s.kind] || {}).output;
    if (ot) {
      const t2 = cel("text", {x: s.x + s.w / 2, y: s.y + s.h - 7,
                              class: "sym-sub"});
      t2.textContent = "→ " + ot;
    }
    cel("circle", {cx: s.x, cy: s.y + s.h / 2, r: 3.5,
      fill: "#8fa8d0", stroke: "#0d0d14", "stroke-width": 1});
    cel("circle", {cx: s.x + s.w, cy: s.y + s.h / 2, r: 3.5,
      fill: "#8fa8d0", stroke: "#0d0d14", "stroke-width": 1});
  }
  $("conntitle").textContent =
    `${CONN.name} — ${CONN.syms.size} commands, ${CONN.edges.length} pipes`;
}
function connWireClick(id) {
  if (!CWIRE.src) { CWIRE.src = id; return; }
  if (CWIRE.src !== id) {
    const spec = CMDSPECS[(CONN.syms.get(id) || {}).kind] || {};
    const ps = (spec.params || []).map(p => p.name);
    let dst_param = ps[0] || "";
    if (ps.length > 1) {
      const pick = prompt(
        `Feed which input socket? (${ps.join(", ")})`, ps[0]);
      if (pick === null) { CWIRE = {src: null}; connRender(); return; }
      if (ps.includes(pick.trim())) dst_param = pick.trim();
    }
    CONN.edges.push({src: CWIRE.src, dst: id, privilege: 0,
      call_style: 0, return_type: 1, seg_idx: 0, offset: 0,
      waypoints: [], condition: "", dst_param});
  }
  CWIRE = {src: null}; connRender();
}
function connProps() {
  const pb = $("connprops");
  if (CSEL === null || !CONN.syms.has(CSEL)) {
    pb.innerHTML = '<div class="hint">select a command node</div>';
    return;
  }
  const s = CONN.syms.get(CSEL);
  pb.innerHTML = "";
  const spec = CMDSPECS[s.kind] || {};
  pb.appendChild(propRow("cmd", s.kind, null, true));
  pb.appendChild(propRow("label", s.label, v => {
    s.label = v; connRender(); }));
  pb.appendChild(propRow("name", s.name, v => { s.name = v; }));
  if (spec.output)
    pb.appendChild(propRow("output →", spec.output, null, true));
  const piped = {};
  for (const e of CONN.edges)
    if (e.dst === CSEL) {
      const src = CONN.syms.get(e.src);
      piped[e.dst_param || ((spec.params || [{}])[0] || {}).name] =
        src ? (src.label || src.kind) : e.src;
    }
  for (const p of spec.params || []) {
    if (piped[p.name] !== undefined) {
      pb.appendChild(propRow(`${p.name} [${p.type}]`,
        `⇐ pipe from ${piped[p.name]}`, null, true));
      continue;
    }
    s.input_bindings = s.input_bindings || {};
    const b = s.input_bindings[p.name] =
      s.input_bindings[p.name] || {kind: "constant", value: ""};
    pb.appendChild(propRow(`${p.name} [${p.type}]`, b.value,
      v => { b.value = v; }));
  }
}
async function connRun() {
  if (!CONN.syms.size) { toast("place commands first"); return; }
  const rep = await api("/api/pipeline/run",
    {cmd_symbols: [...CONN.syms.values()], cmd_edges: CONN.edges});
  if (rep.error || !rep.lines) {
    $("connlines").textContent = "✗ pipeline failed: " +
      (rep.error || "no report"); return; }
  const outs = Object.entries(rep.outputs || {}).map(([i, v]) =>
    `▸ ${(CONN.syms.get(Number(i)) || {}).label || i} ⇒ ` +
    JSON.stringify(v));
  $("connlines").textContent = rep.lines.join("\n") +
    (outs.length ? "\n— pipeline outputs —\n" + outs.join("\n") : "");
}
async function connSave() {
  const name = prompt("Save pipeline as (.fc):", CONN.name);
  if (!name) return;
  const doc = {ternoo_version: "0.3", source_type: "ternoo_design",
    source_file: name, symbols: [], edges: [],
    flow_symbols: [...CONN.syms.values()], flow_edges: CONN.edges,
    cmd_symbols: [...CONN.syms.values()], cmd_edges: CONN.edges,
    sequence: [...CONN.syms.keys()], groups: {},
    tgui_meta: {widget_count: 0, edge_count: 0,
                flow_symbol_count: CONN.syms.size,
                flow_edge_count: CONN.edges.length}};
  const res = await api("/api/flow/" + encodeURIComponent(name) +
                        "/save", {flow: doc});
  if (res.saved) { toast(`saved ${res.saved}`); CONN.name = res.saved;
    loadFlowList(); }
  else toast(res.error || "save failed");
}

/* ══════════════════ AUTHOR ══════════════════ */
function cmd(c) { document.execCommand(c, false, null);
  $("docbody").focus(); }
function blockFmt(t) { document.execCommand("formatBlock", false, t);
  $("docbody").focus(); }
function makeLink() { const u = prompt("Link target (https://…):");
  if (u) document.execCommand("createLink", false, u); }
function inlineCode() {
  const sel = window.getSelection();
  if (!sel.rangeCount || sel.isCollapsed) return;
  try { const c = document.createElement("code");
        sel.getRangeAt(0).surroundContents(c); }
  catch (e) { document.execCommand("insertHTML", false,
    "<code>" + sel.toString().replace(/[<>&]/g,
      m => ({"<": "&lt;", ">": "&gt;", "&": "&amp;"}[m])) + "</code>"); }
}
async function sendMail() {
  const res = await api("/api/send", {to: $("to").value,
    subject: $("subject").value, html: $("docbody").innerHTML});
  if (res.dropped) toast(`dropped ${res.dropped} — the watcher has it`);
  else toast(res.error || "send failed");
}
async function mdOfBody() {
  return (await api("/api/convert",
                    {html: $("docbody").innerHTML})).md;
}
async function previewMd() { alert(await mdOfBody()); }
async function saveMd() {
  download(($("subject").value || "terndoc") + ".md",
           await mdOfBody(), "text/markdown");
}
async function saveHtml() {
  const md = await mdOfBody();
  const r = await api("/api/render", {md});
  download(($("subject").value || "terndoc") + ".html",
    "<!DOCTYPE html><html><head><meta charset='utf-8'></head><body>" +
    r.html + "</body></html>", "text/html");
}
function download(name, text, type) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([text], {type}));
  a.download = name; a.click(); URL.revokeObjectURL(a.href);
}
function loadMd() { $("filepick").click(); }
$("filepick").addEventListener("change", async ev => {
  const f = ev.target.files[0]; if (!f) return;
  const r = await api("/api/render", {md: await f.text()});
  $("docbody").innerHTML = r.html; toast(`opened ${f.name}`);
});
document.addEventListener("keydown", ev => {
  if (!(ev.ctrlKey || ev.metaKey)) return;
  if (!ev.target.closest("#docbody")) return;
  const k = ev.key.toLowerCase();
  if (k === "b") { ev.preventDefault(); cmd("bold"); }
  if (k === "i") { ev.preventDefault(); cmd("italic"); }
});

/* boot */
for (const pick of document.querySelectorAll("select.designpick"))
  pick.addEventListener("change", () => {
    if (pick.value) openDesign(pick.value);   // pick IS open, every tab
  });
loadFlowList(); buildGrid(); loadSheetList();
buildGuiPalettes(); guiLoadList(); guiRender();
api("/api/status").then(st => { window.__BUILD = st.build || "";
  $("statusline").textContent += st.build ? ` · build ${st.build}` : "";
}).catch(() => {});
buildCmdPalette(); connRender();
