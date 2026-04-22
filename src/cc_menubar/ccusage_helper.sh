#!/bin/bash
# Invoked by SwiftBar with terminal=false (runs under Process, no AppleScript).
# $1 = ccusage subcommand  ($2 optional, e.g. --active)
set -eu

CCUSAGE="@@CCUSAGE_PATH@@"  # baked at install() time via shutil.which("ccusage")

# Compound bash parses under `bash -c`. Double-quotes around $CCUSAGE protect
# install paths with spaces (pip-install-user under ~/Library/Application Support).
CMD="\"$CCUSAGE\" $1 ${2:-}; echo; read -n 1 -s -r -p 'press any key to close'"

if [ -d "/Applications/Ghostty.app" ]; then
  # Argv-split -e: login exec's /bin/bash; bash parses the compound.
  # See feedback_ghostty_cold_start_race.md for why single-string -e and
  # bare `open -a Ghostty.app <script>` both race on cold start.
  exec open -na Ghostty.app --args -e /bin/bash -c "$CMD"
fi

# Terminal.app fallback. File-handler has a shell-ready handshake (unlike
# Ghostty) so the tempfile pattern is reliable here.
tmpf=$(mktemp -t ccusage.XXXXXX.sh)
cat > "$tmpf" <<SH
#!/bin/bash
$CMD
rm -f "\$0"
SH
chmod +x "$tmpf"
exec open -a Terminal.app "$tmpf"
