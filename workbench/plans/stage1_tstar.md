# Stage 1: t\* on the Llama-3 tokenizer (read-only probe)

Date: 2026-10-17. Author: engineer (kanban t_4e28ba8d).
Scope: tokenizer files only, no weights, no edits under `src/`. Fence respected:
nothing under `data/`, no Paper B files, no `viewer/`, no git.

## Access (read this first)

| repo | `resolve/main/tokenizer.json` | outcome |
|---|---|---|
| `meta-llama/Llama-3.1-8B-Instruct` | 200 | downloaded, used below |
| `meta-llama/Llama-3.2-1B-Instruct` | **403** "not in the authorized list" | not downloadable |
| `meta-llama/Llama-3.2-1B` | **403** | not downloadable |

The profile `.env` token is valid (`whoami-v2` -> 200, user `Bonorinoa`). The Llama 3.2
licence is a separate gate and this account is not approved for it. **No mirror was used.**
The 3.2 comparison below is therefore made from Meta's public repo metadata (git blob
oids / LFS hashes, which HF serves for gated repos), not from downloaded files. That is a
byte-identity proof, but the 3.2 `tokenizer_config.json` (chat template) stays unverified.

Local copies used for the probes (outside the repo, not committed):
`~/.hermes/profiles/engineer/cache/scratch/tstar/llama31_8b_inst/`
Probe scripts: `probe1.py`, `probe2.py`, `probe3.py` in the same folder.
Run with: `env -u PYTHONPATH uv run --project workbench python <script>`.
transformers 5.20.1, tokenizer class `TokenizersBackend`, `len(tok)=128256`,
`vocab_size=128000`.

## 1-2. Are the answer digits single tokens, and what are their ids

`add_special_tokens=False`.

| string | n tokens | ids | tokens | single token? |
|---|---|---|---|---|
| `' 1'` | 2 | `[220, 16]` | `['Ġ', '1']` | **no** |
| `' 2'` | 2 | `[220, 17]` | `['Ġ', '2']` | **no** |
| `' 3'` | 2 | `[220, 18]` | `['Ġ', '3']` | **no** |
| `' 4'` | 2 | `[220, 19]` | `['Ġ', '4']` | **no** |
| `'1'` | 1 | `[16]` | `['1']` | **yes** |
| `'2'` | 1 | `[17]` | `['2']` | **yes** |
| `'3'` | 1 | `[18]` | `['3']` | **yes** |
| `'4'` | 1 | `[19]` | `['4']` | **yes** |

Wider table, because WVS Q50 has codes `1..10`:

| string | ids | tokens |
|---|---|---|
| `' 0'` | `[220, 15]` | `Ġ 0` |
| `' 5'` .. `' 9'` | `[220, 20]` .. `[220, 24]` | `Ġ 5` .. `Ġ 9` |
| `' 10'` | `[220, 605]` | `Ġ 10` |
| `' 11'` | `[220, 806]` | `Ġ 11` |
| `' 12'` | `[220, 717]` | `Ġ 12` |

Two consequences:

- The completion `" " + code` is **always** `[220] + [one digit token]`. `220` is the
  standalone space token (`Ġ`). All 13 probed codes have a **distinct** last token.
- **The Q50 refusal does not apply to this tokenizer.** On SmolLM2, `' 1' = [216, 33]` and
  `' 10' = [216, 33, 32]`, so the completions differ in length and the shared-prefix
  assumption fails (this is why the contract lists Q50 as refused). On Llama-3, `' 10'` is
  a single trailing token `605`, so every WVS item with codes up to 12 satisfies the
  shared-prefix rule. `items.readout_ids` therefore accepts Q50 here — verified, not
  inferred (`probe2.py`, `=== wvs_Q50 codes=('1','2',...,'10') ... segments OK`).

## 3. The chat template and t\*

`apply_chat_template([{"role":"user","content": <user prompt>}], tokenize=False,
add_generation_prompt=True)` on Llama-3.1-8B-Instruct renders (wvs_Q81, verbatim):

```
<|begin_of_text|><|start_header_id|>system<|end_header_id|>

Cutting Knowledge Date: December 2023
Today Date: 26 Jul 2024

<|eot_id|><|start_header_id|>user<|end_header_id|>

Answer this questionnaire as an individual person. ... Answer:<|eot_id|><|start_header_id|>assistant<|end_header_id|>

```

