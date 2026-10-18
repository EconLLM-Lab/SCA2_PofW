# Config fixtures for the Llama-3 RoPE parity test

`llama-3.1-8B-Instruct.config.json` is the unmodified `config.json` that Hugging Face served for
`meta-llama/Llama-3.1-8B-Instruct`, downloaded on 2026-10-17 with the engineer profile's `HF_TOKEN`:

```
hf_hub_download("meta-llama/Llama-3.1-8B-Instruct", "config.json")
sha256 29e4c210b0d6ac178b16b2a255a568bdb23b581e50ca1ef6a6d071dd85704e6e  (855 bytes)
```

It is checked in so `tests/test_llama3_rope.py` runs offline and so the rope parameters under test
are auditable: the test asserts the file's sha256, then uses it as-is. It is the same
`rope_type: llama3` scheme the Llama-3.2 models use, with `factor: 8.0` and `head_dim: 128`.

`meta-llama/Llama-3.2-1B` and `meta-llama/Llama-3.2-1B-Instruct` are a separate licence gate: the
account behind that token is approved for Llama-3.1 but **not** for Llama-3.2, so
`resolve/main/config.json` answers

```
403 Client Error: Access to model meta-llama/Llama-3.2-1B is restricted and you are not in the
authorized list.
```

(Repo metadata still loads, and `hf_hub_download` is the call that fails.) No mirror is used. The
3.2-1B case in the test is therefore parametrised and skips when that config is not in the local
HF cache; once access is granted, dropping a copy of the real config.json into the cache (or
`hf_hub_download`-ing it once) turns the 3.2-1B parity case on with no code change.
