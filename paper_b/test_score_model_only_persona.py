"""C8: the model-only persona branch of score_cohort, run end to end with a fake model and a fake Hub.

The persona arm existed in score_cohort but had never run in Paper B. This drives `_score_model_only_gpu` itself
(the function the VM calls) with the real prompt builder and the real `score_model_questions`; only the forward
pass, the tokenizer template and the Hub write are replaced.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import score_cohort as S  # noqa: E402
import score_plan as SPL  # noqa: E402
import score_runtime as R  # noqa: E402


@pytest.fixture
def harness(monkeypatch):
    seen = {"prompts": [], "persisted": [], "models": set()}

    def fake_logprob(model, tokenizer, prompt_text, completion):
        seen["prompts"].append(prompt_text)
        seen["models"].add(model)
        assert completion.startswith(" ")                     # the frozen leading space before every code
        return -float(len(completion)) - 0.1 * (hash(prompt_text) % 7), 2

    monkeypatch.setattr(S, "load_base_model_and_tokenizer", lambda: ("BASE_WEIGHTS", "TOK"))
    monkeypatch.setattr(S, "prepare_prompt_for_model", lambda tok, text: {
        "formatted_prompt": text, "model_prompt_text": text, "prompt_token_count_before_truncation": 1,
        "prompt_token_count_model": 1, "prompt_was_truncated": False})
    monkeypatch.setattr(S, "sequence_logprob", fake_logprob)
    monkeypatch.setattr(R, "HuggingFaceArtifactStore", lambda: "STORE")
    monkeypatch.setattr(R, "persist_unit_scores", lambda **kw: seen["persisted"].append(kw) or {})
    monkeypatch.setattr(R, "code_revision", lambda repo: "rev")
    import compute_ledger
    monkeypatch.setattr(compute_ledger, "try_record", lambda *a, **k: True)
    return seen


def _args(countries, arms="persona"):
    return types.SimpleNamespace(arms=arms, countries=countries, run_id=SPL.CONDITIONS["persona_strict_v1"]["run_id"],
                                 artifact_repo=SPL.ARTIFACTS_REPO, adapter_revision=SPL.ADAPTER_REVISION)


def _spec():
    spec = SPL.build_spec("persona_strict_v1")
    return {"spec_sha256": SPL.spec_hash(spec), **spec}


def test_persona_branch_scores_each_country_on_base_weights_with_its_name(harness):
    rc = S._score_model_only_gpu(_args(["ARG", "USA", "GBR"]), _spec())
    assert rc == 0
    assert harness["models"] == {"BASE_WEIGHTS"}                # no adapter is ever loaded
    names = [p["model_name"] for p in harness["persisted"]]
    assert names == ["persona_ARG", "persona_USA", "persona_GBR"]
    for p, country in zip(harness["persisted"], ["Argentina", "the United States", "Great Britain"]):
        frame = p["scores"]
        assert frame["question_id"].nunique() == 23
        assert set(frame["prompt_text"].str.split(". ", regex=False).str[0]) == {
            f"Answer this questionnaire as a typical adult living in {country}"}
        assert p["spec_sha"] == SPL.spec_hash(SPL.build_spec("persona_strict_v1"))
        assert p["adapter_revision"] == "" and p["run_id"] == "persona-strict-v1-20261019"
        sums = frame.groupby("question_id")["model_prob"].sum()
        assert (sums.sub(1).abs() < 1e-8).all()


def test_base_only_call_scores_the_unconditioned_prompt(harness):
    rc = S._score_model_only_gpu(_args([], arms="base"), _spec())
    assert rc == 0
    assert [p["model_name"] for p in harness["persisted"]] == ["base"]
    first = harness["persisted"][0]["scores"]["prompt_text"].str.split(". ", regex=False).str[0]
    assert set(first) == {"Answer this questionnaire as an individual person"}


def test_a_profile_unit_is_refused_as_a_persona_under_the_country_cohort(harness):
    assert S._score_model_only_gpu(_args(["P_0_0_0_0_0_0"]), _spec()) == 2
    assert harness["persisted"] == []
