#!/usr/bin/env bash
set -euo pipefail

# Generate platform icons (logo.ico / logo.icns) from the single source of truth:
# src/assets/logo.png
#
# Usage: npm run icons   (or directly: bash scripts/generate-icons.sh)
#
# - On macOS: uses built-in `sips` + `iconutil` (Xcode CLT recommended) to produce .icns
# - On Linux/Windows (with ImageMagick): produces .ico with common sizes
# - If tools are missing, prints actionable guidance and leaves existing icons in place.
#
# This keeps src/assets/logo.png as the only file designers ever need to touch.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ASSETS="$ROOT/src/assets"
PNG="$ASSETS/logo.png"
ICO="$ASSETS/logo.ico"
ICNS="$ASSETS/logo.icns"

if [[ ! -f "$PNG" ]]; then
  echo "ERROR: $PNG not found. Aborting icon generation."
  exit 1
fi

echo "Generating icons from master: $PNG"
echo ""

# --------------------------
# Windows / Linux: logo.ico
# --------------------------
generate_ico() {
  local cmd
  if command -v magick >/dev/null 2>&1; then
    cmd="magick"
  elif command -v convert >/dev/null 2>&1; then
    cmd="convert"
  else
    echo "  [skip] ImageMagick not found (magick/convert)."
    echo "         Install it (e.g. 'sudo apt install imagemagick' or 'brew install imagemagick')"
    echo "         then re-run to update src/assets/logo.ico automatically."
    return 0
  fi

  echo "  Generating logo.ico via $cmd (auto-resize to 256/128/64/48/32/16)..."
  "$cmd" "$PNG" -define icon:auto-resize=256,128,64,48,32,16 "$ICO"
  echo "  ✓ Updated $ICO"
}

# --------------------------
# macOS: logo.icns
# --------------------------
generate_icns() {
  if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "  [skip] Not running on macOS — cannot generate .icns here."
    echo "         Run this script on a Mac (or macOS CI) to refresh src/assets/logo.icns."
    return 0
  fi

  if ! command -v iconutil >/dev/null 2>&1 || ! command -v sips >/dev/null 2>&1; then
    echo "  [skip] iconutil or sips not found."
    echo "         Install Xcode Command Line Tools: xcode-select --install"
    return 0
  fi

  echo "  Generating logo.icns via sips + iconutil..."

  local ICONSET
  ICONSET="$(mktemp -d -t nora-iconset.XXXXXX)"

  # Standard sizes for a complete .iconset (including @2x retina variants)
  local sizes=(16 32 64 128 256 512 1024)
  for sz in "${sizes[@]}"; do
    sips -z "$sz" "$sz" "$PNG" --out "$ICONSET/icon_${sz}x${sz}.png" >/dev/null 2>&1
    if (( sz <= 512 )); then
      local sz2=$((sz * 2))
      sips -z "$sz2" "$sz2" "$PNG" --out "$ICONSET/icon_${sz}x${sz}@2x.png" >/dev/null 2>&1
    fi
  done

  iconutil -c icns -o "$ICNS" "$ICONSET" >/dev/null 2>&1
  rm -rf "$ICONSET"

  echo "  ✓ Updated $ICNS"
}

# Run both generators (they are platform-aware and skip gracefully)
generate_ico
generate_icns

echo ""
echo "Icon generation finished. Commit the updated .ico/.icns if they changed."
