#!/bin/bash
# Regenerate the DCMTK/GDCM cases in In/ from dcm_qa_xa30 (DCMTK 3.7.0, GDCM 3.2.7).
set -eu
src=${1:-../dcm_validate/dcm_qa_xa30/In}
out="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )/In"
rgb=$src/14_DWI_dir80_PA   # 8-bit RGB enhanced, 39 frames
fmap=$src/8_gre_field_mapping # two 12-bit enhanced files (e1, e2), 33 frames each
run() { # folder tool args... : apply tool to every file of the last arg (a series folder)
  local d=$out/$1 tool=$2; shift 2; local series=${@: -1}; set -- "${@:1:$#-1}"
  rm -rf "$d"; mkdir -p "$d"
  for f in "$series"/*; do $tool "$@" "$f" "$d/$(basename "$f")"; done
}
run gdcm_lossless_rgb gdcmconv -J "$rgb"        # SOF3 component IDs 'R','G','B'
run dcmtk_lossless_rgb dcmcjpeg +e1 "$rgb"       # control: component IDs 0,1,2
run dcmtk_baseline_rgb dcmcjpeg +eb "$rgb"       # control: YBR_FULL_422
run dcmtk_extended_rgb dcmcjpeg +ee "$rgb"      # 8-bit Process 2+4 (SOF1)
run dcmtk_baseline_fmap dcmcjpeg +eb "$fmap"    # multi-file series, per-frame offsets
run dcmtk_extended_fmap dcmcjpeg +ee "$fmap"    # 12-bit Process 2+4 (SOF1)
run dcmtk_fragments_fmap dcmcjpeg +e1 +fs 4 -ot "$fmap" # several fragments per frame, empty BOT