The prompt text ends with `...Answer:<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n`.
Token ids: `[..., 128009, 128006, 78191, 128007, 271]`, i.e. the template closes with
`'ĊĊ'` (271). Then the completion `' 1'` appends `220` and `16`.

Joint tokenisation was checked, not assumed: for wvs_Q81, wvs_Q57 and wvs_Q50,

    tok(formatted + " " + code)  ==  tok(formatted) + [220] + [digit_id]     (all True)

so `items.readout_ids`' `base + prefix_ids` construction is exact for this tokenizer, on
every item tested.

WVS Q81 (`T = 148`, `n_base = 147`):

| segment | range | decoded |
|---|---|---|
| `template` (mislabeled, see 5) | `[0, 30)` | `<\|begin_of_text\|><\|start_header_id\|>system<\|end_header_id\|>\n\nCutting Knowledge Date: December 2023\nToday Date: 26 Jul 2024\n\n` |
| `instruction` | `[30, 59)` | persona and tone |
| `question` | `[59, 94)` | `Question:\n...` |
| `instruction` | `[94, 104)` | response rule |
| `options` | `[104, 128)` | `1: A great deal\n...` |
| `instruction` | `[128, 140)` | output rule |
| `answer_cue` | `[140, 142)` | `Answer:` |
| `template` | `[142, 147)` | `<\|eot_id\|><\|start_header_id\|>assistant<\|end_header_id\|>\n\n` |
| `readout` | `[147, 148)` | `' '` = id `220` |

**t\* definition for this tokenizer.** The answer options share the one-token prefix
`[220]` (the lone `Ġ`); the codes diverge in the very next position. So the readout
position is the last token of the shared completion prefix:

    t* = T - 1,  where T = n_base + 1,  prompt_ids[T-1] = 220 ('Ġ')
    code_token = {'1': 16, '2': 17, '3': 18, '4': 19}      (for Q81)

which is **structurally identical to SmolLM2** (`Ġ` + digit, t* on the `Ġ`). Only the ids
move: space `220` instead of `216`, digits `16..24, 605, 806, 717` instead of `33..36`.
No new t\* concept is needed; `items.readout_ids` and the `readout` segment already
describe it correctly. Verified end to end on wvs_Q81, wvs_Q57 and wvs_Q50: `segments OK`
and `check_segments` passed for all three on the Llama-3 template.

Prompt length is much larger than the SmolLM2 items (147 base tokens for Q81 vs ~50 for
SmolLM2), because of the ~28-token system block that Llama-3 inserts.

## 4. Are the 3.1-8B and 3.2 tokenizers identical?

Hashes from the repo tree API (`/api/models/<repo>/tree/main?recursive=true&expand=true`),
cross-checked locally against the downloaded 3.1 files:

| file | 3.1-8B-Instruct | 3.2-1B-Instruct | 3.2-1B |
|---|---|---|---|
| `tokenizer.json` (9,085,657 B) | git oid `5cc5f00a5b203e90a27a3bd60d1ec393b07971e8` | **same oid** | **same oid** |
| `original/tokenizer.model` (2,183,982 B) | LFS sha256 `82e9d319...5551b55` | **same sha256** | **same sha256** |
| `special_tokens_map.json` | oid `02ee80b6...` (296 B) | **same oid** | differs (301 B) |
| `tokenizer_config.json` | oid `db88166e...` (55,351 B) | differs, oid `4ff488a1...` (54,528 B) | differs (50,500 B) |

Local confirmation on the downloaded 3.1 file: `sha256(tokenizer.json) =
79e3e522635f3171300913bb421464a87de6222182a0570b9b2ccba2a964b2b4` and its git blob oid
recomputes to `5cc5f00a...`, matching the 3.2 entries. `sha256(original/tokenizer.model)
= 82e9d319...`, matching the 3.2 LFS sha256. The canonical vocab/merges hashes of that
`tokenizer.json` are `vocab b571e5e3...`, `merges 0cd100e0...` (128,000 vocab entries,
280,147 merges); since the file bytes are identical in all three repos, these are also
the 3.2 values.

