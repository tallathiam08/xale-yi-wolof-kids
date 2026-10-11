#!/bin/bash
set -e

if [ -n "${BLENDER_BIN:-}" ] && [ -x "$BLENDER_BIN" ]; then
    BLENDER="$BLENDER_BIN"
elif [ "$(uname -s)" = "Darwin" ] && [ -x "/Applications/Blender.app/Contents/MacOS/Blender" ]; then
    BLENDER="/Applications/Blender.app/Contents/MacOS/Blender"
elif command -v blender >/dev/null 2>&1; then
    BLENDER="$(command -v blender)"
else
    echo "❌ Blender introuvable"
    exit 1
fi

"$BLENDER" -b "$@"
