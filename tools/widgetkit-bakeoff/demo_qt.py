#!/usr/bin/env python3
"""TernOO Widget Probe — PySide6 reference scaffold.  [--bench] prints stats and quits."""
import os
import sys
import time
T0 = time.perf_counter()
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                               QLabel, QTextEdit, QFrame)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt, QTimer
T_IMPORT = time.perf_counter()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ternword as W

BENCH = "--bench" in sys.argv


def rss_mb():
    for line in open("/proc/self/status"):
        if line.startswith("VmRSS"):
            return int(line.split()[1]) / 1024.0
    return 0.0


app = QApplication(sys.argv)
app.setStyleSheet("QWidget{background:#1a1f2b;color:#e6e6ec;}"
                  "QTextEdit{background:#15151f;border:1px solid #3a3a52;}")

w = QWidget()
w.setWindowTitle("TernOO Widget Probe — PySide6")
w.resize(560, 580)
box = QVBoxLayout(w)
box.setContentsMargins(12, 12, 12, 12)
box.setSpacing(8)

hdr = QLabel("TernOO · Widget Probe (PySide6)")
hdr.setStyleSheet("color:#3fd08f;font-size:18px;")
box.addWidget(hdr)
sub = QLabel("reference scaffold — retained widget object model")
sub.setStyleSheet("color:#9696a5;")
box.addWidget(sub)

trits = W.to_trits(W.SAMPLE)
strip = QHBoxLayout()
strip.setSpacing(2)
mono = QFont("DejaVu Sans Mono", 14)
mono.setBold(True)
for t in trits:
    cell = QLabel(W.GLYPH[t])
    cell.setFont(mono)
    cell.setAlignment(Qt.AlignmentFlag.AlignCenter)
    cell.setStyleSheet("color:%s;" % W.COLOR[t])
    strip.addWidget(cell)
box.addLayout(strip)

dec = QLabel("primary: %s  (T23,T22 = %s,%s)    word = %d"
             % (W.decode_primary(trits), W.GLYPH[trits[0]], W.GLYPH[trits[1]], W.SAMPLE))
dec.setStyleSheet("color:#e8c890;")
box.addWidget(dec)
line = QFrame()
line.setFrameShape(QFrame.Shape.HLine)
box.addWidget(line)

lab = QLabel("Notes — word-wrap + native cut/copy/paste/undo (right-click)")
lab.setStyleSheet("color:#9696a5;")
box.addWidget(lab)
ed = QTextEdit()
ed.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
ed.setFont(QFont("DejaVu Sans Mono", 11))
ed.setPlainText(W.MUSING)
box.addWidget(ed, 1)

ft = QLabel("wrap: WidgetWidth · clipboard+context-menu: native · undo/redo: native")
ft.setStyleSheet("color:#9696a5;")
box.addWidget(ft)

w.show()

if BENCH:
    def bench():
        shown = time.perf_counter()
        print("BENCH kit=PySide6 import_ms=%.1f build_show_ms=%.1f startup_ms=%.1f rss_mb=%.1f"
              % ((T_IMPORT - T0) * 1000, (shown - T_IMPORT) * 1000, (shown - T0) * 1000, rss_mb()))
        app.quit()
    QTimer.singleShot(0, bench)

sys.exit(app.exec())
