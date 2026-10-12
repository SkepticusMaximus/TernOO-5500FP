# Widget-kit bake-off — PySide6 vs GTK3 (DPG as baseline)

Reference-scaffold evaluation (2026-10-10). Question: which **retained-mode** widget
kit best serves as the "grist" whose object model we dissect to forge the TernOO-native
widget kit (TernUI)? DPG/ImGui is **immediate-mode** — it has *no retained widget object
model to mine* — so it appears only as the incumbent baseline, not a candidate.

All three demos render the *same* probe: a 24-trit strip (TernOO word `-31381059609`,
decodes to **NEURAL**), a primary-decode line, and a multiline notes editor pre-filled
with a long musing to test word-wrap.

## Run
```bash
# GTK3  (system python has PyGObject)
DISPLAY=:0 python3 demo_gtk.py              # add --bench for startup/RSS
# PySide6  (venv python; needs libxcb-cursor0 — see note)
DISPLAY=:0 ~/.venvs/p2pcp/bin/python3 demo_qt.py
# object-model teardown (the grist)
python3 dump.py gtk        #   ~/.venvs/p2pcp/bin/python3 dump.py qt
# word-layer micro-benchmark
python3 bench_word.py
```
PySide6's xcb plugin needs `libxcb-cursor0` (Qt ≥ 6.5). Without sudo:
```bash
apt-get download libxcb-cursor0 && dpkg -x libxcb-cursor0*.deb xcbcursor
export LD_LIBRARY_PATH=$PWD/xcbcursor/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH
```

## Numbers (HP, X11; startup = process-start → first frame; 3-run median)
| kit     | startup | RSS   | text-widget props | native wrap | native undo |
|---------|---------|-------|-------------------|-------------|-------------|
| DPG     | ~96 ms  | 93 MB | — (immediate-mode: no object model) | **no** | no |
| GTK3    | ~117 ms | 47 MB | 67 (GtkTextView)  | yes | GTK4+ only |
| PySide6 | ~165 ms | 81 MB | 87 (QTextEdit)    | yes | **native** |

**Word layer:** int→24-trit encode ~1.5 µs/word; primary-decode ~0.14 µs — about
**11,000 whole-word encodes per 60 fps frame**. Negligible, and *orthogonal to the kit*:
the word system is a thin data layer under whatever widget kit, identical cost either way.
(Native C via `libternoo_c.so` would be ~10–50× faster again.)

## Object-model lineages (the thing DPG structurally cannot give)
```
GtkTextView : GtkTextView → GtkContainer → GtkWidget → GInitiallyUnowned → GObject
QTextEdit   : QTextEdit  → QAbstractScrollArea → QFrame → QWidget → QObject
```
Full property dumps: `objmodel_gtk.txt` (67), `objmodel_qt.txt` (87).

## Finding
Both candidates hand over a clean retained inheritance graph **plus** a full property set
to forge into TernOO words — each property (`wrap-mode`, `editable`, `buffer`/`document`,
margins, `undoRedoEnabled`…) is a candidate word/field; each inheritance layer is a TernUI
class. **PySide6's model is richer (87 vs 67) and exposes a full `QTextDocument`**
(plainText/markdown/html/undo) — the best available blueprint for the native text/char-map
charter. **GTK3** is the lighter, purer-FOSS alternative (GObject is itself a studyable
from-scratch type system) but GTK3's text widget lacks native undo (GTK4 adds it).

Costs that do **not** matter for a reference scaffold: PySide6's ~2× startup and ~1.7× RSS
vs GTK are irrelevant — the scaffold runs on the dev box for *dissection*, never on the Pi.
The dissected model informs TernUI, which is native and light.

**Recommendation: PySide6 for the reference role** (maximal grist + best text model);
GTK3 the principled lighter alternative. Choice is temperament, not capability.
