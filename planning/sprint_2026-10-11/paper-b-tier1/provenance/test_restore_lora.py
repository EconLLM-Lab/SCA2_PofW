"""Small-tensor regression; never instantiates an 8B model."""
from pathlib import Path
import unittest
import torch
from safetensors.torch import load_file
from restore_lora import restore_exact_lora

ADAPTER = Path.home()/'.cache/huggingface/hub/datasets--Bonorinoa--SCA2-paper-b-adapters/snapshots/c4b0f36eae0c15e508f72b606861798c8359131f/adapters/USA'

class ExactLora(unittest.TestCase):
    def test_restores_file_not_rounded_half_copy(self):
        saved = load_file(str(ADAPTER/'adapter_model.safetensors'))
        params = {k.replace('.weight','.default.weight'):torch.nn.Parameter(v.half().float()) for k,v in saved.items()}
        class Scaffold:
            def named_parameters(self):
                return params.items()
        self.assertTrue(any(not torch.equal(params[k.replace('.weight','.default.weight')], v) for k,v in saved.items()))
        restore_exact_lora(Scaffold(), ADAPTER)
        for key,value in saved.items():
            parameter = params[key.replace('.weight','.default.weight')]
            self.assertEqual(parameter.dtype, torch.float32)
            self.assertTrue(torch.equal(parameter,value), key)

if __name__ == '__main__':
    torch.set_num_threads(2)
    unittest.main()
