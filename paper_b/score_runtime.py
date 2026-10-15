"""Paper B — scoring runtime: revision pinning, provenance enforcement, cache
safety, model-only scoring, the independent adapter-path gate, and verified
per-unit HF persistence.

Owned by the scorer worker; `eval_lib.py` is another worker's file. All network
contact is funneled through injectable callables so tests can drive the full
contract against deterministic in-memory fixtures.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import time
from pathlib import Path

import numpy as np
import pandas as pd

import config as C
import eval_config as E

# ------------------------------------------------------------------ constants
PARENT_PINNED_REVISION = "7550fd4cfe514470bb8d80918a43c9ae424d26b5"
REVISION_ENV = "SCA2_PB_ADAPTER_REVISION"
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")

REQUIRED_ADAPTER_FILES = ("adapter_config.json", "adapter_model.safetensors")

# frozen training protocol (must match the run record written by train_country.py)
FROZEN_TRAINING = {
    "model_name": C.MODEL_NAME,
    "beta": C.DPO_BETA,
    "lr": C.LEARNING_RATE,
    "epochs": C.NUM_TRAIN_EPOCHS,
    "max_length": C.MAX_LENGTH,
    "grad_accum": C.GRADIENT_ACCUMULATION_STEPS,
    "bank_run_id": C.BANK_RUN_ID,
    "lora": {"r": C.LORA_R, "alpha": C.LORA_ALPHA},
}

# private artifacts destination (parent-verified: metadata probe commit
# ae15922ca3cfc8a876e48828030feed2e7953255 on 2026-10-11)
ARTIFACTS_REPO = "Bonorinoa/SCA2-paper-b-artifacts"
ARTIFACTS_REPO_TYPE = "dataset"

# model-only sanitized column allowlist for durable persistence.
# question_text is deliberately EXCLUDED (rights review pending); the local CSV
# keeps it and is retained locally for a later join once rights are cleared.
PERSISTED_COLUMNS = [
    "run_id", "model", "adapter_revision", "question_id", "option_index",
    "option_code", "option_logprob", "option_token_count", "model_prob",
]

CODE_README = """# paper_b.score_runtime\n\nNo GPU run launches until `run_adapter_path_gate` passes on the real weights;\nGPU launch stays blocked until that gate is exercised (parent decision,\n2026-10-11). See PARENT_DECISIONS.md and STORAGE_VERIFICATION.md.\n"""


# ================================================================ revision pin
def require_revision(revision: str | None) -> str:
    """A full 40-hex SHA is mandatory: CLI arg, else SCA2_PB_ADAPTER_REVISION,
    else the parent-pinned frozen revision. No short SHAs, no 'main', no None."""
    rev = revision or os.environ.get(REVISION_ENV) or PARENT_PINNED_REVISION
    if not _SHA_RE.match(rev):
        raise ValueError(
            f"adapter revision must be a full 40-hex SHA, got {rev!r} "
            f"(set --adapter-revision or {REVISION_ENV})")
    return rev


def revision_cache_dir(cache_root: Path, revision: str) -> Path:
    """Adapters are cached PER REVISION so a pin change can never silently
    reuse weights from another snapshot."""
    return Path(cache_root) / "adapters_by_revision" / revision


def load_and_validate_run_record(adapter_dir: Path, country: str) -> dict:
    rec_path = Path(adapter_dir) / "run_record.json"
    if not rec_path.exists():
        raise FileNotFoundError(
            f"{country}: run_record.json missing in {adapter_dir} — provenance "
            "incomplete; refusing to score")
    rec = json.loads(rec_path.read_text())
    validate_run_record(rec, country=country)
    return rec


def validate_run_record(record: dict, country: str) -> bool:
    """Enforce cohort membership and every frozen training setting."""
    if country not in C.COHORT:
        raise ValueError(f"country {country!r} not in cohort")
    if record.get("country") != country:
        raise ValueError(f"run_record country {record.get('country')!r} != {country!r}")
    for field, expected in FROZEN_TRAINING.items():
        if field == "lora":
            continue
        got = record.get(field)
        if got != expected:
            raise ValueError(
                f"run_record {field}={got!r} != frozen {expected!r}")
    lora = record.get("lora") or {}
    for k in ("r", "alpha"):
        if lora.get(k) != FROZEN_TRAINING["lora"][k]:
            raise ValueError(
                f"run_record lora.{k}={lora.get(k)!r} != frozen "
                f"{FROZEN_TRAINING['lora'][k]!r}")
    if "n_train" not in record or isinstance(record["n_train"], bool) \
            or not isinstance(record["n_train"], int) or record["n_train"] != C.TRAIN_ROWS:
        raise ValueError(
            f"run_record n_train must be the frozen integer {C.TRAIN_ROWS}, got "
            f"{record.get('n_train')!r}")
    return True


