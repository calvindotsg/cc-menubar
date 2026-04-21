#!/bin/bash
# Invoked by SwiftBar with terminal=false (runs under Process, no AppleScript).
# $1 = ccusage subcommand  ($2 optional, e.g. --active)
#
# LaunchServices hands the executable script to Ghostty (preferred) or
# Terminal.app (fallback) by file-association — avoids the `--args -e`
# cold-start race where Ghostty ignores `-e` on first launch.
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

if [ -d "/Applications/Ghostty.app" ]; then
  exec open -a Ghostty.app "$tmpf"
fi
# Terminal.app always ships with macOS.
exec open -a Terminal.app "$tmpf"
