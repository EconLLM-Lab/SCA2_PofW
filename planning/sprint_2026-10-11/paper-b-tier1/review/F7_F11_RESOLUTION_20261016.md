# F7 and F11: resolved, with the wording to use

Both are documentation questions, not defects. Neither touches the estimand, the bank,
or the preregistration. Evidence below is reproducible from the repository.

## F7 — the recorded pool hash is the CRLF working-tree form, not the LF git blob

Three hashes exist for two files. They are consistent, and the difference is line
endings plus the Amendment 1 repairs.

| File | Line endings | sha256 | Where it appears |
|---|---|---|---|
| `pool_skeleton.csv`, pre-amendment | CRLF (working tree) | `c78faa7552a918e7cf840a726fb60c9b3fd1698259a31f6f18aff43bf91ea135` | preregistration §5 and §11 (line 46, 209) |
| `pool_skeleton.csv`, pre-amendment | LF (git blob at tag `prereg-heldout-2026-10-14` = `59e143e`) | `b221d12aed460772103c729ce3c79860267fa4c5b6940d5de38d6b9967c0e920` | `git show 59e143e:paper_b/heldout/pool_skeleton.csv` |
| `pool_skeleton.csv`, amended | CRLF (working tree) | `19241f6f103c51d64e295045162bb370920223b7ffad7c5f3c8991f5c101bd44` | preregistration §11 (line 242), and it equals `sha256sum paper_b/heldout/pool_skeleton.csv` |

`c78faa75…` is the CRLF form of the same bytes as `b221d12a…`: taking the tag blob and
applying `sed 's/$/\r/'` reproduces `c78faa75…` exactly. `.gitattributes` contains
`* text=auto`, so the repository stores text with LF while the working tree holds CRLF.
The verifier's observation was correct and is now fully explained: 223 items either way,
identical field sets, no content difference.

The amended hash recorded in §11 (`19241f6f…`) matches the working copy bit for bit, so
the pins the amended specs were built from are the pins of the file actually in use.

**Wording to use in the paper's reproducibility appendix.** Record the amended pool hash
`19241f6f…` for `pool_skeleton.csv` and state the convention in one line: the repository
normalizes text to LF, so hashes computed from `git show` differ from working-tree hashes
for CRLF files; both forms are given where they matter. No change to the preregistration.

**The amended pool is rebuildable, not merely hashed.** `python paper_b/heldout/build_pool.py
--out /tmp/pool_rebuild.csv` reproduces `19241f6f…` byte for byte, because the 12 repairs live in
`overrides.json` (now `0f5cd2bb…`) as `override` rows over the questionnaire source. The
amendment therefore pins an artifact a reader can regenerate, which is the stronger claim for
the appendix.

## F11 — `config.py` is byte-identical to the preregistration tag; it differs from the cohort-1 runner commits

- `git diff --stat prereg-heldout-2026-10-14 HEAD -- paper_b/config.py` is empty: **byte-identical to the file at the tag**.
- The verifier's F11 compared it against cohort-1 runner commits `a43fff2` and `86fbf10`, where it is not byte-identical, and separately confirmed the cohort-1 defaults are unchanged when `SCA2_PB_UNITS` is unset.

Both statements are true and compatible. The only correction needed is in prose, not code:
describe the property as "the cohort-1 defaults are unchanged when the environment variable
is unset", not as "`config.py` is byte-identical to the cohort-1 runner".

Working-copy hash for reference: `fafe0b46d6348e9852c3bbe69e957b3b952ccfe6`.