def _is_complete_adapter(d: Path) -> bool:
    return all((d / f).exists() for f in REQUIRED_ADAPTER_FILES)


def resolve_adapter(country: str, revision: str, cache_root: Path,
                    downloader=None, validate: bool = True) -> tuple[Path, str]:
    """Return (adapter_dir, source). Cache-first within the revision dir;
    otherwise download via `downloader(cc, dest_root, revision)`. There is NO
    Drive fallback: if the hub path fails, this raises.

    `downloader` must place files as the HF snapshot layout does:
    dest_root/adapters/<CC>/adapter_config.json (+ .safetensors), matching
    allow_patterns=[f"adapters/{cc}/*"] with local_dir=dest_root. A cache hit
    is re-validated (complete files + run record) — a stale or partial cache
    entry never silently satisfies the resolver.
    """
    rev = require_revision(revision)
    dest_root = revision_cache_dir(cache_root, rev)
    local = dest_root / "adapters" / country

    if _is_complete_adapter(local):
        if validate:
            load_and_validate_run_record(local, country)
        return local, "cache"

    if downloader is None:
        def downloader(cc, dest, r):
            from huggingface_hub import snapshot_download
            snapshot_download(
                repo_id=C.HF_ADAPTER_REPO, repo_type=E.HF_ADAPTER_REPO_TYPE,
                revision=r, allow_patterns=[f"adapters/{cc}/*"],
                local_dir=str(dest))
    try:
        downloader(country, dest_root, rev)
    except FileNotFoundError:
        raise
    except Exception as e:  # noqa: BLE001
        raise FileNotFoundError(
            f"{country}: hub download failed at revision {rev} "
            f"({type(e).__name__}: {e}); no Drive fallback is attempted by design"
        ) from e

    if not _is_complete_adapter(local):
        raise FileNotFoundError(
            f"{country}: no complete adapter at revision {rev} "
            f"(tried cache {local} then hub {C.HF_ADAPTER_REPO}); "
            "no Drive fallback is attempted by design")
    if validate:
        load_and_validate_run_record(local, country)
    return local, "hub"


# ================================================================ hashing
WEIGHT_FILE_BASENAMES = ("adapter_model.safetensors", "adapter_config.json")


def adapter_sha256(adapter_dir: Path) -> str:
    """Full SHA-256 over the adapter's WEIGHT files only (sorted by name);
    provenance metadata like run_record.json is deliberately excluded."""
    h = hashlib.sha256()
    for name in sorted(WEIGHT_FILE_BASENAMES):
        p = Path(adapter_dir) / name
        if not p.exists():
            raise FileNotFoundError(f"adapter weight file missing: {p}")
        h.update(name.encode())
        h.update(b"\0")
        h.update(p.read_bytes())
    return h.hexdigest()


TRACKED_CODE_FILES = (
    "config.py", "eval_config.py", "eval_lib.py", "score_cohort.py",
    "score_runtime.py", "build_scoring_spec.py", "evaluate_local.py",
    "analyze_surface.py",
)


