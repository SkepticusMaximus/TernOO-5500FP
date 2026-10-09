#!/home/stevo/.venvs/p2pcp/bin/python3
"""GrOOM — Gristmill Object Oriented Model — first turn of the mill.

Dissect the object models of the widgets TernDO actually uses (PySide6), and emit
a first-pass mapping from Qt properties to candidate TernOO word fields. This is
the 'grist': the reference kit's retained object graph, ground down toward the
native TernOO/TernUI object model.

Run:  QT_QPA_PLATFORM=offscreen ~/.venvs/p2pcp/bin/python3 groom_dissect.py
"""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import (QApplication, QTextEdit, QTreeWidget, QLineEdit,
                               QComboBox, QPushButton, QDialog)
app = QApplication([])


def ancestry(w):
    mo = w.metaObject()
    chain = []
    while mo:
        chain.append(mo.className())
        mo = mo.superClass()
    return chain


def props(w):
    mo = w.metaObject()
    return [mo.property(i).name() for i in range(mo.propertyCount())]


WIDGETS = {"QTextEdit": QTextEdit(), "QTreeWidget": QTreeWidget(), "QLineEdit": QLineEdit(),
           "QComboBox": QComboBox(), "QPushButton": QPushButton(), "QDialog": QDialog()}

print("=== GrOOM dissection — TernDO widget set (PySide6) ===\n")
for name, w in WIDGETS.items():
    print("%-12s %3d props   %s" % (name, len(props(w)), " -> ".join(ancestry(w))))

print("\n=== GrOOM first-pass: QTextEdit property -> TernOO word field ===")
print("A GrOOM object = identity (TernID) + class-word + parent-ref (MAP) + property words.\n")
MAP = [
    ("lineWrapMode", "DATA word: wrap policy (−/0/+ = none / widget / fixed-col)"),
    ("undoRedoEnabled", "DATA word: trit flag (+ on, 0 off)"),
    ("readOnly", "DATA word: trit flag"),
    ("plainText / markdown / html", "MAP words: content-address of the body (char-map plane)"),
    ("document", "MAP ref: the retained text-document object (its OWN GrOOM object)"),
    ("font", "MAP ref -> font/glyph object (CF5 char-map charter)"),
    ("tabStopDistance", "DATA word: payload = trit-encoded distance"),
    ("textInteractionFlags", "QUALIFIER: capability-shaped (select/edit/link) -> meets TernID"),
    ("palette / styleSheet", "MAP ref -> style object"),
    ("placeholderText", "MAP ref -> hint string (char-map)"),
]
for p, m in MAP:
    print("  %-28s -> %s" % (p, m))

print("\nInheritance (QTextEdit -> QAbstractScrollArea -> QFrame -> QWidget -> QObject)")
print("  == a chain of MAP words: child class-word --MAP--> parent class-word;")
print("     properties accumulate down the chain (exactly the inference DPG can't give).")
print("\nConvergence with TernID: a GrOOM object's IDENTITY is a TernID identity, and")
print("'who may read/edit this object' is a CRYPTO capability-word over it")
print("(textInteractionFlags is the local shadow of that). GrOOM objects are")
print("TernID-addressable by construction — the object model and the capability")
print("model share one word substrate.")
