#!/home/stevo/.venvs/p2pcp/bin/python3
"""TernOO · TernQR — QR maker (PySide6, GrOOM reference).

Point a phone at a print article → a website or digital artifact. Type a URL,
pick error-correction (H for print robustness), save PNG/SVG for the layout.

The module draw is deliberately pluggable (render_pixmap) so a future TernOO
ternary-glyph block style — our in-house char-word font for the QR cells — can
drop in without touching the UI (list item g20).
"""
import sys
import segno
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton, QComboBox, QFileDialog)
from PySide6.QtGui import QImage, QPixmap, QColor, QPainter
from PySide6.QtCore import Qt

DEFAULT = "https://github.com/SkepticusMaximus"


def render_pixmap(rows, scale=8, border=4, fg="#0b0b12", bg="#ffffff"):
    n = len(rows)
    size = (n + 2 * border) * scale
    img = QImage(size, size, QImage.Format.Format_RGB32)
    img.fill(QColor(bg))
    p = QPainter(img)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(fg))
    for y, row in enumerate(rows):
        for x, v in enumerate(row):
            if v:
                p.drawRect((x + border) * scale, (y + border) * scale, scale, scale)
    p.end()
    return QPixmap.fromImage(img)


class TernQR(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TernOO · TernQR")
        self.resize(460, 620)
        self.qr = None
        v = QVBoxLayout(self)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(8)
        hdr = QLabel("TernOO · TernQR")
        hdr.setStyleSheet("color:#3fd08f;font-size:17px;")
        v.addWidget(hdr)
        sub = QLabel("point a phone at a print article → a website or artifact  (GrOOM reference)")
        sub.setStyleSheet("color:#9696a5;")
        v.addWidget(sub)

        row = QHBoxLayout()
        row.addWidget(QLabel("URL / text:"))
        self.inp = QLineEdit(DEFAULT)
        self.inp.returnPressed.connect(self.make)
        row.addWidget(self.inp, 1)
        v.addLayout(row)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("error-correction:"))
        self.ecc = QComboBox()
        for lab, code in [("L (7%)", "l"), ("M (15%)", "m"), ("Q (25%)", "q"),
                          ("H (30%) — print", "h")]:
            self.ecc.addItem(lab, code)
        self.ecc.setCurrentIndex(3)
        self.ecc.currentIndexChanged.connect(self.make)
        row2.addWidget(self.ecc, 1)
        gen = QPushButton("Make QR")
        gen.clicked.connect(self.make)
        row2.addWidget(gen)
        v.addLayout(row2)

        self.canvas = QLabel()
        self.canvas.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.canvas.setStyleSheet("background:#ffffff;border:1px solid #3a3a52;")
        self.canvas.setMinimumHeight(340)
        v.addWidget(self.canvas, 1)
        self.cap = QLabel("")
        self.cap.setStyleSheet("color:#9696a5;")
        self.cap.setWordWrap(True)
        v.addWidget(self.cap)

        row3 = QHBoxLayout()
        sp = QPushButton("Save PNG…")
        sp.clicked.connect(lambda: self.save("png"))
        row3.addWidget(sp)
        sv = QPushButton("Save SVG…")
        sv.clicked.connect(lambda: self.save("svg"))
        row3.addWidget(sv)
        row3.addStretch(1)
        v.addLayout(row3)
        self.make()

    def make(self, *_):
        txt = self.inp.text().strip() or DEFAULT
        try:
            self.qr = segno.make(txt, error=self.ecc.currentData())
        except Exception as e:
            self.cap.setText("error: %s" % e)
            return
        rows = list(self.qr.matrix)
        self.canvas.setPixmap(render_pixmap(rows, scale=8))
        self.cap.setText("“%s”\nversion %s · ECC %s · %d×%d modules"
                         % (txt, self.qr.version, self.ecc.currentData().upper(),
                            len(rows), len(rows)))

    def save(self, fmt):
        if not self.qr:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save QR", "ternqr." + fmt,
                                              "%s (*.%s)" % (fmt.upper(), fmt))
        if path:
            self.qr.save(path, scale=10, border=4)
            self.cap.setText("saved: " + path)


DARK = ("QWidget{background:#1a1f2b;color:#e6e6ec;}"
        "QLineEdit,QComboBox{background:#15151f;border:1px solid #3a3a52;}"
        "QPushButton{background:#2e466e;border:1px solid #5a82be;border-radius:4px;padding:3px 10px;}")


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK)
    w = TernQR()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
