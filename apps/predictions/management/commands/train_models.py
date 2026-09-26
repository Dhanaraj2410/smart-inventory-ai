"""
Management command: python manage.py train_models

Runs the full ML training pipeline (stockout classifier + demand
forecasting regressor) synchronously against the current database, prints
the evaluation metrics for every candidate model, and records them in
ModelPerformance so the /predictions/performance/ page reflects real
results (never hard-coded).
"""
import json
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Train the stockout classification and demand forecasting models."

    def handle(self, *args, **options):
        from ml.training.train_stockout_model import train_stockout_model
        from ml.training.train_demand_model import train_demand_model

        self.stdout.write("Training stockout risk classifier...")
        stockout_summary = train_stockout_model(persist_metrics=True)
        self.stdout.write(self.style.SUCCESS(
            f"  Best model: {stockout_summary['best_model']} "
            f"(source: {stockout_summary['data_source']}, samples: {stockout_summary['training_samples']})"
        ))
        self.stdout.write(json.dumps(stockout_summary["all_results"], indent=2))

        self.stdout.write("\nTraining demand forecasting regressor...")
        demand_summary = train_demand_model(persist_metrics=True)
        self.stdout.write(self.style.SUCCESS(
            f"  Best model: {demand_summary['best_model']} "
            f"(source: {demand_summary['data_source']}, samples: {demand_summary['training_samples']})"
        ))
        self.stdout.write(json.dumps(demand_summary["all_results"], indent=2))

        self.stdout.write(self.style.SUCCESS("\nDone. Models saved to ml/models/."))
