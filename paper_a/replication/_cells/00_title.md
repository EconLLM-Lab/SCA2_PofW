# Verify committed analysis artifacts (Tier A)

This notebook does not train models and does not call an LLM.

It checks that files listed in `replication/HASHES.md` still match git.
Tier B (regenerate tables from eval banks) is documented in `replication/README.md`
and is blocked until `SCA2_EVAL_URL` points at a real public zip.

Survey microdata are not in this repository.
