#!/bin/sh
# usage: screens/shoot.sh <suffix>   -> screens/{individual,side-values,side-delta}-<suffix>.png
cd "$(dirname "$0")"
CH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
BASE="http://127.0.0.1:5178/?pair=smol_inst%7Csmol_inst_usa_e3&single=b&item=wvs_Q81&hscale=log&color=dla&sel=23,0,151"
shot() { "$CH" --headless=new --use-angle=swiftshader --enable-unsafe-swiftshader --hide-scrollbars --window-size=1700,1000 --virtual-time-budget=20000 --screenshot="$PWD/$1-$2.png" "$3" >/dev/null 2>&1; }
shot individual "$1" "$BASE&view=single"
shot side-values "$1" "$BASE&view=side&right=b"
shot side-delta "$1" "$BASE&view=side&right=delta"
ls -la *-"$1".png
