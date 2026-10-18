"""A Hugging Face ``LlamaForCausalLM`` that holds one block of weights at a time.

Paper B's scorer (``score_cohort.sequence_logprob``) takes a HF model. Llama-3.1-8B in float32 is
32 GB, which does not fit on this 24 GB Mac, so the reference model is built with *placeholder*
(empty) parameters and each block is filled from the safetensors file just before it runs and
emptied just after:

    embed_tokens, layers[0], ..., layers[L-1], norm, lm_head   (one at a time)

It is HF's own modelling code (attention, RoPE, RMSNorm, mask) running in ``dtype``; only where the
weights live differs. The parameters stay on ``cpu`` (size 0 between blocks), so
``next(model.parameters()).device`` is a real device, which ``sequence_logprob`` reads.

With ``adapter_dir`` the model is wrapped by peft (``get_peft_model`` with the adapter's own
``LoraConfig``), so the LoRA runs through peft's unmerged forward ``base(x) + B(A(x)) * scale``.
The LoRA tensors are small and stay resident; they are set from the adapter file explicitly and
compared to it (peft 0.21.2 can leave LoRA B at zero, AUDIT.md section 11).
"""

from __future__ import annotations

from pathlib import Path

import torch

from sca2_workbench.stream_capture import SafetensorsSource


def build_offloaded_hf(snapshot: str | Path, dtype: torch.dtype = torch.float32,
                       adapter_dir: str | Path | None = None, model_id: str | None = None):
    """Return a HF ``LlamaForCausalLM`` (eval mode, eager attention) that loads blocks on demand.

    ``adapter_dir`` (with ``model_id``, the base the adapter must name) returns the peft-wrapped
    model; the base weights still stream, the LoRA A/B stay resident.
    """
    from transformers import AutoConfig, AutoModelForCausalLM  # noqa: PLC0415
    from transformers.models.llama.modeling_llama import LlamaRotaryEmbedding  # noqa: PLC0415

    src = SafetensorsSource(snapshot, dtype)         # reuse its file index and config checks
    cfg = AutoConfig.from_pretrained(snapshot)
    with torch.device("meta"):
        model = AutoModelForCausalLM.from_config(cfg, dtype=dtype, attn_implementation="eager")
    model.model.rotary_emb = LlamaRotaryEmbedding(config=cfg)   # a buffer, so rebuilt for real
    inner = model
    file_sd = {}
    if adapter_dir is not None:
        from peft import LoraConfig, get_peft_model  # noqa: PLC0415

        from sca2_workbench.llama_capture import check_adapter  # noqa: PLC0415

        if model_id is None:
            raise ValueError("model_id is required with an adapter (the base it must name)")
        _, file_sd = check_adapter(adapter_dir, model_id)
        model = get_peft_model(model, LoraConfig.from_pretrained(str(adapter_dir)))
    n_lora = 0
    for mname, module in model.named_modules():      # placeholders: real device, no storage
        for name, p in list(module._parameters.items()):
            if p is None:                            # bias=False layers keep their None
                continue
            full = f"{mname}.{name}"
            if "lora_" in full:                      # .lora_A.default.weight -> file key
                key = full.replace(".default.weight", ".weight")
                if key not in file_sd:
                    raise ValueError(f"adapter file has no tensor for {full}")
                module._parameters[name] = torch.nn.Parameter(file_sd[key].to(dtype).clone(),
                                                              requires_grad=False)
                n_lora += 1
            else:
                module._parameters[name] = torch.nn.Parameter(
                    torch.empty(0, dtype=dtype), requires_grad=False)
    if n_lora != len(file_sd):
        raise ValueError(f"set {n_lora} LoRA tensors, the adapter file has {len(file_sd)}")
    for n, p in model.named_parameters():            # what is in the module IS the file
        if "lora_" in n and not torch.equal(p.detach(), file_sd[n.replace(".default.weight", ".weight")].to(dtype)):
            raise ValueError(f"adapter tensor {n} did not load (module != file)")
    model.eval()

    def file_name(full: str) -> str:
        full = full.replace(".base_layer.", ".")     # peft moves the base weight one level down
        if full in src._file_of:
            return full
        if full == "lm_head.weight":                 # tied embeddings
            return "model.embed_tokens.weight"
        raise KeyError(full)

    def fill(prefix: str):
        def pre(module, args, kwargs=None):
            for pname, p in module.named_parameters():
                if "lora_" not in pname:
                    p.data = src._get(file_name(f"{prefix}.{pname}"))
        def post(module, args, output=None, *rest):
            for pname, p in module.named_parameters():
                if "lora_" not in pname:
                    p.data = torch.empty(0, dtype=dtype)
            src.drop_handles()     # else the mmap'd shard pages stay resident (RSS +0.25 GB/layer)
        return pre, post

    if adapter_dir is not None:
        inner = model.base_model.model
    blocks = [("model.embed_tokens", inner.model.embed_tokens), ("model.norm", inner.model.norm),
              ("lm_head", inner.lm_head)]
    blocks += [(f"model.layers.{i}", blk) for i, blk in enumerate(inner.model.layers)]
    for prefix, module in blocks:
        pre, post = fill(prefix)
        module.register_forward_pre_hook(pre)
        module.register_forward_hook(post)
    return model
