"""Shared fixtures for paper_b tests."""
import importlib
import sys

import pytest


@pytest.fixture()
def pb_config_guard(monkeypatch):
    """Tests that reload `config` under bank-2 settings must not leak them into later tests.

    On teardown the SCA2_PB_* variables set through monkeypatch are undone first, then every module that
    reads them at import time is reloaded, which restores the frozen cohort-1 constants.
    """
    yield
    monkeypatch.undo()
    for name in ("config", "run_cohort", "score_runtime", "train_country"):
        if name in sys.modules:
            importlib.reload(sys.modules[name])