def dirty_code_hashes(root: Path) -> dict[str, str]:
    """Hash the scoring modules actually present. Missing files are omitted."""
    out = {}
    root = Path(root)
    for name in TRACKED_CODE_FILES:
        path = root / name
        if path.is_file():
            out[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def code_revision(repo_root: Path) -> str:
    """Full 40-hex commit SHA of the repo running the scorer."""
    git = Path(repo_root) / ".git"
    head = (git / "HEAD").read_text().strip()
    if head.startswith("ref: "):
        return (git / head.split("ref: ", 1)[1].strip()).read_text().strip()
    return head


# ================================================================ cache safety
READOUT_FIELDS = ("temperature", "completion_prefix", "max_prompt_tokens",
                  "max_completion_tokens", "length_normalize")


def cache_fingerprint(specs: list[dict], readout: dict, code_revision: str,
                      adapter_sha256: str, *, code_hashes: dict | None = None,
                      base_revision: str = "", tokenizer_revision: str = "") -> str:
    """SHA-256 over everything that can change a score. Question text and labels
    are hashed, never written into the digest itself."""
    payload = {
        "spec_grid": [
            {"question_id": s["question_id"],
             "question_text_sha256": hashlib.sha256(
                 str(s.get("question_text", "")).encode()).hexdigest(),
             "labels_sha256": hashlib.sha256(
                 json.dumps(list(s.get("labels") or []), sort_keys=True).encode()).hexdigest(),
             "codes": list(s["codes"]),
             "response_type": s.get("response_type"),
             "is_numeric_open": s.get("is_numeric_open"),
             "is_ordered": s.get("is_ordered")}
            for s in specs],
        "readout": {k: readout.get(k) for k in READOUT_FIELDS},
        "code_revision": code_revision,
        "code_hashes": dict(sorted((code_hashes or {}).items())),
        "base_revision": base_revision,
        "tokenizer_revision": tokenizer_revision,
        "adapter_sha256": adapter_sha256,
    }
    blob = json.dumps(payload, sort_keys=True).encode()
    return hashlib.sha256(blob).hexdigest()


def score_csv_path(cache_dir: Path, model_name: str) -> Path:
    return Path(cache_dir) / f"{model_name}_option_probabilities.csv"


def sidecar_path(cache_dir: Path, model_name: str) -> Path:
    return Path(cache_dir) / f"{model_name}_option_probabilities.sidecar.json"


def validate_scored_frame(df: pd.DataFrame, specs: list[dict],
                          model_name: str | None = None) -> str | None:
    """Return a rejection reason or None."""
    required = {"model", "question_id", "option_index", "option_code",
                "option_logprob", "model_prob"}
    missing = required - set(df.columns)
    if missing:
        return f"corrupt: missing columns {sorted(missing)}"
    if df.empty:
        return "corrupt: empty frame"
    probs = pd.to_numeric(df["model_prob"], errors="coerce")
    logps = pd.to_numeric(df["option_logprob"], errors="coerce")
    if not np.isfinite(probs).all() or not np.isfinite(logps).all():
        return "non-finite model_prob or option_logprob present"
    if (probs < 0).any():
        return "negative model_prob present"
    keys = list(zip(df["question_id"].astype(str), df["option_code"].astype(str),
                    pd.to_numeric(df["option_index"], errors="coerce")))
    if len(keys) != len(set(keys)):
        return "duplicate question/option keys present"
    models = set(df["model"].astype(str))
    if len(models) != 1:
        return f"mixed model values in one score file: {sorted(models)}"
    if model_name and (
            model_name == "base" or model_name.endswith("_adapter") or model_name.startswith("persona_")
    ) and models != {str(model_name)}:
        return f"model column {sorted(models)} != requested model {model_name}"
    want = {(str(s["question_id"]), str(c)) for s in specs for c in s["codes"]}
    have = {(str(q), str(c)) for q, c in zip(df["question_id"], df["option_code"])}
    if want != have:
        miss = sorted(want - have)[:3]
        extra = sorted(have - want)[:3]
        return (f"incomplete grid: missing {miss}…, unexpected {extra}… "
                f"(want {len(want)}, have {len(have)})")
    by_q = {str(s["question_id"]): [str(c) for c in s["codes"]] for s in specs}
    for qid, group in df.groupby(df["question_id"].astype(str), sort=False):
        expected = by_q.get(str(qid))
        if expected is None:
            continue
        paired = {int(i): str(c) for i, c in zip(group["option_index"], group["option_code"])}
        if any(paired.get(i) != code for i, code in enumerate(expected)):
            return f"option_index/option_code alignment failed for {qid}"
    sums = df.groupby("question_id")["model_prob"].sum()
    bad = sums[(sums - 1.0).abs() > 1e-8]
    if len(bad):
        return f"model_prob does not sum to 1 for {sorted(bad.index)[:3]}"
    return None


def save_cached_scores(cache_dir: Path, model_name: str, df: pd.DataFrame,
                       fingerprint: str, extra_meta: dict | None = None,
                       code_revision: str = "", adapter_sha256: str = "") -> Path:
    """Persist the score CSV plus a provenance sidecar. The sidecar fingerprint
    covers spec/readout/code-revision/adapter-SHA — not just a row count."""
    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    csv = score_csv_path(cache_dir, model_name)
    df.to_csv(csv, index=False)
    sidecar = {"model": model_name, "fingerprint_sha256": fingerprint,
               "code_revision_sha256": code_revision,
               "adapter_sha256": adapter_sha256,
               "n_rows": int(len(df)), "saved_at_utc": time.strftime(
                   "%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               **(extra_meta or {})}
    sidecar_path(cache_dir, model_name).write_text(json.dumps(sidecar, indent=2))
    return csv


def load_cached_scores(cache_dir: Path, model_name: str, specs: list[dict],
                       fingerprint: str) -> tuple[pd.DataFrame | None, dict]:
    """Strict cache validation: fingerprint match + full structural checks.
    Never accepts on row count alone. Returns (df_or_None, meta)."""
    meta = {"valid": False, "reason": None, "path": str(score_csv_path(cache_dir, model_name))}
    csv, sc = score_csv_path(cache_dir, model_name), sidecar_path(cache_dir, model_name)
    if not csv.exists():
        meta["reason"] = "no cache file"
        return None, meta
    if not sc.exists():
        meta["reason"] = "sidecar missing: cache provenance unverifiable"
        return None, meta
    try:
        sidecar = json.loads(sc.read_text())
    except json.JSONDecodeError as e:
        meta["reason"] = f"corrupt sidecar: {e}"
        return None, meta
    if sidecar.get("fingerprint_sha256") != fingerprint:
        meta["reason"] = (f"fingerprint mismatch: sidecar {sidecar.get('fingerprint_sha256')} "
                          f"!= expected {fingerprint} (stale cache)")
        return None, meta
    try:
        df = pd.read_csv(csv, dtype={"option_code": str, "question_id": str})
    except Exception as e:  # noqa: BLE001
        meta["reason"] = f"corrupt CSV: {type(e).__name__}: {e}"
        return None, meta
    reason = validate_scored_frame(df, specs, model_name=model_name)
    if reason:
        meta["reason"] = reason
        return None, meta
    meta["valid"] = True
    return df, meta


# ============================================================ model-only scoring
def load_spec(spec_path: Path) -> dict:
    from build_scoring_spec import spec_sha256
    spec = json.loads(Path(spec_path).read_text())
    if "spec_sha256" in spec:
        body = {k: v for k, v in spec.items() if k != "spec_sha256"}
        if spec_sha256(body) != spec["spec_sha256"]:
            raise ValueError(
                f"spec file hash mismatch: {spec_path} was modified after export")
    if spec.get("battery") not in ("strict", "archive"):
        raise ValueError(f"spec battery must be strict|archive, got {spec.get('battery')!r}")
    return spec


def score_model_only(spec_path: Path, model_name: str, scorer) -> pd.DataFrame:
    """Score a model against a spec file ONLY — no survey frames, no question
    map, no population joins, no Drive. `scorer(spec, model_name) -> DataFrame`.

    The returned frame is structurally validated (complete grid, string codes,
    per-question probability sums) before it is allowed to exist.
    """
    spec = load_spec(spec_path)
    df = scorer(spec, model_name)
    df = df.copy()
    df["option_code"] = df["option_code"].astype(str)
    df["question_id"] = df["question_id"].astype(str)
    reason = validate_scored_frame(df, spec["questions"])
    if reason:
        raise AssertionError(f"{model_name}: scored output invalid: {reason} "
                             "(option probabilities do not sum to one?)")
    return df


# ================================================================ gate matching
GATE_KEYS = ["question_id", "option_index", "option_code"]


def _gate_key_frame(df: pd.DataFrame, label: str) -> pd.DataFrame:
    out = df.copy()
    out["question_id"] = out["question_id"].astype(str)
    out["option_code"] = out["option_code"].astype(str)
    for col in ("option_logprob", "model_prob"):
        out[col] = pd.to_numeric(out[col], errors="coerce")
        if not np.isfinite(out[col]).all():
            raise ValueError(f"{label}: non-finite or NaN value in {col}")
    if out.duplicated(subset=GATE_KEYS).any():
        dups = out.loc[out.duplicated(subset=GATE_KEYS, keep=False), GATE_KEYS].head(3)
        raise ValueError(f"{label}: duplicate gate keys at {dups.to_dict('records')}")
    return out


def compare_gate_scores(got: pd.DataFrame, ref: pd.DataFrame, spec: dict,
                        tol_logprob: float, tol_prob: float) -> tuple[bool, dict]:
    """One-to-one keyed match (question_id, option_index). Any key on one side
    without its counterpart is fatal, NOT dropped. NaN anywhere is fatal.
    Tolerances are pinned by the caller; they are never widened here."""
    for name, value in (("tol_logprob", tol_logprob), ("tol_prob", tol_prob)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not np.isfinite(value) or value <= 0:
            raise ValueError(f"tolerance {name} must be positive and finite, got {value!r}")
    got_k, ref_k = _gate_key_frame(got, "got"), _gate_key_frame(ref, "ref")
    want = {(str(q["question_id"]), i, str(code)) for q in spec["questions"]
            for i, code in enumerate(q["codes"])}
    have_g = set(map(tuple, got_k[GATE_KEYS].itertuples(index=False, name=None)))
    have_r = set(map(tuple, ref_k[GATE_KEYS].itertuples(index=False, name=None)))
    if want != have_g or want != have_r:
        raise ValueError(
            f"one-to-one gate match failed: spec={len(want)}, got={len(have_g)}, "
            f"ref={len(have_r)}, missing_got={sorted(want - have_g)[:3]}, "
            f"missing_ref={sorted(want - have_r)[:3]}")
    m = got_k.merge(ref_k, on=GATE_KEYS, suffixes=("_got", "_ref"), validate="one_to_one")
    dl = (m["option_logprob_got"] - m["option_logprob_ref"]).abs().max()
    dp = (m["model_prob_got"] - m["model_prob_ref"]).abs().max()
    report = {"n_compared": int(len(m)), "max_dlogprob": float(dl), "max_dprob": float(dp),
              "tol_logprob": tol_logprob, "tol_prob": tol_prob,
              "pass": bool(dl <= tol_logprob and dp <= tol_prob)}
    return report["pass"], report


def run_adapter_path_gate(prod_scores: pd.DataFrame, ref_scores: pd.DataFrame,
                          switchback_scores: pd.DataFrame | None, spec: dict,
                          tol_logprob: float, tol_prob: float,
                          require_switchback: bool = True) -> tuple[bool, dict]:
    """Adapter-path gate: production switch path vs an INDEPENDENT reference
    loader, both loading THE SAME frozen weights; plus an adapter
    disable/switch-back check (base path must reproduce after the adapter is
    deactivated). Nothing here compares fresh Paper B scores to Paper A."""
    ok_prod, rep = compare_gate_scores(prod_scores, ref_scores, spec,
                                       tol_logprob, tol_prob)
    report = {"production_vs_reference": rep}
    if require_switchback and switchback_scores is None:
        raise ValueError("switchback scores required: the adapter disable/"
                         "switch-back check is part of the gate")
    if switchback_scores is not None:
        ok_sb, rep_sb = compare_gate_scores(switchback_scores, prod_scores, spec,
                                            tol_logprob, tol_prob)
        report["switchback_vs_production"] = rep_sb
        report["switchback_ok"] = bool(rep_sb["pass"])
    else:
        report["switchback_ok"] = None
    overall = ok_prod and (report["switchback_ok"] is not False)
    report["gate_pass"] = bool(overall)
    return overall, report


_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,80}$")


def require_path_token(name: str, value: str) -> str:
    """Reject values that could escape the intended repository directory."""
    if not isinstance(value, str) or not _TOKEN_RE.fullmatch(value) or ".." in value:
        raise ValueError(f"{name} is not a safe path token: {value!r}")
    return value


class HuggingFaceArtifactStore:
    """Real Hub client: one create_commit, then byte read-back of that commit.

    `hf_hub_download` returns file bytes, matching the persistence contract.
    `upload_file` is intentionally absent: its SDK signature is keyword-only and
    a two-call upload is not one verified commit.
    """

    def __init__(self, api=None, token: str | None = None):
        self.api = api
        self.token = os.environ.get("HF_TOKEN") if token is None else token
        self._commit_sha: str | None = None

    def _client(self):
        if self.api is None:
            from huggingface_hub import HfApi
            self.api = HfApi(token=self.token)
        return self.api

    def commit_files(self, files: dict[str, bytes], repo_id: str, repo_type: str,
                     commit_message: str) -> str:
        from huggingface_hub import CommitOperationAdd
        operations = [
            CommitOperationAdd(path_in_repo=path, path_or_fileobj=data)
            for path, data in files.items()
        ]
        info = self._client().create_commit(
            repo_id=repo_id, operations=operations,
            commit_message=commit_message, repo_type=repo_type,
        )
        self._commit_sha = info.oid
        return info.oid

    def hf_hub_download(self, repo_id, filename, repo_type, revision=None):
        from huggingface_hub import hf_hub_download
        path = hf_hub_download(
            repo_id=repo_id, filename=filename, repo_type=repo_type,
            revision=revision or self._commit_sha, force_download=True,
            token=self.token,
        )
        return Path(path).read_bytes()

    def read_commit_sha(self) -> str | None:
        return self._commit_sha


# ================================================================ persistence
def persist_unit_scores(scores: pd.DataFrame, model_name: str, run_id: str,
                        repo: str, hub, adapter_sha256: str, code_revision: str,
                        local_dir: Path, spec_sha: str = "",
                        adapter_revision: str = "") -> dict:
    """Persist ONE scored unit (per model/adapter) durably, then VERIFY by
    readback. Order of operations:
      1. write the full local copy (question_text retained, for a later
         rights-cleared join — question text files are NOT uploaded until
         parent clears rights);
      2. upload the sanitized, allowlisted CSV + manifest over HTTPS to
         runs/<run_id>/synthetic/ and runs/<run_id>/manifests/;
      3. read the CSV back from the hub and verify the SHA-256 matches byte
         for byte, plus the destination commit SHA;
      4. any failure raises (halt before the next adapter) — the local copy
         is always preserved.
    """
    if not run_id or not isinstance(run_id, str):
        raise ValueError("run_id is required for persistence")
    if not repo or not isinstance(repo, str):
        raise ValueError("destination repo is required for persistence")
    require_path_token("run_id", run_id)
    require_path_token("model_name", model_name)
    if repo != ARTIFACTS_REPO:
        raise ValueError(f"destination repo must be {ARTIFACTS_REPO!r}, got {repo!r}")

    # 1. local durable copy FIRST (full frame; survives upload failure)
    unit_dir = Path(local_dir) / run_id / "synthetic"
    unit_dir.mkdir(parents=True, exist_ok=True)
    local_csv = unit_dir / f"{model_name}_option_probabilities.csv"
    scores.to_csv(local_csv, index=False)

    # 2. sanitized allowlisted upload copy. Provenance-only columns
    # (question_text, prompt text/debug columns) are allowed in the local frame
    # — retained locally for the later rights-cleared join — but NEVER uploaded.
    # Any other column outside the allowlist is a hard error.
    LOCAL_ONLY_COLUMNS = {"question_text", "prompt_text", "formatted_prompt",
                          "complete_prompt_model_received", "option_label",
                          "response_type", "gps_dimension", "is_ordered",
                          "is_numeric_open", "prompt_country",
                          "prompt_token_count_before_truncation",
                          "prompt_token_count_model", "prompt_was_truncated",
                          "generated_answer_raw", "generated_answer",
                          "generated_answer_code", "generated_answer_is_valid",
                          "generated_token_count", "option_value"}
    extra = set(scores.columns) - set(PERSISTED_COLUMNS)
    disallowed = extra - LOCAL_ONLY_COLUMNS
    if disallowed:
        raise ValueError(
            f"columns outside the model-only persist allowlist: {sorted(disallowed)} — "
            "human/aggregate data must never reach the artifacts repo")
    remote = scores[PERSISTED_COLUMNS].copy()
    remote["option_code"] = remote["option_code"].astype(str)
    remote["question_id"] = remote["question_id"].astype(str)
    csv_bytes = remote.to_csv(index=False).encode()
    csv_path = f"runs/{run_id}/synthetic/{model_name}_option_probabilities.csv"
    csv_sha = hashlib.sha256(csv_bytes).hexdigest()

    manifest = {
        "run_id": run_id, "model": model_name,
        "adapter_revision": adapter_revision or None,
        "adapter_sha256": adapter_sha256,
        "code_revision_sha256": code_revision,
        "spec_sha256": spec_sha or None,
        "csv_sha256": csv_sha,
        "n_rows": int(len(remote)),
        "columns": PERSISTED_COLUMNS,
        "sanitized": True, "contains_human_data": False,
        "persisted_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    man_path = f"runs/{run_id}/manifests/{model_name}_manifest.json"
    man_bytes = json.dumps(manifest, indent=2).encode()

    # 3. upload + verify
    try:
        files = {csv_path: csv_bytes, man_path: man_bytes}
        if hasattr(hub, "commit_files"):
            commit_sha = hub.commit_files(
                files, repo_id=repo, repo_type=ARTIFACTS_REPO_TYPE,
                commit_message=f"{run_id}: {model_name} option probabilities",
            )
        else:
            hub.upload_file(csv_bytes, csv_path, repo_id=repo,
                            repo_type=ARTIFACTS_REPO_TYPE,
                            commit_message=f"{run_id}: {model_name} option probabilities")
            hub.upload_file(man_bytes, man_path, repo_id=repo,
                            repo_type=ARTIFACTS_REPO_TYPE,
                            commit_message=f"{run_id}: {model_name} manifest")
            commit_sha = hub.read_commit_sha()
        for path, expected in ((csv_path, csv_sha), (man_path, hashlib.sha256(man_bytes).hexdigest())):
            readback = hub.hf_hub_download(
                repo_id=repo, filename=path, repo_type=ARTIFACTS_REPO_TYPE,
                revision=commit_sha,
            )
            if isinstance(readback, str):
                readback = Path(readback).read_bytes()
            got = hashlib.sha256(readback).hexdigest()
            if got != expected:
                raise RuntimeError(
                    f"readback hash mismatch for {path}: {got} != {expected} — "
                    "persistence NOT verified; local copy preserved, halting")
        if not commit_sha:
            raise RuntimeError("destination commit SHA unavailable — persistence NOT verified")
        return {"verified": True, "csv_sha256": csv_sha, "commit_sha": commit_sha,
                "local_copy": str(local_csv), "remote_csv": csv_path,
                "remote_manifest": man_path}
    except RuntimeError:
        raise
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(
            f"upload failed for {model_name} -> {repo}: {type(e).__name__}: {e} — "
            "local copy preserved at "
            f"{local_csv}; halting before the next adapter") from e


# ================================================================ orchestration
def _readout() -> dict:
    return {"temperature": E.OPTION_SCORE_TEMPERATURE,
            "completion_prefix": E.COMPLETION_PREFIX,
            "max_prompt_tokens": E.EVAL_MAX_PROMPT_TOKENS,
            "max_completion_tokens": E.EVAL_MAX_COMPLETION_TOKENS,
            "length_normalize": E.LENGTH_NORMALIZE_OPTION_LOGPROBS}


def run_unit(country: str, spec: dict, spec_sha: str, revision: str,
             cache_root: Path, run_id: str, repo: str, hub,
             code_revision: str, local_dir: Path, production_scorer,
             reference_scorer, switchback_scorer, downloader=None,
             tol_logprob: float = 1e-6, tol_prob: float = 1e-4,
             force: bool = False) -> dict:
    """One scored unit end-to-end, with the gate BEFORE scoring and verified
    persistence AFTER. Any failure raises (the caller must halt the cohort).

    production_scorer(spec, model_name, adapter_active=True/False) scores via
    the production PEFT switch path (adapter on / disabled for switchback);
    reference_scorer(spec, model_name) is an INDEPENDENT loader of the SAME
    weights. Both get the same adapter dir resolved at `revision`.
    """
    country = country.upper()
    if country not in C.COHORT:
        raise ValueError(f"country {country!r} not in cohort")
    adapter_dir, source = resolve_adapter(country, revision, cache_root,
                                          downloader=downloader)
    adapter_sha = adapter_sha256(adapter_dir)
    model_name = f"{country}_adapter"

    # ---- 1. adapter-path gate: same weights, independent loader + switchback.
    # The switchback check compares base-path output AFTER disabling the
    # adapter against the base-path output BEFORE enabling it, so a separate
    # base_scorer captures the adapter-free state at both points.
    gate_spec = spec
    base_before = switchback_scorer(gate_spec, model_name)  # adapter not yet loaded
    prod = production_scorer(gate_spec, model_name, adapter_active=True)
    ref = reference_scorer(gate_spec, model_name)
    base_after = switchback_scorer(gate_spec, model_name)   # adapter disabled
    gate_ok, gate_report = run_adapter_path_gate(
        prod_scores=prod, ref_scores=ref, switchback_scores=None, spec=gate_spec,
        tol_logprob=tol_logprob, tol_prob=tol_prob, require_switchback=False)
    sb_ok, sb_report = compare_gate_scores(base_after, base_before, gate_spec,
                                           tol_logprob, tol_prob)
    gate_report["switchback_vs_base"] = sb_report
    gate_report["switchback_ok"] = bool(sb_ok)
    gate_report["gate_pass"] = bool(gate_ok and sb_ok)
    gate_report["adapter_sha256"] = adapter_sha
    gate_report["adapter_source"] = source
    if not gate_report["gate_pass"]:
        raise RuntimeError(
            f"{country}: adapter-path gate FAILED "
            f"({json.dumps(gate_report)}) — cohort scoring refused; tolerances "
            "are pinned and must not be widened to pass")

    # ---- 2. score (cache-aware)
    fingerprint = cache_fingerprint(spec["questions"], readout=_readout(),
                                    code_revision=code_revision,
                                    adapter_sha256=adapter_sha)
    df, meta = (None, {"valid": False})
    if not force:
        df, meta = load_cached_scores(cache_root, model_name, spec["questions"],
                                      fingerprint)
        if not meta["valid"]:
            print(f"  {model_name}: cache rejected — {meta['reason']}; rescoring")
    if df is None:
        df = production_scorer(spec, model_name, adapter_active=True)
        df["option_code"] = df["option_code"].astype(str)
        reason = validate_scored_frame(df, spec["questions"])
        if reason:
            raise AssertionError(f"{model_name}: scored output invalid: {reason}")
        save_cached_scores(cache_root, model_name, df, fingerprint=fingerprint,
                           code_revision=code_revision, adapter_sha256=adapter_sha)

    # ---- 3. persist verified
    df = df.copy()
    df["run_id"] = run_id
    df["adapter_revision"] = revision
    persisted = persist_unit_scores(
        scores=df, model_name=model_name, run_id=run_id, repo=repo, hub=hub,
        adapter_sha256=adapter_sha, code_revision=code_revision,
        local_dir=local_dir, spec_sha=spec_sha, adapter_revision=revision)
    return {"gate": gate_report, "cached": meta["valid"],
            "adapter_source": source, "persisted": persisted}


def run_cohort(countries: list[str], spec: dict, gate_marker_path: Path | None,
               cache_root: Path, run_id: str, repo: str, hub,
               code_revision: str, local_dir: Path, downloader=None,
               production_scorer=None, reference_scorer=None,
               switchback_scorer=None, tol_logprob: float = 1e-6,
               tol_prob: float = 1e-4, force: bool = False) -> list[dict]:
    """Score adapters country by country. GPU-launch block: refuses to start
    unless an adapter-path gate marker exists (written by the gate exercise).
    Halts at the first failed unit (exception propagates)."""
    if gate_marker_path is None or not Path(gate_marker_path).exists():
        raise RuntimeError(
            "adapter-path gate marker missing: the GPU cohort launch stays "
            "BLOCKED until run_adapter_path_gate has been exercised on the "
            "real weights (parent decision 2026-10-11)")
    marker = json.loads(Path(gate_marker_path).read_text())
    if not marker.get("gate_pass"):
        raise RuntimeError("adapter-path gate marker says gate_pass=false")

    from build_scoring_spec import spec_sha256
    spec_sha = spec_sha256(spec)
    results = []
    for cc in countries:
        results.append(run_unit(
            country=cc, spec=spec, spec_sha=spec_sha, revision=require_revision(None),
            cache_root=cache_root, run_id=run_id, repo=repo, hub=hub,
            code_revision=code_revision, local_dir=local_dir,
            production_scorer=production_scorer, reference_scorer=reference_scorer,
            switchback_scorer=switchback_scorer, downloader=downloader,
            tol_logprob=tol_logprob, tol_prob=tol_prob, force=force))
    return results
