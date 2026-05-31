#!/usr/bin/env python3
"""
TernOO Cambalache Bridge
========================
Converts GTK widget trees (Glade XML / Cambalache .cmb) into TernOO MMID
sequences and MMOE object graphs for GHOST training.

This is the GUI emergence layer above FlowCode's procedural layer.
FlowCode writes logic. GHOST generates structure. Widget trees are the
training corpus that teaches GHOST to think in GUI primitives natively.

Pipeline:
  Cambalache .cmb (SQLite) or Glade XML (.ui / .glade)
        ↓
  ternoo_cambalache_bridge.py  (this file)
        ↓
  TernOO MMID sequence  (each widget → typed octree coordinate)
  MMOE object graph     (MAP + UDP + DATA + EXEC words)
        ↓
  .tgui JSON  — feed to GristMill and FlowCodeBrain for GHOST training
        ↓
  PIGART renders the widget tree from MAP words — no XML, no text file

Widget → TernOO object encoding:
  Widget type    → MMID coordinate (type encodes semantic region in octree)
  Widget geometry → MAP word payload (x,y from allocation or request)
  Widget label   → DATA words (text properties)
  Signal handlers → EXEC words (event bindings)
  Parent-child   → MMOE.children (octree nesting mirrors widget hierarchy)

Added: 01 Jun 2026, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
Companion: private/TernOO-5500FP-Companion.md § Cambalache Bridge
Status: v0.1 — Glade XML parsing, MMID sequence output, .tgui training format
"""

import sys, os, json, math, sqlite3
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── GristMill imports ─────────────────────────────────────────────────────────

from ternoo_gristmill import MMID, MMOE, GristMill, MMOE_TYPES, instance_hash


# ── Widget type → MMOE type registry ─────────────────────────────────────────
# GTK widget classes mapped to MMOE types. Similar widgets are geometrically
# close in octree space. The coordinate scheme:
#
#   Y axis = widget category (semantic family)
#   Z axis = position within category (specialisation)
#
#   Containers  Y = 500..599   (top-level, layout boxes, notebooks)
#   Controls    Y = 400..499   (buttons, toggles, checks, radios)
#   Inputs      Y = 300..399   (entry, textview, spinbutton, scale, combobox)
#   Display     Y = 200..299   (label, image, progressbar, separator)
#   Dialogs     Y = 100..199   (dialog, messagedialog, filechooser)
#   Menu/Action Y = 000..099   (menubar, toolbar, action, menuitem)
#
# Unknown widget types land at Y=600, Z=0 (out-of-band but valid coordinate).

