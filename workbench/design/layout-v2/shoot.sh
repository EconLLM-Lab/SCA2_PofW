#!/bin/sh
# usage: shoot.sh <name> <page?query> [W,H]   -> shots/<name>.png  (serve.sh must be running)
# A fresh Chrome profile per shot, so no cached common.js leaks into a screenshot.
cd "$(dirname "$0")"
CH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SIZE="${3:-1700,1000}"
PROF="$(mktemp -d /tmp/lv2c.XXXXXX)"
"$CH" --headless=new --user-data-dir="$PROF" --use-angle=swiftshader --enable-unsafe-swiftshader --hide-scrollbars \
  --window-size="$SIZE" --virtual-time-budget=15000 --screenshot="$PWD/shots/$1.png" \
  "http://127.0.0.1:5181/design/layout-v2/$2" >/dev/null 2>&1
rc=$?; rm -rf "$PROF"; echo "shots/$1.png exit=$rc"; exit $rc
