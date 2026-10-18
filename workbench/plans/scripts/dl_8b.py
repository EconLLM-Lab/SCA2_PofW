"""Download the official bf16 safetensors of Llama-3.1-8B-Instruct into the HF cache (no original/).

The caller must provide a read-scoped ``HF_TOKEN``; credentials are never read from a profile file.
"""
import os

from huggingface_hub import snapshot_download

if not os.environ.get("HF_TOKEN"):
    raise RuntimeError("HF_TOKEN is required for the gated Meta checkpoint")

p = snapshot_download("meta-llama/Llama-3.1-8B-Instruct",
                      allow_patterns=["*.safetensors", "*.json"],
                      token=os.environ["HF_TOKEN"])
print("SNAPSHOT", p)
