from pathlib import Path

from sca2.notebook import eval_claim, labeled_file, load_plan, to_iso3, train_knobs


def test_us_alias_is_usa() -> None:
    assert to_iso3("US") == "USA"
    assert to_iso3("mex") == "MEX"


def test_train_knobs_map_notebook_names(tmp_path: Path) -> None:
    plan_path = tmp_path / "train_plan.json"
    plan_path.write_text(
        """
        {
          "base_model": "meta-llama/Llama-3.1-8B-Instruct",
          "files": {"USA": "/tmp/D_syn_USA.jsonl"},
          "split": {"train_frac": 0.8, "seed": 42},
          "dpo": {"beta": 0.1},
          "lora": {"r": 16, "alpha": 32},
          "execute": false
        }
        """
    )
    plan = load_plan(plan_path)
    knobs = train_knobs(plan)
    assert knobs["MODEL_NAME"].endswith("8B-Instruct")
    assert knobs["beta"] == 0.1
    assert knobs["lora_r"] == 16
    assert knobs["execute"] is False
    assert labeled_file(plan, "US") == Path("/tmp/D_syn_USA.jsonl")


def test_eval_claim_repeats_boundary(tmp_path: Path) -> None:
    path = tmp_path / "eval_plan.json"
    path.write_text('{"claim_boundary": "not recovery of P_human"}')
    assert "not recovery" in eval_claim(load_plan(path))
