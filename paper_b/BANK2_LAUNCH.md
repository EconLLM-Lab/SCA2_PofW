# Bank2 launch note

> **Record, not status.** Written 2026-10-14. Lines about what is done, blocked or next describe that date, not today. Current status: [STATUS.md](../STATUS.md). Executed: 64 bank-2 profile adapters are on the Hub.

Do not run this until `verify_gates.py --bank-dir <new bank> --scan-text` exits 0 and the manifest has 658 triplets.

Cohort 1 is not this run. Its Hub path is `adapters/<CC>` at revision `7550fd4cfe514470bb8d80918a43c9ae424d26b5`.

```
export SCA2_PB_PROTOCOL=bank2
export SCA2_PB_DATA_ROOT=/content/paper_b_bank2
export SCA2_PB_BANK2_DIR=/content/SCA2_PofW/synthetic_generation/outputs/gps_sign_relabel_bank2
export HF_TOKEN=...
python paper_b/compute_ref_cache.py
python paper_b/run_cohort.py --wave 1
python paper_b/run_cohort.py --wave 2
```

The reference cache is the first GPU hour. It is not reusable from cohort 1. Uploads go to `bank2/<bank_run_id>/adapters/<CC>` in `Bonorinoa/SCA2-paper-b-adapters`. An adapter file from another bank in that data root stops the wave.
