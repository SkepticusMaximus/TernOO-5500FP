"use strict";
/* TernOO-FlowCode web face — mechanics for all tabs.
   Engine-sovereign: every computation happens server-side in the real
   organs (walker, sheet_formula, command registry, TernDoc). */

const $ = id => document.getElementById(id);
const toast = m => { const t = $("toast"); t.textContent = m;
  t.style.opacity = 1; setTimeout(() => t.style.opacity = 0, 2600); };
async function api(path, body) {
  const r = await fetch(path, body ?
    {method: "POST", body: JSON.stringify(body)} : {});
  return r.json();
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
  const pick = $("designpick");
  pick.innerHTML = '<option value="">— designs aboard —</option>' +
    designs.map(n => `<option>${n}</option>`).join("");
  $("statusline").textContent =
    `on TernOO · ${designs.length} designs aboard`;
}
async function openDesign(name) {
  if (!name) { toast("pick a design first"); return; }
  const raw = await api("/api/design/" + encodeURIComponent(name));
  if (raw.error) { toast(raw.error); return; }
  DOC = {name, raw};
  const syms = new Map();
  for (const s of raw.flow_symbols || []) syms.set(s.id, s);
  FLOW = {name, raw, syms,
          edges: raw.flow_edges || raw.edges || [],
          edgeKey: raw.flow_edges ? "flow_edges" : "edges"};
  SEL = null; SELEDGE = null; render(); fitView(); showProps();
  GUI.widgets = new Map(); let maxid = 0;
  for (const s of raw.symbols || []) {
    if ((s.kind || "").startsWith("gui_")) {
      GUI.widgets.set(s.id, s); maxid = Math.max(maxid, s.id);
    }
  }
  GUI.next = maxid + 1; GUI.name = name; GUI.raw = raw;
  GSEL = null; guiRender(); guiProps();
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
  toast(`opened ${name} — families distributed to every tab`);
}
function closeDesign() {
  DOC = null;
  FLOW = null; SEL = null; SELEDGE = null;
  $("world").innerHTML = "";
  $("flowtitle").textContent = "no design open — File ▸ Open";
  showProps();
  GUI.widgets.clear(); GUI.name = null; GSEL = null;
  guiRender(); guiProps();
  SHEET = {name: null, raw: new Map()}; buildGrid();
  CONN = {name: "pipeline.fc", syms: new Map(), edges: [], next: 1};
  connRender(); connProps();
  $("runlines").textContent = "";
  $("watchbody").textContent = "";
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
  doc.symbols = [...GUI.widgets.values()];
  doc.cell_symbols = [...SHEET.raw.entries()].map(([rc, value], i) => {
    const [row, col] = rc.split(",").map(Number);
    return {id: i + 1, row, col, value,
            kind: value.startsWith("=") ? "cell_formula" : "cell_value",
            label: colName(col) + (row + 1), properties: []};
  });
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
async function runFlow() {
  if (!FLOW) { toast("open a flow first"); return; }
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
  const rep = await api("/api/flow/" + encodeURIComponent(FLOW.name) +
                        "/run", {variables: vars});
  $("runlines").textContent = rep.lines.join("\n");
  const w = $("watchbody");
  w.textContent = Object.entries(rep.vars || {})
    .map(([k, v]) => `${k} = ${JSON.stringify(v)}`).join("\n");
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
  "gui_checkbox"];
const GUI_SIZE = {gui_window: [220, 170], gui_dialog: [200, 160],
  gui_box: [200, 120], gui_frame: [200, 120], gui_notebook: [200, 120],
  gui_toolbar: [240, 34], gui_statusbar: [240, 26],
  gui_menubar: [240, 26], gui_headerbar: [240, 44],
  gui_button: [96, 34], gui_label: [110, 26], gui_entry: [150, 30],
  gui_checkbox: [120, 26]};
let GUI = {name: null,
           raw: {ternoo_version: "0.3", source_type: "ternoo_design",
                 word_stream: [], symbols: [], edges: [],
                 flow_symbols: [], flow_edges: [], cmd_symbols: [],
                 cmd_edges: [], cell_symbols: [], sheet_regions: [],
                 free_cells: [], sequence: [], groups: {}},
           widgets: new Map(), next: 1};
let GSEL = null, gdrag = null;
function buildGuiPalettes() {
  const mk = (kinds, host) => {
    const box = $(host); box.innerHTML = "";
    for (const k of kinds) {
      const b = document.createElement("button");
      b.className = "tool";
      b.innerHTML = `<span class="glyph">▢</span> ${k.replace("gui_", "")}`;
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
  GSEL = id; guiRender(); guiProps();
}
function guiRender() {
  const c = $("guicanvas"); c.innerHTML = "";
  const order = [...GUI.widgets.values()]
    .sort((a, b) => (GUI_CONTAINERS.includes(b.kind) ? 1 : 0) -
                    (GUI_CONTAINERS.includes(a.kind) ? 1 : 0));
  for (const w of order) {
    const d = document.createElement("div");
    d.className = "gw gw-" + w.kind + (GSEL === w.id ? " sel" : "");
    d.style.cssText =
      `left:${w.x}px;top:${w.y}px;width:${w.w}px;height:${w.h}px`;
    if (["gui_window", "gui_dialog", "gui_frame", "gui_notebook",
         "gui_box"].includes(w.kind)) {
      d.innerHTML = `<div class="ttl">${w.label}</div>`;
    } else {
      d.textContent = w.label;
    }
    d.addEventListener("mousedown", e => {
      e.stopPropagation(); e.preventDefault();
      GSEL = w.id;
      gdrag = {id: w.id, mx: e.clientX, my: e.clientY, sx: w.x, sy: w.y};
      guiRender(); guiProps();
    });
    d.addEventListener("dblclick", () => {
      const nl = prompt("Label:", w.label);
      if (nl !== null) { w.label = nl; guiRender(); guiProps(); }
    });
    c.appendChild(d);
  }
  $("guititle").textContent = (GUI.name || "new design") +
    ` — ${GUI.widgets.size} widget(s)`;
}
window.addEventListener("mousemove", e => {
  if (!gdrag) return;
  const w = GUI.widgets.get(gdrag.id);
  w.x = Math.max(0, gdrag.sx + e.clientX - gdrag.mx);
  w.y = Math.max(0, gdrag.sy + e.clientY - gdrag.my);
  guiRender();
});
window.addEventListener("mouseup", () => { gdrag = null; });
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
}
function guiDelete() {
  if (GSEL === null) return;
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
    GUI.widgets.set(s.id, s);
    maxid = Math.max(maxid, s.id);
  }
  GUI.next = maxid + 1; GSEL = null;
  guiRender(); guiProps();
}
async function guiSave() {
  const name = prompt("Save as (.gui):", GUI.name || "untitled.gui");
  if (!name) return;
  const doc = {...GUI.raw};
  doc.source_file = name;
  doc.symbols = [...GUI.widgets.values()];
  doc.edges = doc.edges || [];
  doc.sequence = [...GUI.widgets.keys()];
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
const NROWS = 24, NCOLS = 10;
let SHEET = {name: null, raw: new Map()};
let FOCUS = null;
function colName(c) { return String.fromCharCode(65 + c); }
function buildGrid() {
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
  const c = [...SHEET.raw.entries()].map(([rc, value], i) => {
    const [row, col] = rc.split(",").map(Number);
    return {id: i + 1, row, col, value,
            kind: value.startsWith("=") ? "cell_formula" : "cell_value",
            label: colName(col) + (row + 1), properties: []};
  });
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
async function buildCmdPalette() {
  const names = await api("/api/commands");
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
    const r = cel("rect", {x: s.x, y: s.y, width: s.w, height: s.h,
      rx: 12, fill: "url(#g-cmd)", stroke: "#0d0d14",
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
    const t = cel("text", {x: s.x + s.w / 2, y: s.y + s.h / 2,
                           class: "sym-label"});
    t.textContent = s.label;
  }
  $("conntitle").textContent =
    `${CONN.name} — ${CONN.syms.size} commands, ${CONN.edges.length} pipes`;
}
function connWireClick(id) {
  if (!CWIRE.src) { CWIRE.src = id; return; }
  if (CWIRE.src !== id)
    CONN.edges.push({src: CWIRE.src, dst: id, privilege: 0,
      call_style: 0, return_type: 1, seg_idx: 0, offset: 0,
      waypoints: [], condition: ""});
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
  pb.appendChild(propRow("cmd", s.kind, null, true));
  pb.appendChild(propRow("label", s.label, v => {
    s.label = v; connRender(); }));
  pb.appendChild(propRow("name", s.name, v => { s.name = v; }));
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
loadFlowList(); buildGrid(); loadSheetList();
buildGuiPalettes(); guiLoadList(); guiRender();
buildCmdPalette(); connRender();
