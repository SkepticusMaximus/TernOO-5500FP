"""gguf_ternary.py — pull REAL ternary tensors out of a GGUF file, honestly.

DICK v0.2's first leg (captain's overnight go, 13-09): the kernel should
chew weights that came from an actual model, not a seed. Our Bonsai is a
TQ2_0 quant — genuinely ternary: each weight is a trit in {-1, 0, +1},
packed 2 bits each in 66-byte blocks (64 bytes of quants + fp16 scale),
per llama.cpp's ggml-common.h / dequantize_row_tq2_0 (read from source,
not guessed):

    for j in (0, 32):          # two 32-byte halves of the 64-byte qs
      for l in 0..3:           #   four 2-bit planes per byte
        for m in 0..31:        #     32 bytes per half
          q = (qs[j+m] >> (l*2)) & 3;  weight = q - 1

The fp16 per-block scale is RECORDED in the output (as its raw uint16)
but NEVER used in DICK math — the kernel is integer-only; scales are
future work (fixed-point), and pretending otherwise would smuggle floats
back in through the cargo hold.

Output: a canonical ".dick" weight file — JSON, sorted keys, no spaces —
carrying the trits base64-packed 4-per-byte in OUR defined row-major
order plus shape/provenance/crop metadata. Canonical bytes → the file's
sha256 is itself reproducible: the same GGUF on any machine yields the
IDENT identical .dick file. Weights become auditable cargo.

Usage:
  python3 gguf_ternary.py --list  MODEL.gguf                # ternary tensors
  python3 gguf_ternary.py --pull  MODEL.gguf TENSOR OUT.dick [--rows N] [--cols N]
  python3 gguf_ternary.py --info  OUT.dick                  # shape + sha256

Added: 13 Sep 2026 (night watch). Authors: Stevo + Claude.
"""

import base64
import hashlib
import json
import struct
import sys

GGUF_MAGIC = b"GGUF"
GGML_TYPE_TQ2_0 = 35
QK_K = 256
TQ2_BLOCK_BYTES = 66            # 64 qs + 2 fp16 scale

# GGUF metadata value types → (struct fmt, size) for scalars
_SCALAR = {0: ("<B", 1), 1: ("<b", 1), 2: ("<H", 2), 3: ("<h", 2),
           4: ("<I", 4), 5: ("<i", 4), 6: ("<f", 4), 7: ("<?", 1),
           10: ("<Q", 8), 11: ("<q", 8), 12: ("<d", 8)}


class _Reader:
    def __init__(self, f):
        self.f = f

    def u32(self):
        return struct.unpack("<I", self.f.read(4))[0]

    def u64(self):
        return struct.unpack("<Q", self.f.read(8))[0]

    def s(self):
        n = self.u64()
        return self.f.read(n).decode("utf-8", "replace")

    def value(self, vtype):
        if vtype in _SCALAR:
            fmt, size = _SCALAR[vtype]
            return struct.unpack(fmt, self.f.read(size))[0]
        if vtype == 8:                       # string
            return self.s()
        if vtype == 9:                       # array
            etype = self.u32()
            n = self.u64()
            return [self.value(etype) for _ in range(n)]
        raise ValueError(f"unknown GGUF value type {vtype}")


def read_header(path):
    """(tensor_infos, alignment, data_start). Skips metadata values but
    honours general.alignment — offsets are relative to the aligned data
    section, per the GGUF spec."""
    with open(path, "rb") as f:
        r = _Reader(f)
        if f.read(4) != GGUF_MAGIC:
            raise ValueError("not a GGUF file")
        version = r.u32()
        if version < 2:
            raise ValueError(f"GGUF v{version} too old")
        n_tensors = r.u64()
        n_kv = r.u64()
        alignment = 32
        for _ in range(n_kv):
            key = r.s()
            vtype = r.u32()
            val = r.value(vtype)
            if key == "general.alignment":
                alignment = int(val)
        infos = []
        for _ in range(n_tensors):
            name = r.s()
            n_dims = r.u32()
            dims = [r.u64() for _ in range(n_dims)]
            ttype = r.u32()
            offset = r.u64()
            infos.append({"name": name, "dims": dims, "type": ttype,
                          "offset": offset})
        pos = f.tell()
        data_start = (pos + alignment - 1) // alignment * alignment
        return infos, alignment, data_start


def unpack_tq2_block(block: bytes):
    """One 66-byte TQ2_0 block → (256 trits in {-1,0,+1}, raw fp16 scale).
    Loop order copied from llama.cpp's dequantize_row_tq2_0 verbatim."""
    qs = block[:64]
    (d_raw,) = struct.unpack("<H", block[64:66])
    out = []
    for j in (0, 32):
        for l in range(4):
            for m in range(32):
                q = (qs[j + m] >> (l * 2)) & 3
                if q > 2:
                    raise ValueError("non-ternary quant in TQ2_0 block")
                out.append(q - 1)
    return out, d_raw


