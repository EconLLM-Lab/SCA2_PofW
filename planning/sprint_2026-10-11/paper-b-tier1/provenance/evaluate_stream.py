"""CPU-only, single-block replay; NF4 is a diagnostic, not the frozen CUDA kernel.

The prefix factorization is checked against the unmodified scorer when requested.
No human records, joins, or means are read. No model files are written.
"""
import argparse
import csv
import json
import os
import resource
import sys
import time
from pathlib import Path

import torch

P = argparse.ArgumentParser()
P.add_argument('--mode', choices=['f32','f16','nf4'], required=True)
P.add_argument('--arm', choices=['base','USA_adapter'], required=True)
P.add_argument('--items', nargs='+', default=['Q57','Q58','Q81','Q106','Q107'])
P.add_argument('--check-serial', action='store_true')
P.add_argument('--compute-dtype', choices=['float16','float32'], default='float16')
P.add_argument('--no-double-quant', action='store_true')
P.add_argument('--quant-type', choices=['nf4','fp4'], default='nf4')
P.add_argument('--tag', choices=['no_double_quant','compute_f32','fp4'])
a = P.parse_args()
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
WB = ROOT/'.worktrees/adapter-brain-vizualization/workbench'
sys.path[:0] = [str(ROOT/'paper_b'), str(WB/'src')]
from sca2_workbench.offload_hf import build_offloaded_hf
from sca2_workbench.stream_capture import SafetensorsSource
import sca2_workbench.offload_hf as OH
from transformers import AutoTokenizer
import score_cohort as S

LIMIT = 16_000_000_000

def guard():
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if rss > LIMIT:
        raise SystemExit(f'STOP: peak RSS {rss} > {LIMIT} bytes')
    return rss

# Never select MPS/CUDA: all input and weight tensors stay on CPU.
torch.set_num_threads(8)
SNAP = Path.home()/'.cache/huggingface/hub/models--meta-llama--Llama-3.1-8B-Instruct/snapshots/0e9e39f249a16976918f6564b8830bc894c89659'
ADAPTER = Path.home()/'.cache/huggingface/hub/datasets--Bonorinoa--SCA2-paper-b-adapters/snapshots/c4b0f36eae0c15e508f72b606861798c8359131f/adapters/USA'
DTYPE = torch.float32 if a.mode == 'f32' else torch.float16
class DiagnosticSource(SafetensorsSource):
    def __init__(self, snapshot, dtype):
        super().__init__(snapshot, torch.float32)
        self.dtype = dtype
OH.SafetensorsSource = DiagnosticSource
quantized = set()
if a.mode == 'nf4':
    import bitsandbytes.functional as F
    original_get = SafetensorsSource._get
    def nf4_get(self, name):
        weight = original_get(self, name)
        # The frozen BNB loader replaces Linear modules, but not lm_head or embeddings/norms.
        if name.startswith('model.layers.') and ('.self_attn.' in name or '.mlp.' in name) and name.endswith('.weight'):
            packed, state = F.quantize_4bit(weight.contiguous(), quant_type=a.quant_type, blocksize=64,
                                           compress_statistics=not a.no_double_quant)
            weight = F.dequantize_4bit(packed, state).reshape_as(weight)
            quantized.add(name)
        guard()
        return weight
    SafetensorsSource._get = nf4_get

tok = AutoTokenizer.from_pretrained(SNAP, local_files_only=True)
model = build_offloaded_hf(SNAP, DTYPE,
    adapter_dir=ADAPTER if a.arm=='USA_adapter' else None,
    model_id='meta-llama/Llama-3.1-8B-Instruct' if a.arm=='USA_adapter' else None)
# Production PEFT keeps saved F32 LoRA values, not a half-rounded scaffold copy.
lora_restored = 0
if a.arm == 'USA_adapter':
    from restore_lora import restore_exact_lora
    lora_restored = restore_exact_lora(model, ADAPTER)
model.eval()
if a.mode == 'nf4' and a.compute_dtype == 'float32':
    # Isolate Linear arithmetic only; residuals/embeddings/norms stay fp16.
    import types
    def diagnostic_linear(self, inputs):
        return torch.nn.functional.linear(inputs.float(), self.weight.float(), self.bias).to(inputs.dtype)
    for name, module in model.named_modules():
        if (isinstance(module, torch.nn.Linear) and 'lora_' not in name
                and ('.self_attn.' in name or '.mlp.' in name)):
            module.forward = types.MethodType(diagnostic_linear, module)
