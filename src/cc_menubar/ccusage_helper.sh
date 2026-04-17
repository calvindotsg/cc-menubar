#!/bin/bash
# Invoked by SwiftBar with terminal=false (runs under Process, no AppleScript).
# $1 = ccusage subcommand  ($2 optional, e.g. --active)
#
# On macOS, Ghostty cannot be launched from the CLI directly (per
# `ghostty --help`). `open -na Ghostty.app --args -e <path>` routes through
# the app bundle and runs that script.
set -eu

CCUSAGE="@@CCUSAGE_PATH@@"  # baked at install() time via shutil.which("ccusage")

tmpf=$(mktemp -t ccusage.XXXXXX.sh)
cat > "$tmpf" <<SH
#!/bin/bash
"$CCUSAGE" $1 ${2:-}
echo
read -n 1 -s -r -p 'press any key to close'
rm -f "\$0"
SH
chmod +x "$tmpf"

exec open -na Ghostty.app --args -e "$tmpf"
