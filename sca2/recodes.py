"""Single source of truth for WVS answer recodes (E[recode] map).

Matches the locked Paper B definition in ``paper_b/analyze_surface.py``
(``recode_value``) on every item Paper B scores. Two groups of items are
added that Paper B never scores (it is not edited; it is locked):

* Q174: binary (1 = mentioned, 2 = no). The other live Phase 2 scripts
  (06, 10, 13, 14, 16, 22) treat it that way.
* Q12, Q13, Q14: binary, as in 06, 10, 13, 14 and 16.

Recodes are per option code. Never apply them to a mean: the binary recode
is nonlinear, so use E[recode(V)], not recode(E[V]).
"""

from __future__ import annotations

# 1-4 scales, higher = less trust/agreement -> 5 - raw
INVERT_1_4: frozenset[str] = frozenset({
    "Q58", "Q59", "Q60", "Q61", "Q62", "Q63", "Q64", "Q69", "Q70",
    "Q71", "Q73", "Q81",
})
# 1-10 justifiability, higher = more justifiable -> 11 - raw
INVERT_10: frozenset[str] = frozenset({"Q177", "Q179"})
# 1 = yes / mentioned / trust, 2 = no -> 1 / 0
BINARY: frozenset[str] = frozenset({"Q57", "Q12", "Q13", "Q14", "Q174"})


def recode_value(raw: float, item: str) -> float:
    s = float(raw)
    if item in INVERT_1_4:
        return 5.0 - s
    if item in INVERT_10:
        return 11.0 - s
    if item in BINARY:
        return 1.0 if s == 1.0 else 0.0
    return s