**Verdict.**
- The **tokenizer proper is byte-identical** across `Llama-3.1-8B-Instruct`,
  `Llama-3.2-1B-Instruct` and `Llama-3.2-1B`: same `tokenizer.json` bytes and same
  SentencePiece model. Byte identity is a stronger statement than "the probe strings
  encode the same" — it implies it. The ids above are 3.2 ids too.
- The **wrapper config is not identical**: `tokenizer_config.json` differs in size/oid in
  all three, so the Jinja chat template and the `added_tokens_decoder` block are not
  proven equal. This one file could not be fetched (403), so it is **unverified**.
  Consequence: the template *string* around the prompt may differ slightly between 3.2
  and 3.1 (and base vs instruct), which changes `n_base` and the segment layout — never
  `t*`, which is defined as `T - 1` from whatever prompt is actually rendered.

## 5. Concrete recommended changes to the capture

1. **`items.readout_ids` — no change needed.** It already derives the prefix and per-code
   token ids from the tokenizer. Do not hardcode `16..19`: code `"10"` is `605`, not
   `16` + `0`. The function handles Q50 correctly on this tokenizer.
2. **Pin the chat-template date.** Llama-3's template calls `strftime_now`:
   `Today Date: 26 Jul 2024`. transformers 5.20 happens to default `date_string` to
   `"26 Jul 2024"`, so today's output is reproducible, but that default is not a contract.
   Pass `date_string="26 Jul 2024"` (a constant in `items.py`) to every
   `apply_chat_template` call, or `n_base` and the prompt hash silently change with the
   wall clock. Reproduced: `date_string="01 Jan 2025"` changes the rendered text.
3. **`items.prompt_segments` needs a Llama-3 branch.** Its system-block regex is
   ChatML-only (`<|im_start|>system\n(.*?)<|im_end|>`). On the Llama-3 template it does not
   match, falls through to the `else` branch, and lumps the entire system block into one
   `template` segment labelled "user turn opens" (`[0, 30)` for Q81). That is legal under
   the contract's cover rule, so nothing raises — the `system` kind just disappears and
   "Cutting Knowledge Date / Today Date" gets drawn as chat markers. Add
   `<|start_header_id|>system<|end_header_id|>\n\n(.*?)<|eot_id|>` (same three-way split:
   markers, system text, markers) and select the regex by tokenizer family, not by
   trying ChatML first and hoping.
4. **Expected `n_base` values** (Llama-3 template, with date pinned): wvs_Q81 147,
   wvs_Q57 131, wvs_Q50 162. Useful as a regression assertion in the new test.
5. **`readout` segment is correct as implemented**: `[T-1, T)`, one token `220`, t\* =
   `T-1`. `spec/export_contract.md`'s "It is the lone `Ġ` token" stays true; only the
   id (220, not SmolLM2's 216) differs, and that id is not in the contract.
6. **Update the contract's Q50 sentence.** "Items whose codes do not split as a shared
   prefix plus one token are refused. Q50 is one" is a SmolLM2 fact. On Llama-3, Q50 is
   exportable. Suggest rewording to "refused for the SmolLM2 tokenizer; the check is per
   tokenizer" and leaving the runtime check in `readout_ids` as the real gate.
7. **Do not add special tokens around the rendered prompt.** The template string already
   starts with `<|begin_of_text|>` (id 128000) and `readout_ids` tokenises with
   `add_special_tokens=False`. Adding them would prepend a second BOS and shift every
   segment by one.
8. **Add a tokenizer test** (for t_7d7ad93e): assert `tok(" 1")..tok(" 4")` are 2 tokens
   with prefix `[220]` and last ids `16..19`; assert `tok(" 10")[-1] == 605`; assert
   `readout_ids` accepts Q50 and that `prompt_ids[-1] == 220` for Q81. Load the tokenizer
   with `AutoTokenizer.from_pretrained("meta-llama/Llama-3.1-8B-Instruct")` under the
   profile token and cache it (it is the same file as 3.2); `pytest.importorskip`-style
   skip if the cache is cold, so the suite stays offline-clean.
9. **Downstream (not mine to do):** `load_hf` uses the tokenizer of the *loaded* model id.
   For the 3.2 pair that is the 3.2 `tokenizer_config.json`, whose chat template is
   unverified here. Whoever gets 3.2 access should re-render one prompt and diff it
   against the 3.1 rendering before trusting the segment labels.
