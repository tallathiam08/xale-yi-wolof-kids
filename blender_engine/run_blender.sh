#!/bin/bash

BLENDER="/Applications/Blender.app/Contents/MacOS/Blender"

if [ ! -x "$BLENDER" ]; then
    echo "❌ Blender introuvable : $BLENDER"
    exit 1
fi

"$BLENDER" -b "$@"
