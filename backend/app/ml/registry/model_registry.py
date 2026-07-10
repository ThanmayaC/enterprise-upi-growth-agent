"""Enterprise model registry — versioned artifacts with full lineage.

The registry is a JSON document (``artifacts/registry.json``) plus one
joblib bundle per model version (``artifacts/models/<name>_v<NNN>.joblib``).

Tracked per version:
    name, version, training date, task, feature list, evaluation metrics,
    status (``active`` / ``archived``), description, artifact path.

Rules:
    - Registering a new version archives the previous active one — exactly
      one active version per model name.
    - A bundle is self-contained: estimator, fitted feature transformer,
      feature names, label vocabulary, and training metadata travel
      together, so the prediction engine can serve any registered model
      without reconstructing preprocessing.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib

from app.ml import config


@dataclass
class ModelRecord:
    """One registered model version (a row of the registry)."""

    name: str
    version: int
    task: str
    trained_at: str
    features: list[str]
    metrics: dict[str, Any]
    status: str
    description: str
    artifact: str
    extras: dict[str, Any] = field(default_factory=dict)


class ModelRegistry:
    """JSON-backed registry with joblib persistence for model bundles."""

    def __init__(self, registry_path: Path | None = None,
                 models_dir: Path | None = None) -> None:
        self._path = registry_path or config.REGISTRY_PATH
        self._models_dir = models_dir or config.MODELS_DIR
        config.ensure_dirs()

    # ------------------------------------------------------------------
    # Persistence primitives
    # ------------------------------------------------------------------
    def _read(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        return json.loads(self._path.read_text(encoding="utf-8"))

    def _write(self, records: list[dict[str, Any]]) -> None:
        self._path.write_text(
            json.dumps(records, indent=2, default=str), encoding="utf-8"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def register(
        self,
        *,
        name: str,
        task: str,
        bundle: dict[str, Any],
        features: list[str],
        metrics: dict[str, Any],
        description: str,
    ) -> ModelRecord:
        """Persist a bundle, version it, activate it, archive the old one."""

        records = self._read()
        prior = [r for r in records if r["name"] == name]
        version = 1 + max((r["version"] for r in prior), default=0)
        artifact = self._models_dir / f"{name}_v{version:03d}.joblib"
        joblib.dump(bundle, artifact)

        for r in records:
            if r["name"] == name and r["status"] == "active":
                r["status"] = "archived"

        record = ModelRecord(
            name=name,
            version=version,
            task=task,
            trained_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            features=features,
            metrics=metrics,
            status="active",
            description=description,
            artifact=str(artifact),
        )
        records.append(asdict(record))
        self._write(records)
        return record

    def get_active(self, name: str) -> ModelRecord:
        """Return the active record for ``name`` (raises if none)."""

        for r in self._read():
            if r["name"] == name and r["status"] == "active":
                return ModelRecord(**r)
        raise KeyError(f"no active model registered under {name!r}")

    def load_active(self, name: str) -> tuple[ModelRecord, dict[str, Any]]:
        """Return (record, bundle) for the active version of ``name``."""

        record = self.get_active(name)
        bundle = joblib.load(record.artifact)
        return record, bundle

    def list_models(self) -> list[ModelRecord]:
        """All registry rows, newest first."""

        rows = [ModelRecord(**r) for r in self._read()]
        return sorted(rows, key=lambda r: (r.name, -r.version))
