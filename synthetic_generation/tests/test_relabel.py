from sca2_datagen.relabel import (
    build_triplet_bank,
    label_triplet_for_country,
    recover_ab_scores,
    sign_choice,
    triplet_id,
)


def test_sign_choice_uses_nonnegative_as_a() -> None:
    assert sign_choice(0.15) == "A"
    assert sign_choice(0.0) == "A"
    assert sign_choice(-0.01) == "B"


def test_build_triplet_bank_deduplicates_and_checks_ab_identity() -> None:
    prompt = "A scenario"
    rows = [
        {
            "prompt": prompt,
            "gps_dimension": "trust",
            "facet": "stranger",
            "response_a": "high",
            "response_b": "low",
            "chosen_option": "A",
            "qc_status": "pass",
            "contamination_ratio": 0.2,
            "contamination_category": "low",
            "m_chosen_trust": 0.8,
            "m_rejected_trust": 0.2,
            "m_chosen_patience": 0.5,
            "m_rejected_patience": 0.4,
            "m_chosen_risktaking": 0.1,
            "m_rejected_risktaking": 0.1,
            "m_chosen_altruism": 0.1,
            "m_rejected_altruism": 0.1,
            "m_chosen_posrecip": 0.1,
            "m_rejected_posrecip": 0.1,
            "m_chosen_negrecip": 0.1,
            "m_rejected_negrecip": 0.1,
        },
        {
            "prompt": prompt,
            "gps_dimension": "trust",
            "facet": "stranger",
            "response_a": "high",
            "response_b": "low",
            "chosen_option": "B",
            "qc_status": "pass",
            "contamination_ratio": 0.2,
            "contamination_category": "low",
            "m_chosen_trust": 0.2,
            "m_rejected_trust": 0.8,
            "m_chosen_patience": 0.4,
            "m_rejected_patience": 0.5,
            "m_chosen_risktaking": 0.1,
            "m_rejected_risktaking": 0.1,
            "m_chosen_altruism": 0.1,
            "m_rejected_altruism": 0.1,
            "m_chosen_posrecip": 0.1,
            "m_rejected_posrecip": 0.1,
            "m_chosen_negrecip": 0.1,
            "m_rejected_negrecip": 0.1,
        },
    ]
    bank = build_triplet_bank(rows)
    assert len(bank) == 1
    assert bank[0]["triplet_id"] == triplet_id(prompt, "trust")
    assert bank[0]["m_a_trust"] == 0.8
    assert bank[0]["m_b_trust"] == 0.2


def test_label_triplet_flips_with_country_sign() -> None:
    triplet = {
        "triplet_id": "abc",
        "prompt": "A scenario",
        "facet": "stranger",
        "gps_dimension": "trust",
        "response_a": "high trust",
        "response_b": "low trust",
        "source_qc_status": "pass",
        "source_contamination_ratio": 0.2,
        "source_contamination_category": "low",
        "m_a_trust": 0.8,
        "m_b_trust": 0.2,
    }
    z_pos = {key: 0.2 for key in ("trust", "risktaking", "patience", "altruism", "posrecip", "negrecip")}
    z_neg = {key: -0.2 for key in z_pos}
    pos = label_triplet_for_country(triplet, "USA", z_pos, run_id="r", export_timestamp="t")
    neg = label_triplet_for_country(triplet, "MEX", z_neg, run_id="r", export_timestamp="t")
    assert pos["chosen_option"] == "A"
    assert pos["chosen"] == "high trust"
    assert neg["chosen_option"] == "B"
    assert neg["chosen"] == "low trust"
    assert pos["m_chosen"] == 0.8
    assert neg["m_chosen"] == 0.2
    assert pos["labeling_rule"] == "deterministic_sign"


def test_recover_ab_scores_inverts_when_b_was_chosen() -> None:
    row = {
        "chosen_option": "B",
        "m_chosen_trust": 0.1,
        "m_rejected_trust": 0.9,
        "m_chosen_risktaking": 0.0,
        "m_rejected_risktaking": 0.0,
        "m_chosen_patience": 0.0,
        "m_rejected_patience": 0.0,
        "m_chosen_altruism": 0.0,
        "m_rejected_altruism": 0.0,
        "m_chosen_posrecip": 0.0,
        "m_rejected_posrecip": 0.0,
        "m_chosen_negrecip": 0.0,
        "m_rejected_negrecip": 0.0,
    }
    recovered = recover_ab_scores(row)
    assert recovered["m_a_trust"] == 0.9
    assert recovered["m_b_trust"] == 0.1
