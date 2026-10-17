#!/bin/sh
# Re-shoots every screenshot referenced by DECISION.md. Exits non-zero if any shot fails.
cd "$(dirname "$0")"; rm -f shots/*-test.png; fail=0
for v in 1700,1000 1440,860; do s=${v%%,*}
  ./shoot.sh landing-$s "landing.html" $v || fail=1
  ./shoot.sh variant-a-$s "variant-a.html?still=1&sel=23,0,151" $v || fail=1
  ./shoot.sh variant-a-delta-overview-$s "variant-a.html?still=1&view=delta&cam=overview" $v || fail=1
  ./shoot.sh variant-a-search-$s "variant-a.html?still=1&view=single&q=confidence&fly=74" $v || fail=1
  ./shoot.sh variant-b-$s "variant-b.html?qty=attn&pin=23,151" $v || fail=1
  ./shoot.sh variant-b-resid-$s "variant-b.html?qty=resid&hl=24&pin=24,151" $v || fail=1
  ./shoot.sh variant-c-$s "variant-c.html?sel=23,0" $v || fail=1
  ./shoot.sh variant-c-delta-clamped-$s "variant-c.html?sel=24,4&shade=d&clamp=1" $v || fail=1
done
./shoot.sh variant-a-top-1700 "variant-a.html?still=1&view=single&cam=top" || fail=1
./shoot.sh learn-more-popup "variant-c.html?sel=23,0&learn=conservation" || fail=1
./shoot.sh landing-full "landing.html" 1700,4300 || fail=1
exit $fail
