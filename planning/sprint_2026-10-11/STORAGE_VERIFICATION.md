# Paper B artifact destination verification

User approved HF-first model-only artifact architecture and scoped scoring repairs in this session.

Created private HF dataset repository: https://huggingface.co/datasets/Bonorinoa/SCA2-paper-b-artifacts

Read back repo_info and confirmed private=True. Authenticated account Bonorinoa; token metadata role fineGrained (no token values exposed).

Real HTTPS upload/readback probe:
- Path: manifests/storage_probe.json
- Commit: ae15922ca3cfc8a876e48828030feed2e7953255
- URL: https://huggingface.co/datasets/Bonorinoa/SCA2-paper-b-artifacts/commit/ae15922ca3cfc8a876e48828030feed2e7953255
- SHA256: 020c307a3da5021b9e3e0de026b3f0b660347c591451d650e1dd7194f783caf0
- Downloaded exact committed target with force_download and compared bytes: identical.
- Probe contains provenance metadata only, no human data, survey text, training bank or model outputs.

This proves the destination accepts a small write with current credentials. It does not establish total remaining storage quota or future large-upload capacity. No paid upgrade enabled.

Next outputs restricted to approved model-only artifacts under runs/<run_id>/synthetic/ and companion manifests/gates. Human data and model–human derivatives remain local; historical Drive copies untouched.