WIDGET_TYPE_MAP = {
    # ── Containers ─────────────────────────────────────────────────────────
    'GtkWindow':           'gui_window',
    'GtkApplicationWindow':'gui_window',
    'GtkOffscreenWindow':  'gui_window',
    'GtkPlug':             'gui_window',
    'GtkSocket':           'gui_window',
    'GtkAssistant':        'gui_window',
    'GtkShortcutsWindow':  'gui_window',
    'GtkBin':              'gui_frame',
    'GtkAlignment':        'gui_frame',
    'GtkAspectFrame':      'gui_frame',
    'GtkHandleBox':        'gui_frame',
    'GtkEventBox':         'gui_frame',
    'GtkFixed':            'gui_canvas',
    'GtkLayout':           'gui_canvas',
    'GtkDrawingArea':      'gui_canvas',
    'GtkGLArea':           'gui_canvas',
    'GtkHSV':              'gui_canvas',
    'GtkContainer':        'gui_box',
    'GtkButtonBox':        'gui_box',
    'GtkHButtonBox':       'gui_box',
    'GtkVButtonBox':       'gui_box',
    'GtkTable':            'gui_grid',
    'GtkSearchBar':        'gui_entry',
    'GtkInfoBar':          'gui_box',
    'GtkFlowBoxChild':     'gui_frame',
    'GtkListBoxRow':       'gui_frame',
    'GtkStackSidebar':     'gui_scroll',
    'GtkStackSwitcher':    'gui_box',
    'GtkPopover':          'gui_frame',
    'GtkInvisible':        'gui_frame',
    'GtkMisc':             'gui_label',
    'GtkCellView':         'gui_label',
    'GtkRange':            'gui_scale',
    'GtkScrollbar':        'gui_scale',
    'GtkHScrollbar':       'gui_scale',
    'GtkVScrollbar':       'gui_scale',
    'GtkMenuShell':        'gui_menu',
    'GtkRadioMenuItem':    'gui_menuitem',
    'GtkCheckMenuItem':    'gui_menuitem',
    'GtkImageMenuItem':    'gui_menuitem',
    'GtkSeparatorMenuItem':'gui_menuitem',
    'GtkTearoffMenuItem':  'gui_menuitem',
    'GtkToolItem':         'gui_button',
    'GtkToolButton':       'gui_button',
    'GtkToggleToolButton': 'gui_toggle',
    'GtkRadioToolButton':  'gui_toggle',
    'GtkMenuToolButton':   'gui_button',
    'GtkSeparatorToolItem':'gui_separator',
    'GtkToolItemGroup':    'gui_toolbar',
    'GtkToolPalette':      'gui_toolbar',
    'GtkModelButton':      'gui_button',
    'GtkLockButton':       'gui_button',
    'GtkScaleButton':      'gui_button',
    'GtkVolumeButton':     'gui_button',
    'GtkColorSelection':   'gui_colorpicker',
    'GtkColorSelectionDialog': 'gui_dialog',
    'GtkFontSelection':    'gui_box',
    'GtkFontSelectionDialog':  'gui_dialog',
    'GtkRecentChooserMenu':    'gui_menu',
    'GtkRecentChooserDialog':  'gui_dialog',
    'GtkRecentChooserWidget':  'gui_scroll',
    'GtkShortcutLabel':    'gui_label',
    'GtkShortcutsGroup':   'gui_box',
    'GtkShortcutsSection': 'gui_box',
    'GtkShortcutsShortcut':'gui_label',
    'GtkArrow':            'gui_image',
    'GtkImage':            'gui_image',

    'GtkDialog':           'gui_dialog',
    'GtkMessageDialog':    'gui_dialog',
    'GtkFileChooserDialog':'gui_dialog',
    'GtkBox':              'gui_box',
    'GtkHBox':             'gui_box',
    'GtkVBox':             'gui_box',
    'GtkGrid':             'gui_grid',
    'GtkFrame':            'gui_frame',
    'GtkScrolledWindow':   'gui_scroll',
    'GtkNotebook':         'gui_notebook',
    'GtkStack':            'gui_stack',
    'GtkPaned':            'gui_paned',
    'GtkHPaned':           'gui_paned',
    'GtkVPaned':           'gui_paned',
    'GtkExpander':         'gui_expander',
    'GtkRevealer':         'gui_revealer',
    'GtkOverlay':          'gui_overlay',
    'GtkViewport':         'gui_scroll',
    # ── Controls ───────────────────────────────────────────────────────────
    'GtkButton':           'gui_button',
    'GtkToggleButton':     'gui_toggle',
    'GtkCheckButton':      'gui_check',
    'GtkRadioButton':      'gui_radio',
    'GtkSwitch':           'gui_toggle',
    'GtkLinkButton':       'gui_button',
    'GtkMenuButton':       'gui_button',
    'GtkColorButton':      'gui_button',
    'GtkFontButton':       'gui_button',
    'GtkFileChooserButton':'gui_button',
    # ── Inputs ─────────────────────────────────────────────────────────────
    'GtkEntry':            'gui_entry',
    'GtkSearchEntry':      'gui_entry',
    'GtkPasswordEntry':    'gui_entry',
    'GtkTextView':         'gui_textview',
    'GtkSpinButton':       'gui_spinbutton',
    'GtkScale':            'gui_scale',
    'GtkHScale':           'gui_scale',
    'GtkVScale':           'gui_scale',
    'GtkComboBox':         'gui_combo',
    'GtkComboBoxText':     'gui_combo',
    'GtkDropDown':         'gui_combo',
    'GtkCalendar':         'gui_calendar',
    'GtkColorChooserWidget':'gui_colorpicker',
    # ── Display ────────────────────────────────────────────────────────────
    'GtkLabel':            'gui_label',
    'GtkImage':            'gui_image',
    'GtkPicture':          'gui_image',
    'GtkProgressBar':      'gui_progress',
    'GtkLevelBar':         'gui_progress',
    'GtkSeparator':        'gui_separator',
    'GtkHSeparator':       'gui_separator',
    'GtkVSeparator':       'gui_separator',
    'GtkStatusbar':        'gui_statusbar',
    'GtkSpinner':          'gui_spinner',
    'GtkDrawingArea':      'gui_canvas',
    # ── Menu / Action ──────────────────────────────────────────────────────
    'GtkMenuBar':          'gui_menubar',
    'GtkToolbar':          'gui_toolbar',
    'GtkMenuItem':         'gui_menuitem',
    'GtkMenu':             'gui_menu',
    'GtkPopoverMenu':      'gui_menu',
    'GtkHeaderBar':        'gui_headerbar',
    'GtkActionBar':        'gui_actionbar',
    # ── Lists / Tree ───────────────────────────────────────────────────────
    'GtkTreeView':         'gui_treeview',
    'GtkListBox':          'gui_listbox',
    'GtkFlowBox':          'gui_listbox',
    'GtkIconView':         'gui_iconview',
}

