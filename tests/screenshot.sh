#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PORT="${INTEREST_PRESS_PORT:-4292}"
CHROME="$(command -v google-chrome || command -v chromium || command -v chromium-browser)"
mkdir -p screenshots dist
if ! ss -ltn | grep -q "127.0.0.1:$PORT "; then
  nohup python3 server.py > /tmp/interest-press-$PORT.log 2>&1 &
  sleep 1
fi
shot() {
  local url="$1" out="$2" size="$3"; shift 3 || true
  local prof; prof="$(mktemp -d /tmp/ipshot.XXXX)"
  "$CHROME" --headless=new --no-sandbox --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
    --run-all-compositor-stages-before-draw --virtual-time-budget=25000 \
    --window-size="$size" --user-data-dir="$prof" --screenshot="$out" "$@" "$url" >/dev/null 2>&1
  rm -rf "$prof"; echo "  $out ($(wc -c < "$out") bytes)"
}
U="http://127.0.0.1:$PORT"
if [[ -f dist/interest-press.html ]]; then
  shot "file://$PWD/dist/interest-press.html" screenshots/00-best-home.png 1440,1100
else
  shot "$U/" screenshots/00-best-home.png 1440,1100
fi
shot "$U/#front" screenshots/00-best-desktop-top.png 1440,1000
shot "$U/#sports" screenshots/01-sports.png 1440,1100
shot "$U/#space" screenshots/02-space.png 1440,1100
shot "$U/#bookmarks" screenshots/03-bookmarks.png 1440,1000
shot "$U/#archive" screenshots/04-archive.png 1440,1000
shot "$U/#front" screenshots/05-phone-top.png 390,844 --user-agent="Mozilla/5.0 (iPhone)"
echo "screenshots done"
