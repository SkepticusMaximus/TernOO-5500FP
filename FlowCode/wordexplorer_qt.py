#!/home/stevo/.venvs/p2pcp/bin/python3
"""TernOO · 24-trit Word Format Explorer — PySide6 edition (GrOOM reference app).

Edit the word value or click a primary; the 24-trit strip, the primary selection
and the decode panel all stay in sync. Word = 2 trit PRIMARY · 4 trit QUALIFIER ·
18 trit PAYLOAD.
"""
import sys
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                               QLabel, QLineEdit, QPushButton, QRadioButton, QButtonGroup,
                               QFrame, QTextEdit, QGroupBox)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

PRIMS = [  # (glyphs, (T23,T22), name, blurb)
    ("−−", (-1, -1), "EXEC", "Executable / control flow."),
    ("−0", (-1, 0), "MAP", "Addressing · references · content-addresses."),
    ("−+", (-1, 1), "DATA", "Literal data · values · flags."),
    ("0−", (0, -1), "NEURAL", "Neural primitives — 9-level ternary weights (±4); "
                              "exceed BitNet {−1,0,+1}."),
    ("00", (0, 0), "I/O", "Input · output · devices · widgets."),
    ("0+", (0, 1), "CRYPTO", "Capability words · identity · grants (TernID)."),
    ("+−", (1, -1), "OPCODE", "Instruction opcodes."),
    ("+0", (1, 0), "OPEN_B", "Open block · reserved-B."),
    ("++", (1, 1), "POOL", "Dynamic allocation · pools."),
]
BYPAIR = {p[1]: p for p in PRIMS}
GLY = {-1: "−", 0: "0", 1: "+"}
COL = {-1: "#ff8a8a", 0: "#9a9aac", 1: "#7dd3a0"}
SAMPLE = -31381059609


def to_trits(n, w=24):
    ts = [0] * w
    for i in range(w):
        r = n % 3
        n //= 3
        if r == 2:
            r = -1
            n += 1
        ts[i] = r
    return ts[::-1]


def from_trits(ts):
    n = 0
    for t in ts:
        n = n * 3 + t
    return n


class WordExplorer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TernOO · Word Format Explorer (PySide6)")
        self.resize(720, 560)
        self.trits = to_trits(SAMPLE)
        v = QVBoxLayout(self)
        v.setContentsMargins(12, 10, 12, 10)
        v.setSpacing(8)
        hdr = QLabel("TernOO · 24-trit Word Format Explorer")
        hdr.setStyleSheet("color:#3fd08f;font-size:17px;")
        v.addWidget(hdr)
        sub = QLabel("2 + 4 + 18 trits  —  primary · qualifier · payload   (GrOOM reference)")
        sub.setStyleSheet("color:#9696a5;")
        v.addWidget(sub)

        row = QHBoxLayout()
        row.addWidget(QLabel("word ="))
        self.valedit = QLineEdit(str(SAMPLE))
        self.valedit.returnPressed.connect(self._from_value)
        row.addWidget(self.valedit, 1)
        for lbl, fn in (("Sample", lambda: self._set_value(SAMPLE)),
                        ("Zero", lambda: self._set_value(0))):
            b = QPushButton(lbl)
            b.clicked.connect(fn)
            row.addWidget(b)
        v.addLayout(row)

        self.stripbox = QGridLayout()
        self.stripbox.setHorizontalSpacing(1)
        sb = QWidget()
        sb.setLayout(self.stripbox)
        v.addWidget(sb)
        seg = QLabel("T23–T22  type        T21–T18  qualifier        T17–T0  payload")
        seg.setStyleSheet("color:#9696a5;")
        seg.setFont(QFont("DejaVu Sans Mono", 9))
        v.addWidget(seg)
        f = QFrame()
        f.setFrameShape(QFrame.Shape.HLine)
        v.addWidget(f)

        body = QHBoxLayout()
        gb = QGroupBox("primary type (click to set)")
        gl = QVBoxLayout(gb)
        self.grp = QButtonGroup(self)
        self.radios = []
        for i, (g, pair, name, blurb) in enumerate(PRIMS):
            rb = QRadioButton("%s  %s" % (g, name))
            self.grp.addButton(rb, i)
            gl.addWidget(rb)
            self.radios.append(rb)
        self.grp.idClicked.connect(self._from_primary)
        body.addWidget(gb)
        self.decode = QTextEdit()
        self.decode.setReadOnly(True)
        self.decode.setFont(QFont("DejaVu Sans Mono", 10))
        body.addWidget(self.decode, 1)
        v.addLayout(body, 1)
        self._render()

    def _set_value(self, n):
        self.trits = to_trits(n)
        self._render()

    def _from_value(self):
        try:
            self._set_value(int(self.valedit.text()))
        except ValueError:
            pass

    def _from_primary(self, i):
        self.trits[0], self.trits[1] = PRIMS[i][1]
        self._render()

    def _render(self):
        while self.stripbox.count():
            it = self.stripbox.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        for idx, t in enumerate(self.trits):
            num = QLabel(str(23 - idx))
            num.setStyleSheet("color:#6a6a7a;")
            num.setFont(QFont("DejaVu Sans Mono", 7))
            num.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cell = QLabel(GLY[t])
            cell.setStyleSheet("color:%s;background:#15151f;border:1px solid #2a2a3a;" % COL[t])
            cell.setFont(QFont("DejaVu Sans Mono", 14))
            cell.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cell.setFixedWidth(26)
            self.stripbox.addWidget(num, 0, idx)
            self.stripbox.addWidget(cell, 1, idx)
        val = from_trits(self.trits)
        self.valedit.setText(str(val))
        pair = (self.trits[0], self.trits[1])
        g, _, name, blurb = BYPAIR.get(pair, ("??", pair, "?", "unknown"))
        for i, (gg, pp, nn, bb) in enumerate(PRIMS):
            if pp == pair:
                self.radios[i].setChecked(True)
        qual = from_trits(self.trits[2:6])
        payload = from_trits(self.trits[6:24])
        self.decode.setHtml(
            "<div style='color:#3fd08f;font-size:15px'>%s &nbsp;"
            "<span style='color:#888'>(%s)</span></div>"
            "<div style='color:#e8c890'>T23,T22 = %s,%s</div>"
            "<p style='color:#cfcfe0'>%s</p>"
            "<div style='color:#9696a5'>qualifier (T21–T18) = "
            "<b style='color:#e6e6ec'>%d</b> of 0..80<br>"
            "payload (T17–T0) = <b style='color:#e6e6ec'>%d</b><br>"
            "word value = <b style='color:#e6e6ec'>%d</b></div>"
            % (name, g, GLY[pair[0]], GLY[pair[1]], blurb, qual, payload, val))


DARK = ("QWidget{background:#1a1f2b;color:#e6e6ec;}"
        "QLineEdit,QTextEdit{background:#15151f;border:1px solid #3a3a52;}"
        "QGroupBox{border:1px solid #3a3a52;margin-top:8px;padding-top:6px;}"
        "QGroupBox::title{color:#9696a5;subcontrol-origin:margin;left:8px;}"
        "QPushButton{background:#2e466e;border:1px solid #5a82be;border-radius:4px;padding:3px 10px;}")


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK)
    w = WordExplorer()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
