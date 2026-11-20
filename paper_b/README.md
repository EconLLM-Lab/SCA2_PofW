# paper_b

Paper B code, tests, and locked results. The manuscript is not in this release.

Claim lock: [`results/CLAIM_LOCK.md`](results/CLAIM_LOCK.md).
Locked numbers: [`results/NUMBERS_TABLE.csv`](results/NUMBERS_TABLE.csv).

An outsider, with no licensed archive and no token:

```bash
env -u PYTHONPATH .venv/bin/python -m pytest paper_b/tests/test_build_numbers_table.py -q
```

After `uv sync`, the same check is `uv run python -m pytest paper_b/tests/test_build_numbers_table.py -q`.

See the repository [README](../README.md) for the install and the data fence. Scoring and training read licensed survey files that are not in this tree. Those commands are not listed here. [DATA.md](../DATA.md) says where the files come from. A test that needs a licensed file skips when the file is absent.
