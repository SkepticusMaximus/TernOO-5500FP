#!/usr/bin/env python3
"""Contact canvas — an Obsidian-style pan/zoom graph of the identity namespace.

Nodes are OWNERS (seats/people) and ENTITIES (the people they know). Edges are
PETNAMES: @owner@petname. The federated point made visible — when two owners'
petnames resolve to the SAME TernID, their edges land on ONE node (@Dave,
"implied by the common link"); different TernIDs stay separate nodes (your Dave
is not my Dave). A shared node is the CONVERGENCE node for that identity.

Pan: drag. Zoom: wheel, or the +/- buttons / Ctrl+= / Ctrl+-. Reads the live
TernID agent when present; always overlays the mock petnames so the federated
look is demonstrable with only the crew on the system.
"""
import math
import os
import sys

from PySide6.QtWidgets import (QApplication, QMainWindow, QGraphicsScene, QGraphicsView,
                               QGraphicsEllipseItem, QGraphicsSimpleTextItem, QGraphicsLineItem,
                               QToolBar)
from PySide6.QtGui import QAction, QColor, QPen, QBrush, QPainter, QFont
from PySide6.QtCore import Qt, QPointF, QRectF, QLineF

BG = QColor("#141821")
OWNER = QColor("#3fd08f")        # seats / people who hold petnames
ENTITY = QColor("#5a82be")       # a known person (one TernID)
CONVERGE = QColor("#e8c23a")     # shared TernID — two+ owners' petnames land here
EDGE = QColor("#44506a")
TXT = QColor("#e6e6ec")


def load_graph():
    """(owners, petnames) where petnames = {owner: {petname: ternid}}.
    Real crew from the agent if reachable; the mock Daves/Bobs always overlaid."""
    owners = ["Stevo", "CC", "CCC", "CF5", "CAI", "Professor"]
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from ternid_agent_protocol import Client
        c = Client(os.environ.get("TERNID_AGENT_SOCK", "/run/user/1000/ternid-agent.sock"))
        owners = [c.account_display(account_handle=a) for a in c.list_accounts()]
    except Exception:
        pass
    # mock federated petnames: Dave CONVERGES (same tid), Bob DIVERGES (distinct tids)
    petnames = {
        "Stevo": {"Dave": "tid_dave_shared", "Bob": "tid_bob_stevo"},
        "CC":    {"Dave": "tid_dave_shared", "Bob": "tid_bob_cc"},
    }
    return owners, petnames


class CanvasView(QGraphicsView):
    def __init__(self, scene):
        super().__init__(scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)      # drag to pan
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setBackgroundBrush(QBrush(BG))

    def wheelEvent(self, e):
        self.zoom(1.15 if e.angleDelta().y() > 0 else 1 / 1.15)

    def zoom(self, f):
        self.scale(f, f)


def _node(scene, pos, label, colour, r=30):
    dot = QGraphicsEllipseItem(QRectF(pos.x() - r, pos.y() - r, 2 * r, 2 * r))
    dot.setBrush(QBrush(colour))
    dot.setPen(QPen(colour.darker(140), 2))
    dot.setZValue(2)
    scene.addItem(dot)
    t = QGraphicsSimpleTextItem(label)
    t.setBrush(QBrush(TXT))
    f = QFont(); f.setPointSize(10); f.setBold(True); t.setFont(f)
    br = t.boundingRect()
    t.setPos(pos.x() - br.width() / 2, pos.y() - br.height() / 2)
    t.setZValue(3)
    scene.addItem(t)
    return dot


def _edge(scene, a, b, label):
    ln = QGraphicsLineItem(QLineF(a, b))
    ln.setPen(QPen(EDGE, 2))
    ln.setZValue(1)
    scene.addItem(ln)
    if label:
        t = QGraphicsSimpleTextItem(label)
        t.setBrush(QBrush(QColor("#9aa7bd")))
        f = QFont(); f.setPointSize(8); t.setFont(f)
        mid = QPointF((a.x() + b.x()) / 2, (a.y() + b.y()) / 2)
        t.setPos(mid.x() + 4, mid.y() - 8)
        t.setZValue(3)
        scene.addItem(t)


def build_scene():
    owners, petnames = load_graph()
    scene = QGraphicsScene()
    scene.setBackgroundBrush(QBrush(BG))

    # owners around a ring
    R = 300
    opos = {}
    n = len(owners)
    for i, o in enumerate(owners):
        a = -math.pi / 2 + 2 * math.pi * i / n
        opos[o] = QPointF(R * math.cos(a), R * math.sin(a))

    # entity position = centroid of the owners that name it, pulled toward centre
    ent_owners = {}          # tid -> [(owner, petname)]
    for o, pn in petnames.items():
        for name, tid in pn.items():
            ent_owners.setdefault(tid, []).append((o, name))
    epos = {}
    for tid, refs in ent_owners.items():
        pts = [opos[o] for o, _ in refs if o in opos]
        if not pts:
            continue
        cx = sum(p.x() for p in pts) / len(pts)
        cy = sum(p.y() for p in pts) / len(pts)
        pull = 0.45 if len(refs) > 1 else 0.62      # shared sits between owners; private hugs its owner
        epos[tid] = QPointF(cx * pull, cy * pull)

    # draw edges first (behind nodes)
    for tid, refs in ent_owners.items():
        for o, petname in refs:
            if o in opos and tid in epos:
                _edge(scene, opos[o], epos[tid], petname)

    # owner nodes
    for o, p in opos.items():
        _node(scene, p, o, OWNER, r=30)
    # entity nodes — converged (2+ owners) highlighted gold + labelled @petname
    for tid, p in epos.items():
        refs = ent_owners[tid]
        shared = len({o for o, _ in refs}) > 1
        label = refs[0][1] if not shared else "@%s" % refs[0][1]   # @Dave when convergent
        _node(scene, p, label, CONVERGE if shared else ENTITY, r=26 if shared else 22)
    return scene


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Contact Canvas")
    win = QMainWindow()
    win.setWindowTitle("TernOO · Contact Canvas — identity namespace")
    win.resize(960, 640)
    view = CanvasView(build_scene())
    win.setCentralWidget(view)
    tb = QToolBar()
    win.addToolBar(tb)
    tb.addAction(QAction("Zoom +", win, shortcut="Ctrl+=", triggered=lambda: view.zoom(1.25)))
    tb.addAction(QAction("Zoom −", win, shortcut="Ctrl+-", triggered=lambda: view.zoom(1 / 1.25)))
    tb.addAction(QAction("Fit", win, triggered=lambda: view.fitInView(view.scene().itemsBoundingRect().adjusted(-40, -40, 40, 40), Qt.AspectRatioMode.KeepAspectRatio)))
    view.fitInView(view.scene().itemsBoundingRect().adjusted(-40, -40, 40, 40), Qt.AspectRatioMode.KeepAspectRatio)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
