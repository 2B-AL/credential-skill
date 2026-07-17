#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "usage: browser-assist-macos.sh ABSOLUTE_EXTENSION_DIRECTORY" >&2
  exit 2
fi
DIRECTORY=$1
case "$DIRECTORY" in
  /*) ;;
  *) echo "extension directory must be absolute" >&2; exit 2 ;;
esac
if [ ! -d "$DIRECTORY" ] || [ ! -f "$DIRECTORY/manifest.json" ]; then
  echo "extension directory is missing manifest.json" >&2
  exit 2
fi
open "$DIRECTORY"
open -b com.google.Chrome -u 'chrome://extensions/'
python3 - "$DIRECTORY" <<'PY'
import json
import sys

print(json.dumps({"ok": True, "directory": sys.argv[1], "url": "chrome://extensions/"}, separators=(",", ":")))
PY
