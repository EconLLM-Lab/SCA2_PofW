"""Render model-only prompts from a selected source tree, never survey frames."""
import argparse
import hashlib
import inspect
import json
import sys
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--root', type=Path, required=True)
p.add_argument('--out', type=Path, required=True)
p.add_argument('--snapshot', type=Path, required=True)
a = p.parse_args()
sys.path.insert(0, str(a.root/'paper_b'))
import eval_config as E
import eval_lib as L
import score_cohort as S
import build_scoring_spec as B
from transformers import AutoTokenizer

tok = AutoTokenizer.from_pretrained(a.snapshot, local_files_only=True)
qmap = L.load_question_map()
spec = B.build_scoring_spec(qmap, numeric_support={}, battery='strict')
result = {'root':str(a.root), 'spec_sha256':B.spec_sha256(spec), 'spec':spec,
          'constants':{k:getattr(E,k) for k in ['ARCHIVE_CHAT_DATE','COMPLETION_PREFIX','EVAL_MAX_PROMPT_TOKENS','EVAL_MAX_COMPLETION_TOKENS','LENGTH_NORMALIZE_OPTION_LOGPROBS','OPTION_SCORE_TEMPERATURE']},
          'functions':{f.__name__:inspect.getsource(f) for f in [L.build_survey_user_prompt,S.prepare_prompt_for_model,S.sequence_logprob,S.load_base_model_and_tokenizer]}, 'items':{}}
for q in spec['questions']:
    if q['question_id'] not in ['Q57','Q58','Q81','Q106','Q107']:
        continue
    text = L.build_survey_user_prompt(q, prompt_country=None)
    prepared = S.prepare_prompt_for_model(tok,text)
    result['items'][q['question_id']] = {'spec':q, 'prompt_text':text, **prepared,
        'prompt_utf8_hex':prepared['formatted_prompt'].encode().hex(),
        'formatted_prompt_sha256':hashlib.sha256(prepared['formatted_prompt'].encode()).hexdigest(),
        'completion_ids':{c:tok(E.COMPLETION_PREFIX+c,add_special_tokens=False).input_ids for c in q['codes']},
        'base_and_usa_share_same_prompt':True}
a.out.write_text(json.dumps(result,indent=2))
print('rendered',str(a.out),'spec_sha256',B.spec_sha256(spec),'items',list(result['items']))
