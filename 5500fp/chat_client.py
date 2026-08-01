#!/usr/bin/env python3
"""chat_client.py — the Mesh-Chat harness as a light standalone window.

The exact same chat as the FlowCode "Mesh-Chat" tab — talk to a live Professor on
the mesh, with memory, named saved chats, copy/paste, and a ⚙ Setup drawer — but on
its own, no IDE to load down the machine. It simply hosts MeshTabView in a plain Tk
window, so every feature the tab has, this has.

    python3 chat_client.py            # or double-click the desktop launcher

Away from home (pub/park): open ⚙ Setup → "🧳 Away from home — talk via relay" and
paste the bore.pub:PORT that park-relay.sh printed back home. Clear it to use the LAN.
"""
import importlib.util as _ilu
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = _ilu.spec_from_file_location(name, os.path.join(_HERE, name + ".py"))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(argv=None):
    import tkinter as tk
    TAB = _load("p2pcp_tab_view")
    # the shared FlowCode dark palette (the keys MeshTabView expects)
    C = {"palette": "#1b1e28", "text": "#e8e8e8", "dim": "#8a90a0", "bg": "#12141c"}

    root = tk.Tk()
    root.title("Mesh-Chat — TernOO P2PCP")
    root.geometry("780x860")
    root.minsize(520, 560)
    root.configure(bg=C["bg"])

    frame = tk.Frame(root, bg=C["bg"])
    frame.pack(side="top", fill="both", expand=True)
    status = tk.Label(root, text="ready", bg=C["palette"], fg=C["dim"],
                      font=("Monospace", 9), anchor="w", padx=8)
    status.pack(side="bottom", fill="x")

    TAB.MeshTabView(frame, C, root, lambda msg: status.config(text=msg))
    root.mainloop()


if __name__ == "__main__":
    main(sys.argv[1:])
