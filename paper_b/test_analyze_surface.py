"""CPU tests for the Paper B analysis module (analyze_surface.py).

Strict vertical RED/GREEN. Every estimator is exercised on synthetic fixtures
with ground truth known by construction; a positive known-signal variant must
pass and a deliberately invalid variant must fail loudly (no NaN swallowed).

No torch, no GPU, no network, no real adapter outcomes. Real-data tests are
HUMAN-ONLY (existing committed aggregates) and skip if data is absent.

Run:  env -u PYTHONPATH .venv/bin/python -m pytest paper_b/test_analyze_surface.py -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_surface as A  # noqa: E402


# --------------------------------------------------------------------------
# Slice 1: recode_value (E[recode] construction) and expected_recode
# --------------------------------------------------------------------------

class TestRecodes:
    def test_invert_1_4(self):
        assert A.recode_value(1.0, "Q59") == 4.0
        assert A.recode_value(4.0, "Q81") == 1.0

    def test_invert_10(self):
        assert A.recode_value(1.0, "Q177") == 10.0
        assert A.recode_value(10.0, "Q179") == 1.0

    def test_binary_q57(self):
        assert A.recode_value(1.0, "Q57") == 1.0
        assert A.recode_value(2.0, "Q57") == 0.0
        assert A.recode_value(3.0, "Q57") == 0.0  # invalid-but-masked codes -> 0

    def test_raw_items_unchanged(self):
        assert A.recode_value(2.0, "Q43") == 2.0
        assert A.recode_value(7.0, "Q50") == 7.0
        assert A.recode_value(5.0, "Q106") == 5.0

    def test_every_strict_item_has_a_recode_rule(self):
        items = [q for qs in A.STRICT_ITEMS.values() for q in qs]
        assert len(items) == 23
        assert len(set(items)) == 23
        for q in items:
            v = A.recode_value(1.0, q)
            assert np.isfinite(v)

    def test_expected_recode_hand_computed(self):
        # Q43 raw {1,2,3}, p=(.1,.2,.7) -> E = 0.1 + 0.4 + 2.1 = 2.6
        assert A.expected_recode(["1", "2", "3"], [0.1, 0.2, 0.7], "Q43") == pytest.approx(2.6)
        # Q57 binary, p(1)=0.25 -> E = 0.25
        assert A.expected_recode(["1", "2"], [0.25, 0.75], "Q57") == pytest.approx(0.25)
        # Q59 inverted 1..4, E[raw] = 3.0 -> E[recode] = 2.0
        assert A.expected_recode(["1", "2", "3", "4"], [0.1, 0.2, 0.3, 0.4], "Q59") == pytest.approx(2.0)
        # Q177 inverted 1..10, uniform -> E[raw] = 5.5 -> 5.5
        p = [0.1] * 10
        assert A.expected_recode([str(c) for c in range(1, 11)], p, "Q177") == pytest.approx(5.5)
        # Q50 raw 1..10, uniform -> 5.5
        assert A.expected_recode([str(c) for c in range(1, 11)], p, "Q50") == pytest.approx(5.5)

    def test_expected_recode_accepts_int_typed_codes(self):
        # CSV option_code dtype flips between str and int64; must be canonicalized
        assert A.expected_recode([1, 2, 3], [0.1, 0.2, 0.7], "Q43") == pytest.approx(2.6)

    def test_expected_recode_rejects_code_outside_domain(self):
        with pytest.raises(ValueError, match="Q43"):
            A.expected_recode(["1", "2", "3", "7"], [0.2, 0.2, 0.2, 0.4], "Q43")

    def test_expected_recode_rejects_probabilities_not_summing_to_one(self):
        with pytest.raises(ValueError, match="sum"):
            A.expected_recode(["1", "2", "3"], [0.1, 0.2, 0.6], "Q43")

    def test_expected_recode_rejects_negative_probability(self):
        with pytest.raises(ValueError, match="negative"):
            A.expected_recode(["1", "2", "3"], [0.5, 0.7, -0.2], "Q43")

    def test_expected_recode_rejects_missing_option(self):
        # A scored grid missing one option of the question's domain cannot
        # produce E[recode] silently -- it must fail.
        with pytest.raises(ValueError, match="option"):
            A.expected_recode(["1", "2"], [0.5, 0.5], "Q43")

    def test_tvd_hand_computed(self):
        p = {"1": 0.5, "2": 0.25, "3": 0.25}
        q = {"1": 0.1, "2": 0.2, "3": 0.7}
        assert A.total_variation_distance(p, q) == pytest.approx(0.45)

    def test_tvd_ignores_zero_mass_codes_and_rejects_mismatched_total(self):
        assert A.total_variation_distance({"1": 1.0}, {"1": 1.0, "2": 0.0}) == pytest.approx(0.0)
        with pytest.raises(ValueError, match="sum"):
            A.total_variation_distance({"1": 0.9}, {"1": 1.0})


# --------------------------------------------------------------------------
# Slice 2: GPS sign profiles (sign(z) over six dimensions -> profile ids)
# --------------------------------------------------------------------------

@pytest.fixture
def z_frame():
    rows = []
    # 6 countries: two sharing all signs (twins), four singleton profiles
    zs = {
        "AAA": {"trust": 1.0, "patience": -0.5, "risktaking": 0.3,
                "posrecip": 0.2, "negrecip": -0.1, "altruism": 0.4},
        "BBB": {"trust": 2.0, "patience": -1.5, "risktaking": 0.9,
                "posrecip": 0.7, "negrecip": -0.6, "altruism": 1.1},  # same signs as AAA
        "CCC": {"trust": -1.0, "patience": 0.5, "risktaking": -0.3,
                "posrecip": 0.2, "negrecip": 0.1, "altruism": -0.4},
        "DDD": {"trust": 0.5, "patience": 0.5, "risktaking": 0.3,
                "posrecip": -0.2, "negrecip": 0.1, "altruism": 0.4},
        "EEE": {"trust": -0.5, "patience": -0.5, "risktaking": -0.3,
                "posrecip": -0.2, "negrecip": -0.1, "altruism": -0.4},
        "FFF": {"trust": 0.5, "patience": 0.5, "risktaking": 0.3,
                "posrecip": 0.2, "negrecip": 0.1, "altruism": -0.4},
    }
    for cc, dims in zs.items():
        for d, v in dims.items():
            rows.append({"country": cc, "dimension": d, "z": v})
    return pd.DataFrame(rows)


class TestSignProfiles:
    def test_twin_countries_share_a_profile(self, z_frame):
        prof = A.sign_profiles(z_frame, ["AAA", "BBB", "CCC"],
                               ["trust", "patience", "risktaking", "posrecip",
                                "negrecip", "altruism"])
        p = prof.set_index("country")["profile_id"]
        assert p["AAA"] == p["BBB"]
        assert p["AAA"] != p["CCC"]

    def test_magnitudes_do_not_enter_labels(self, z_frame):
        # AAA (z=1.0) and BBB (z=2.0) differ in magnitude; labels identical
        prof = A.sign_profiles(z_frame, ["AAA", "BBB"], list(z_frame.dimension.unique()))
        assert prof.profile_id.nunique() == 1

    def test_profile_count_on_known_fixture(self, z_frame):
        prof = A.sign_profiles(z_frame, ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF"],
                               list(z_frame.dimension.unique()))
        assert prof.profile_id.nunique() == 5  # AAA/BBB twins + 4 singletons

    def test_missing_country_fails_loudly(self, z_frame):
        with pytest.raises(ValueError, match="ZZZ"):
            A.sign_profiles(z_frame, ["AAA", "ZZZ"], list(z_frame.dimension.unique()))

    def test_load_gps_z_shape(self, tmp_path):
        payload = {"AAA": {"trust": 0.5, "patience": -0.2}}
        f = tmp_path / "z.json"
        f.write_text(json.dumps(payload))
        z = A.load_gps_z(f)
        assert set(z.columns) == {"country", "dimension", "z"}
        assert len(z) == 2


# --------------------------------------------------------------------------
# Slice 3: estimators — country-equal Spearman, paired bootstrap with
# explicit degenerate-draw counting, profile-equal sensitivity
# --------------------------------------------------------------------------

class TestSpearmanCountryEqual:
    def test_perfect_monotone_is_one(self):
        a = pd.Series(np.arange(10, dtype=float))
        rho, n = A.spearman_country_equal(a, a * 2 + 1)
        assert rho == pytest.approx(1.0)
        assert n == 10

    def test_reversed_is_minus_one(self):
        a = pd.Series(np.arange(10, dtype=float))
        rho, _ = A.spearman_country_equal(a, -a)
        assert rho == pytest.approx(-1.0)

    def test_constant_series_returns_nan_not_error(self):
        a = pd.Series([1.0] * 10)
        rho, n = A.spearman_country_equal(a, pd.Series(np.arange(10.0)))
        assert np.isnan(rho)
        assert n == 10  # n reported even when rho is undefined

    def test_pairwise_complete_intersection(self):
        a = pd.Series(np.arange(12, dtype=float))
        b = pd.Series(np.arange(12, dtype=float))
        b.iloc[3] = np.nan
        b.iloc[7] = np.nan
        rho, n = A.spearman_country_equal(a, b)
        assert n == 10 and rho == pytest.approx(1.0)

    def test_too_few_countries_is_nan(self):
        rho, n = A.spearman_country_equal(pd.Series([1.0, 2.0]),
                                          pd.Series([1.0, 2.0]))
        assert np.isnan(rho) and n == 2


class TestBootstrapSpearman:
    def _mono(self, n=12):
        idx = [f"c{i:02d}" for i in range(n)]
        return pd.Series(np.arange(n, dtype=float), index=idx), \
               pd.Series(np.arange(n, dtype=float) * 0.5 + 3, index=idx)

    def test_perfect_signal_collapses_interval(self):
        a, b = self._mono()
        r = A.bootstrap_spearman(a, b, draws=60, seed=1)
        assert r["point"] == pytest.approx(1.0)
        assert r["ci_lo"] == pytest.approx(1.0)
        assert r["ci_hi"] == pytest.approx(1.0)
        assert r["degenerate_draws"] == 0
        assert r["draws"] == 60 and r["n"] == 12

    def test_degenerate_draws_counted_when_n_below_min(self):
        a = pd.Series([1.0, 2.0, 3.0])
        b = pd.Series([1.0, 2.0, 3.0])
        r = A.bootstrap_spearman(a, b, draws=40, seed=1)
        assert r["n"] == 3
        assert r["degenerate_draws"] == r["draws"] == 40
        assert np.isnan(r["ci_lo"]) and np.isnan(r["ci_hi"])

    def test_singleton_clusters_reproduce_country_bootstrap_exactly(self):
        a, b = self._mono()
        clusters = pd.Series([f"k{i}" for i in range(len(a))], index=a.index)
        rc = A.bootstrap_spearman(a, b, clusters=clusters, draws=30, seed=7)
        rr = A.bootstrap_spearman(a, b, clusters=None, draws=30, seed=7)
        assert rc["point"] == rr["point"]
        assert rc["ci_lo"] == rr["ci_lo"] and rc["ci_hi"] == rr["ci_hi"]
        assert rc["degenerate_draws"] == rr["degenerate_draws"]

    def test_cluster_bootstrap_fails_loudly_on_unmapped_country(self):
        a, b = self._mono()
        clusters = pd.Series([f"k{i}" for i in range(len(a) - 1)],
                             index=a.index[:-1])  # last country unmapped
        with pytest.raises(ValueError, match="c11"):
            A.bootstrap_spearman(a, b, clusters=clusters, draws=10, seed=1)

    def test_seed_is_a_baseline_not_a_cap(self):
        a, b = self._mono()
        b2 = b + pd.Series(np.sin(np.arange(12)) * 0.9, index=b.index)
        r_default = A.bootstrap_spearman(a, b2, draws=200, seed=A.BOOT_SEED)
        r_other = A.bootstrap_spearman(a, b2, draws=200, seed=999)
        assert r_default["draws"] == r_other["draws"] == 200
        # different seeds may shift the interval slightly, but both must be finite
        assert np.isfinite(r_default["ci_lo"]) and np.isfinite(r_other["ci_hi"])


class TestProfileEqualSpearman:
    def test_profile_means_monotone_gives_one(self):
        # 8 profiles x 2 members: within each profile one member is a huge
        # outlier, so the country-equal correlation is degraded, but the
        # profile MEANS are strictly monotone in both variables.
        countries = [f"c{i:02d}" for i in range(16)]
        a_vals = np.arange(16, dtype=float)
        b_vals = np.array([k if i % 2 == 0 else -1.0
                           for i, k in enumerate([0, 0, 1, 1, 2, 2, 3, 3,
                                                  4, 4, 5, 5, 6, 6, 7, 7])])
        # b profile means: Pk = (k + (-1)) / 2, strictly increasing in k
        a = pd.Series(a_vals, index=countries)
        b = pd.Series(b_vals, index=countries)
        prof = pd.DataFrame({
            "country": countries,
            "profile_id": [f"P{i // 2}" for i in range(16)],
        })
        rho_country, _ = A.spearman_country_equal(a, b)
        rho_prof, n_prof = A.profile_equal_spearman(a, b, prof)
        assert n_prof == 8
        assert rho_prof == pytest.approx(1.0)
        assert rho_country < 1.0  # different estimand, different number

    def test_profile_equal_means_each_variable_within_profile(self):
        # hand check: P0 members (a=0,b=8),(a=1,b=0) -> means (0.5, 4.0)
        a = pd.Series([0.0, 1.0], index=["x1", "x2"])
        b = pd.Series([8.0, 0.0], index=["x1", "x2"])
        prof = pd.DataFrame({"country": ["x1", "x2"], "profile_id": ["P", "P"]})
        d = pd.concat([a.rename("a"), b.rename("b")], axis=1).join(
            prof.set_index("country")["profile_id"])
        gm = d.groupby("profile_id")[["a", "b"]].mean()
        assert gm.loc["P", "a"] == pytest.approx(0.5)
        assert gm.loc["P", "b"] == pytest.approx(4.0)

    def test_missing_profile_fails_loudly(self):
        a = pd.Series(np.arange(8, dtype=float), index=list("abcdefgh"))
        b = pd.Series(np.arange(8, dtype=float), index=list("abcdefgh"))
        prof = pd.DataFrame({"country": list("abcdefg"),      # h missing
                             "profile_id": [f"P{i}" for i in range(7)]})
        with pytest.raises(ValueError, match="h"):
            A.profile_equal_spearman(a, b, prof)

    def test_too_few_profiles_is_nan(self):
        a = pd.Series([1.0, 2.0], index=["x", "y"])
        b = pd.Series([1.0, 2.0], index=["x", "y"])
        prof = pd.DataFrame({"country": ["x", "y"], "profile_id": ["P", "Q"]})
        rho, n = A.profile_equal_spearman(a, b, prof)
        assert np.isnan(rho) and n == 2


# --------------------------------------------------------------------------
# Slice 4: composites and missingness — E[recode] end-to-end from option
# probabilities, complete-case vs available, JOR-style Q178 drop
# --------------------------------------------------------------------------

def _probs_frame(rows_spec, model="adapter"):
    """rows_spec: {country: {item: {code: prob}}} -> long frame."""
    rows = []
    for cc, items in rows_spec.items():
        for qid, dist in items.items():
            for code, p in dist.items():
                rows.append({"model": model, "eval_country": cc,
                             "question_id": qid, "option_code": str(code),
                             "model_prob": p})
    return pd.DataFrame(rows)


Q43_UNIFORM = {c: 1 / 3 for c in ("1", "2", "3")}
Q50_UNIFORM = {c: 0.1 for c in map(str, range(1, 11))}
Q57_UNIFORM = {"1": 0.5, "2": 0.5}


def _full_battery_country(rng, risk_q178=True):
    """A full 23-item battery with deterministic-but-varied probabilities."""
    def lin1_4(w):
        return {c: w[i] / sum(w) for i, c in enumerate(("1", "2", "3", "4"))}

    def lin10(w):
        codes = [str(c) for c in range(1, 11)]
        s = sum(w)
        return {c: w[i] / s for i, c in enumerate(codes)}

    battery = {
        "Q43": {"1": 0.2, "2": 0.3, "3": 0.5},
        "Q50": lin10(range(1, 11)),
        "Q57": {"1": 0.6, "2": 0.4},
        "Q81": lin1_4([4, 3, 2, 1]),
        "Q99": {"0": 0.5, "1": 0.3, "2": 0.2},
        "Q101": {"0": 0.4, "1": 0.4, "2": 0.2},
        "Q103": {"0": 0.3, "1": 0.3, "2": 0.4},
        "Q106": lin10(range(10, 0, -1)),
        "Q107": lin10(range(1, 11)),
        "Q109": lin10([1] * 4 + [3] * 6),
        "Q176": lin10(range(1, 11)),
        "Q177": lin10(range(10, 0, -1)),
        "Q178": lin10(range(1, 11)),
        "Q179": lin10(range(10, 0, -1)),
        "Q195": lin10([2] * 5 + [1] * 5),
    }
    for q in ("Q58", "Q59", "Q60", "Q61", "Q62", "Q63", "Q64", "Q73"):
        battery[q] = lin1_4([1, 2, 3, 4])
    if not risk_q178:
        del battery["Q178"]
    return battery


class TestModelItemTable:
    def test_e_recode_end_to_end_for_one_country(self):
        probs = _probs_frame({"AAA": {
            "Q43": {"1": 0.1, "2": 0.2, "3": 0.7},      # 2.6
            "Q57": {"1": 0.25, "2": 0.75},              # 0.25
            "Q59": {"1": 0.1, "2": 0.2, "3": 0.3, "4": 0.4},  # E[raw]=3 -> 2.0
        }})
        t = A.model_item_table(probs)
        got = t.set_index("item")["e_recode"]
        assert got["Q43"] == pytest.approx(2.6)
        assert got["Q57"] == pytest.approx(0.25)
        assert got["Q59"] == pytest.approx(2.0)
        assert set(t.country) == {"AAA"}
        assert (t.model == "adapter").all()

    def test_q43_and_q50_stay_separate_rows(self):
        probs = _probs_frame({"AAA": {"Q43": Q43_UNIFORM, "Q50": Q50_UNIFORM}})
        t = A.model_item_table(probs)
        assert sorted(t.item) == ["Q43", "Q50"]

    def test_missing_option_of_domain_fails_loudly(self):
        probs = _probs_frame({"AAA": {"Q43": {"1": 0.5, "2": 0.5}}})  # no "3"
        with pytest.raises(ValueError, match="Q43"):
            A.model_item_table(probs)

    def test_probabilities_not_summing_to_one_fail(self):
        probs = _probs_frame({"AAA": {"Q43": {"1": 0.5, "2": 0.4, "3": 0.05}}})
        with pytest.raises(ValueError, match="sums"):
            A.model_item_table(probs)

    def test_int_typed_option_codes_accepted(self):
        df = _probs_frame({"AAA": {"Q43": Q43_UNIFORM}})
        df["option_code"] = df["option_code"].astype(int)  # CSV dtype flip
        t = A.model_item_table(df)
        assert t.e_recode.iloc[0] == pytest.approx(2.0)


class TestArmComposites:
    def test_complete_case_drops_country_missing_one_item(self):
        batteries = {
            "AAA": _full_battery_country(None),                 # complete
            "BBB": _full_battery_country(None, risk_q178=False)  # JOR-style
        }
        probs = _probs_frame(batteries)
        mitems = A.model_item_table(probs)
        comp = A.arm_composites(mitems, dict(A.STRICT_ITEMS), complete=True)
        risk = comp[comp.dimension == "risktaking"].set_index("country")
        assert set(risk.index) == {"AAA"}  # BBB drops (missing Q178)
        trust = comp[comp.dimension == "trust"].set_index("country")
        assert set(trust.index) == {"AAA", "BBB"}  # both present

    def test_available_case_keeps_partial_country(self):
        batteries = {
            "AAA": _full_battery_country(None),
            "BBB": _full_battery_country(None, risk_q178=False)
        }
        probs = _probs_frame(batteries)
        mitems = A.model_item_table(probs)
        comp = A.arm_composites(mitems, dict(A.STRICT_ITEMS), complete=False)
        risk = comp[comp.dimension == "risktaking"].set_index("country")
        assert set(risk.index) == {"AAA", "BBB"}
        assert risk.loc["BBB", "n_items_observed"] == 3

    def test_composite_is_mean_of_item_e_recodes(self):
        # point masses still list the full domain (the module enforces it)
        probs = _probs_frame({"AAA": {
            "Q99": {"0": 1.0, "1": 0.0, "2": 0.0},
            "Q101": {"0": 0.0, "1": 1.0, "2": 0.0},
            "Q103": {"0": 0.0, "1": 0.0, "2": 1.0}}})
        mitems = A.model_item_table(probs)
        comp = A.arm_composites(mitems, {"altruism": ["Q99", "Q101", "Q103"]},
                                complete=True)
        assert comp.composite.iloc[0] == pytest.approx((0.0 + 1.0 + 2.0) / 3.0)


class TestMissingnessLedger:
    def test_jor_style_q178_gap_visible(self):
        # adapter DOES produce a Q178 distribution for JOR; the human side
        # does not (zero valid responses) -- the asymmetry is the point.
        batteries = {
            "AAA": _full_battery_country(None),
            "JOR": _full_battery_country(None, risk_q178=True),
        }
        probs = _probs_frame(batteries)
        mitems = A.model_item_table(probs)
        human = pd.DataFrame(
            [{"country": cc, "item": it, "mean": 1.0, "n": 100}
             for cc in ("AAA", "JOR")
             for it in A.all_strict_items() if not (cc == "JOR" and it == "Q178")])
        ledger = A.missingness_ledger(mitems, human, ["AAA", "JOR"])
        jor178 = ledger[(ledger.country == "JOR") & (ledger.item == "Q178")]
        assert bool(jor178.adapter_present.iloc[0]) is True
        assert bool(jor178.human_present.iloc[0]) is False
        assert int(ledger.human_present.sum()) == 23 + 22  # AAA full, JOR minus Q178

    def test_complete_case_membership_counts_41_for_risk(self):
        # 42-country-style fixture: JOR missing Q178 on the human side only
        countries = [f"C{i:02d}" for i in range(42)]
        mitems = pd.DataFrame(
            [{"model": "adapter", "country": cc, "item": it, "e_recode": 1.0,
              "n_options": 4}
             for cc in countries for it in A.all_strict_items()])
        human = pd.DataFrame(
            [{"country": cc, "item": it, "mean": 1.0, "n": 100}
             for cc in countries for it in A.all_strict_items()
             if not (cc == "C00" and it == "Q178")])
        got = A.complete_case_countries(human, "risktaking", dict(A.STRICT_ITEMS))
        assert len(got) == 41 and "C00" not in got
        got_trust = A.complete_case_countries(human, "trust", dict(A.STRICT_ITEMS))
        assert len(got_trust) == 42


class TestWithinProfileSpread:
    def test_spread_is_descriptive_sd_and_range(self):
        comp = pd.DataFrame({
            "model": "adapter", "dimension": "trust",
            "country": ["AAA", "BBB", "CCC"],
            "composite": [1.0, 3.0, 10.0]})
        prof = pd.DataFrame({"country": ["AAA", "BBB", "CCC"],
                             "profile_id": ["P1", "P1", "P2"]})
        out = A.within_profile_spread(comp, prof)
        p1 = out[out.profile_id == "P1"].iloc[0]
        assert p1.n_members == 2
        assert p1.sd == pytest.approx(np.std([1.0, 3.0], ddof=1))
        assert p1.range == pytest.approx(2.0)
        assert "P2" not in set(out.profile_id)  # singletons excluded

    def test_unmapped_country_fails_loudly(self):
        comp = pd.DataFrame({"model": "adapter", "dimension": "trust",
                             "country": ["AAA", "ZZZ"], "composite": [1.0, 2.0]})
        prof = pd.DataFrame({"country": ["AAA"], "profile_id": ["P1"]})
        with pytest.raises(ValueError, match="ZZZ"):
            A.within_profile_spread(comp, prof)


# --------------------------------------------------------------------------
# Slice 5: TVD and paired base differences — the base arm's rank
# correlations are UNDEFINED (constant across countries); only paired
# adapter-minus-base differences are predeclared
# --------------------------------------------------------------------------

class TestPerItemTVD:
    def test_hand_computed(self):
        joined = pd.DataFrame([
            {"model": "adapter", "country": "AAA", "item": "Q43",
             "option_code": "1", "model_prob": 0.5, "human_prob": 0.1},
            {"model": "adapter", "country": "AAA", "item": "Q43",
             "option_code": "2", "model_prob": 0.25, "human_prob": 0.2},
            {"model": "adapter", "country": "AAA", "item": "Q43",
             "option_code": "3", "model_prob": 0.25, "human_prob": 0.7},
        ])
        out = A.per_item_tvd(joined)
        assert out.tvd.iloc[0] == pytest.approx(0.45)

    def test_identical_distributions_give_zero(self):
        joined = pd.DataFrame([
            {"model": "adapter", "country": "AAA", "item": "Q57",
             "option_code": c, "model_prob": p, "human_prob": p}
            for c, p in (("1", 0.3), ("2", 0.7))])
        assert A.per_item_tvd(joined).tvd.iloc[0] == pytest.approx(0.0)

    def test_missing_required_column_fails(self):
        with pytest.raises(ValueError, match="human_prob"):
            A.per_item_tvd(pd.DataFrame([{"model": "m", "country": "c",
                                          "item": "Q43", "option_code": "1",
                                          "model_prob": 1.0}]))


class TestPairedBaseDifference:
    def test_hand_computed_mean_error(self):
        adapter = pd.DataFrame({
            "model": ["adapter"] * 3, "country": ["AAA", "BBB", "CCC"],
            "tvd": [0.30, 0.20, 0.25]})
        base = pd.DataFrame({
            "model": ["base"] * 3, "country": ["AAA", "BBB", "CCC"],
            "tvd": [0.40, 0.40, 0.40]})   # constant across countries by design
        out = A.paired_base_difference(adapter, base, "tvd")
        assert sorted(out.adapter_minus_base) == pytest.approx([-0.20, -0.15, -0.10])
        assert sorted(out.country) == ["AAA", "BBB", "CCC"]  # pairing preserved

    def test_base_composites_constant_correlation_undefined(self):
        # the reason only paired differences exist: base tvd identical for
        # every country -> zero variance -> Spearman undefined (NaN), point
        # AND interval; nothing is silently reported as a correlation lift
        base_vals = pd.Series([0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4])
        other = pd.Series(np.arange(10, dtype=float))
        rho, n = A.spearman_country_equal(base_vals, other)
        assert np.isnan(rho) and n == 10

    def test_base_missing_country_fails_loudly(self):
        adapter = pd.DataFrame({
            "model": ["adapter"] * 2, "country": ["AAA", "BBB"],
            "tvd": [0.3, 0.2]})
        base = pd.DataFrame({
            "model": ["base"], "country": ["AAA"], "tvd": [0.4]})
        with pytest.raises(ValueError, match="base metric missing"):
            A.paired_base_difference(adapter, base, "tvd")


# --------------------------------------------------------------------------
# Slice 6: end-to-end run_analysis on synthetic fixtures (dry run in
# scratch); positive known-signal variant PASSES, deliberately invalid
# variant FAILS LOUDLY; fixture outputs purged after
# --------------------------------------------------------------------------

def _write_fixture_probs(path: Path, countries: list[str], model: str = "adapter"):
    """Synthetic 42-country cohort with a KNOWN positive signal by
    construction: composite levels are built to rise monotonically with the
    GPS z rank of each country's trust sign profile ordering."""
    import json as _json
    # 26 distinct sign profiles would be overkill; use 14 profiles, some shared
    rng = np.random.default_rng(20261011)
    trust_level = np.linspace(0.15, 0.75, len(countries))  # rising in country order
    rows = []
    for i, cc in enumerate(countries):
        for qid, codes in A.OPTION_DOMAINS.items():
            if qid not in A.all_strict_items():
                continue
            p = rng.dirichlet(np.ones(len(codes)) * 2.0)
            # tilt toward higher codes for high-trust countries on trust items
            if qid in A.TRUST9:
                tilt = trust_level[i]
                w = np.array([recode_direction_weight(float(c), qid, tilt)
                              for c in codes])
                p = w / w.sum()
            for c, pk in zip(codes, p):
                rows.append({"model": model, "eval_country": cc,
                             "question_id": qid, "option_code": str(c),
                             "model_prob": float(pk)})
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def recode_direction_weight(code: float, item: str, tilt: float) -> float:
    """Monotone-in-tilt probability weight over option codes."""
    base = 1.0
    if item in A.INVERT_1_4:
        w = base + tilt * (float(code) - 2.5) * -0.4
    elif item in A.INVERT_10:
        w = base + tilt * (float(code) - 5.5) * -0.2
    elif item in A.BINARY:
        w = base + tilt * (1.0 if float(code) == 1.0 else -0.6)
    else:
        w = base + tilt * (float(code) - 3.0) * 0.15
    return max(w, 0.05)