def pull_tensor(path, tensor_name, rows=None, cols=None):
    """Extract one TQ2_0 tensor as a list-of-rows of trits (+ scales).
    GGUF dims are [ne0, ne1, ...] where ne0 is the CONTIGUOUS dimension —
    row length ne0, row count ne1 (2-D tensors). Optional crop keeps the
    demo-scale kernel fed without shipping 50M-trit matrices; the crop is
    RECORDED so the file never pretends to be the whole tensor."""
    infos, _al, data_start = read_header(path)
    info = next((t for t in infos if t["name"] == tensor_name), None)
    if info is None:
        raise KeyError(f"tensor not found: {tensor_name}")
    if info["type"] != GGML_TYPE_TQ2_0:
        raise TypeError(f"{tensor_name} is ggml type {info['type']}, "
                        f"not TQ2_0 ({GGML_TYPE_TQ2_0})")
    ne0 = info["dims"][0]
    ne1 = info["dims"][1] if len(info["dims"]) > 1 else 1
    if ne0 % QK_K:
        raise ValueError("row length not a multiple of QK_K")
    take_rows = min(rows or ne1, ne1)
    take_cols = min(cols or ne0, ne0)
    blocks_per_row = ne0 // QK_K
    row_bytes = blocks_per_row * TQ2_BLOCK_BYTES
    matrix, scales = [], []
    with open(path, "rb") as f:
        base = data_start + info["offset"]
        for r_i in range(take_rows):
            f.seek(base + r_i * row_bytes)
            trits, row_scales = [], []
            need_blocks = (take_cols + QK_K - 1) // QK_K
            for _b in range(need_blocks):
                t, d_raw = unpack_tq2_block(f.read(TQ2_BLOCK_BYTES))
                trits.extend(t)
                row_scales.append(d_raw)
            matrix.append(trits[:take_cols])
            scales.append(row_scales)
    meta = {"source_tensor": tensor_name, "source_dims": [ne0, ne1],
            "crop": [take_rows, take_cols]}
    return matrix, scales, meta


# ── the canonical .dick weight file ──────────────────────────────────────────
def pack_trits(matrix):
    """Row-major trits → base64, 4 trits/byte, OUR canonical order (row
    after row, 2 bits each, value = trit + 1, little slot first)."""
    flat = [t + 1 for row in matrix for t in row]
    while len(flat) % 4:
        flat.append(1)                        # pad with zeros (trit 0)
    raw = bytearray()
    for i in range(0, len(flat), 4):
        raw.append(flat[i] | (flat[i+1] << 2) | (flat[i+2] << 4)
                   | (flat[i+3] << 6))
    return base64.b64encode(bytes(raw)).decode("ascii")


def unpack_trits(b64, shape):
    rows, cols = shape
    raw = base64.b64decode(b64)
    flat = []
    for byte in raw:
        for s in range(4):
            flat.append(((byte >> (s * 2)) & 3) - 1)
    return [flat[r * cols:(r + 1) * cols] for r in range(rows)]


def write_dick_file(out_path, matrix, scales, meta):
    obj = {"v": 1, "kind": "dick-weights", "shape": [len(matrix),
           len(matrix[0]) if matrix else 0],
           "trits_b64": pack_trits(matrix),
           "scales_fp16_raw": scales, "meta": meta}
    blob = json.dumps(obj, separators=(",", ":"), sort_keys=True).encode()
    with open(out_path, "wb") as f:
        f.write(blob)
    return hashlib.sha256(blob).hexdigest()


def load_dick_file(path):
    blob = open(path, "rb").read()
    obj = json.loads(blob)
    if obj.get("kind") != "dick-weights":
        raise ValueError("not a .dick weight file")
    matrix = unpack_trits(obj["trits_b64"], obj["shape"])
    return matrix, obj, hashlib.sha256(blob).hexdigest()


def main(argv=None):
    a = list(sys.argv[1:] if argv is None else argv)
    if a[:1] == ["--list"]:
        infos, _, _ = read_header(a[1])
        for t in infos:
            if t["type"] == GGML_TYPE_TQ2_0:
                print(f"{t['name']}  dims={t['dims']}")
        return
    if a[:1] == ["--pull"]:
        opts = {"rows": None, "cols": None}
        for k in ("rows", "cols"):
            flag = f"--{k}"
            if flag in a:
                i = a.index(flag)
                opts[k] = int(a[i + 1])
                del a[i:i + 2]
        m, s, meta = pull_tensor(a[1], a[2], **opts)
        sha = write_dick_file(a[3], m, s, meta)
        print(f"wrote {a[3]}  shape={len(m)}x{len(m[0])}  sha256={sha}")
        return
    if a[:1] == ["--info"]:
        _m, obj, sha = load_dick_file(a[1])
        print(f"shape={obj['shape']}  meta={obj['meta']}  sha256={sha}")
        return
    print(__doc__)


if __name__ == "__main__":
    main()
