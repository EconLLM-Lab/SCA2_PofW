#!/bin/sh
# Serves workbench/ so the sketches can fetch ../../exports/ and ../../viewer/node_modules/three.
# usage: design/layout-v2/serve.sh  -> http://127.0.0.1:5181/design/layout-v2/landing.html
cd "$(dirname "$0")/../.." && exec python3 -m http.server 5181 --bind 127.0.0.1
