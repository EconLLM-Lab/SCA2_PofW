# paper_a

Paper A scripts, committed outputs, and the replication guide. The manuscript is in `manuscripts/paper_a/`.

Start at the repository [README](../README.md). The no-data headline check is:

```bash
env -u PYTHONPATH .venv/bin/python paper_a/22_paper_a_surface.py
```

With the WVS and GPS files in place (see `DATA.md`) it recomputes and prints the adapter-GPS trust correlation
0.744. Without them it says the extracts are absent and checks only the committed scores. The hash check is in [replication/README.md](replication/README.md).

Committed scores are in `outputs/paper_a/`. That doubled directory name is intentional: the paths are pinned in hashes. Do not rename it.

Licensed survey files are not in this folder. See [DATA.md](../DATA.md).

## Rebuilding `tvd`

Model-to-human distances (`tvd`) are not shipped. `tvd_rebuild.py` recomputes them from the model option
probabilities in `inputs/model_option_probs.csv` plus your WVS Wave 7 and GPS downloads, and writes
`outputs/paper_a/country_item_scores_tvd.csv`. `reproduce_tables.py` uses the committed `tvd` column if it is present
and otherwise this file. Exact steps and expected headline means are in [DATA.md](../DATA.md); the exact-match tests
are in `tests/`. How `inputs/model_option_probs.csv` was built is in [inputs/README.md](inputs/README.md).
