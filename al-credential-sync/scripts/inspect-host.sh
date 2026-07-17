#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if ! command -v python3 >/dev/null 2>&1; then
  echo '{"schema_version":1,"error":"python3_required"}'
  exit 1
fi
exec python3 "$SCRIPT_DIR/inspect-host.py"