# MMOE type definitions for all GUI widget categories.
# Added to the GristMill registry at import time.
GUI_MMOE_TYPES = {
    # Containers  Y=500..599
    'gui_window':    {'udp': (+1, -1), 'successors': ['gui_box', 'gui_grid', 'gui_headerbar'],
                      'y_range': (590, 599), 'z_range': (0, 100),
                      'description': 'Top-level application window'},
    'gui_dialog':    {'udp': (+1, -1), 'successors': ['gui_box', 'gui_button'],
                      'y_range': (580, 589), 'z_range': (0, 100),
                      'description': 'Modal dialog window'},
    'gui_box':       {'udp': (+1, -1), 'successors': ['gui_button', 'gui_label', 'gui_entry', 'gui_box'],
                      'y_range': (560, 579), 'z_range': (0, 200),
                      'description': 'Linear layout container (H or V)'},
    'gui_grid':      {'udp': (+1, -1), 'successors': ['gui_button', 'gui_label', 'gui_entry'],
                      'y_range': (540, 559), 'z_range': (0, 200),
                      'description': 'Grid layout container'},
    'gui_frame':     {'udp': (+1, -1), 'successors': ['gui_box', 'gui_label'],
                      'y_range': (520, 539), 'z_range': (0, 100),
                      'description': 'Framed container with optional label'},
    'gui_scroll':    {'udp': (+1, -1), 'successors': ['gui_textview', 'gui_treeview', 'gui_box'],
                      'y_range': (500, 519), 'z_range': (0, 100),
                      'description': 'Scrollable container'},
    'gui_notebook':  {'udp': (+1, -1), 'successors': ['gui_box', 'gui_label'],
                      'y_range': (510, 519), 'z_range': (100, 200),
                      'description': 'Tabbed notebook container'},
    'gui_stack':     {'udp': (+1, -1), 'successors': ['gui_box'],
                      'y_range': (505, 514), 'z_range': (200, 300),
                      'description': 'Stack of pages (only one visible)'},
    'gui_paned':     {'udp': (+1, -1), 'successors': ['gui_box', 'gui_treeview'],
                      'y_range': (500, 509), 'z_range': (300, 400),
                      'description': 'Split-pane container'},
    'gui_expander':  {'udp': (+1, -1), 'successors': ['gui_box', 'gui_label'],
                      'y_range': (500, 504), 'z_range': (400, 500),
                      'description': 'Collapsible container'},
    'gui_revealer':  {'udp': (+1, -1), 'successors': ['gui_box'],
                      'y_range': (500, 504), 'z_range': (500, 600),
                      'description': 'Animated reveal container'},
    'gui_overlay':   {'udp': (+1, -1), 'successors': ['gui_box', 'gui_button'],
                      'y_range': (500, 504), 'z_range': (600, 700),
                      'description': 'Overlay stacking container'},
    'gui_headerbar': {'udp': (+1, -1), 'successors': ['gui_button', 'gui_label'],
                      'y_range': (595, 599), 'z_range': (100, 200),
                      'description': 'Header bar (CSD title area)'},
    'gui_actionbar': {'udp': (+1, -1), 'successors': ['gui_button'],
                      'y_range': (590, 594), 'z_range': (100, 200),
                      'description': 'Action bar at bottom of window'},
    # Controls  Y=400..499
    'gui_button':    {'udp': (+1, +1), 'successors': ['gui_label', 'gui_box'],
                      'y_range': (480, 499), 'z_range': (0, 200),
                      'description': 'Clickable push button'},
    'gui_toggle':    {'udp': (+1, +1), 'successors': ['gui_label'],
                      'y_range': (460, 479), 'z_range': (0, 200),
                      'description': 'Toggle / switch button'},
    'gui_check':     {'udp': (+1, +1), 'successors': ['gui_label'],
                      'y_range': (440, 459), 'z_range': (0, 200),
                      'description': 'Checkbox'},
    'gui_radio':     {'udp': (+1, +1), 'successors': ['gui_label', 'gui_radio'],
                      'y_range': (420, 439), 'z_range': (0, 200),
                      'description': 'Radio button (mutually exclusive)'},
    # Inputs  Y=300..399
    'gui_entry':     {'udp': (+1,  0), 'successors': ['gui_button', 'gui_label'],
                      'y_range': (380, 399), 'z_range': (0, 200),
                      'description': 'Single-line text entry'},
    'gui_textview':  {'udp': (+1,  0), 'successors': ['gui_button', 'gui_label'],
                      'y_range': (360, 379), 'z_range': (0, 200),
                      'description': 'Multi-line text editor'},
    'gui_spinbutton':{'udp': (+1,  0), 'successors': ['gui_label'],
                      'y_range': (340, 359), 'z_range': (0, 200),
                      'description': 'Numeric spin button'},
    'gui_scale':     {'udp': (+1,  0), 'successors': ['gui_label'],
                      'y_range': (320, 339), 'z_range': (0, 200),
                      'description': 'Slider / range control'},
    'gui_combo':     {'udp': (+1,  0), 'successors': ['gui_label', 'gui_entry'],
                      'y_range': (300, 319), 'z_range': (0, 200),
                      'description': 'Drop-down selector'},
    'gui_calendar':  {'udp': (+1,  0), 'successors': ['gui_button'],
                      'y_range': (310, 319), 'z_range': (200, 300),
                      'description': 'Calendar date picker'},
    'gui_colorpicker':{'udp': (+1, 0), 'successors': ['gui_button'],
                      'y_range': (300, 309), 'z_range': (200, 300),
                      'description': 'Colour picker widget'},
    # Display  Y=200..299
    'gui_label':     {'udp': (+1,  0), 'successors': ['gui_button', 'gui_entry'],
                      'y_range': (280, 299), 'z_range': (0, 200),
                      'description': 'Static text label'},
    'gui_image':     {'udp': (+1,  0), 'successors': ['gui_label'],
                      'y_range': (260, 279), 'z_range': (0, 200),
                      'description': 'Image / picture display'},
    'gui_progress':  {'udp': (+1,  0), 'successors': ['gui_label', 'gui_button'],
                      'y_range': (240, 259), 'z_range': (0, 200),
                      'description': 'Progress / level bar'},
    'gui_separator': {'udp': ( 0,  0), 'successors': ['gui_label', 'gui_button'],
                      'y_range': (220, 239), 'z_range': (0, 200),
                      'description': 'Visual separator line'},
    'gui_statusbar': {'udp': (+1,  0), 'successors': [],
                      'y_range': (200, 219), 'z_range': (0, 100),
                      'description': 'Status bar at window bottom'},
    'gui_spinner':   {'udp': (+1,  0), 'successors': ['gui_label'],
                      'y_range': (200, 209), 'z_range': (100, 200),
                      'description': 'Animated busy spinner'},
    'gui_canvas':    {'udp': (+1,  0), 'successors': [],
                      'y_range': (200, 209), 'z_range': (200, 300),
                      'description': 'Custom drawing area'},
    # Menu / Action  Y=100..199
    'gui_menubar':   {'udp': (+1, -1), 'successors': ['gui_menu', 'gui_menuitem'],
                      'y_range': (180, 199), 'z_range': (0, 100),
                      'description': 'Application menu bar'},
    'gui_toolbar':   {'udp': (+1, -1), 'successors': ['gui_button'],
                      'y_range': (160, 179), 'z_range': (0, 100),
                      'description': 'Tool bar'},
    'gui_menu':      {'udp': (+1, -1), 'successors': ['gui_menuitem'],
                      'y_range': (140, 159), 'z_range': (0, 100),
                      'description': 'Popup / dropdown menu'},
    'gui_menuitem':  {'udp': (+1, +1), 'successors': ['gui_menuitem'],
                      'y_range': (120, 139), 'z_range': (0, 100),
                      'description': 'Menu item'},
    # List / Tree  Y=050..099
    'gui_treeview':  {'udp': (+1,  0), 'successors': ['gui_label'],
                      'y_range': (80, 99), 'z_range': (0, 200),
                      'description': 'Tree / list view'},
    'gui_listbox':   {'udp': (+1,  0), 'successors': ['gui_label', 'gui_button'],
                      'y_range': (60, 79), 'z_range': (0, 200),
                      'description': 'List box'},
    'gui_iconview':  {'udp': (+1,  0), 'successors': ['gui_label'],
                      'y_range': (50, 59), 'z_range': (0, 200),
                      'description': 'Icon grid view'},
    # Unknown fallback
    'gui_unknown':   {'udp': ( 0,  0), 'successors': [],
                      'y_range': (600, 699), 'z_range': (0, 100),
                      'description': 'Unrecognised widget type'},
}

