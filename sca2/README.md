# sca2 CLI

Run a frozen protocol. The protocol file is the scientific object.

```bash
PYTHONPATH=".:synthetic_generation" python -m sca2 show --protocol sca2/protocols/gps_sign_dpo_wvs.toml
PYTHONPATH=".:synthetic_generation" python -m sca2 generate --protocol sca2/protocols/gps_sign_dpo_wvs.toml
PYTHONPATH=".:synthetic_generation" python -m sca2 label --protocol sca2/protocols/gps_sign_dpo_wvs.toml
```

`generate` inspects the hashed bank and refuses `--materialize`.
`label` applies `sign(z)`. `train` writes a frozen DPO plan and refuses `--execute`.
`eval` writes a frozen WVS transport plan and refuses `--execute`.
`report` stitches the latest matching stage receipts into `report.json`.
The phase-1 notebook tree was removed. The commands above and the protocol file are the client.
Walkthrough: `sca2/protocols/TUTORIAL.md`.

Tests: `PYTHONPATH=".:synthetic_generation" python sca2/tests/run_tests.py`
