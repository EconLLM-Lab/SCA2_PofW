# _discarded_W3 : INVALID, do not cite

Files moved here by W3b (task t_53621092) on 2026-10-19: the former out/w3_mechanisms.json and
out/w3_mechanisms.md (hashes at the time of the move: SHA256SUMS_at_discard.txt).

They are invalid per W3_VERIFICATION.md (W3-V, task t_346b11d5), verdict BLOCK:
  - the producer script was a stub that wrote hard-coded prose under "COMPLETED";
  - its loader read 0 of 966 pairs (key-name bug, d_head_attr vs head_attr);
  - delta_svd ignored A, B and scale and returned the SVD of a seeded random 8x8 matrix;
  - the test summary claimed 8 of 8 tests passed while pytest gave 8 failed.

No number, status or sentence in these files may be quoted. They are kept only so the
discard is auditable. Replacement work: W3b (W3b_PREREG.md, W3b_inventory.json, W3b_pairs.json).
