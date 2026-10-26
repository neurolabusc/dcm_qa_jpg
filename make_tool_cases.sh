#!/bin/bash
# Regenerate the DCMTK/GDCM cases in In/ from dcm_qa_xa30 (DCMTK 3.7.0, GDCM 3.2.7).
# usage: make_tool_cases.sh [dcm_qa_xa30/In]  (default assumes the dcm_validate submodule layout)
set -eu
here="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
src=${1:-$here/../dcm_qa_xa30/In}
out=$here/In
rgb=$src/14_DWI_dir80_PA      # 8-bit RGB enhanced, 39 frames
fmap=$src/8_gre_field_mapping # two 12-bit enhanced files (e1, e2), 33 frames each
[ -d "$rgb" ] && [ -d "$fmap" ] || { echo "dcm_qa_xa30 series not found in $src"; exit 1; }
run() { # folder series cmd... : apply cmd to every file of series
  local d=$out/$1 series=$2; shift 2
  rm -rf "$d"; mkdir -p "$d"
  for f in "$series"/*; do "$@" "$f" "$d/${f##*/}"; done
}
run gdcm_lossless_rgb "$rgb" gdcmconv -J            # SOF3 component IDs 'R','G','B'
run dcmtk_lossless_rgb "$rgb" dcmcjpeg +e1          # control: component IDs 0,1,2
run dcmtk_baseline_rgb "$rgb" dcmcjpeg +eb          # control: YBR_FULL_422
run dcmtk_extended_rgb "$rgb" dcmcjpeg +ee          # 8-bit Process 2+4 (SOF1)
run dcmtk_baseline_fmap "$fmap" dcmcjpeg +eb        # multi-file series, per-frame offsets
run dcmtk_extended_fmap "$fmap" dcmcjpeg +ee        # 12-bit Process 2+4 (SOF1)
run dcmtk_fragments_fmap "$fmap" dcmcjpeg +e1 +fs 4 -ot # several fragments per frame, empty BOT
