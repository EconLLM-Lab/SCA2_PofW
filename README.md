# SCA2_PofW

Synthetic Cultural Agents from aggregate anchors. EconLLM Lab.

Country signs from the Global Preferences Survey label one shared bank of synthetic preference pairs. Each sign profile is written into a small DPO adapter. Evaluation prompts do not name a country.

This is a curated public release. It has a fresh git history. How it was produced, and what is not here, is in [PROVENANCE.md](PROVENANCE.md).

## Papers

| Paper | What it is | Where |
|---|---|---|
| A | Synthetic Cultural Agents from Aggregate Anchors (Gonzalez-Bonorino, Biriukova, Capra) | [arXiv:2610.06562](https://arxiv.org/abs/2610.06562) |
| B | Journal version of A | In preparation. Manuscript to be added with its preprint. |

Paper A's headline, on sixteen countries and nine trust items, is an adapter-GPS Spearman correlation of 0.744. That is coarse sign transfer, not recovery of magnitudes within a sign.

A live demo of the workbench is at <https://huggingface.co/spaces/EconLLM/sca2-workbench>. The source repository is private for now.

## Install

```bash
uv sync
```

That builds `.venv` from `pyproject.toml` and `uv.lock` (Python 3.14). Do not install packages into the system Python. Run project Python as `env -u PYTHONPATH .venv/bin/python`.

## Data

Licensed survey files are not in this repository. [DATA.md](DATA.md) says where to get them and where to put them.

## Replicate

Paper A, no licensed data. The committed scores cover 16 countries, 27 items and 8 model arms (3,424 scored cells):

```bash
env -u PYTHONPATH .venv/bin/python paper_a/22_paper_a_surface.py
```

Without the GPS country file the script says the extract is absent and does not recompute the adapter-GPS headline. With `data/GPS/GPS_dataset_country_level/country_gps.dta` in place (see DATA.md) it prints 0.744. The public bank ships sign labels only; see PUBLIC_REDACTIONS.md. The hash check of the committed score files is in [paper_a/replication/README.md](paper_a/replication/README.md).

Paper A, with licensed data. Place the files as DATA.md says, then run the same script. It rebuilds the 42-country human map. `paper_a/reproduce_tables.py` reprints the committed tables.

Paper B, no licensed data. The locked numbers are in `paper_b/results/NUMBERS_TABLE.csv`. Rebuild and check:

```bash
env -u PYTHONPATH .venv/bin/python -m pytest paper_b/tests/test_build_numbers_table.py -q
```

Paper B, with licensed data. Place the files as DATA.md says, then:

```bash
HF_TOKEN= env -u PYTHONPATH .venv/bin/python -m pytest paper_b -q
```

A test that needs a licensed file skips when the file is absent, and runs when it is present.

An agent can follow [REPLICATE_WITH_AN_AGENT.md](REPLICATE_WITH_AN_AGENT.md).

## Repository layout

| Path | Role |
|---|---|
| `sca2/` | Protocol CLI and frozen protocol files |
| `synthetic_generation/` | Synthetic-bank code. The shipped bank is `outputs/gps_sign_relabel_all/` |
| `paper_a/` | Paper A scripts, committed outputs, and the replication guide |
| `paper_a/outputs/paper_a/` | Doubled directory name. Left as-is: those paths are pinned in hashes |
| `paper_b/` | Paper B code, tests, and locked results. No manuscript yet |
| `manuscripts/paper_a/` | Paper A PDF as posted to arXiv (LaTeX source on arXiv) |
| `manuscripts/talks/presentation_v2.pdf` | Talk slides |
| `data/` | Build scripts and manifests only. No licensed rows |

## License

Code is MIT. See [LICENSE](LICENSE). Survey wording in our prompts, GPS signs and Llama outputs stay under their
owners' terms; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). To cite Paper A, use [CITATION.cff](CITATION.cff).