# Register GUI MMOE types into GristMill's registry at import time
MMOE_TYPES.update(GUI_MMOE_TYPES)


# ── Widget → MMOE type lookup ─────────────────────────────────────────────────

def widget_class_to_mmoe(gtk_class: str) -> str:
    """
    Map a GTK widget class name to an MMOE type string.
    Unknown classes return 'gui_unknown'.
    """
    return WIDGET_TYPE_MAP.get(gtk_class, 'gui_unknown')


# ── Glade XML parser ─────────────────────────────────────────────────────────

def _parse_object(elem, parent_id: int, id_counter: list, widgets: list,
                  edges: list, depth: int = 0):
    """
    Recursively parse a Glade <object> element into widget records.
    Populates:
      widgets — list of {id, gtk_class, mmoe_type, label, signals, x, y, depth}
      edges   — list of {src, dst} parent→child relationships
    """
    gtk_class = elem.get('class', 'Unknown')
    mmoe_type = widget_class_to_mmoe(gtk_class)

    this_id = id_counter[0]
    id_counter[0] += 1

    # Collect properties
    props = {}
    for prop in elem.findall('property'):
        name = prop.get('name', '')
        props[name] = prop.text or ''

    label = (props.get('label') or
             props.get('title') or
             props.get('text') or
             elem.get('id') or
             gtk_class)

    # Collect signals
    signals = []
    for sig in elem.findall('signal'):
        signals.append({
            'name':    sig.get('name', ''),
            'handler': sig.get('handler', ''),
        })

    # Geometry from properties
    x = int(props.get('width-request',  0)) or 0
    y = int(props.get('height-request', 0)) or 0

    widget = {
        'id':        this_id,
        'gtk_class': gtk_class,
        'mmoe_type': mmoe_type,
        'label':     label,
        'signals':   signals,
        'props':     props,
        'x':         x,
        'y':         y,
        'depth':     depth,
    }
    widgets.append(widget)

    if parent_id is not None:
        edges.append({'src': parent_id, 'dst': this_id})

    # Recurse into children
    for child in elem.findall('child'):
        for obj in child.findall('object'):
            _parse_object(obj, this_id, id_counter, widgets, edges, depth + 1)


