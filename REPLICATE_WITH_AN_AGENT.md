# Replicate with an AI agent

Copy the prompt below into a coding agent that can run a terminal. The agent prepares everything it is allowed to. You do the parts that need your identity: registering with the survey archives, accepting their terms, and logging in to Hugging Face. No agent should accept a licence or type a password for you.

What you can check today without a GPU, and without licensed data: Paper B's locked numbers table, and that Paper A's surface script reports the GPS extract absent. The adapter-GPS headline 0.744 needs the GPS country file (DATA.md). Re-scoring or retraining adapters needs a GPU and the model weights. Paper B's manuscript is not in this release. It will be added with its preprint.

---

```text
You are setting up the SCA2_PofW public repository (EconLLM Lab) so that I can replicate the results in its papers. Work step by step. Report what you ran and what it printed, and never invent output. Stop and ask me whenever a step needs my account, a licence acceptance or a password. Do not accept terms, solve CAPTCHAs or enter credentials yourself.

1. Clone this repository and enter it. Read README.md, DATA.md and paper_a/replication/README.md before doing anything else.

2. Environment: use uv (https://docs.astral.sh/uv/) and no global pip installs. From the repository root run `uv sync`. It builds `.venv` from `pyproject.toml` and `uv.lock` (Python 3.14). Do not use `--extra gpu` unless you are on a GPU machine. Run Python as `env -u PYTHONPATH .venv/bin/python`.

3. Data: DATA.md lists every third-party file, its official download page and the exact path where the code expects it. For each source:
   a. Open its download page and show me the page.
   b. Wait while I register, accept the terms and start the download myself.
   c. Once I confirm that the file is in my Downloads folder, move it to the path in DATA.md and print its size and sha256.
   The GPS country-level file alone is enough to rebuild Paper A's human side of the headline. Add WVS Wave 7 for the 42-country human map and for Paper B tests that read respondents. Never upload, commit or paste the contents of these files anywhere.

4. Our artifacts: if I want the adapter weights, ask me to run `hf auth login` and accept the gate at https://huggingface.co/Bonorinoa/SCA2-phase2-adapters. Then download at commit 03c43dfd27c9535283feb78ffa727da3bfa1b966. The table check below does not need the weights.

5. Replicate Paper A without licensed data:
   env -u PYTHONPATH .venv/bin/python paper_a/22_paper_a_surface.py
   Confirm the script says the GPS extract is absent and does not recompute the adapter-GPS headline.
   The headline 0.744 is checked only after country_gps.dta is in place (DATA.md).
   Then follow paper_a/replication/README.md and check the committed artifacts against paper_a/replication/HASHES.md.

6. Check Paper B numbers without licensed data:
   env -u PYTHONPATH .venv/bin/python -m pytest paper_b/tests/test_build_numbers_table.py -q
   The locked table is paper_b/results/NUMBERS_TABLE.csv.
   With the licensed files from step 3 in place, run:
   HF_TOKEN= env -u PYTHONPATH .venv/bin/python -m pytest paper_b -q
   Tests that need a licensed file skip when it is absent.

7. Finish with a table with one row per step: the command, its exit code, the key printed number and whether it matched. List anything that needed my action and anything that failed, with the error message.
```

---

If a step fails, the agent should report the exact error rather than work around it. A workaround can quietly change what is being replicated.
