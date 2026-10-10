"""Reproducible retrieval and grounded-answer evaluation."""

from irishclinicalrag.evaluation.dataset import build_evaluation_dataset
from irishclinicalrag.evaluation.models import EvaluationCase

__all__ = ["EvaluationCase", "build_evaluation_dataset"]
