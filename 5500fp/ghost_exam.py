#!/usr/bin/env python3
"""
GHOST GUI Brain — Exam
Run with: python3 ghost_exam.py
"""
import json, os

brain_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          'ghost_gui_brain.json')
weights = json.load(open(brain_path))['weights']

def predict(start, steps=6):
    seq  = [start]
    tok  = start
    seen = {start}
    for _ in range(steps):
        candidates = {k: v for k, v in weights.get(tok, {}).items()
                      if k != tok}          # no self-loops
        if not candidates:
            break
        tok = max(candidates, key=candidates.get)
        if tok in seen:
            break                           # stop if we hit a cycle
        seen.add(tok)
        seq.append(tok)
    return ' → '.join(seq)

seeds = ['gui_window', 'gui_dialog', 'gui_button',
         'gui_entry',  'gui_menuitem', 'gui_label',
         'gui_box',    'gui_treeview']

print("=" * 60)
print("  GHOST GUI Brain — Emergence Exam")
print("=" * 60)
for s in seeds:
    if s in weights:
        print(f"  {s:<18} {predict(s)}")
    else:
        print(f"  {s:<18} (not in brain yet)")
print("=" * 60)