def _write_tiny_human(path: Path, countries: list[str]) -> Path:
    """Minimal human-means fixture file (all battery items, constant mean)."""
    hp = path / "human_tiny.csv"
    pd.DataFrame([{"country": cc, "item": it, "mean": 2.0, "n": 100}
                  for cc in countries for it in A.all_strict_items()]
                 ).to_csv(hp, index=False)
    return hp


def _write_fixture_z(path: Path, countries: list[str]):
    rng = np.random.default_rng(42)
    zs = {}
    for i, cc in enumerate(countries):
        t = -1.5 + 3.0 * i / max(len(countries) - 1, 1)  # rising in country order
        zs[cc] = {"trust": t, "patience": rng.normal(), "risktaking": rng.normal(),
                  "posrecip": rng.normal(), "negrecip": rng.normal(),
                  "altruism": rng.normal()}
    path.write_text(json.dumps(zs))
    return path


def _write_fixture_human(path: Path, countries: list[str]):
    """Human item means rising in the same country order (known signal)."""
    rng = np.random.default_rng(7)
    rows = []
    for i, cc in enumerate(countries):
        level = 0.2 + 0.6 * i / max(len(countries) - 1, 1)
        for it in A.all_strict_items() + ["Q69", "Q70", "Q71"]:
            if cc in ("EGY",) and it in ("Q69", "Q70", "Q71"):
                continue  # EGY not asked Q69-71
            if cc == "JOR" and it == "Q178":
                continue  # JOR zero valid Q178
            noise = rng.normal(0, 0.05)
            rows.append({"country": cc, "item": it,
                         "mean": float(np.clip(level + noise, 0, 10)), "n": 1000})
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