def check_rss_hook(*_):
    guard()
for m in model.modules():
    m.register_forward_hook(check_rss_hook)
render = json.loads((OUT/'prompts_new.json').read_text())
archive = list(csv.DictReader((ROOT/f'planning/sprint_2026-10-11/paper-b-20261011/scores_for_join/{a.arm}_option_probabilities.csv').open()))
result = {'mode':a.mode,'arm':a.arm,'device':'cpu','torch':torch.__version__,
          'dtype':str(DTYPE),'lora_dtype':'float32','quantization': 'CPU block64 quantize/dequantize + dense linear; not CUDA BNB matmul' if a.mode=='nf4' else None,
          'quant_type':a.quant_type if a.mode=='nf4' else None,
          'double_quant':not a.no_double_quant if a.mode=='nf4' else None,
          'linear_compute_dtype':a.compute_dtype if a.mode=='nf4' else str(DTYPE),
          'lora_tensors_restored_from_file':lora_restored,
          'items':{}, 'limitations':['New transformers/torch/peft; not the frozen CUDA image.']}
t0 = time.monotonic()
for qid in a.items:
    entry = render['items'][qid]
    codes = entry['spec']['codes']
    completions = [entry['completion_ids'][c] for c in codes]
    prefix = completions[0][:-1]
    assert prefix and all(c[:-1]==prefix for c in completions), 'factorization requires shared completion prefix'
    ids = entry['model_prompt_ids'] + prefix
    with torch.no_grad():
        logits = model(input_ids=torch.tensor([ids],device='cpu')).logits[0]
    guard()
    scores_by_dtype = {}
    # New HF upcasts output logits; old HF returned the model dtype. Isolate this reduction difference.
    for label, reduction_dtype in [('float32',torch.float32),('float16',torch.float16)]:
        lp = torch.log_softmax(logits.to(reduction_dtype),dim=-1)
        shared = sum((lp[len(entry['model_prompt_ids'])-1+i,token] for i,token in enumerate(prefix)))
        scores = torch.stack([shared+lp[-1,c[-1]] for c in completions])
        scores_by_dtype[label] = {'scores':scores.tolist(), 'probs':torch.softmax(scores.double(),dim=-1).tolist()}
    ref = sorted([r for r in archive if r['question_id']==qid],key=lambda r:int(r['option_index']))
    assert [r['option_code'] for r in ref] == codes
    ar_probs = [float(r['model_prob']) for r in ref]
    item = {'codes':codes,'archive_scores':[float(r['option_logprob']) for r in ref],
            'archive_probs':ar_probs,'reductions':scores_by_dtype}
    for red in scores_by_dtype.values():
        red['max_abs_probability_gap_vs_archive'] = max(abs(x-y) for x,y in zip(red['probs'],ar_probs))
        red['reproduced_at_1e_3'] = red['max_abs_probability_gap_vs_archive'] <= 1e-3
    if a.check_serial and qid=='Q81':
        serial = [S.sequence_logprob(model,tok,entry['prompt_text'],' '+c)[0] for c in codes]
        gap = max(abs(x-y) for x,y in zip(serial,scores_by_dtype['float32']['scores']))
        item['serial_sequence_logprob'] = serial
        item['prefix_factorization_max_abs_score_gap'] = gap
        assert gap < 1e-3, gap
    item['peak_rss_bytes'] = guard()
    result['items'][qid] = item
    result['elapsed_seconds'] = time.monotonic()-t0
    result['quantized_weight_count'] = len(quantized)
    suffix = f'_{a.tag}' if a.tag else ''
    (OUT/f'replay_{a.mode}_{a.arm}{suffix}.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({'qid':qid,'arm':a.arm,'mode':a.mode,'reductions':scores_by_dtype,
                      'elapsed_seconds':result['elapsed_seconds'],'peak_rss_bytes':guard()}),flush=True)
print('DONE',a.mode,a.arm,flush=True)
