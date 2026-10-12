#!/usr/bin/env python3
"""TernOO Widget Probe — GTK3 reference scaffold.  [--bench] prints stats and quits."""
import os
import sys
import time
T0 = time.perf_counter()
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Pango
T_IMPORT = time.perf_counter()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ternword as W

BENCH = "--bench" in sys.argv


def rss_mb():
    for line in open("/proc/self/status"):
        if line.startswith("VmRSS"):
            return int(line.split()[1]) / 1024.0
    return 0.0


class Probe(Gtk.Window):
    def __init__(self):
        super().__init__(title="TernOO Widget Probe — GTK3")
        self.set_default_size(560, 580)
        self.set_border_width(12)
        box = Gtk.VBox(spacing=8)
        self.add(box)

        hdr = Gtk.Label(xalign=0)
        hdr.set_markup('<span foreground="#3fd08f" size="x-large">TernOO · Widget Probe (GTK3)</span>')
        box.pack_start(hdr, False, False, 0)
        sub = Gtk.Label(xalign=0)
        sub.set_markup('<span foreground="#9696a5">reference scaffold — retained widget object model</span>')
        box.pack_start(sub, False, False, 0)

        trits = W.to_trits(W.SAMPLE)
        strip = Gtk.HBox(spacing=2)
        mono = Pango.FontDescription("DejaVu Sans Mono 14")
        for t in trits:
            cell = Gtk.Label()
            cell.set_markup('<span foreground="%s"><b>%s</b></span>' % (W.COLOR[t], W.GLYPH[t]))
            cell.modify_font(mono)
            strip.pack_start(cell, True, True, 0)
        box.pack_start(strip, False, False, 0)

        dec = Gtk.Label(xalign=0)
        dec.set_markup('<span foreground="#e8c890">primary: %s  (T23,T22 = %s,%s)</span>'
                       '   word = %d'
                       % (W.decode_primary(trits), W.GLYPH[trits[0]], W.GLYPH[trits[1]], W.SAMPLE))
        box.pack_start(dec, False, False, 0)
        box.pack_start(Gtk.Separator(), False, False, 0)

        lab = Gtk.Label(xalign=0)
        lab.set_markup('<span foreground="#9696a5">Notes — word-wrap + native cut/copy/paste (right-click)</span>')
        box.pack_start(lab, False, False, 0)
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        tv = Gtk.TextView()
        tv.set_wrap_mode(Gtk.WrapMode.WORD)
        tv.modify_font(Pango.FontDescription("DejaVu Sans Mono 11"))
        tv.get_buffer().set_text(W.MUSING)
        sw.add(tv)
        box.pack_start(sw, True, True, 0)

        ft = Gtk.Label(xalign=0)
        ft.set_markup('<span foreground="#9696a5">wrap: WORD · clipboard+context-menu: native · '
                      'undo: GTK4+ (absent in GTK3)</span>')
        box.pack_start(ft, False, False, 0)

        self.connect("destroy", Gtk.main_quit)
        self._benched = False
        if BENCH:
            self.connect("draw", self._bench_once)

    def _bench_once(self, *a):
        if self._benched:
            return False
        self._benched = True
        shown = time.perf_counter()
        print("BENCH kit=GTK3 import_ms=%.1f build_show_ms=%.1f startup_ms=%.1f rss_mb=%.1f"
              % ((T_IMPORT - T0) * 1000, (shown - T_IMPORT) * 1000, (shown - T0) * 1000, rss_mb()))
        GLib.timeout_add(60, Gtk.main_quit)
        return False


win = Probe()
win.show_all()
Gtk.main()
