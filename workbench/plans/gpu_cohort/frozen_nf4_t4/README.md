# frozen_nf4_t4: frozen T4-CUDA NF4 instrument (card t_cb68fe78, C1)

What this is: the 224 NF4 double-quantized Linear layers of Llama-3.1-8B-Instruct, quantized on a Tesla T4 by the production HF loader and exported in the layout `FrozenNF4Source` / `runner/unit.py --frozen` reads (`<module>.weight.safetensors` + `instrument.json`). Embedding, norm and lm_head stay fp16 and are read from the base snapshot, so they are not stored here. Use as: `--frozen workbench/plans/gpu_cohort/frozen_nf4_t4`.

Do not commit this directory (3.4 GB, not in .gitignore).

## Provenance
- Device: Tesla T4 (driver 580.82.07, CUDA 13.0), Colab session c1-t4, 2026-10-18.
- Loader: `benchmark/prepare_nf4_bench.py` (copy of `runner/prepare_nf4.py` with the A100-only check removed). NF4, double-quant, fp16 compute, blocksize 64.
- Base: meta-llama/Llama-3.1-8B-Instruct @ 0e9e39f249a16976918f6564b8830bc894c89659.
- Stack: torch 2.11.0+cu130, transformers 4.46.3, bitsandbytes 0.50.2, huggingface_hub 0.36.2, accelerate 0.34.0, Python 3.13.15.
- `instrument.json`: diagnostic=false, quantization_device=cuda, per-file sha256. `MANIFEST.json`: sha256 of all 225 files (224 + instrument.json), device, versions, revision, nvidia-smi.
- All 225 files on this Mac match `MANIFEST.json` (0 bad, 0 missing, 0 extra). `instrument.json` hashes equal the manifest.
- Replicability: this is the third T4 session. The first and third sessions produced identical sha256 for the three decode-check layer files. Session 1's tar download failed (500 on a single 3.6 GB file) and session 2 was reclaimed by Colab at part 50 of 54; the delivered files come from session 3 (64 MB parts, each hash-checked).
- sha256 MANIFEST.json = d46831d43e47b32206c1e79571f331de2ae6d5ff764576fb589de1585ede7928
- sha256 instrument.json = 46079e2729f34d887d8e8a25ad0c4006293dd1bd5f8f58c6db3cc40dbfccc956

## Decode equality (dequantize_4bit, fp16 output, sha256 of the raw dequantized bytes)

Layers: early = model.layers.0.self_attn.q_proj, middle = model.layers.16.mlp.gate_proj, late = model.layers.31.mlp.down_proj.

    layer   VM CUDA (T4)      Mac CPU (arm64)   VM CPU (x86)      CUDA vs x86-CPU
    early   f1b5c32b8bd1ed96  f1b5c32b8bd1ed96  f4166ec5906fb6b2  n_diff 573,  max|d| 1.22e-04
    middle  b4a77586a1a85e70  b4a77586a1a85e70  eaf2686c6184b9cc  n_diff 3175, max|d| 3.05e-05
    late    01a1e06c4d757b9b  01a1e06c4d757b9b  ded58d0e2c1562d5  n_diff 6716, max|d| 6.10e-05

Full 64-hex hashes: `records/decode_vm.json`, `records/decode_mac_cpu.json`.

1. Step 2 (VM CUDA vs VM CPU): NOT bitwise equal. The x86 CPU path of bnb 0.50.2 differs from CUDA in 0.003% to 0.04% of fp16 elements (at most 1 fp16 ulp at those magnitudes). This is a property of the x86 CPU kernel and does not touch the Mac.
2. Step 4 (go/no-go, Mac CPU vs VM CUDA): bitwise EQUAL on all three layers (n_diff 0). Mac env: torch 2.14.1, bitsandbytes 0.50.2, via `env -u PYTHONPATH uv run --project workbench --with bitsandbytes==0.50.2`. The Mac run decodes this instrument exactly as the T4 does.

Scope: 3 of 224 layers were checked, so equality on the other 221 is expected and not measured. A full-layer Mac decode versus CUDA is not available; the CUDA decode hashes exist only for these three layers.

## Contents of records/
decode_vm.json, decode_mac_cpu.json, nvidia_smi.txt, nf4_prepare.log (session 3).
