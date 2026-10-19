"""Cohort persistence, quantized instrument, and precision regressions (RED first)."""
import json
from pathlib import Path

import pytest
import torch

from sca2_workbench import cohort as C
from sca2_workbench import nf4_source as N


def test_immutable_publish_is_idempotent_and_rejects_changed_bytes(tmp_path):
    p = tmp_path / "run.json"
    C.publish(p, b"original")
    C.publish(p, b"original")
    with pytest.raises(ValueError, match="immutable"):
        C.publish(p, b"changed")
    assert p.read_bytes() == b"original"


def test_completion_requires_every_digest_and_failed_gates_are_not_skipped(tmp_path):
    C.publish(tmp_path / "run.bin", b"weights")
    rec = {"files": {"run.bin": C.digest(tmp_path / "run.bin")}, "pass": False, "identity": "x"}
    C.publish(tmp_path / "done.json", C.json_bytes(rec))
    assert C.completed(tmp_path, tmp_path / "done.json", "x") is False
    rec["pass"] = True
    (tmp_path / "done.json").write_bytes(C.json_bytes(rec))
    assert C.completed(tmp_path, tmp_path / "done.json", "x") is True
    assert C.completed(tmp_path, tmp_path / "done.json", "different") is False
    (tmp_path / "run.bin").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="digest"):
        C.completed(tmp_path, tmp_path / "done.json", "x")


def test_report_only_archive_parity_never_changes_fatal_verdict():
    got = C.archive_parity({"1": .4, "2": .6}, {"1": .5, "2": .5}, "archive.csv",
                           logprobs={"1": -32.125, "2": -16.},
                           archived_logprobs={"1": -32., "2": -16.})
    assert got["pass"] is True and got["fatal"] is False
    assert got["max_abs_prob_gap"] == pytest.approx(.1)
    assert got["max_fp16_ulp"] == 4.
    assert got["options"]["1"]["abs_logprob_gap_nats"] == .125
    assert got["options"]["1"]["archived_fp16_ulp_nats"] == .03125
    assert got["tau"] == 4. and got["unit"] == "archived fp16 logprob ulp"
    got = C.archive_parity({"1": .5}, {"1": .5}, "archive.csv",
                           logprobs={"1": -32.15625}, archived_logprobs={"1": -32.})
    assert got["pass"] is False and got["fatal"] is False
    assert got["max_fp16_ulp"] == 5.
    with pytest.raises(ValueError, match="codes"):
        C.archive_parity({"1": .4}, {"1": .5, "2": .5}, "archive.csv",
                         logprobs={"1": -1.}, archived_logprobs={"1": -1.})


def test_full_completion_logprobs_include_the_shared_space_not_just_code_logits():
    import math
    ro = {"prefix_ids": [2], "code_token": {"1": 0, "2": 1}}
    out = {"logits_last": torch.tensor([0., 0., 0.], dtype=torch.float64),
           "logits_before_readout": torch.tensor([0., 0., 0.], dtype=torch.float64)}
    scores = C.completion_logprobs(out, ro)
    assert scores["1"] == pytest.approx(-2 * math.log(3))
    assert scores["2"] == pytest.approx(-2 * math.log(3))
    with pytest.raises(ValueError, match="one shared"):
        C.completion_logprobs(out, {**ro, "prefix_ids": [2, 2]})


def test_streamed_prefix_logits_equal_a_separate_truncated_prompt_forward(tmp_path):
    from transformers import LlamaConfig, LlamaForCausalLM
    from sca2_workbench import stream_capture as SC, llama_capture as LC
    model = LlamaForCausalLM(LlamaConfig(vocab_size=32, hidden_size=16, intermediate_size=32,
                                        num_hidden_layers=2, num_attention_heads=2, num_key_value_heads=1))
    model.save_pretrained(tmp_path)
    ids = [1, 2, 3, 4]
    with torch.no_grad():
        (got,) = SC.run_streamed(SC.SafetensorsSource(tmp_path), ids, j_plus=1, j_minus=2, full_logits=True)
        ref = LC.run(LC.weights_from_hf(model), ids[:-1], j_plus=1, j_minus=2)
    torch.testing.assert_close(got["logits_before_readout"], ref["logits_last"], atol=1e-12, rtol=1e-12)