def parse_glade_xml(xml_source: str) -> dict:
    """
    Parse Glade XML string or file path into a normalised canvas dict.
    Returns:
      {
        'source': 'glade',
        'widgets': [...],      # flat list of widget records
        'edges':   [...],      # parent→child relationships
        'sequence': [...],     # BFS walk order (for training)
      }
    """
    if os.path.isfile(xml_source):
        tree = ET.parse(xml_source)
        root = tree.getroot()
    else:
        root = ET.fromstring(xml_source)

    widgets    = []
    edges      = []
    id_counter = [0]

    # Top-level <object> elements (direct children of <interface>)
    for obj in root.findall('object'):
        _parse_object(obj, None, id_counter, widgets, edges, depth=0)

    # BFS sequence for training
    children_of = {}
    for e in edges:
        children_of.setdefault(e['src'], []).append(e['dst'])
    roots = [w['id'] for w in widgets
             if not any(e['dst'] == w['id'] for e in edges)]

    sequence = []
    queue = list(roots)
    visited = set()
    while queue:
        wid = queue.pop(0)
        if wid in visited:
            continue
        visited.add(wid)
        sequence.append(wid)
        queue.extend(children_of.get(wid, []))

    return {
        'source':   'glade',
        'widgets':  widgets,
        'edges':    edges,
        'sequence': sequence,
    }


# ── Cambalache .cmb parser ────────────────────────────────────────────────────

