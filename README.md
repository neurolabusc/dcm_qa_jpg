## About

Synthetic JPEG Lossless (`1.2.840.10008.1.2.4.70`, SOF3) DICOMs for dcm2niix [issue 1054](https://github.com/rordenlab/dcm2niix/issues/1054). The JPEG component identifier `Ci` may be any value 0..255 (ITU-T T.81 B.2.2), but the SOF3 decoder in `jpg_0XC3_helper.h` used it as an array index, writing out of bounds when `Ci` > number of components.

`In/` was written by `make_sof3_cid_repro.py` (Python 3 standard library only), copied from the issue:

```
python3 make_sof3_cid_repro.py In 0 1 87 255
```

Each `In/cid<N>/image.dcm` is a 32×32 16-bit gradient; the files differ only in the SOF3 `Ci` byte and matching SOS `Cs` byte, so all `Ref/` images are identical and match `In/expected_pixels.txt`. The files share UIDs, so `batch.sh` converts each folder separately. Libjpeg-turbo labels RGB components 82, 71, 66 ('R','G','B'); 16-bit monochrome files with `Ci = 87` have been seen in the wild.

Unpatched dcm2niix (v1.0.20260416 to v1.0.20261024) overflows the heap on `cid87` and `cid255`; optimized builds may still pass by luck, so also test with an AddressSanitizer build (`make sanitize`).

## Running

Run `batch.sh`. It converts `In/` → `Out/` and diffs against `Ref/`.
