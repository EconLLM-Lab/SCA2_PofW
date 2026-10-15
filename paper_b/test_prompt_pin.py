"""The archived readout froze Llama's chat date. A later 'today' changes logprobs."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import eval_config as E
import score_cohort as S


class _Ids:
    input_ids = [1, 2, 3]


class FakeTokenizer:
    def __init__(self):
        self.kwargs = None

    def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=True, **kwargs):
        self.kwargs = kwargs
        return "FORMATTED"

    def __call__(self, text, add_special_tokens=False):
        return _Ids()

    def decode(self, ids, skip_special_tokens=False, clean_up_tokenization_spaces=False):
        return "FORMATTED"


def test_archive_prompt_uses_pinned_chat_date():
    ref = pd.read_csv(
        E.ARCHIVE_DIR / "model_option_probabilities_base_on_CHN.csv", dtype=str)
    assert E.ARCHIVE_CHAT_DATE in ref.loc[ref.question_id.eq("Q57"), "formatted_prompt"].iloc[0]


def test_prepare_prompt_passes_pinned_chat_date():
    tok = FakeTokenizer()
    S.prepare_prompt_for_model(tok, "question")
    assert tok.kwargs["date_string"] == E.ARCHIVE_CHAT_DATE
