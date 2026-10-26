## About

Synthetic JPEG Lossless (`1.2.840.10008.1.2.4.70`, SOF3) DICOMs for dcm2niix [issue 1054](https://github.com/rordenlab/dcm2niix/issues/1054). The JPEG component identifier `Ci` may be any value 0..255 (ITU-T T.81 B.2.2), but the SOF3 decoder in `jpg_0XC3_helper.h` used it as an array index, writing out of bounds when `Ci` > number of components.

`In/` was written by `make_sof3_cid_repro.py` (Python 3 standard library only), copied from the issue:

```
python3 make_sof3_cid_repro.py In 0 1 87 255
```

Each `In/cid<N>/image.dcm` is a 32×32 16-bit gradient; the files differ only in the SOF3 `Ci` byte and matching SOS `Cs` byte, so all `Ref/` images are identical and match `In/expected_pixels.txt`. The files share UIDs, so `batch.sh` converts each folder separately. Libjpeg-turbo labels RGB components 82, 71, 66 ('R','G','B'); 16-bit monochrome files with `Ci = 87` have been seen in the wild.

Unpatched dcm2niix (v1.0.20260416 to v1.0.20261024) overflows the heap on `cid87` and `cid255`; optimized builds may still pass by luck, so also test with an AddressSanitizer build (`make sanitize`).

The synthetic files are valid: DCMTK 3.7.0 (`dcmdjpeg`), GDCM 3.2.7 (`gdcmconv --raw`), libjpeg-turbo 3.2.0 (`djpeg` on the extracted codestream) and libdicom all read them, and every decoder reproduces `expected_pixels.txt` exactly.

## DCMTK and GDCM cases

`make_tool_cases.sh` recompresses two [dcm_qa_xa30](https://github.com/neurolabusc/dcm_qa_xa30) series (8-bit RGB DWI `14`, two-file 12-bit field map `8`) with DCMTK 3.7.0 and GDCM 3.2.7. Except the controls, each breaks dcm2niix v1.0.20261024, though DCMTK and GDCM decode them:

- `gdcm_lossless_rgb` — `gdcmconv -J`: GDCM labels lossless RGB components 'R','G','B' (82, 71, 66), the issue 1054 overflow. Optimized builds may pass by luck; use AddressSanitizer.
- `dcmtk_lossless_rgb` (`dcmcjpeg +e1`, component IDs 0, 1, 2) and `dcmtk_baseline_rgb` (`dcmcjpeg +eb`, `YBR_FULL_422`) — RGB controls that already convert.
- `dcmtk_baseline_fmap` — `dcmcjpeg +eb`: echo 1 is decoded with the frame offsets of echo 2, which is read last, so it fails. RLE, JPEG-LS and JPEG 2000 fail the same way, while lossless JPEG survives because its decoder scans for markers. Each file converts on its own.
- `dcmtk_extended_rgb`, `dcmtk_extended_fmap` — `dcmcjpeg +ee`: Extended JPEG (Process 2+4, `1.2.840.10008.1.2.4.51`), 8-bit and 12-bit; not decoded.
- `dcmtk_fragments_fmap` — `dcmcjpeg +e1 +fs 4 -ot`: several fragments per frame, empty Basic Offset Table; not supported.

`Ref/` for these was made by decompressing with `dcmdjpeg` and converting with dcm2niix. Sidecars match those of the compressed files. The baseline images instead hold dcm2niix's own decode, which differs from DCMTK's by ±1 in places. The extended (lossy) images hold DCMTK's decode, so a new decoder may need its `Ref/` regenerated.

## Running

Run `batch.sh`. It converts `In/` → `Out/` and diffs against `Ref/`.