def test_canonical_export_strips_only_volatile_metadata():
    m = {"provenance": {"generated_at": "now", "wall_seconds": 4, "git_head": "old",
                        "streaming": {"wall_seconds": 4, "peak_rss_gb": 8, "layer_at_a_time": True}},
         "conservation": {"pass": False}}
    got = C.canonical_manifest(m, {"weights": "nf4_dequant", "source_digest": "abc"})
    assert "generated_at" not in got["provenance"]
    assert "wall_seconds" not in got["provenance"]
    assert got["provenance"]["streaming"] == {"layer_at_a_time": True}
    assert got["weights"] == "nf4_dequant"
    assert got["conservation"]["pass"] is False


def test_frozen_nf4_roundtrip_preserves_codes_state_and_effective_weights(tmp_path):
    bnb = pytest.importorskip("bitsandbytes")
    w = torch.linspace(-2, 3, 8192).reshape(128, 64).half()
    q, state = bnb.functional.quantize_4bit(w, blocksize=64, compress_statistics=True, quant_type="nf4")
    N.save_quant(tmp_path / "q.safetensors", q, state)
    restored = N.load_quant(tmp_path / "q.safetensors", "cpu", torch.float64)
    want = bnb.functional.dequantize_4bit(q, state).double()
    assert torch.equal(restored, want)
    assert not torch.equal(restored, w.double())


def test_offloaded_hf_never_roundtrips_file_lora_through_half(tmp_path):
    from transformers import LlamaConfig, LlamaForCausalLM
    from peft import LoraConfig, get_peft_model
    from safetensors.torch import save_file
    from sca2_workbench.offload_hf import build_offloaded_hf
    cfg = LlamaConfig(vocab_size=32, hidden_size=16, intermediate_size=32,
                      num_hidden_layers=1, num_attention_heads=2, num_key_value_heads=1)
    model_dir, adapter = tmp_path / "model", tmp_path / "adapter"
    LlamaForCausalLM(cfg).save_pretrained(model_dir)
    m = get_peft_model(LlamaForCausalLM(cfg), LoraConfig(r=2, lora_alpha=4, target_modules=["q_proj"]))
    m.save_pretrained(adapter)
    config = json.loads((adapter / "adapter_config.json").read_text())
    config["base_model_name_or_path"] = "test/base"
    (adapter / "adapter_config.json").write_text(json.dumps(config))
    sd = {n.replace(".default.weight", ".weight"): torch.full_like(p, .123456789, dtype=torch.float32)
          for n, p in m.named_parameters() if "lora_" in n}
    save_file(sd, adapter / "adapter_model.safetensors")
    # File tensors must stay F32 even when the base uses another dtype.
    got = build_offloaded_hf(model_dir, torch.float64, adapter_dir=adapter, model_id="test/base")
    for n, p in got.named_parameters():
        if "lora_" in n:
            assert p.dtype == torch.float32
            assert torch.equal(p, sd[n.replace(".default.weight", ".weight")])


def test_index_keeps_failed_run_and_pair(tmp_path):
    for kind in ("run", "pair"):
        m = {"schema": "sca2-workbench/capture@1.1", "kind": kind,
             "model": {"key": "b", "label": "B [nf4_dequant]", "model_id": "test/base", "adapter": None},
             "item": {"item_id": "wvs_Q57"}, "tokens": [1],
             "conservation": {"pass": False}, "readout": {"margin": 0, "probs": {}},
             "a": "a", "b": "b", "item_id": "wvs_Q57", "d_margin": 0}
        (tmp_path / f"{kind}__test.json").write_text(json.dumps(m))
    C.update_index(tmp_path)
    idx = json.loads((tmp_path / "index.json").read_text())
    assert len(idx["runs"]) == len(idx["pairs"]) == 1
    assert idx["runs"][0]["pass"] is False


def test_sync_prefix_rejects_adapter_destination():
    with pytest.raises(ValueError, match="workbench_cohort"):
        C.check_prefix("adapters/ARG")
    assert C.check_prefix("workbench_cohort/pilot") == "workbench_cohort/pilot"


def test_rss_limit_is_decimal_16gb():
    assert C.RSS_LIMIT == 16_000_000_000


def test_cli_directory_does_not_shadow_stdlib_queue():
    import subprocess
    import sys
    got = subprocess.run([sys.executable, "-c", "import queue; import torch; assert hasattr(queue, 'Queue')"],
                         cwd=C.PACKAGE / "runner", capture_output=True, text=True)
    assert got.returncode == 0, got.stderr


