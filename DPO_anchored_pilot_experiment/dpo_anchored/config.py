"""Shared configuration for the anchored pilot DPO experiment."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


COUNTRIES: tuple[str, ...] = ("ARG", "SWE", "USA")
MODEL_NAME = "meta-llama/Llama-3.1-8B-Instruct"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def experiment_root() -> Path:
    return Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ExperimentConfig:
    """Paths and hyperparameters shared by preparation, training, and evaluation."""

    repo_root: Path = repo_root()
    output_root: Path = experiment_root() / "outputs" / "anchored_pilot_v1_dpo"
    model_name: str = MODEL_NAME
    train_frac: float = 0.80
    seed: int = 42
    beta: float = 0.1
    max_prompt_tokens: int = 256
    max_completion_tokens: int = 256
    max_length: int = 768
    num_train_epochs: int = 1
    per_device_train_batch_size: int = 1
    gradient_accumulation_steps: int = 16
    learning_rate: float = 1e-4
    warmup_ratio: float = 0.03

    @property
    def source_dir(self) -> Path:
        return self.repo_root / "synthetic_generation" / "outputs" / "anchored_pilot_v1"

    @property
    def splits_dir(self) -> Path:
        return self.output_root / "splits"

    @property
    def ref_dir(self) -> Path:
        return self.output_root / "with_ref"

    @property
    def adapters_dir(self) -> Path:
        return self.output_root / "adapters"

    @property
    def results_dir(self) -> Path:
        return self.output_root / "results"

    @property
    def reports_dir(self) -> Path:
        return self.output_root / "reports"

    def source_file(self, country: str) -> Path:
        self.require_country(country)
        return self.source_dir / f"D_syn_{country}_172.jsonl"

    def train_file(self, country: str) -> Path:
        self.require_country(country)
        return self.splits_dir / f"D_syn_{country}_train.jsonl"

    def eval_file(self, country: str) -> Path:
        self.require_country(country)
        return self.splits_dir / f"D_syn_{country}_eval.jsonl"

    def train_with_ref_file(self, country: str) -> Path:
        self.require_country(country)
        return self.ref_dir / f"D_syn_{country}_train_with_ref.jsonl"

    def adapter_dir(self, country: str) -> Path:
        self.require_country(country)
        return self.adapters_dir / f"dpo_qlora_adapter_llama3_{country}"

    def adapter_result_file(self, adapter_country: str) -> Path:
        self.require_country(adapter_country)
        return self.results_dir / f"reward_recovery_{adapter_country}_adapter.csv"

    def require_country(self, country: str) -> None:
        if country not in COUNTRIES:
            raise ValueError(f"Unknown country {country!r}; expected one of {COUNTRIES}")

    def ensure_output_dirs(self) -> None:
        for path in (
            self.splits_dir,
            self.ref_dir,
            self.adapters_dir,
            self.results_dir,
            self.reports_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)
