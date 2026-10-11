#!/usr/bin/env bash
# Interest Press: collect → build → optional screenshots → serve :4292
#   ./run.sh           collect + build + serve
#   ./run.sh --shots   collect + build + screenshot + serve
set -euo pipefail
cd "$(dirname "$0")"
PORT=4292
python3 collect.py
python3 build.py
if [[ "${1:-}" == "--shots" ]]; then bash tests/screenshot.sh; fi
if ss -ltn | grep -q "127.0.0.1:$PORT "; then
  echo "already serving on http://127.0.0.1:$PORT/"
else
  nohup python3 server.py > /tmp/interest-press-$PORT.log 2>&1 &
  sleep 1
  echo "serving http://127.0.0.1:$PORT/ (pid $!)  ·  offline file: dist/interest-press.html"
fi