def test_pair_gate_failure_can_be_retained_without_weakening_the_gate():
    from sca2_workbench import stream_export as SE
    out = {"head_attr": torch.zeros(1, 1, dtype=torch.float64),
           "mlp_attr": torch.zeros(1, dtype=torch.float64), "embed_attr": 0.,
           "attn_attr": torch.zeros(1, dtype=torch.float64)}
    a = {"tokens": [{"id": 1}], "readout": {"margin": 0., "margin_clamped": 0., "probs": {"1": .5}}}
    b = {"tokens": [{"id": 1}], "readout": {"margin": 1., "margin_clamped": 1., "probs": {"1": .5}}}
    res = {"a": out, "a_clamped": out, "b": out, "b_clamped": out,
           "diffs": {"d_resid_norm": torch.zeros(2, 1), "d_attn_norm": torch.zeros(1, 1),
                     "d_mlp_norm": torch.zeros(1, 1), "d_head_norm": torch.zeros(1, 1, 1)}}
    kwargs = dict(key_a="a", key_b="b", item_id="fixture", man_a=a, man_b=b, res=res,
                  d_weight_head=torch.zeros(1, 1, 4), d_weight_mlp=torch.zeros(1, 3), run_files={})
    with pytest.raises(AssertionError, match="attributions"):
        SE.pair_manifest(**kwargs)
    man, binary = SE.pair_manifest(**kwargs, retain_failed=True)
    assert man["conservation"]["pass"] is False
    assert binary.parts


def test_hub_sync_verifies_the_exact_commit_and_restore_fails_closed(tmp_path, monkeypatch):
    import importlib.util
    import types
    import huggingface_hub as hub
    spec = importlib.util.spec_from_file_location("cohort_sync_test", C.PACKAGE / "runner" / "sync.py")
    sync = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sync)
    root = tmp_path / "local"
    C.publish(root / "run.bin", b"test-only-export")
    marker = root / "units" / "test.json"
    C.publish(marker, C.json_bytes({"files": {"run.bin": C.digest(root / "run.bin")}, "pass": True, "identity": "fixture"}))
    calls = []
    class API:
        def __init__(self, **kwargs):
            pass
        def upload_folder(self, **kwargs):
            assert kwargs["path_in_repo"] == "workbench_cohort/test/exports"
            return types.SimpleNamespace(oid="test-commit")
        def list_repo_files(self, *args, **kwargs):
            raise RuntimeError("listing denied")
    def download(repo, path, **kwargs):
        calls.append(kwargs["revision"])
        return str(root / path.split("/exports/")[1])
    monkeypatch.setenv("HF_TOKEN", "TEST_FIXTURE_NOT_A_CREDENTIAL")
    monkeypatch.setattr(hub, "HfApi", API)
    monkeypatch.setattr(hub, "hf_hub_download", download)
    assert sync.upload_unit(root, marker, "workbench_cohort/test") == "test-commit"
    assert calls == ["test-commit", "test-commit"]
    with pytest.raises(RuntimeError, match="listing denied"):
        sync.restore(root, "workbench_cohort/test")


