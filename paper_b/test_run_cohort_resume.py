"""Resume must read the durable Hub store, not only the lagging Drive mount."""
import run_cohort as RC


class FakeCfg:
    @staticmethod
    def hub_adapter_path(u):
        return f"bank2/RUN/profiles/{u}"


def _files(units, names=("adapter_model.safetensors", "adapter_config.json", "run_record.json")):
    return [f"bank2/RUN/profiles/{u}/{n}" for u in units for n in names]


def test_complete_units_need_all_three_files():
    files = _files(["P_A"]) + _files(["P_B"], names=("adapter_model.safetensors",))
    got = RC.hub_complete_units(["P_A", "P_B", "P_C"], FakeCfg, lambda: files)
    assert got == {"P_A"}                      # partial upload and absent unit do not count


def test_other_paths_never_count():
    files = ["adapters/ARG/adapter_model.safetensors", "adapters/ARG/adapter_config.json",
             "adapters/ARG/run_record.json"]
    assert RC.hub_complete_units(["ARG"], FakeCfg, lambda: files) == set()


def test_listing_failure_is_loud_not_silent():
    import pytest
    def boom():
        raise OSError("hub down")
    with pytest.raises(RuntimeError, match="refusing to retrain"):
        RC.hub_complete_units(["P_A"], FakeCfg, boom)
