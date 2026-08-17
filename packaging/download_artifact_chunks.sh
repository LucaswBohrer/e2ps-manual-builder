#!/usr/bin/env bash
set -euo pipefail
URL="${1:?artifact URL required}"
TOKEN="${2:?token required}"
OUT_DIR="${3:?output directory required}"
TOTAL="${4:?total bytes required}"
PARTS="${5:-8}"
mkdir -p "$OUT_DIR"
CHUNK=$(( (TOTAL + PARTS - 1) / PARTS ))
export URL TOKEN OUT_DIR TOTAL PARTS CHUNK
seq 0 $((PARTS - 1)) | xargs -P "$PARTS" -I{} bash -c '
  i="$1"
  start=$((i * CHUNK))
  end=$((start + CHUNK - 1))
  if [ "$end" -ge "$TOTAL" ]; then end=$((TOTAL - 1)); fi
  curl --fail --silent --show-error --location --retry 5 --retry-all-errors --retry-delay 3 \
    --max-time 300 -H "Authorization: Bearer $TOKEN" -H "Range: bytes=${start}-${end}" \
    -o "$OUT_DIR/part_$i" "$URL"
' _ {}
cat "$OUT_DIR"/part_* > "$OUT_DIR/artifact.zip"
actual=$(stat -c '%s' "$OUT_DIR/artifact.zip")
if [ "$actual" -ne "$TOTAL" ]; then
  echo "download size mismatch: expected $TOTAL, got $actual" >&2
  exit 1
fi
echo "$OUT_DIR/artifact.zip $actual bytes"
