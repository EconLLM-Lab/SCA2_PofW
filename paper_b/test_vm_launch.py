"""Detached launcher: survives its caller, records each step's return code, refuses a double launch."""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "colab"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import vm_fact_common as V  # noqa: E402


def _wait(path, timeout=20):
    t0 = time.time()
    while not path.exists():
        assert time.time() - t0 < timeout, f"timed out waiting for {path}"
        time.sleep(0.1)


@pytest.fixture()
def vm(tmp_path, monkeypatch):
    monkeypatch.setattr(V, "ROOT", str(tmp_path / "pb"))
    monkeypatch.setattr(V, "REPO", str(tmp_path))
    return tmp_path / "pb" / "logs"


def test_steps_run_in_order_and_a_failure_does_not_block_the_next(vm):
    V.launch_detached([
        ("s1", ["-c", "import sys; print('one'); sys.exit(3)"], {}),
        ("s2", ["-c", "import os; print('two', os.environ['SCA2_PB_REPLICATE'])"], {"SCA2_PB_REPLICATE": "r1"}),
    ])
    _wait(vm / "s2.rc")
    assert (vm / "s1.rc").read_text().strip() == "3"          # the failure is recorded, not hidden
    assert (vm / "s2.rc").read_text().strip() == "0"
    assert "one" in (vm / "s1.log").read_text() and "two r1" in (vm / "s2.log").read_text()


def test_second_launch_is_refused_while_running(vm):
    V.launch_detached([("slow", ["-c", "import time; time.sleep(3)"], {})])
    with pytest.raises(SystemExit, match="already running"):
        V.launch_detached([("slow", ["-c", "print(1)"], {})])
    _wait(vm / "slow.rc")
    V.launch_detached([("slow", ["-c", "print(2)"], {})])      # finished, so a relaunch is allowed
    _wait(vm / "slow.rc")
