#!/usr/bin/env bash
# Capture cc-menubar README screenshots.
#
# Prerequisites:
#   - cc-menubar installed and running in SwiftBar
#   - macOS dark mode + dark wallpaper
#   - Real Claude Code usage data
#
# Usage:
#   ./demo/capture.sh icon       # Capture menu bar strip
#   ./demo/capture.sh dropdown   # Capture expanded dropdown
#   ./demo/capture.sh optimize   # Optimize existing PNGs
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

optimize() {
    for f in "$SCRIPT_DIR"/*.png; do
        [ -f "$f" ] || continue
        local before=$(stat -f%z "$f")
        sips -s format png -s formatOptions best "$f" --out "$f" >/dev/null 2>&1
        local after=$(stat -f%z "$f")
        echo "$(basename "$f"): $(( before / 1024 ))KB → $(( after / 1024 ))KB"
    done
}

case "${1:-help}" in
    icon)
        echo "Capture the menu bar strip showing the gauge icon."
        echo "Steps:"
        echo "  1. Ensure cc-menubar is running in SwiftBar"
        echo "  2. A crosshair cursor will appear — select the menu bar region"
        echo "     around the gauge icon (include a few neighboring icons for context)"
        screencapture -i "$SCRIPT_DIR/menubar.png"
        echo "Saved: $SCRIPT_DIR/menubar.png"
        optimize
        ;;
    dropdown)
        echo "Capture the expanded dropdown."
        echo "Steps:"
        echo "  1. Click the gauge icon to open the dropdown"
        echo "  2. A crosshair cursor will appear after 3 seconds — select the dropdown"
        sleep 3
        screencapture -i "$SCRIPT_DIR/dropdown.png"
        echo "Saved: $SCRIPT_DIR/dropdown.png"
        optimize
        ;;
    optimize)
        optimize
        ;;
    *)
        echo "Usage: $0 {icon|dropdown|optimize}"
        exit 1
        ;;
esac
