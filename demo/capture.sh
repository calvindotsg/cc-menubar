#!/usr/bin/env bash
# Capture the cc-menubar README hero screenshot.
#
# Prerequisites:
#   - cc-menubar installed and running in SwiftBar
#   - macOS dark mode + dark wallpaper (Liquid Glass vibrancy visible)
#   - Seeded quota: 5h at ~55% used (medium gauge glyph)
#   - Real Claude Code activity so every section renders
#
# Usage:
#   ./demo/capture.sh hero       # Capture the single README hero image
#   ./demo/capture.sh optimize   # Re-optimize existing PNGs
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

optimize() {
    for f in "$SCRIPT_DIR"/*.png; do
        [ -f "$f" ] || continue
        local before
        local after
        before=$(stat -f%z "$f")
        sips -s format png -s formatOptions best "$f" --out "$f" >/dev/null 2>&1
        after=$(stat -f%z "$f")
        echo "$(basename "$f"): $(( before / 1024 ))KB → $(( after / 1024 ))KB"
    done
}

case "${1:-help}" in
    hero)
        cat <<'EOM'
Capture the single README hero image.

Setup checklist:
  1. Ensure cc-menubar is installed and running in SwiftBar.
  2. Dark mode + dark wallpaper. macOS 14+ Liquid Glass vibrancy visible.
  3. Seed a 'medium' 5-hour state:
         FIVE_H=$(date -v+4H -v+12M +%s); SEVEN_D=$(date -v+5d +%s)
         printf '{"rate_limits":{"five_hour":{"used_percentage":55,"resets_at":%d},"seven_day":{"used_percentage":32,"resets_at":%d}}}' \
           "$FIVE_H" "$SEVEN_D" > ~/Library/Caches/cc-menubar/statusline-input.json
         open -g "swiftbar://refreshallplugins"
  4. Ensure recent Claude Code activity so Activity, Projects, Tools,
     Model Mix, Context Size all render.
  5. Click the gauge icon to open the dropdown (all six sections
     folded — do NOT hover-expand any submenu).

Capture (after 3s delay):
  6. Crosshair cursor appears — drag a region from just above the
     menu bar (to include 3-4 neighbour system icons) down through
     the full expanded dropdown. Single frame.
EOM
        sleep 3
        screencapture -i "$SCRIPT_DIR/hero.png"
        echo "Saved: $SCRIPT_DIR/hero.png"
        optimize
        ;;
    optimize)
        optimize
        ;;
    *)
        echo "Usage: $0 {hero|optimize}"
        exit 1
        ;;
esac
