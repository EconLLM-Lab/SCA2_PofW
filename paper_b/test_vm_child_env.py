"""The VM child environment must be built per call, not snapshotted at import.

Regression test for 2026-10-16: an HF token set AFTER vm_fact_common was first imported never reached
the children, so the gate refused with "HF_TOKEN missing" on a VM whose kernel had the token.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "colab"))
import vm_fact_common as V  # noqa: E402


def test_a_var_set_after_import_reaches_the_child(monkeypatch):
    monkeypatch.setenv("SCA2_PB_TEST_LATE", "late-value")
    assert V.child_env()["SCA2_PB_TEST_LATE"] == "late-value"


def test_bank2_defaults_are_present_and_overridable():
    env = V.child_env()
    assert env["SCA2_PB_PROTOCOL"] == "bank2" and env["SCA2_PB_UNITS"] == "profiles"
    assert V.child_env(SCA2_PB_ADAPTER_REVISION="rev")["SCA2_PB_ADAPTER_REVISION"] == "rev"
