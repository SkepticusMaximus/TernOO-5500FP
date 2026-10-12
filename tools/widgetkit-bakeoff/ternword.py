"""Shared TernOO word logic — identical for both demos (keeps the GUI LOC comparison fair)."""
PRIMARIES = {(-1, -1): "EXEC", (-1, 0): "MAP", (-1, 1): "DATA",
             (0, -1): "NEURAL", (0, 0): "I/O", (0, 1): "CRYPTO",
             (1, -1): "OPCODE", (1, 0): "OPEN_B", (1, 1): "POOL"}
GLYPH = {-1: "−", 0: "0", 1: "+"}          # U+2212 MINUS, 0, +
COLOR = {-1: "#ff8a8a", 0: "#9a9aac", 1: "#7dd3a0"}
SAMPLE = -31381059609                            # the Word Explorer's NEURAL sample


def to_trits(n, width=24):
    """Balanced-ternary, returned MSB-first (index 0 = T23 ... index 23 = T0)."""
    ts = [0] * width
    for i in range(width):
        r = n % 3
        n //= 3
        if r == 2:
            r = -1
            n += 1
        ts[i] = r
    return ts[::-1]


def decode_primary(trits):
    """trits MSB-first; primary = (T23, T22)."""
    return PRIMARIES.get((trits[0], trits[1]), "?")


MUSING = (
    "TernOO Widget Probe — word-wrap demo. This is the exact thing the DPG face cannot do: a "
    "long line of text that simply keeps going and going, well past the right edge of the box, and "
    "instead of scrolling sideways into oblivion it softly wraps at word boundaries so you can "
    "actually read your musing. Right-click for the native cut / copy / paste menu; selection, "
    "clipboard and (in Qt) undo/redo all come for free from the widget's own object model.\n\n"
    "Scooter idea: a GHOST AI on a Raspberry Pi, driving a retro-fitted mobility scooter with "
    "vision and infra-red sensors — a self-driving retrofit kit for a few hundred dollars "
    "instead of the $5,000–7,000 commercial units. Footpath-speed, keep-to-the-path, "
    "obstacle-stop: a co-pilot that won't let you hit things."
)
