#!/usr/bin/env python3
"""Build a tiny synthetic DICOM that uses JPEG Lossless (1.2.840.10008.1.2.4.70).

Python 3 standard library only. No real data: a 32x32, 16-bit gradient image.

    python3 make_sof3_cid_repro.py OUTDIR [COMPONENT_ID ...]

writes OUTDIR/cid<N>/image.dcm for every requested JPEG component identifier
(default: 1 and 87), plus OUTDIR/expected_pixels.txt. The files are identical
except for the one "Ci" byte in the SOF3 header and the matching "Cs" byte in
the SOS header. Each goes in its own folder because dcm2niix scans the whole
folder of an input file.
JPEG allows Ci to be any value 0..255 (ITU-T T.81 B.2.2).
"""
import os
import struct
import sys
import uuid

ROWS = COLS = 32
TS_UID = "1.2.840.10008.1.2.4.70"            # JPEG Lossless, First-Order Prediction
MR_SOP_CLASS = "1.2.840.10008.5.1.4.1.1.4"   # MR Image Storage


def uid(name):  # deterministic synthetic UID under the 2.25 (UUID) arc
    return "2.25.%d" % uuid.uuid5(uuid.NAMESPACE_URL, "synthetic-sof3-repro/" + name).int


def pixels():
    """Deterministic gradient plus a little pseudo-noise (16-bit)."""
    out, s = [], 12345
    for y in range(ROWS):
        for x in range(COLS):
            s = (s * 1103515245 + 12345) & 0x7FFFFFFF
            out.append(500 + 40 * x + 25 * y + ((s >> 16) & 15))
    return out


def lossless_jpeg(samples, cid):
    """Single-component, 16-bit, predictor 1 (Ra) lossless JPEG (SOF3)."""
    # one DC-style Huffman table: 17 symbols (SSSS 0..16), all with 5-bit codes
    bits = [0] * 16
    bits[4] = 17
    dht = bytes([0x00]) + bytes(bits) + bytes(range(17))
    sof = struct.pack(">BHHB", 16, ROWS, COLS, 1) + bytes([cid, 0x11, 0x00])
    sos = bytes([1, cid, 0x00, 1, 0, 0x00])  # Ns=1, Cs=cid, Td/Ta=0, Ss=1 (predictor), Se=0, Ah/Al=0

    acc, nacc, data = 0, 0, bytearray()

    def put(value, n):
        nonlocal acc, nacc
        acc = (acc << n) | (value & ((1 << n) - 1))
        nacc += n
        while nacc >= 8:
            b = (acc >> (nacc - 8)) & 0xFF
            data.append(b)
            if b == 0xFF:
                data.append(0x00)  # byte stuffing
            nacc -= 8
        acc &= (1 << nacc) - 1

    for y in range(ROWS):
        for x in range(COLS):
            v = samples[y * COLS + x]
            if y == 0 and x == 0:
                pred = 1 << 15                      # 2^(P-1)
            elif x == 0:
                pred = samples[(y - 1) * COLS]       # first column: sample above
            else:
                pred = samples[y * COLS + x - 1]     # predictor 1: sample to the left
            d = (v - pred) & 0xFFFF
            if d >= 0x8000:
                d -= 0x10000
            ssss = abs(d).bit_length()
            put(ssss, 5)                              # Huffman code of symbol ssss (5 bits)
            if 0 < ssss < 16:
                put(d if d > 0 else d + (1 << ssss) - 1, ssss)
    if nacc:
        put((1 << (8 - nacc)) - 1, 8 - nacc)          # pad with 1-bits

    def seg(marker, body):
        return bytes([0xFF, marker]) + struct.pack(">H", len(body) + 2) + body

    return (b"\xFF\xD8" + seg(0xC4, dht) + seg(0xC3, sof) + seg(0xDA, sos)
            + bytes(data) + b"\xFF\xD9")


def el(group, elem, vr, value):
    if isinstance(value, str):
        value = value.encode("ascii")
    if len(value) % 2:
        value += b"\x00" if vr == "UI" else b" "
    head = struct.pack("<HH", group, elem) + vr.encode("ascii")
    if vr in ("OB", "OW", "UN", "SQ", "UT"):
        return head + b"\x00\x00" + struct.pack("<I", len(value)) + value
    return head + struct.pack("<H", len(value)) + value


def us(g, e, v):
    return el(g, e, "US", struct.pack("<H", v))


def build_dicom(cid):
    jpg = lossless_jpeg(pixels(), cid)
    if len(jpg) % 2:
        jpg += b"\x00"
    sop_inst = uid("instance")
    meta_body = b"".join([
        el(0x0002, 0x0001, "OB", b"\x00\x01"),
        el(0x0002, 0x0002, "UI", MR_SOP_CLASS),
        el(0x0002, 0x0003, "UI", sop_inst),
        el(0x0002, 0x0010, "UI", TS_UID),
        el(0x0002, 0x0012, "UI", uid("implementation")),
    ])
    meta = el(0x0002, 0x0000, "UL", struct.pack("<I", len(meta_body))) + meta_body
    ds = b"".join([
        el(0x0008, 0x0016, "UI", MR_SOP_CLASS),
        el(0x0008, 0x0018, "UI", sop_inst),
        el(0x0008, 0x0060, "CS", "MR"),
        el(0x0010, 0x0010, "PN", "SYNTHETIC"),
        el(0x0010, 0x0020, "LO", "SYNTH0001"),
        el(0x0018, 0x0050, "DS", "1"),
        el(0x0020, 0x000D, "UI", uid("study")),
        el(0x0020, 0x000E, "UI", uid("series")),
        el(0x0020, 0x0011, "IS", "1"),
        el(0x0020, 0x0013, "IS", "1"),
        el(0x0020, 0x0032, "DS", "0\\0\\0"),
        el(0x0020, 0x0037, "DS", "1\\0\\0\\0\\1\\0"),
        us(0x0028, 0x0002, 1),
        el(0x0028, 0x0004, "CS", "MONOCHROME2"),
        us(0x0028, 0x0010, ROWS),
        us(0x0028, 0x0011, COLS),
        el(0x0028, 0x0030, "DS", "1\\1"),
        us(0x0028, 0x0100, 16),
        us(0x0028, 0x0101, 16),
        us(0x0028, 0x0102, 15),
        us(0x0028, 0x0103, 0),
    ])
    pixel = (struct.pack("<HH", 0x7FE0, 0x0010) + b"OB\x00\x00" + struct.pack("<I", 0xFFFFFFFF)
             + struct.pack("<HHI", 0xFFFE, 0xE000, 0)                   # empty basic offset table
             + struct.pack("<HHI", 0xFFFE, 0xE000, len(jpg)) + jpg     # one fragment = whole frame
             + struct.pack("<HHI", 0xFFFE, 0xE0DD, 0))                  # sequence delimiter
    return b"\x00" * 128 + b"DICM" + meta + ds + pixel


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    outdir = argv[1]
    cids = [int(a) for a in argv[2:]] or [1, 87]
    os.makedirs(outdir, exist_ok=True)
    for cid in cids:
        os.makedirs(os.path.join(outdir, "cid%d" % cid), exist_ok=True)
        path = os.path.join(outdir, "cid%d" % cid, "image.dcm")
        with open(path, "wb") as f:
            f.write(build_dicom(cid))
        print("wrote", path)
    with open(os.path.join(outdir, "expected_pixels.txt"), "w") as f:
        f.write(" ".join(str(v) for v in pixels()) + "\n")


if __name__ == "__main__":
    main(sys.argv)
