"""Run sca2 unit tests without pytest (stdlib)."""

from __future__ import annotations

import tempfile
import traceback
from pathlib import Path

from sca2.tests.test_eval import (
    test_eval_execute_is_refused,
    test_eval_missing_map_fails,
    test_eval_plans_existing_item_map,
    test_inspect_item_map_counts_mapped,
)
from sca2.tests.test_generate import (
    test_generate_reuses_declared_bank,
    test_inspect_bank_counts_unique_triplets,
    test_inspect_bank_flags_conflict,
    test_inspect_reports_inverted_polarity,
    test_materialize_is_refused,
)
from sca2.tests.test_label import test_label_on_tiny_bank
from sca2.tests.test_protocol import (
    test_missing_table_is_rejected,
    test_paper_protocol_loads_and_hashes,
    test_receipt_is_scannable,
    test_run_id_uses_protocol_name,
)
from sca2.tests.test_report import (
    test_collect_keeps_latest_matching_hash,
    test_report_chains_four_stages,
    test_report_incomplete_without_all_stages,
)
from sca2.tests.test_train import (
    test_train_execute_is_refused,
    test_train_missing_country_fails,
    test_train_plans_existing_country_files,
)


def main() -> int:
    tests = [
        test_paper_protocol_loads_and_hashes,
        test_receipt_is_scannable,
        test_run_id_uses_protocol_name,
        test_inspect_bank_counts_unique_triplets,
        test_inspect_bank_flags_conflict,
        test_inspect_reports_inverted_polarity,
        test_generate_reuses_declared_bank,
        test_materialize_is_refused,
        test_train_plans_existing_country_files,
        test_train_missing_country_fails,
        test_train_execute_is_refused,
        test_inspect_item_map_counts_mapped,
        test_eval_plans_existing_item_map,
        test_eval_missing_map_fails,
        test_eval_execute_is_refused,
        test_collect_keeps_latest_matching_hash,
        test_report_incomplete_without_all_stages,
        test_report_chains_four_stages,
    ]
    failed = 0
    for test in tests:
        try:
            if test.__code__.co_argcount:
                with tempfile.TemporaryDirectory() as tmp:
                    test(Path(tmp))
            else:
                test()
            print(f"ok   {test.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL {test.__name__}")
            traceback.print_exc()
    with tempfile.TemporaryDirectory() as tmp:
        try:
            test_missing_table_is_rejected(Path(tmp))
            print("ok   test_missing_table_is_rejected")
        except Exception:
            failed += 1
            print("FAIL test_missing_table_is_rejected")
            traceback.print_exc()
        try:
            test_label_on_tiny_bank(Path(tmp) / "label")
            print("ok   test_label_on_tiny_bank")
        except Exception:
            failed += 1
            print("FAIL test_label_on_tiny_bank")
            traceback.print_exc()
    print(f"{20 - failed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