def _load_runner(name):
    import importlib.util
    import sys
    sys.path.insert(0, str(C.PACKAGE / "runner"))  # scripts import siblings (sync) from their own dir
    spec = importlib.util.spec_from_file_location(f"{name}_test", C.PACKAGE / "runner" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_pilot_is_one_adapter_by_every_item_and_full_run_is_every_model_by_every_item():
    queue = _load_runner("cohort_queue")
    reg = json.loads((C.PACKAGE / "models.json").read_text())
    items = json.loads((C.PACKAGE / "items.json").read_text())["items"]
    keys, got = queue.plan(True, reg, items)
    assert keys == ["base", "ARG"] and len(got) == len(items) == 23
    keys, got = queue.plan(False, reg, items)
    assert len(keys) * len(got) == 43 * 23


def test_cu_cap_aborts_once_elapsed_compute_exceeds_it():
    queue = _load_runner("cohort_queue")
    queue.check_cu_budget(3600.0, 13.08, 35.0)       # 13.08 CU spent: fine
    queue.check_cu_budget(10 ** 9, 13.08, None)      # no cap configured: fine
    with pytest.raises(RuntimeError, match="CU cap"):
        queue.check_cu_budget(3 * 3600.0, 13.08, 35.0)  # 39.24 CU spent


def test_pilot_queue_command_carries_the_cu_cap_and_cohort_does_not():
    job = _load_runner("vm_job")
    cfg = {"a100_unit_seconds": 100.0, "a100_base_seconds": 90.0, "assumed_cu_per_hour": 13.08}
    pilot = job.queue_command("pilot", cfg, "workbench_cohort/x")
    cohort = job.queue_command("cohort", cfg, "workbench_cohort/x")
    assert "--pilot" in pilot and pilot[pilot.index("--max-cu") + 1] == str(job.PILOT_MAX_CU)
    assert pilot[pilot.index("--cu-per-hour") + 1] == "13.08"
    assert "--pilot" not in cohort and "--max-cu" not in cohort


# ---- Mac local queue (runner/mac_queue.py): token-free, local resume, continue/abort policy ----

def _bank(root, key, item, passed=True, source="S"):
    """A fake finished unit: one data file plus a hash-checked marker, as unit.py writes them."""
    C.publish(root / f"run__{key}__{item}.bin", b"data " + key.encode() + item.encode())
    rec = {"identity": "i", "pass": passed, "inputs": {"source_digest": source},
           "files": {f"run__{key}__{item}.bin": C.digest(root / f"run__{key}__{item}.bin")}}
    C.publish(root / "units" / f"nf4_dequant_float64_{key}_{item}.json", C.json_bytes(rec))


def _fake_runner(root, outcomes, calls):
    """outcomes: {(key, item): 'ok'|'gate'|'crash'|'rss'|'slow'}; default 'ok'."""
    Result = _load_runner("mac_queue").UnitResult

    def run_unit(key, item):
        calls.append((key, item))
        what = outcomes.get((key, item), "ok")
        if what in ("ok", "gate"):
            _bank(root, key, item, passed=what == "ok")
        return Result(rc=0 if what == "ok" else 2 if what == "gate" else 1,
                      wall=999.0 if what == "slow" else 10.0,
                      peak_rss=17e9 if what == "rss" else 8e9)
    return run_unit


def _run(root, keys, items, outcomes=None, free=lambda: 200e9, source="S"):
    q = _load_runner("mac_queue")
    calls = []
    status = q.run_queue(keys, items, root=root, run_unit=_fake_runner(root, outcomes or {}, calls),
                         free_bytes=free, source_digest=source, pid=4242)
    return status, calls


def test_local_queue_plan_is_base_first_and_covers_every_model_and_item():
    q = _load_runner("mac_queue")
    reg = json.loads((C.PACKAGE / "models.json").read_text())
    items = json.loads((C.PACKAGE / "items.json").read_text())["items"]
    keys, got = q.plan(False, reg, items)
    assert keys[0] == "base" and len(keys) == 43 and len(keys) * len(got) == 989


def test_local_resume_skips_hash_checked_units_and_never_calls_the_hub(tmp_path, monkeypatch):
    import huggingface_hub as hub
    monkeypatch.setattr(hub, "HfApi", lambda *a, **k: pytest.fail("Hub call in local mode"))
    monkeypatch.delenv("HF_TOKEN", raising=False)
    _bank(tmp_path, "base", "q1")
    status, calls = _run(tmp_path, ["base", "ARG"], [{"item_id": "q1"}, {"item_id": "q2"}])
    assert calls == [("base", "q2"), ("ARG", "q1"), ("ARG", "q2")]
    assert status["done"] == 4 and status["state"] == "finished" and status["failed"] == []


def test_local_resume_refuses_a_tampered_marker_file_or_a_different_source(tmp_path):
    _bank(tmp_path, "base", "q1")
    (tmp_path / "run__base__q1.bin").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="digest"):
        _run(tmp_path, ["base"], [{"item_id": "q1"}])
    other = tmp_path / "b"
    _bank(other, "base", "q1", source="OLD")
    with pytest.raises(ValueError, match="source"):
        _run(other, ["base"], [{"item_id": "q1"}], source="NEW")


