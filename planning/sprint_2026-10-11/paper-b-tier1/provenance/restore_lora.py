"""Restore adapter precision after the streaming scaffold's dtype conversion."""

def restore_exact_lora(model, adapter_dir):
    from safetensors.torch import load_file
    import torch
    from pathlib import Path
    saved = load_file(str(Path(adapter_dir)/'adapter_model.safetensors'), device='cpu')
    restored = 0
    for name, parameter in model.named_parameters():
        if 'lora_' in name:
            value = saved[name.replace('.default.weight','.weight')].float()
            parameter.data = value.clone()
            assert torch.equal(parameter.detach(),value), name
            restored += 1
    assert restored == len(saved), (restored,len(saved))
    return restored
