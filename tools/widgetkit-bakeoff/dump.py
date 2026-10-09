#!/usr/bin/env python3
"""Object-model teardown of the text widget — the 'grist' we forge into TernOO words.
Usage: dump.py gtk   |   dump.py qt"""
import os
import sys
kit = sys.argv[1] if len(sys.argv) > 1 else "qt"

if kit == "gtk":
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk, GObject
    tv = Gtk.TextView()
    print("=== GTK3 · GtkTextView — object model ===")
    print("\nPython MRO:")
    for c in type(tv).__mro__:
        print("   ", c.__module__ + "." + c.__name__)
    gt = type(tv).__gtype__
    chain = [gt.name]
    while gt.name != "GObject":
        gt = GObject.type_parent(gt)
        chain.append(gt.name)
    print("\nGType ancestry (inherits ->):")
    print("   " + " -> ".join(chain))
    props = sorted(p.name for p in tv.list_properties())
    print("\nproperties (%d):" % len(props))
    print("   " + ", ".join(props))
else:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication, QTextEdit
    _ = QApplication([])
    ed = QTextEdit()
    print("=== PySide6 · QTextEdit — object model ===")
    print("\nPython MRO:")
    for c in type(ed).__mro__:
        print("   ", c.__module__ + "." + c.__name__)
    mo = ed.metaObject()
    chain = []
    while mo:
        chain.append(mo.className())
        mo = mo.superClass()
    print("\nQt meta ancestry (inherits ->):")
    print("   " + " -> ".join(chain))
    mo = ed.metaObject()
    props = [mo.property(i).name() for i in range(mo.propertyCount())]
    print("\nmeta-properties (%d, own+inherited):" % len(props))
    print("   " + ", ".join(props))
