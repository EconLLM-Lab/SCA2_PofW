"""The SCA2 story data the viewer reads (viewer/public/sca2/sca2_data.json).

Written by scripts/build_sca2_data.py from Paper B artifacts (one-way read). These tests check the
invariants a reader relies on, without the main repo: the file holds model scores and GPS signs only,
the profile partition is consistent, every click-through pair differs in exactly one bit, and every
number that carries a claim id equals that claim's value.
"""
import json
import math
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parents[1] / "viewer/public/sca2/sca2_data.json"
DIMS = ["trust", "risktaking", "patience", "altruism", "posrecip", "negrecip"]
SURFACES = ["trust", "risktaking", "patience:Q43", "patience:Q50", "altruism", "posrecip", "negrecip"]


@pytest.fixture(scope="module")
def D():
    return json.loads(DATA.read_text())


def test_schema_and_label(D):
    assert D["schema"] == "sca2-workbench/story-data@1"
    assert "DESCRIPTIVE" in D["label"] and "NOT PREREGISTERED" in D["label"]
    assert D["dims"] == DIMS and D["surfaces"] == SURFACES
    for s in D["sources"]:
        assert len(s["sha256"]) == 64 and s["path"]


def test_root_exposes_static_story_entry():
    landing = DATA.parents[2] / "src/landing.ts"
    assert 'href="/sca2/index.html"' in landing.read_text()


def test_no_human_quantities(D):
    # Countries carry six signs (as 0/1 bits) and a unit code; nothing continuous.
    for c in D["countries"]:
        assert set(c) == {"cc", "unit", "bits"}
        assert len(c["bits"]) == 6 and set(c["bits"]) <= {0, 1}
    assert_model_only(D)


def assert_model_only(data):
    # Metadata strings may name input files (including gps_z_vectors.json).
    # Payloads, not substrings in provenance, are restricted by exact field sets.
    def fields(value, allowed):
        assert set(value) == set(allowed.split()), set(value)

    fields(data, "schema label generated_by main_repo_head sources dims surfaces surface_items countries profiles routes crosstalk claims c9 bit_pairs featured export")
    for source in data["sources"]:
        fields(source, "role path sha256")
        assert not Path(source["path"]).is_absolute()
    for country in data["countries"]:
        fields(country, "cc unit bits")
        assert len(country["bits"]) == len(DIMS)
        assert all(type(v) is int and v in (0, 1) for v in country["bits"])
    for route in data["routes"].values():
        fields(route, "name desc unit_of_score scores within")
        for row in route["scores"].values():
            fields(row, " ".join(SURFACES))
            assert all(type(v) in (float, int) and math.isfinite(v) for v in row.values())
        fields(route["within"], " ".join(SURFACES))
        for summary in route["within"].values():
            fields(summary, "within_profile_sd_mean sd_all n_profiles_with_2plus")
    for route in data["crosstalk"].values():
        fields(route, "cells reproduced_max_abs_gap source units")
        for cell in route["cells"]:
            fields(cell, "bit surface beta se t t_lenth claims own")
    for claim in data["claims"].values():
        fields(claim, "value statistic use output_file")
    fields(data["c9"], "label tvd_cells contrasts label_recovery")
    assert data["c9"]["label"] == "descriptive, not preregistered; cross-family audited"
    for group in (data["c9"]["tvd_cells"], data["c9"]["contrasts"], data["c9"]["label_recovery"]["summary"]):
        for claim in group.values():
            fields(claim, "claim_id value ci_low ci_high statistic")
    fields(data["c9"]["label_recovery"], "summary countries")
    for country in data["c9"]["label_recovery"]["countries"]:
        fields(country, "cc recovery accuracy")
    for featured in data["featured"]:
        fields(featured, "bit surface item x y prompt_x prompt_y n_candidates n_with_exports rule")
    fields(data["export"], "src prompt_src base country_key default_units j_plus j_minus")
    for unit in data["export"]["default_units"]:
        fields(unit, "cc item")


@pytest.mark.parametrize("location", ["root", "country", "route", "cell"])
def test_privacy_schema_rejects_human_payloads(D, location):
    from copy import deepcopy
    data = deepcopy(D)
    target = {"root": data, "country": data["countries"][0],
              "route": data["routes"]["cohort1"],
              "cell": data["crosstalk"]["adapter"]["cells"][0]}[location]
    target["human_mean"] = 0.5  # negative test fixture, never a delivered score
    with pytest.raises(AssertionError):
        assert_model_only(data)


def test_profiles_partition(D):
    cs = D["countries"]
    assert len(cs) == 42
    units = {c["unit"] for c in cs}
    assert len(units) == 26
    for c in cs:
        assert c["unit"] == "P_" + "_".join(map(str, c["bits"]))
    members = sorted(cc for ccs in D["profiles"].values() for cc in ccs)
    assert members == sorted(c["cc"] for c in cs)


