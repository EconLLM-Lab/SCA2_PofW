# Provenance and use of generative AI

This note explains how we produced this work. It also says what you can audit here and what you cannot.

## How this work was produced

Augusto Gonzalez-Bonorino, Kseniia Biriukova and C. Monica Capra are the authors of Paper A (arXiv:2610.06562).
We designed the studies and made every scientific decision. We are responsible for all content.

AI agents did much of the engineering. We used Anthropic Claude models through Claude Code and the Hermes agent.
We also used OpenAI Codex models and xAI Grok models. The agents wrote and ran code and tests.
They drafted documentation and manuscript prose under our direction. They also reviewed one another.
Before a result entered a paper, an agent from a different model family checked it.

## What is in this repository

This repository is a curated release. We built it from an allowlist and gave it a fresh git history.
You can check these safeguards here:

- Preregistration and freeze records in `paper_b/heldout/`.
- A claim lock with dated, append-only amendments in `paper_b/results/CLAIM_LOCK.md`.
- One locked table of every Paper B number in `paper_b/results/NUMBERS_TABLE.csv`.
- Macros keyed to that table. The manuscripts print numbers only through them. An automatic audit checks them.
- Tests across the code.

Paper B is in preparation. We will add its manuscript when its preprint is posted.

## What is not, and why

- Licensed survey microdata and values derived from respondents. These include WVS, GPS and EVS, among others.
  The data are licensed, so we do not ship them. `DATA.md` explains how to obtain them.
- Internal planning records and agent conversation transcripts.
- Development history and the working record of the project. This covers dated decision logs and plans.
  It also covers sprint reports, verifier reports and agent task records.

The working record lives in a private lab repository. Editors, reviewers and replication auditors can request
access. Please write to the corresponding author.

## Frozen records

Preregistrations, the claim lock, freeze files and dated verification reports are shipped byte for byte, because
their hashes are registered. Some of them name lab paths, agent task ids or internal file names from when they were
written. Those names are part of the record; they do not point to anything in this repository.

## Requests

Open a GitHub issue. You can also email the corresponding author listed on the arXiv paper.
