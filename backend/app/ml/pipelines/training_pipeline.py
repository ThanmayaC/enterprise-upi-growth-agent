"""Generic training pipeline: train → validate → evaluate → save → register.

One pipeline serves every :class:`TrainerSpec`; the task type selects the
branch:

    regression / classification
        stratified-where-possible train/test split → fit → held-out
        evaluation → refit on the full dataset for serving.
    clustering
        standard-scale → fit K-means → silhouette / Davies-Bouldin →
        rank centroids on the spec's ordering column → business labels.
    anomaly
        standard-scale → fit IsolationForest → score distribution captured
        for confidence normalization and anomaly typing at prediction time.

Every run produces a self-contained serving bundle (estimator + fitted
transformer + metadata) and a registry record with metrics — the model
version is the atomic unit of deployment.

Run all models from the backend directory:

    python -m app.ml.pipelines.training_pipeline
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from app.ml import config
from app.ml.evaluation.metrics import (
    evaluate_classification,
    evaluate_clustering,
    evaluate_regression,
    save_metrics,
)
from app.ml.models.estimators import make_estimator
from app.ml.registry.model_registry import ModelRecord, ModelRegistry
from app.ml.training.trainers import (
    TRAINER_SPECS,
    BuilderSet,
    PreparedData,
    TrainerSpec,
)


class TrainingPipeline:
    """Reusable trainer for any spec in the catalog."""

    def __init__(self, registry: ModelRegistry | None = None) -> None:
        self._registry = registry or ModelRegistry()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run(self, spec: TrainerSpec, builders: BuilderSet) -> ModelRecord:
        """Train, evaluate, persist, and register one model."""

        started = time.monotonic()
        prepared = spec.prepare(builders)
        x = prepared.transformer.fit_transform(prepared.dataset.frame)

        if spec.task in ("regression", "classification"):
            bundle, metrics = self._train_supervised(spec, prepared, x)
        elif spec.task == "clustering":
            bundle, metrics = self._train_clustering(spec, prepared, x)
        else:
            bundle, metrics = self._train_anomaly(spec, prepared, x)

        metrics["rows"] = int(len(x))
        metrics["features"] = int(x.shape[1])
        metrics["training_seconds"] = round(time.monotonic() - started, 2)

        record = self._registry.register(
            name=spec.name,
            task=spec.task,
            bundle=bundle,
            features=list(prepared.transformer.feature_names_),
            metrics=metrics,
            description=spec.description,
        )
        save_metrics(spec.name, record.version, metrics)
        return record

    def run_all(self, builders: BuilderSet) -> list[ModelRecord]:
        """Train the entire catalog, in order."""

        return [self.run(spec, builders) for spec in TRAINER_SPECS]

    # ------------------------------------------------------------------
    # Task branches
    # ------------------------------------------------------------------
    def _train_supervised(
        self, spec: TrainerSpec, prepared: PreparedData, x: pd.DataFrame
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        y = prepared.y
        assert y is not None, f"{spec.name}: supervised task requires y"
        y = y.reset_index(drop=True)
        x = x.reset_index(drop=True)

        stratify = None
        if spec.task == "classification" and y.value_counts().min() >= 2:
            stratify = y
        x_train, x_test, y_train, y_test = train_test_split(
            x, y, test_size=config.TEST_SIZE,
            random_state=config.RANDOM_STATE, stratify=stratify,
        )

        model = make_estimator(spec.name, spec.task)
        model.fit(x_train, y_train)

        if spec.task == "classification":
            proba = model.predict_proba(x_test)
            metrics = evaluate_classification(
                y_test.to_numpy(), model.predict(x_test), proba
            )
        else:
            metrics = evaluate_regression(
                y_test.to_numpy(), model.predict(x_test)
            )
        metrics["holdout_rows"] = int(len(x_test))

        # Refit on the full dataset — the served model uses all evidence;
        # the recorded metrics remain the honest held-out numbers above.
        model = make_estimator(spec.name, spec.task)
        model.fit(x, y)

        bundle = {
            "task": spec.task,
            "estimator": model,
            "transformer": prepared.transformer,
            "feature_names": list(prepared.transformer.feature_names_),
            "classes": [str(c) for c in getattr(model, "classes_", [])],
        }
        return bundle, metrics

    def _train_clustering(
        self, spec: TrainerSpec, prepared: PreparedData, x: pd.DataFrame
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        scaler = StandardScaler()
        x_scaled = scaler.fit_transform(x)

        model = make_estimator(spec.name, spec.task)
        clusters = model.fit_predict(x_scaled)
        metrics = evaluate_clustering(x_scaled, clusters)

        # Map raw cluster ids to business segments by ranking each cluster's
        # mean of the ordering column (worst → best, e.g. growth/activity).
        order_col = prepared.order_column or ""
        order_values = pd.to_numeric(
            prepared.dataset.frame.reset_index(drop=True).get(
                order_col, pd.Series(np.zeros(len(x)))
            ),
            errors="coerce",
        ).fillna(0.0)
        if order_col and order_col in x.columns:
            order_values = x[order_col].reset_index(drop=True)
        cluster_rank = (
            pd.DataFrame({"cluster": clusters, "order": order_values})
            .groupby("cluster")["order"].mean().sort_values()
        )
        labels = prepared.segment_labels or [
            f"Segment {i}" for i in range(len(cluster_rank))
        ]
        segment_map = {
            int(cluster): labels[min(rank, len(labels) - 1)]
            for rank, cluster in enumerate(cluster_rank.index)
        }
        metrics["segment_sizes"] = {
            segment_map[int(c)]: int(n)
            for c, n in pd.Series(clusters).value_counts().items()
        }

        bundle = {
            "task": spec.task,
            "estimator": model,
            "scaler": scaler,
            "transformer": prepared.transformer,
            "feature_names": list(prepared.transformer.feature_names_),
            "segment_map": segment_map,
        }
        return bundle, metrics

    def _train_anomaly(
        self, spec: TrainerSpec, prepared: PreparedData, x: pd.DataFrame
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        scaler = StandardScaler()
        x_scaled = scaler.fit_transform(x)

        model = make_estimator(spec.name, spec.task)
        model.fit(x_scaled)
        scores = model.decision_function(x_scaled)
        flags = model.predict(x_scaled)  # -1 anomaly / 1 normal

        metrics = {
            "observations": int(len(x)),
            "anomalies_flagged": int((flags == -1).sum()),
            "anomaly_rate": round(float((flags == -1).mean()), 4),
            "score_min": round(float(scores.min()), 4),
            "score_max": round(float(scores.max()), 4),
        }

        # Feature medians support anomaly-typing and explanations at
        # prediction time (which signal deviates most).
        medians = {c: float(x[c].median()) for c in x.columns}
        bundle = {
            "task": spec.task,
            "estimator": model,
            "scaler": scaler,
            "transformer": prepared.transformer,
            "feature_names": list(prepared.transformer.feature_names_),
            "score_range": (float(scores.min()), float(scores.max())),
            "feature_medians": medians,
        }
        return bundle, metrics


def main() -> None:
    """Train the full catalog against the live database and print a summary."""

    from app.db.database import SessionLocal
    from app.ml.datasets.data_provider import MLDataProvider

    config.ensure_dirs()
    with SessionLocal() as session:
        builders = BuilderSet.from_provider(MLDataProvider(session))
        pipeline = TrainingPipeline()
        print(f"Training {len(TRAINER_SPECS)} models ...")
        for spec in TRAINER_SPECS:
            record = pipeline.run(spec, builders)
            headline = {
                k: v for k, v in record.metrics.items()
                if k in ("accuracy", "f1", "roc_auc", "rmse", "mae", "r2",
                         "silhouette", "davies_bouldin", "anomalies_flagged",
                         "rows")
            }
            print(f"  [OK] {record.name:28s} v{record.version:03d}  {headline}")
    print("done.")


if __name__ == "__main__":
    main()
