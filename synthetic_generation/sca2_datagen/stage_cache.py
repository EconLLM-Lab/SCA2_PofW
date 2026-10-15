"""Append-only JSONL cache of finished generation requests.

A long generation run (facets -> scenario batches -> triplets) used to keep every
result in memory until the end of its stage, so a killed process lost all of it.
Each finished request is now appended here (flushed and fsynced) and looked up
before a request is sent, so a rerun with the same cache pays only for missing work.

Keys are tuples serialized as JSON lists:
  ("facets", dim)                          -> list[str]
  ("scenarios", dim, facet, batch_index)   -> list[str]
  ("triplet", dim, sha1(scenario prompt))  -> {"response_a", "response_b", "reasoning"}

Only successful results are stored. A torn final line (process killed mid-write)
is ignored on load.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)
_OPEN: dict[str, "StageCache"] = {}


def prompt_key(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


class StageCache:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._data: dict[str, Any] = {}
        if self.path.is_file():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                self._data[json.dumps(rec["key"])] = rec["value"]

    def __len__(self) -> int:
        return len(self._data)

    def get(self, key: tuple) -> Any:
        return self._data.get(json.dumps(list(key)))

    def put(self, key: tuple, value: Any) -> None:
        k = json.dumps(list(key))
        self._data[k] = value
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"key": list(key), "value": value}, ensure_ascii=False) + "\n")
            fh.flush()
            os.fsync(fh.fileno())


def for_config(config: Any) -> StageCache | None:
    """The shared cache for config.stage_cache_path, or None when caching is off."""
    path = getattr(config, "stage_cache_path", None)
    if not path:
        return None
    path = str(Path(path).resolve())
    if path not in _OPEN or not Path(path).exists():
        _OPEN[path] = StageCache(path)
        if len(_OPEN[path]):
            LOGGER.info("Stage cache %s: %d finished requests will be reused", path, len(_OPEN[path]))
    return _OPEN[path]
