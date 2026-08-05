"""Freeze and run-id discipline (extracted idea from cvprofiles: paper numbers
require frozen inputs + pinned seed/version; theta-grid excluded from run_id)."""
from __future__ import annotations

import hashlib
import json
from typing import Any

PACKAGE_VERSION = "0.1.0"


def hash_payload(payload: Any) -> str:
    """SHA-256 hex of a canonical JSON payload (stable across dict order)."""
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def compute_run_id(
    scores_hash: str,
    network_hash: str,
    protocol_hash: str,
    seed: int,
    package_version: str = PACKAGE_VERSION,
) -> str:
    """Deterministic run id: 16-hex suffix of the freeze preimage hash.

    Theta-grid settings are intentionally NOT part of the preimage (they are
    an additive diagnostic viewport over the same frozen bundle).
    """
    preimage = {
        "scores_hash": scores_hash,
        "network_hash": network_hash,
        "protocol_hash": protocol_hash,
        "seed": int(seed),
        "package_version": package_version,
    }
    return hash_payload(preimage)[:16]
