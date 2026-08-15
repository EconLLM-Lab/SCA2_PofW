# Adversarial claim-boundary brief (rewrite)

Hostile Nature/PNAS referee. Frozen facts given. Cells = country-demeaned. No `.tex` promotion.

## A) Eight sentences the paper MAY assert

1. Empty \(\mathcal R\) on the seven-measure patience menu (\(n=41\)) returns \(M^*=\) full menu and \([L,U]=[-0.21875,0.40246]\), rounded \([-0.219,0.402]\) — the unrestricted specification-curve range (empty-\(\mathcal R\) table).
2. Campbell–Fiske patience\(\times\)trust (\(n=41\), \(\tau_{\mathrm{conv}}=0.30\), \(\tau_{\mathrm{disc}}=0.35\)) has classical retain \(=\emptyset\) and engine \(M^*=\emptyset\); binding \(r(\)GPS patience, child-qualities\()=-0.252\), \(r(\)GPS trust, Q57\()=0.284\), \(r(\)Q57, GPS patience\()=0.825\) (stays \(0.706\) after partialling log GDP and education) (MTMM table).
3. Patience-country \(M^*=\{\)GPS patience\(\}\), \(\beta=0.402\) (OLS of \(m\) on log GDP \(|\) education), coverage \([0.079,0.563]\), empty-rep \(=0.297\) (patience-country table).
4. WVS Q13, Q14, and the patience composite fail leftover education at \(n=41\) (slacks \(-0.533/-0.777/-0.722\)) with negative \(\beta\) (same table).
5. GPS patience passes leftover `mono_edu` on the full \(n=41\) sample (slack \(+0.233\)); the 2026-08-10 fold-0 slack \(-0.383\) was a train-split artifact (leftover note).
6. Trust-country \(M^*=\{\)Q57, in-group, out-group, composite\(\}\), \([L,U]=[0.107,0.391]\), coverage \([-0.016,0.639]\) crossing zero, empty-rep \(=0.002\); GPS trust and institution fail rule-of-law; leftover education rejects the composite (slack \(-0.052\)) (trust-country table).
7. Demeaned cells (480, 42 countries): patience \(M^*=\{\)Q13\(\}\), \(\beta=0.245\) vs GPS patience, coverage \([0.174,0.335]\), empty-rep \(=0.17\), edu slack \(+0.051\) (knife-edge); Q14 stays anti-aligned (slack \(-0.564\), \(\beta=-0.326\)); \(\lambda=1.5\) empties \(M^*\) (patience-cell table).
8. Demeaned-cell trust \(M^*=\emptyset\) even at \(\lambda=0.5\); education bar and GPS-recovery disagree (demeaned \(\beta\): Q57 \(+0.052\), in \(+0.224\), out \(+0.211\), inst \(+0.285\), composite \(+0.318\)); tool holdout \(0.75\) vs random-\(k_1\) \(0.52\) (pctl \(0.48\)) is not a strong win (trust-cell table; holdout diagnostic).

## B) Eight sentences a hostile referee would desk-reject

1. “The identified range for patience is \([0.328,0.402]\).” That is the 2026-08-10 posture-(a) pilot after an empty robust set; its fold-0 band already swallows the interval.
2. “We complete the leftover §6.5 agenda (six GPS dimensions, a culture composite, LLM menu columns).” Confirmatory menus are human patience and trust only.
3. “Patience is point-identified at \(0.402\).” Empty-rep \(=0.297\) and coverage \([0.079,0.563]\) make the singleton selection-fragile; \(\lambda=0.5\) empties \(M^*\) via the risk discriminant.
4. “Trust has a strictly positive construct-identified association with log GDP.” Survivor \([L,U]\) is not coverage; the band \([-0.016,0.639]\) crosses zero.
5. “Within-country cells retain trust \(M^*=\{\)Q57, in, out\(\}\) with \([0.251,0.317]\).” That is the pooled undemeaned contrast; confirmatory demeaned cells yield \(M^*=\emptyset\).
6. “GPS patience fails education (slack \(-0.383\)).” That was fold-0; full-sample leftover slack is \(+0.233\).
7. “The selection rule is confirmed by a \(0.75\) holdout pass rate.” Versus random-\(k_1\) \(0.52\) at pctl \(0.48\), this is not a strong win.
8. “Q13/Q14 fail only through ecological confounding.” They fail education at both resolutions, and Q14 is anti-aligned inside countries (\(\beta=-0.326\)).

## C) Recommended significance-statement thesis (103 words)

One survey item, lab task, or model score is routinely treated as the latent construct it names. When candidate measures are cheap, conclusions move with the representation. This paper writes Cronbach–Meehl restrictions as moment inequalities over a declared menu and reports only the image of the admissible set. On human patience and trust, an empty network recovers the unrestricted range, a classical multitrait–multimethod screen rejects every instrument, country-level trust coverage crosses zero, and country-demeaned cells empty the trust set. The change is a reporting rule, not a new preferred measure: if the network cannot retain a representation, the paper cannot retain the conclusion.

## D) Holdout vernacular

Restriction-stage split holds out some declared restrictions, forms \(M^*\) on the rest, and tests the held-out restrictions on those survivors — the powered falsification at this \(n\). All-restrictions-for-selection uses the full network to form \(M^*\) and leaves nothing to test (empty \(\mathcal R\) is the unrestricted special case, not a holdout). Units-split holds out countries or cells and re-forms \(M^*\) on the complement; at \(n=41/35\) it is diagnostic, not headline, and the 2026-08-10 fold-0 education failure was this split artifact. The uncertainty band is a units bootstrap that re-forms \(M^*\) each replicate — not a CI around a selected \(\beta\), not the holdout. Band and empty-replicate rate belong on the same table as \([L,U]\); these four objects need not return the same \(M^*\).