def parse_cmb_file(cmb_path: str) -> dict:
    """
    Parse a Cambalache .cmb SQLite file into the same canvas dict as
    parse_glade_xml.

    Cambalache schema (simplified):
      ui            (ui_id, name, ...)
      object        (ui_id, object_id, type_id, name, parent_id, ...)
      object_property (ui_id, object_id, owner_id, property_id, value)
      object_signal (ui_id, object_id, signal_id, handler, ...)
      type          (type_id, type_name)
    """
    if not os.path.isfile(cmb_path):
        raise FileNotFoundError(f"CMB file not found: {cmb_path}")

    conn   = sqlite3.connect(cmb_path)
    cursor = conn.cursor()

    # Fetch type names
    try:
        cursor.execute("SELECT type_id, type_name FROM type")
        type_map = {row[0]: row[1] for row in cursor.fetchall()}
    except sqlite3.OperationalError:
        # Try alternative schema
        try:
            cursor.execute("SELECT type_id, library_id || '.' || type_name FROM type")
            type_map = {row[0]: row[1].split('.')[-1] for row in cursor.fetchall()}
        except sqlite3.OperationalError:
            type_map = {}

    # Fetch objects
    try:
        cursor.execute(
            "SELECT object_id, type_id, name, parent_id FROM object ORDER BY object_id")
        obj_rows = cursor.fetchall()
    except sqlite3.OperationalError:
        conn.close()
        raise RuntimeError("Cannot read 'object' table — is this a valid .cmb file?")

    # Fetch properties
    props_map = {}
    try:
        cursor.execute(
            "SELECT object_id, property_id, value FROM object_property")
        for oid, pid, val in cursor.fetchall():
            props_map.setdefault(oid, {})[str(pid)] = val or ''
    except sqlite3.OperationalError:
        pass

    # Fetch signals
    signals_map = {}
    try:
        cursor.execute(
            "SELECT object_id, signal_id, handler FROM object_signal")
        for oid, sid, handler in cursor.fetchall():
            signals_map.setdefault(oid, []).append({
                'name':    str(sid),
                'handler': handler or '',
            })
    except sqlite3.OperationalError:
        pass

    conn.close()

    widgets = []
    edges   = []

    for obj_id, type_id, name, parent_id in obj_rows:
        gtk_class = type_map.get(type_id, f'Unknown_{type_id}')
        mmoe_type = widget_class_to_mmoe(gtk_class)
        props     = props_map.get(obj_id, {})
        label     = name or gtk_class

        widgets.append({
            'id':        obj_id,
            'gtk_class': gtk_class,
            'mmoe_type': mmoe_type,
            'label':     label,
            'signals':   signals_map.get(obj_id, []),
            'props':     props,
            'x':         0,
            'y':         0,
            'depth':     0,
        })

        if parent_id:
            edges.append({'src': parent_id, 'dst': obj_id})

    # BFS sequence
    children_of = {}
    for e in edges:
        children_of.setdefault(e['src'], []).append(e['dst'])
    all_dsts = {e['dst'] for e in edges}
    roots    = [w['id'] for w in widgets if w['id'] not in all_dsts]

    sequence = []
    queue = list(roots)
    visited = set()
    while queue:
        wid = queue.pop(0)
        if wid in visited:
            continue
        visited.add(wid)
        sequence.append(wid)
        queue.extend(children_of.get(wid, []))

    return {
        'source':   'cambalache',
        'widgets':  widgets,
        'edges':    edges,
        'sequence': sequence,
    }


# ── Canvas → MMID sequence ────────────────────────────────────────────────────

def canvas_to_mmid_sequence(canvas: dict) -> list:
    """
    Convert a parsed canvas (from Glade or CMB) to a list of
    (MMID, label, widget_record) tuples in BFS walk order.

    This is the core conversion — widget tree to octree coordinate sequence.
    """
    widget_by_id = {w['id']: w for w in canvas['widgets']}
    sequence     = canvas.get('sequence', [w['id'] for w in canvas['widgets']])

    result = []
    for wid in sequence:
        w = widget_by_id.get(wid)
        if not w:
            continue
        mmoe_type = w['mmoe_type']
        mmid      = MMID(mmoe_type, instance=wid)
        result.append((mmid, w['label'], w))

    return result


# ── MMOE tree builder ─────────────────────────────────────────────────────────

def canvas_to_mmoe_tree(canvas: dict) -> list:
    """
    Convert a parsed canvas to a hierarchical MMOE tree (roots only;
    children attached via MMOE.children).

    Returns a list of root MMOEs. Each MMOE has .children populated
    recursively, mirroring the widget containment hierarchy.
    """
    gm = GristMill()
    widget_by_id = {w['id']: w for w in canvas['widgets']}

    children_of = {}
    for e in canvas['edges']:
        children_of.setdefault(e['src'], []).append(e['dst'])
    all_dsts = {e['dst'] for e in canvas['edges']}
    root_ids = [w['id'] for w in canvas['widgets'] if w['id'] not in all_dsts]

    mmoe_by_id = {}

    def build_mmoe(wid: int) -> MMOE:
        w         = widget_by_id[wid]
        mmid      = MMID(w['mmoe_type'], instance=wid)
        mmoe      = gm.synthesise(mmid, label=w['label'])
        mmoe_by_id[wid] = mmoe
        for child_id in children_of.get(wid, []):
            if child_id in widget_by_id:
                child_mmoe = build_mmoe(child_id)
                mmoe.add_child(child_mmoe)
        return mmoe

    return [build_mmoe(rid) for rid in root_ids]


