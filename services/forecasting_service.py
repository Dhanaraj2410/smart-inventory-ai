"""Re-exports the Django-aware forecasting logic so it lives under services/
as the spec's project structure expects, without duplicating the
implementation (which needs the ORM and lives in apps.forecasting)."""
from apps.forecasting.services import run_forecast, get_latest_forecast

__all__ = ["run_forecast", "get_latest_forecast"]
