#!/usr/bin/env bash
set -euo pipefail
LAUNCH_DIR="$HOME/Library/LaunchAgents"
for plist in com.cos.briefing com.cos.journal com.cos.emailloop; do
    dst="$LAUNCH_DIR/${plist}.plist"
    if [[ -f "$dst" ]]; then
        launchctl unload "$dst" 2>/dev/null || true
        rm -f "$dst"
        echo "removed $plist"
    fi
done