def test_failed_gate_is_recorded_and_the_queue_continues(tmp_path):
    items = [{"item_id": f"q{i}"} for i in range(4)]
    status, calls = _run(tmp_path, ["base"], items, {("base", "q1"): "gate"})
    assert len(calls) == 4 and status["state"] == "finished"
    assert status["failed"] == ["base/q1"] and status["done"] == 3
    # a banked failing unit stays failed on resume, is reported, and is not rerun
    status, calls = _run(tmp_path, ["base"], items)
    assert calls == [] and status["failed"] == ["base/q1"] and status["done"] == 3


def test_three_consecutive_failures_abort_but_a_success_resets_the_count(tmp_path):
    items = [{"item_id": f"q{i}"} for i in range(8)]
    bad = {("base", f"q{i}"): "crash" for i in (0, 1, 3, 4)}
    status, _ = _run(tmp_path, ["base"], items, bad)
    assert status["state"] == "finished" and len(status["failed"]) == 4
    bad = {("ARG", f"q{i}"): "gate" for i in (0, 1, 2)}
    status, calls = _run(tmp_path, ["ARG"], items, bad)
    assert status["state"] == "aborted" and "3 consecutive" in status["abort_reason"]
    assert len(calls) == 3 and status["failed"] == ["ARG/q0", "ARG/q1", "ARG/q2"]


@pytest.mark.parametrize("what, reason", [("rss", "RSS"), ("slow", "wall")])
def test_rss_over_16gb_and_wall_over_4x_b0_abort(tmp_path, what, reason):
    items = [{"item_id": f"q{i}"} for i in range(3)]
    status, calls = _run(tmp_path, ["ARG"], items, {("ARG", "q1"): what})
    assert status["state"] == "aborted" and reason in status["abort_reason"]
    assert calls == [("ARG", "q0"), ("ARG", "q1")]


def test_wall_limit_is_4x_the_b0_time_of_the_unit_kind():
    q = _load_runner("mac_queue")
    assert q.wall_limit("base") == pytest.approx(4 * 32.5) and q.wall_limit("ARG") == pytest.approx(4 * 65.3)


def test_low_disk_aborts_before_starting_a_unit(tmp_path):
    status, calls = _run(tmp_path, ["base"], [{"item_id": "q0"}], free=lambda: 39e9)
    assert status["state"] == "aborted" and "disk" in status["abort_reason"] and calls == []


def test_status_file_is_complete_after_every_unit_and_never_partial(tmp_path):
    q = _load_runner("mac_queue")
    seen = []
    base = _fake_runner(tmp_path, {}, [])

    def run_unit(key, item):
        p = tmp_path / "RUN_STATUS.json"
        seen.append(json.loads(p.read_text()) if p.exists() else None)   # always parseable mid-run
        return base(key, item)
    items = [{"item_id": f"q{i}"} for i in range(3)]
    status = q.run_queue(["base"], items, root=tmp_path, run_unit=run_unit, free_bytes=lambda: 200e9,
                         source_digest="S", pid=4242, total=989)
    assert [s["done"] if s else None for s in seen[1:]] == [1, 2] and seen[1]["state"] == "running"
    on_disk = json.loads((tmp_path / "RUN_STATUS.json").read_text())
    assert on_disk == status
    assert {"total", "done", "failed", "last_unit", "last_unit_at", "pid", "state", "abort_reason"} <= set(on_disk)
    assert on_disk["total"] == 989 and on_disk["pid"] == 4242 and on_disk["last_unit"] == "base/q2"
    assert on_disk["abort_reason"] is None and isinstance(on_disk["last_unit_at"], (int, float))
    assert not list(tmp_path.glob(".RUN_STATUS*"))


def test_a_second_queue_on_the_same_output_is_refused(tmp_path):
    q = _load_runner("mac_queue")
    with q.single_queue(tmp_path):
        with pytest.raises(RuntimeError, match="already running"):
            with q.single_queue(tmp_path):
                pass
    with q.single_queue(tmp_path):
        pass


def test_sigterm_during_a_unit_records_an_aborted_status(tmp_path):
    q = _load_runner("mac_queue")

    def run_unit(key, item):
        raise q.Terminated()
    status = q.run_queue(["base"], [{"item_id": "q0"}], root=tmp_path, run_unit=run_unit,
                         free_bytes=lambda: 200e9, source_digest="S", pid=1)
    assert status["state"] == "aborted" and "SIGTERM" in status["abort_reason"]
    assert json.loads((tmp_path / "RUN_STATUS.json").read_text()) == status