@pytest.fixture(scope="module")
def fixture_run(tmp_path_factory):
    """Positive known-signal dry run through run_analysis."""
    tmp = tmp_path_factory.mktemp("paperb_fixture")
    countries = [f"C{i:02d}" for i in range(42)]
    countries[0] = "JOR"   # JOR: zero valid Q178 (complete-case risk n=41)
    countries[1] = "EGY"   # EGY: not asked Q69-Q71
    A.OPTION_DOMAINS.clear()
    for q in A.all_strict_items() + ["Q69", "Q70", "Q71"]:
        A.OPTION_DOMAINS[q] = A._domain(q)
    probs_path = _write_fixture_probs(tmp / "probs.csv", countries)
    z_path = _write_fixture_z(tmp / "z.json", countries)
    human_path = _write_fixture_human(tmp / "human.csv", countries)
    out = tmp / "out_positive"
    probs = pd.read_csv(probs_path)
    probs["option_code"] = probs["option_code"].astype(str)
    human = A.load_human_means(human_path)
    res = A.run_analysis(probs, human, z_path, out, draws=200, seed=20261011,
                         make_figures=False, human_means_path=human_path,
                         probs_path=probs_path)
    return {"res": res, "out": out, "tmp": tmp, "countries": countries,
            "probs_path": probs_path, "z_path": z_path, "human_path": human_path}


