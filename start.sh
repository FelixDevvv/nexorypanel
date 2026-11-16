#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
python_command="${PYTHON:-python3}"

if ! command -v "$python_command" >/dev/null 2>&1; then
  echo "Python 3.11 or newer is required. Install Python and try again." >&2
  exit 1
fi

if ! "$python_command" -c 'import sys; sys.exit(sys.version_info < (3, 11))'; then
  echo "Python 3.11 or newer is required." >&2
  exit 1
fi

if [[ ! -x ".venv/bin/python" ]]; then
  "$python_command" -m venv .venv
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -r requirements.txt
fi

echo "NexoryPanel local server: http://127.0.0.1:5000"
echo "Press Ctrl+C to stop. Application logs are shown in this terminal."
export NEXORY_OPEN_BROWSER=true
exec .venv/bin/python app.py
