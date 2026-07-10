"""Trainer catalog: one declarative spec per registered model."""

from app.ml.training.trainers import TRAINER_SPECS, BuilderSet, TrainerSpec

__all__ = ["TRAINER_SPECS", "BuilderSet", "TrainerSpec"]