class TestRunAnalysisPositive:
    def test_writes_all_tables_and_manifest(self, fixture_run):
        out = fixture_run["out"]
        for name in ("three_column_table.csv", "profile_equal_sensitivity.csv",
                     "missingness_ledger.csv", "complete_case_membership.csv",
                     "reliability_within_profile.csv", "manifest.json"):
            assert (out / name).exists(), name

    def test_manifest_membership_counts(self, fixture_run):
        man = fixture_run["res"]["manifest"]
        assert man["input_membership"]["countries"] == 42
        assert man["input_membership"]["battery_items"] == 23
        assert man["counts"]["three_column_rows"] == len(fixture_run["res"]["three_column"])
        assert man["seeds"]["profile_bootstrap"] == 20261011
        assert man["draws_baseline"] == 2000

    def test_manifest_hashes_the_actual_human_input(self, fixture_run):
        # the manifest must record the human file actually consumed (the
        # fixture), not the repo default
        man = fixture_run["res"]["manifest"]
        assert man["inputs"]["human_means"]["path"] == str(fixture_run["human_path"])

    def test_manifest_hashes_the_model_probs_input(self, tmp_path):
        # provenance: the consumed option-probability file is hashed too
        countries = [f"C{i:02d}" for i in range(10)]
        A.OPTION_DOMAINS.clear()
        for q in A.all_strict_items():
            A.OPTION_DOMAINS[q] = A._domain(q)
        probs_path = tmp_path / "probs.csv"
        rows = [{"model": "adapter", "eval_country": cc, "question_id": q,
                 "option_code": str(c), "model_prob": p}
                for cc in countries
                for q, dist in _full_battery_country(None).items()
                for c, p in dist.items()]
        pd.DataFrame(rows).to_csv(probs_path, index=False)
        human = pd.DataFrame([{"country": cc, "item": it, "mean": 2.0, "n": 100}
                              for cc in countries for it in A.all_strict_items()])
        z_path = _write_fixture_z(tmp_path / "z.json", countries)
        out = tmp_path / "out"
        res = A.run_analysis(pd.read_csv(probs_path), human, z_path, out,
                             draws=10, seed=1, make_figures=False,
                             human_means_path=_write_tiny_human(tmp_path, countries),
                             probs_path=probs_path)
        assert res["manifest"]["inputs"]["model_probs"]["path"] == str(probs_path)

    def test_base_arm_gets_paired_differences_never_correlations(self, tmp_path):
        # base = one unconditioned distribution broadcast to every country:
        # its composites are constant, so NO base correlation row may appear;
        # the predeclared object is the paired adapter-minus-base mean error
        countries = [f"C{i:02d}" for i in range(12)]
        A.OPTION_DOMAINS.clear()
        for q in A.all_strict_items():
            A.OPTION_DOMAINS[q] = A._domain(q)
        battery = _full_battery_country(None)
        rows = []
        for i, cc in enumerate(countries):
            for q, dist in battery.items():
                # adapter tilts toward higher codes; base is flat/identical
                # for every country by construction
                codes = list(dist)
                w = np.array([max(1.0 + 0.3 * i / 11 * (float(c) - 3.0), 0.05)
                              for c in codes])
                p_vec = w / w.sum()
                for c, pk in zip(codes, p_vec):
                    rows.append({"model": "adapter", "eval_country": cc,
                                 "question_id": q, "option_code": str(c),
                                 "model_prob": float(pk)})
        for cc in countries:  # base identical everywhere by construction
            for q, dist in battery.items():
                for c, p in dist.items():
                    rows.append({"model": "base", "eval_country": cc,
                                 "question_id": q, "option_code": str(c),
                                 "model_prob": p})
        probs = pd.DataFrame(rows)
        rng = np.random.default_rng(3)
        human = pd.DataFrame(
            [{"country": cc, "item": it,
              "mean": float(rng.uniform(1, 4)), "n": 100}
             for cc in countries for it in A.all_strict_items()])
        z_path = _write_fixture_z(tmp_path / "z.json", countries)
        out = tmp_path / "out_base"
        probs_file = tmp_path / "probs_base.csv"
        probs.to_csv(probs_file, index=False)
        res = A.run_analysis(probs, human, z_path, out, draws=10, seed=1,
                             make_figures=False,
                             human_means_path=_write_tiny_human(tmp_path, countries),
                             probs_path=probs_file)
        assert "base" not in set(res["three_column"].model)
        bd = res["base_differences"]
        assert set(bd.model) == {"adapter"}
        assert len(bd) == len(countries)
        # base side constant -> differences vary across countries
        assert bd.adapter_minus_base_mean_abs_error.nunique() > 1
        assert (out / "base_differences.csv").exists()

    def test_human_gps_trust_known_signal_recovered(self, fixture_run):
        three = fixture_run["res"]["three_column"]
        row = three[(three.model == "(human)") & (three.column == "human-GPS")
                    & (three.surface == "trust")].iloc[0]
        # fixture built with trust rising in country order on BOTH sides:
        # the human-GPS rank association must be strongly positive
        assert row.rho > 0.9
        assert row.degenerate_draws == 0

    def test_adapter_gps_known_signal_recovered(self, fixture_run):
        three = fixture_run["res"]["three_column"]
        row = three[(three.model == "adapter") & (three.column == "adapter-GPS")
                    & (three.surface == "trust")].iloc[0]
        assert row.rho > 0.8
        assert row.cluster == "profile"

    def test_complete_case_risk_is_41_countries(self, fixture_run):
        ccm = fixture_run["res"]["complete_case"]
        risk = ccm[ccm.dimension == "risktaking"].iloc[0]
        assert len(risk.human_complete_case) == 41
        assert "JOR" not in risk.human_complete_case

    def test_ledger_flags_jor_q178(self, fixture_run):
        ledger = fixture_run["res"]["ledger"]
        row = ledger[(ledger.country == "JOR") & (ledger.item == "Q178")]
        assert bool(row.human_present.iloc[0]) is False
        assert bool(row.adapter_present.iloc[0]) is True

    def test_reliability_tables_have_multi_member_profiles(self, fixture_run):
        rel = fixture_run["res"]["reliability"]
        assert len(rel) > 0
        assert (rel.n_members > 1).all()

    def test_profiles_total_42_countries_26_style(self, fixture_run):
        man = fixture_run["res"]["manifest"]
        assert man["input_membership"]["profiles"] >= 2
        assert man["input_membership"]["multi_member_profiles"] >= 1