def test_routes_cover_every_country_and_surface(D):
    assert set(D["routes"]) == {"cohort1", "bank2", "signprompt", "persona"}
    ccs = {c["cc"] for c in D["countries"]}
    unit = {c["cc"]: c["unit"] for c in D["countries"]}
    for name, r in D["routes"].items():
        assert set(r["scores"]) == ccs, name
        for cc, row in r["scores"].items():
            assert set(row) == set(SURFACES)
            assert all(math.isfinite(v) for v in row.values())
        if r["unit_of_score"] == "profile":   # mapped routes are constant within a profile
            for u in set(unit.values()):
                rows = [r["scores"][cc] for cc in ccs if unit[cc] == u]
                assert all(x == rows[0] for x in rows), (name, u)


def test_bit_pairs_differ_in_exactly_one_bit(D):
    bits = {c["cc"]: c["bits"] for c in D["countries"]}
    for dim, pairs in D["bit_pairs"].items():
        i = DIMS.index(dim)
        assert pairs, dim
        for x, y in pairs:
            diff = [k for k in range(6) if bits[x][k] != bits[y][k]]
            assert diff == [i] and bits[x][i] == 0 and bits[y][i] == 1, (dim, x, y)


def test_crosstalk_cells_and_claims(D):
    claims = D["claims"]
    for route in ("adapter", "signprompt"):
        cells = D["crosstalk"][route]["cells"]
        assert len(cells) == 42
        assert {(c["bit"], c["surface"]) for c in cells} == {(b, s) for b in DIMS for s in SURFACES}
        for c in cells:
            for cid in c["claims"]:
                assert abs(claims[cid]["value"] - c["beta"]) < 1e-12, cid
        # reproduced from the scores the cohort tab shows (bank-2 / sign-prompt 64 units)
        assert D["crosstalk"][route]["reproduced_max_abs_gap"] < 1e-9
    own = {c["surface"]: c["beta"] for c in D["crosstalk"]["adapter"]["cells"]
           if c["bit"] == c["surface"].split(":")[0]}
    assert len(own) == 7 and all(v > 0 for v in own.values())   # adapters: 0 of 7 own effects wrong-signed


def test_c9_is_claim_id_selected_model_only_data(D):
    c9 = D["c9"]
    assert set(c9["tvd_cells"]) == {"base", "adapter", "persona", "adapter_persona"}
    assert {v["claim_id"] for v in c9["tvd_cells"].values()} == {
        "C9_TVD_base_mean_tvd_country_equal",
        "C9_TVD_adapter_mean_tvd_country_equal",
        "C9_TVD_persona_mean_tvd_country_equal",
        "C9_TVD_adapter_persona_mean_tvd_country_equal",
    }
    assert {v["claim_id"] for v in c9["contrasts"].values()} == {
        "C9_TVD_adapter_minus_base_profile_block",
        "C9_TVD_adapter_persona_minus_adapter_profile_block",
        "C9_TVD_adapter_persona_minus_base_profile_block",
        "C9_TVD_adapter_persona_minus_persona_profile_block",
        "C9_TVD_persona_minus_base_profile_block",
        "C9_TVD_interaction_profile_block",
    }
    assert {v["claim_id"] for v in c9["label_recovery"]["summary"].values()} == {
        "C9_label_recovery_recovery_profile_block",
        "C9_label_recovery_accuracy_profile_block",
        "C9_label_recovery_base_accuracy_profile_block",
        "C9_label_recovery_mean_margin_shift_profile_block",
    }
    countries = c9["label_recovery"]["countries"]
    assert len(countries) == 42
    assert {r["cc"] for r in countries} == {r["cc"] for r in D["countries"]}
    assert all(set(r) == {"cc", "recovery", "accuracy"} for r in countries)
    # The only country-level C9 values shipped are model-only label recovery and accuracy.
    assert all("tvd" not in key.lower() and "human" not in key.lower() for r in countries for key in r)


def test_c9_rendered_values_are_not_typed_into_the_page(D):
    html = (DATA.parent / "index.html").read_text()
    records = list(D["c9"]["tvd_cells"].values())
    records += list(D["c9"]["label_recovery"]["summary"].values())[:3]
    for record in records:
        assert f'{record["value"]:.3f}' not in html


def test_c9_projection_polish_is_present_and_data_driven():
    html = (DATA.parent / "index.html").read_text()
    required = [
        "lower = closer to respondents",
        "no persona",
        "persona",
        "no adapter",
        "adapter",
        "data-c9-mean",
        "chance",
        "forestPlot",
        "forest-zero",
        "95% profile-block bootstrap over the ${Object.keys(D.profiles).length} sign profiles",
        "(adapter + persona − persona) − (adapter − base)",
        "Label fidelity is not agreement with respondents.",
    ]
    for text in required:
        assert text in html
    assert '<div class="contrast-list">' not in html


def test_featured_links_are_valid(D):
    bits = {c["cc"]: c["bits"] for c in D["countries"]}
    for f in D["featured"]:
        assert [f["x"], f["y"]] in D["bit_pairs"][f["bit"]]
        assert f["item"].removeprefix("wvs_") in D["surface_items"][f["surface"]]
        assert f["n_candidates"] == len(D["bit_pairs"][f["bit"]])
        assert bits[f["x"]] != bits[f["y"]]
        assert f["prompt_x"].endswith("_sp" + "".join(map(str, bits[f["x"]])))
        assert f["prompt_y"].endswith("_sp" + "".join(map(str, bits[f["y"]])))
