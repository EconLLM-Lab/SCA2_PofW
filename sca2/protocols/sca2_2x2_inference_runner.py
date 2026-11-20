#!/usr/bin/env python3
"""sca2_2x2_one.py — run ONE adapter under persona prompt, save CSV.

Usage: python sca2_2x2_one.py {COUNTRY}
Loads the base model (from HF cache if warm), loads the country adapter
(subfolder per bank), computes per-option log-probs under the persona
prompt, saves /content/out/model_option_probabilities_{C}_adapter_persona.csv.
"""
import json, pathlib, sys
import numpy as np
import pandas as pd
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel

MODEL_ID = "meta-llama/Llama-3.1-8B-Instruct"
HF_REPO = "Bonorinoa/SCA2-phase2-adapters"
BASE8 = {"CHN","JPN","GBR","USA","MEX","ARG","DEU","RUS"}
COUNTRY_NAMES = {
    "ARG": "Argentina", "BRA": "Brazil", "CHN": "China", "DEU": "Germany",
    "EGY": "Egypt", "GBR": "Great Britain", "GRC": "Greece", "IDN": "Indonesia",
    "IND": "India", "JPN": "Japan", "MEX": "Mexico", "NGA": "Nigeria",
    "NLD": "the Netherlands", "RUS": "Russia", "TUR": "Turkey", "USA": "the United States",
}
MAX_TOK = 1200
OUT = pathlib.Path("/content/out"); OUT.mkdir(exist_ok=True)

def main():
    country = sys.argv[1]
    survey = json.loads(pathlib.Path("/content/survey_spec.json").read_text())

    def build_prompt(spec, c):
        persona = f"Answer this questionnaire as a typical adult living in {COUNTRY_NAMES[c]}."
        if spec["is_numeric_open"]:
            resp = "Give one whole-number response. Return only the number, with no words or explanation."
        else:
            lines = "\n".join(f"{code}: {label}" for code, label in zip(spec["codes"], spec["labels"]))
            resp = ("Select exactly one response code from the options below.\n" + lines +
                    "\n\nReturn only the response code, with no words or explanation.")
        return (f"{persona} Respond naturally and sincerely, as someone would in real life. "
                "Do not mention being an AI or assistant.\n\n"
                f"Question:\n{spec['question_text']}\n\n{resp}\n\nAnswer:")

    def fmt(tok, text):
        return tok.apply_chat_template([{"role": "user", "content": text}],
                                       tokenize=False, add_generation_prompt=True)

    def option_probs(model, tok, formatted, codes):
        import torch.nn.functional as F
        out = {}
        dev = next(model.parameters()).device
        for code in codes:
            answer = tok(f"{code}", add_special_tokens=False)["input_ids"]
            full = tok(formatted + f"{code}", return_tensors="pt",
                       truncation=True, max_length=MAX_TOK + 8).to(dev)
            with torch.no_grad():
                lg = model(**full, labels=full["input_ids"]).logits[0, :-1, :]
            ids = full["input_ids"][0, 1:]
            logp = F.log_softmax(lg.float(), dim=-1).gather(1, ids.unsqueeze(1)).squeeze(1)
            out[code] = float(logp[-len(answer):].sum())
        vals = np.array([out[c] for c in codes])
        probs = np.exp(vals - vals.max()); probs = probs / probs.sum()
        return {c: (float(vals[i]), float(probs[i])) for i, c in enumerate(codes)}

    # load base (HF cache warm after first)
    print("loading base...")
    import torch.cuda as tc
    gpu_mem = tc.get_device_properties(0).total_memory // (1024**2) if tc.is_available() else 0
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                             bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.float16)
    tok = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID, quantization_config=bnb, device_map="auto",
        torch_dtype=torch.float16,
        max_memory={0: f"{int(gpu_mem * 0.92)}MB"} if gpu_mem else None)
    model.eval()

    # Hub quirk: the USA adapter was uploaded as base8/US (no trailing 'A')
    HUB_NAME = {"USA": "US"}
    sub = ("base8" if country in BASE8 else "co2_8") + "/" + HUB_NAME.get(country, country)
    print(f"loading adapter {HF_REPO} subfolder={sub}")
    pm = PeftModel.from_pretrained(model, HF_REPO, subfolder=sub)
    pm.eval()

    rows = []
    LOG = pathlib.Path("/content/progress.log")
    for i, (qid, spec) in enumerate(survey.items()):
        fp = fmt(tok, build_prompt(spec, country))
        res = option_probs(pm, tok, fp, spec["codes"])
        for code in spec["codes"]:
            lp, pr = res[code]
            rows.append({"model": f"{country}_adapter_persona", "prompt_country": country,
                         "question_id": qid, "option_code": code,
                         "option_value": float(spec["option_values"][spec["codes"].index(code)]),
                         "option_logprob": lp, "model_prob": pr,
                         "response_type": spec["response_type"],
                         "is_numeric_open": spec["is_numeric_open"]})
        with LOG.open("a") as f:
            f.write(f"{country} q{i+1}/{len(survey)} {qid} done\n")
    pd.DataFrame(rows).to_csv(OUT / f"model_option_probabilities_{country}_adapter_persona.csv", index=False)
    print(f"DONE {country}: {len(rows)} rows saved")

if __name__ == "__main__":
    main()