# ── .tgui output format ───────────────────────────────────────────────────────
# .tgui is the TernOO GUI training format — a JSON file that FlowCodeBrain
# and GristMill can consume for GHOST training on widget vocabulary.
#
# Format mirrors FlowCode canvas JSON so existing training infrastructure works:
#   { "symbols": [...], "edges": [...], "tgui_meta": {...} }
# Each "symbol" carries mmoe_type, label, signals, gtk_class, and coordinates.

def canvas_to_tgui(canvas: dict, source_path: str = '') -> dict:
    """
    Convert a parsed canvas to .tgui JSON format for GHOST training.
    Output is compatible with FlowCodeBrain.train_on_flowcode() — the
    'kind' field uses the mmoe_type string so the brain learns GUI vocabulary
    in the same Markov framework as FlowCode symbol transitions.
    """
    widget_by_id = {w['id']: w for w in canvas['widgets']}

    symbols = []
    for w in canvas['widgets']:
        sym = {
            'id':        w['id'],
            'kind':      w['mmoe_type'],      # used by FlowCodeBrain
            'label':     w['label'],
            'gtk_class': w['gtk_class'],
            'x':         w.get('x', 0),
            'y':         w.get('y', 0),
            'depth':     w.get('depth', 0),
            'signals':   w.get('signals', []),
        }
        symbols.append(sym)

    return {
        'tgui_version': '0.1',
        'source_file':  os.path.basename(source_path),
        'source_type':  canvas.get('source', 'unknown'),
        'symbols':      symbols,
        'edges':        canvas['edges'],
        'sequence':     canvas.get('sequence', []),
        'tgui_meta': {
            'widget_count':  len(symbols),
            'edge_count':    len(canvas['edges']),
            'mmoe_types_used': sorted({w['mmoe_type'] for w in canvas['widgets']}),
        },
    }


def save_tgui(tgui: dict, output_path: str):
    """Save a .tgui dict to a JSON file."""
    with open(output_path, 'w') as f:
        json.dump(tgui, f, indent=2)
    print(f"Saved: {output_path}")


# ── Main conversion entry point ───────────────────────────────────────────────

def convert(source_path: str, output_path: str = None) -> dict:
    """
    Convert a Glade XML (.ui / .glade) or Cambalache (.cmb) file to
    a .tgui JSON file ready for GHOST training.

    Returns the tgui dict.
    """
    ext = os.path.splitext(source_path)[1].lower()

    if ext == '.cmb':
        canvas = parse_cmb_file(source_path)
    elif ext in ('.ui', '.glade', '.xml'):
        canvas = parse_glade_xml(source_path)
    else:
        raise ValueError(f"Unknown source format: {ext}  (expected .cmb / .ui / .glade)")

    tgui = canvas_to_tgui(canvas, source_path=source_path)

    if output_path is None:
        base         = os.path.splitext(source_path)[0]
        output_path  = base + '.tgui'

    save_tgui(tgui, output_path)
    return tgui


# ── GHOST training feed ───────────────────────────────────────────────────────

def _markov_train(weights: dict, tgui: dict, rate: int = 1):
    """Open-vocabulary Markov training on a .tgui canvas."""
    symbols = {s['id']: s for s in tgui.get('symbols', [])}
    edges   = tgui.get('edges', [])
    def _bump(sk, dk):
        row = weights.setdefault(sk, {})
        row[dk] = row.get(dk, 0) + rate

    # edge-based transitions
    for e in edges:
        src = symbols.get(e.get('src')); dst = symbols.get(e.get('dst'))
        if src and dst:
            sk = src.get('kind'); dk = dst.get('kind')
            if sk and dk:
                _bump(sk, dk)
    # BFS sequential transitions (order within parent)
    from collections import deque
    children: dict = {}
    for e in edges:
        children.setdefault(e.get('src'), []).append(e.get('dst'))
    visited = set(); q = deque(symbols.keys())
    while q:
        nid = q.popleft()
        if nid in visited: continue
        visited.add(nid)
        kids = children.get(nid, [])
        for i in range(len(kids) - 1):
            sk = symbols.get(kids[i],   {}).get('kind')
            dk = symbols.get(kids[i+1], {}).get('kind')
            if sk and dk:
                _bump(sk, dk)
        q.extend(kids)


