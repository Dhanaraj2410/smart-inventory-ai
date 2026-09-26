"""Thin orchestration layer over the trained ML models (ml/prediction/predict.py).
Kept separate from apps.predictions.services so ml/ stays framework-agnostic
and could, in principle, be reused outside Django (e.g. a batch job)."""
from ml.prediction.predict import predict_stockout_risk, predict_demand

__all__ = ["predict_stockout_risk", "predict_demand"]
