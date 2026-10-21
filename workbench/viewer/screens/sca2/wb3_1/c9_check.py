#!/usr/bin/env python3
import argparse
import csv
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dom", type=Path)
    ap.add_argument("story", type=Path)
    ap.add_argument("numbers_root", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    rows = {row["claim_id"]: row for row in csv.DictReader((args.numbers_root / "NUMBERS_TABLE.csv").open())}
    ev = json.loads(args.dom.read_text())
    data = json.loads(args.story.read_text())
    failures = []
    checks = 0

    def f3(value):
        return f"{float(value):.3f}"

    def check(name, ok, detail=""):
        nonlocal checks
        checks += 1
        if not ok:
            failures.append({"name": name, "detail": detail})

    summary_claims = {
        "recovery": "C9_label_recovery_recovery_profile_block",
        "accuracy": "C9_label_recovery_accuracy_profile_block",
        "base_accuracy": "C9_label_recovery_base_accuracy_profile_block",
    }
    cell_claims = {
        "base": "C9_TVD_base_mean_tvd_country_equal",
        "persona": "C9_TVD_persona_mean_tvd_country_equal",
        "adapter": "C9_TVD_adapter_mean_tvd_country_equal",
        "adapter_persona": "C9_TVD_adapter_persona_mean_tvd_country_equal",
    }
    contrast_claims = {
        "adapter_minus_base": "C9_TVD_adapter_minus_base_profile_block",
        "adapter_persona_minus_adapter": "C9_TVD_adapter_persona_minus_adapter_profile_block",
        "adapter_persona_minus_base": "C9_TVD_adapter_persona_minus_base_profile_block",
        "adapter_persona_minus_persona": "C9_TVD_adapter_persona_minus_persona_profile_block",
        "persona_minus_base": "C9_TVD_persona_minus_base_profile_block",
        "interaction": "C9_TVD_interaction_profile_block",
    }
    for viewport in (1440, 1700):
        observed = ev["dom"][f"c9-{viewport}"]
        assert [row["k"] for row in observed["summ"]] == list(summary_claims)
        for row in observed["summ"]:
            source = rows[summary_claims[row["k"]]]
            check(f"{viewport} summary {row['k']} text", row["txt"] == f3(source["value"]))
            check(f"{viewport} summary {row['k']} exact", float(row["v"]) == float(source["value"]))
        assert [row["k"] for row in observed["cells"]] == list(cell_claims)
        for row in observed["cells"]:
            source = rows[cell_claims[row["k"]]]
            check(f"{viewport} cell {row['k']} text", row["txt"] == f3(source["value"]))
            check(f"{viewport} cell {row['k']} exact", float(row["v"]) == float(source["value"]))
        assert [row["k"] for row in observed["contr"]] == list(contrast_claims)
        for row in observed["contr"]:
            source = rows[contrast_claims[row["k"]]]
            exact = f"{f3(source['value'])} [{f3(source['ci_low'])}, {f3(source['ci_high'])}]"
            check(f"{viewport} contrast {row['k']} text", row["txt"] == exact)
            check(
                f"{viewport} contrast {row['k']} exact",
                float(row["v"]) == float(source["value"])
                and float(row["lo"]) == float(source["ci_low"])
                and float(row["hi"]) == float(source["ci_high"]),
            )

    country_rows = {
        row["country"]: row
        for row in csv.DictReader((args.numbers_root / "results/c9/c9_label_recovery.csv").open())
    }
    for viewport in (1440, 1700):
        dots = {row["k"]: row for row in ev["dom"][f"c9-{viewport}"]["dots"]}
        check(f"{viewport} dot tracks", set(dots) == {"recovery", "accuracy"})
        for key, row in dots.items():
            check(f"{viewport} dots {key} count", row["n"] == 42 and len(row["vals"]) == 42)
            for country, value in row["vals"]:
                check(f"{viewport} dot {key} {country}", float(value) == float(country_rows[country][key]))

    c9_claim_records = 0

    def optional_equal(value, source):
        if value is None:
            return source == ""
        return float(value) == float(source)

    def walk(value):
        nonlocal c9_claim_records
        if isinstance(value, dict):
            if "claim_id" in value:
                source = rows[value["claim_id"]]
                c9_claim_records += 1
                low_matches = optional_equal(value["ci_low"], source["ci_low"])
                high_matches = optional_equal(value["ci_high"], source["ci_high"])
                check(
                    "json " + value["claim_id"],
                    float(value["value"]) == float(source["value"]) and low_matches and high_matches,
                )
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(data["c9"])
    for row in data["c9"]["label_recovery"]["countries"]:
        source = country_rows[row["cc"]]
        check(
            "json dot " + row["cc"],
            float(row["recovery"]) == float(source["recovery"])
            and float(row["accuracy"]) == float(source["accuracy"]),
        )
        check("json dot fields " + row["cc"], set(row) == {"cc", "recovery", "accuracy"})

    report = {"pass": not failures, "checks": checks, "failures": failures, "c9_claim_records": c9_claim_records}
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