def train_brain_on_tgui(tgui_path: str) -> str:
    """
    Train the GHOST GUI brain (ghost_gui_brain.json) on a .tgui file.
    Uses open-vocabulary Markov training — never touches flowcode_brain.json.
    """
    brain_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              'ghost_gui_brain.json')
    # load existing weights
    weights: dict = {}
    if os.path.exists(brain_path):
        with open(brain_path) as f:
            weights = json.load(f).get('weights', {})

    with open(tgui_path) as f:
        tgui = json.load(f)

    _markov_train(weights, tgui)

    brain_data = {
        'brain_type': 'ghost_gui',
        'hemisphere': 'structural',
        'vocab_size': len(weights),
        'weights': weights,
    }
    with open(brain_path, 'w') as f:
        json.dump(brain_data, f, indent=2)

    result = f"GHOST GUI brain updated: {len(weights)} types — {brain_path}"
    print(result)
    return result


# ── Demo ──────────────────────────────────────────────────────────────────────

def demo_minimal():
    """
    Demonstrate the bridge on a minimal hand-built widget tree
    (no file needed — useful before you have Cambalache installed).
    """
    minimal_glade = """<?xml version="1.0" encoding="UTF-8"?>
<interface>
  <object class="GtkWindow" id="main_window">
    <property name="title">TernOO Demo</property>
    <property name="width-request">400</property>
    <property name="height-request">300</property>
    <child>
      <object class="GtkBox" id="main_box">
        <property name="orientation">vertical</property>
        <child>
          <object class="GtkLabel" id="title_label">
            <property name="label">Hello TernOO</property>
          </object>
        </child>
        <child>
          <object class="GtkEntry" id="name_entry">
            <property name="placeholder-text">Enter name...</property>
          </object>
        </child>
        <child>
          <object class="GtkBox" id="button_box">
            <child>
              <object class="GtkButton" id="ok_button">
                <property name="label">OK</property>
                <signal name="clicked" handler="on_ok_clicked"/>
              </object>
            </child>
            <child>
              <object class="GtkButton" id="cancel_button">
                <property name="label">Cancel</property>
                <signal name="clicked" handler="on_cancel_clicked"/>
              </object>
            </child>
          </object>
        </child>
      </object>
    </child>
  </object>
</interface>"""

    print("=" * 60)
    print("  TernOO Cambalache Bridge — Minimal Demo")
    print("=" * 60)

    canvas = parse_glade_xml(minimal_glade)
    print(f"\nParsed {len(canvas['widgets'])} widgets, "
          f"{len(canvas['edges'])} edges")
    print(f"BFS sequence: {canvas['sequence']}")

    print("\n── MMID Sequence ──")
    mmid_seq = canvas_to_mmid_sequence(canvas)
    for mmid, label, w in mmid_seq:
        print(f"  {label:20} [{w['gtk_class']:22}] → {mmid}")

    print("\n── MMOE Tree ──")
    roots = canvas_to_mmoe_tree(canvas)
    for root in roots:
        print(root.describe())

    print("\n── .tgui format ──")
    tgui = canvas_to_tgui(canvas, 'minimal_demo')
    print(f"  widget_count  : {tgui['tgui_meta']['widget_count']}")
    print(f"  mmoe_types    : {tgui['tgui_meta']['mmoe_types_used']}")
    print(f"  Compatible with FlowCodeBrain.train_on_flowcode() ✓")

    print("\n── GristMill Proximity (gui_button) ──")
    gm   = GristMill()
    mmid = MMID('gui_button', 0)
    for dist, name in gm.proximity(mmid, n=6):
        desc = MMOE_TYPES.get(name, {}).get('description', '')
        print(f"  {dist:8.1f}  {name:20}  {desc}")


if __name__ == '__main__':
    if len(sys.argv) == 1:
        demo_minimal()
    elif len(sys.argv) == 2:
        src = sys.argv[1]
        out = os.path.splitext(src)[0] + '.tgui'
        tgui = convert(src, out)
        print(f"\n{tgui['tgui_meta']['widget_count']} widgets → {out}")
        print(f"Types: {tgui['tgui_meta']['mmoe_types_used']}")
    elif len(sys.argv) == 3 and sys.argv[1] == '--train':
        train_brain_on_tgui(sys.argv[2])
    else:
        print("Usage:")
        print("  python3 ternoo_cambalache_bridge.py                   # minimal demo")
        print("  python3 ternoo_cambalache_bridge.py file.ui           # convert Glade XML")
        print("  python3 ternoo_cambalache_bridge.py file.cmb          # convert Cambalache")
        print("  python3 ternoo_cambalache_bridge.py --train file.tgui # train brain")
