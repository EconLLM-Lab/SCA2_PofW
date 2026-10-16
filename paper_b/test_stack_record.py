"""Stack identity is recorded, and an archive gap is reported, not hidden."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

import score_runtime as R
from test_persist_unit import CODE_REV, InMemoryHub, _scores


def test_package_versions_reads_metadata_without_importing_heavy_packages():
    import sys
    before = set(sys.modules)
    v = R.package_versions()
    assert {"python", "torch", "transformers", "peft", "bitsandbytes", "accelerate"} <= set(v)
    assert all(isinstance(x, str) for x in v.values())
    assert "torch" not in (set(sys.modules) - before)          # reading versions must never import a package


def test_missing_package_is_reported_as_not_installed():
    assert R.package_versions(names=("definitely_not_a_package_xyz",))["definitely_not_a_package_xyz"] == "not installed"


def _frame(q, codes, logps):
    probs = np.exp(logps) / np.exp(logps).sum()
    return pd.DataFrame({"question_id": q, "option_index": range(len(codes)), "option_code": codes,
                         "option_logprob": logps, "model_prob": probs})


def test_archive_gap_summary_counts_and_localises_the_gap():
    ref = pd.concat([_frame("Q1", ["1", "2"], np.array([-1.0, -2.0])),
                     _frame("Q2", ["1", "2", "3"], np.array([-1.0, -2.0, -3.0]))], ignore_index=True)
    got = ref.copy()
    got.loc[got.question_id.eq("Q2") & got.option_code.eq("3"), "option_logprob"] -= 0.4
    s = R.archive_gap_summary(got, ref, tol_logprob=0.01)
    assert s["n_compared"] == 5 and s["n_over_tol"] == 1 and s["questions_over_tol"] == ["Q2"]
    assert s["max_dlogprob"] == pytest.approx(0.4) and s["share_over_tol"] == pytest.approx(0.2)
    clean = R.archive_gap_summary(ref, ref, tol_logprob=0.01)
    assert clean["n_over_tol"] == 0 and clean["questions_over_tol"] == [] and clean["max_dlogprob"] == 0.0


def test_archive_gap_summary_refuses_unmatched_keys():
    ref = _frame("Q1", ["1", "2"], np.array([-1.0, -2.0]))
    with pytest.raises(ValueError, match="one-to-one"):
        R.archive_gap_summary(ref.iloc[:1], ref, tol_logprob=0.01)


def test_unit_manifest_carries_the_stack(tmp_path):
    hub = InMemoryHub()
    R.persist_unit_scores(scores=_scores(), model_name="CHN_adapter", run_id="run-x", repo=R.ARTIFACTS_REPO,
                          hub=hub, adapter_sha256="a" * 64, code_revision=CODE_REV, local_dir=tmp_path)
    man = json.loads(hub.files["runs/run-x/manifests/CHN_adapter_manifest.json"])
    assert man["stack_versions"]["python"] and "bitsandbytes" in man["stack_versions"]


def test_bank2_gate_keeps_adapter_checks_fatal_and_archive_check_report_only():
    """Policy in PAPER_B_STACK_FREEZE.md: archive mismatch is reported; same-weights and switch-back gate."""
    from pathlib import Path
    src = (Path(__file__).resolve().parent / "colab" / "vm_gate_factorial.py").read_text()
    assert "BASE GATE FAILED" not in src                       # the archive comparison cannot stop the run
    assert "report-only" in src and "archive_gap_summary" in src
    assert "ADAPTER GATE FAILED" in src                        # the binding check still stops it
    assert 'report["gate_pass"] = bool(adapter_ok and switch_ok)' in src
    assert "formatted prompt differs from the archive; model was not loaded" in src   # prompt identity stays fatal


def test_gate_uploads_its_report_and_hashes_the_spec_and_setup_pins_bitsandbytes():
    from pathlib import Path
    colab = Path(__file__).resolve().parent / "colab"
    gate = (colab / "vm_gate_factorial.py").read_text()
    assert "gate_report.json" in gate and "spec_sha256(strict)" in gate          # verifier F5, F10
    assert "bitsandbytes==0.50.2" in (colab / "vm_setup.py").read_text()          # verifier F6; the frozen version


def test_gate_report_names_the_unit_it_gated():
    from pathlib import Path
    gate = (Path(__file__).resolve().parent / "colab" / "vm_gate_factorial.py").read_text()
    assert '"unit": GATE_UNIT' in gate           # a reader must not have to infer which cell was gated