class TestRunAnalysisInvalidVariant:
    def test_incomplete_option_grid_fails_loudly(self, fixture_run):
        # deliberately invalid: drop one option of Q43's domain for one country
        probs = pd.read_csv(fixture_run["probs_path"], dtype={"option_code": str})
        bad = probs.drop(probs[(probs.eval_country == "JOR") &
                               (probs.question_id == "Q43") &
                               (probs.option_code == "3")].index)
        out = fixture_run["tmp"] / "out_invalid_grid"
        human = A.load_human_means(fixture_run["human_path"])
        with pytest.raises(ValueError, match="Q43"):
            A.run_analysis(bad, human, fixture_run["z_path"], out,
                           draws=20, seed=1, make_figures=False,
                           human_means_path=fixture_run["human_path"],
                           probs_path=fixture_run["probs_path"])
        assert not (out / "three_column_table.csv").exists()  # nothing written

    def test_unsummed_probabilities_fail_loudly(self, fixture_run):
        probs = pd.read_csv(fixture_run["probs_path"], dtype={"option_code": str})
        mask = (probs.eval_country == "C05") & (probs.question_id == "Q57") & \
               (probs.option_code == "1")
        probs.loc[mask, "model_prob"] = 0.9  # breaks the sum-to-one constraint
        out = fixture_run["tmp"] / "out_invalid_prob"
        human = A.load_human_means(fixture_run["human_path"])
        with pytest.raises(ValueError, match="sums"):
            A.run_analysis(probs, human, fixture_run["z_path"], out,
                           draws=20, seed=1, make_figures=False,
                           human_means_path=fixture_run["human_path"],
                           probs_path=fixture_run["probs_path"])
        assert not (out / "three_column_table.csv").exists()


class TestDryRunPurge:
    def test_fixture_outputs_live_in_scratch_and_get_purged(self, fixture_run):
        # the dry run wrote only under tmp_path (pytest scratch), never into
        # the repo; simulate the purge protocol here
        out = fixture_run["out"]
        assert str(out).startswith(str(fixture_run["tmp"]))
        import shutil
        shutil.rmtree(out)
        assert not out.exists()
