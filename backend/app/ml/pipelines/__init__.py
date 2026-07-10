"""Training pipeline: train -> validate -> evaluate -> save -> register."""

from app.ml.pipelines.training_pipeline import TrainingPipeline

__all__ = ["TrainingPipeline"]
