#!/usr/bin/env bash
# Install launchd jobs for daily briefing, journal reminder, and email loop.
set -euo pipefail

COS_HOME="$(cd "$(dirname "$0")/.." && pwd)"
COS_BIN="$(command -v cos || true)"
if [[ -z "$COS_BIN" ]]; then
    COS_BIN="$COS_HOME/.venv/bin/cos"
fi
if [[ ! -x "$COS_BIN" ]]; then
    echo "Can't find 'cos' executable. Activate the venv and run 'pip install -e .' first."
    exit 1
fi

mkdir -p "$COS_HOME/logs"
LAUNCH_DIR="$HOME/Library/LaunchAgents"
mkdir -p "$LAUNCH_DIR"

for plist in com.cos.briefing com.cos.journal com.cos.emailloop; do
    src="$COS_HOME/scripts/${plist}.plist"
    dst="$LAUNCH_DIR/${plist}.plist"
    sed -e "s|__COS_BIN__|$COS_BIN|g" -e "s|__COS_HOME__|$COS_HOME|g" "$src" > "$dst"
    launchctl unload "$dst" 2>/dev/null || true
    launchctl load "$dst"
    echo "loaded $plist"
done

echo
echo "Installed. View status with: launchctl list | grep com.cos"
echo "Logs in: $COS_HOME/logs/"
