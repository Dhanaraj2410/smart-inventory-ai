"""
Shared feature engineering for stockout classification and demand forecasting.

CRITICAL: every function here must be usable both at training time (on
historical data) and at prediction time (on "today"), using only information
that would actually be available at the moment of prediction. No leakage.
"""
import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "day", "week", "month", "day_of_week", "is_weekend",
    "rolling_7_day_sales", "rolling_14_day_sales", "rolling_30_day_sales",
    "average_daily_sales", "sales_growth", "sales_volatility",
    "lag_1", "lag_7", "lag_14",
    "current_stock", "supplier_lead_time", "safety_stock", "reorder_point",
    "stock_to_demand_ratio",
]

CLASSIFICATION_TARGET = "stockout_within_horizon"
REGRESSION_TARGET = "quantity_sold"


def build_daily_sales_frame(sales_qs, product):
    """Turn sales rows (single product) into a complete daily time series
    (missing days filled with 0 units sold).

    `sales_qs` may be a Django QuerySet of SalesRecord (in which case
    `.values("date", "quantity_sold")` is used), or a plain iterable of
    dicts/records already shaped like `{"date": ..., "quantity_sold": ...}`
    (used by the CSV-based training/prediction fallback so this module has
    no hard Django dependency)."""
    records = sales_qs.values("date", "quantity_sold") if hasattr(sales_qs, "values") else sales_qs
    df = pd.DataFrame.from_records(records)
    if df.empty:
        return pd.DataFrame(columns=["date", "quantity_sold"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.groupby("date", as_index=False)["quantity_sold"].sum()
    full_range = pd.date_range(df["date"].min(), df["date"].max(), freq="D")
    df = df.set_index("date").reindex(full_range, fill_value=0).rename_axis("date").reset_index()
    return df


def add_calendar_features(df, date_col="date"):
    df["day"] = df[date_col].dt.day
    df["week"] = df[date_col].dt.isocalendar().week.astype(int)
    df["month"] = df[date_col].dt.month
    df["day_of_week"] = df[date_col].dt.dayofweek
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
    return df


def add_rolling_and_lag_features(df, qty_col="quantity_sold"):
    df = df.sort_values("date").reset_index(drop=True)
    df["rolling_7_day_sales"] = df[qty_col].rolling(7, min_periods=1).sum().shift(1).fillna(0)
    df["rolling_14_day_sales"] = df[qty_col].rolling(14, min_periods=1).sum().shift(1).fillna(0)
    df["rolling_30_day_sales"] = df[qty_col].rolling(30, min_periods=1).sum().shift(1).fillna(0)
    df["average_daily_sales"] = df[qty_col].expanding(min_periods=1).mean().shift(1).fillna(0)

    prev_week = df[qty_col].rolling(7, min_periods=1).sum().shift(8).fillna(0)
    this_week = df["rolling_7_day_sales"]
    df["sales_growth"] = np.where(prev_week > 0, (this_week - prev_week) / prev_week, 0.0)

    df["sales_volatility"] = df[qty_col].rolling(14, min_periods=2).std().shift(1).fillna(0)

    for lag in (1, 7, 14):
        df[f"lag_{lag}"] = df[qty_col].shift(lag).fillna(0)

    return df


def add_inventory_features(df, current_stock, supplier_lead_time, safety_stock):
    """Attach point-in-time inventory attributes. In training these are
    approximated as constant (current values) since we don't have a full
    historical stock ledger; this mirrors typical practical setups where
    inventory reference data is refreshed periodically rather than per-day."""
    avg_daily = df["average_daily_sales"].replace(0, np.nan)
    df["current_stock"] = current_stock
    df["supplier_lead_time"] = supplier_lead_time
    df["safety_stock"] = safety_stock
    df["reorder_point"] = df["average_daily_sales"] * supplier_lead_time + safety_stock
    df["stock_to_demand_ratio"] = (current_stock / avg_daily).replace([np.inf, -np.inf], np.nan).fillna(
        current_stock + 1)
    return df


def add_stockout_label(df, current_stock, horizon_days=7):
    """Label each historical day: would the *then-current* stock trajectory
    have led to a stockout within `horizon_days`, given the demand that
    actually followed? Uses forward-looking cumulative demand for the label
    only (labels are allowed to look forward; features are not)."""
    future_sum = df["quantity_sold"][::-1].rolling(horizon_days, min_periods=1).sum()[::-1].shift(-0)
    # cumulative demand over the next horizon_days, evaluated from day t+1
    future_demand = df["quantity_sold"].shift(-1).rolling(horizon_days, min_periods=1).sum().shift(-(horizon_days - 1))
    future_demand = future_demand.fillna(df["quantity_sold"].rolling(horizon_days, min_periods=1).sum())
    df[CLASSIFICATION_TARGET] = (future_demand >= current_stock).astype(int)
    return df


def build_training_frame(sales_qs, product, horizon_days=7):
    df = build_daily_sales_frame(sales_qs, product)
    if len(df) < 15:
        return None
    df = add_calendar_features(df)
    df = add_rolling_and_lag_features(df)
    df = add_inventory_features(df, product.current_stock, product.supplier_lead_time, product.safety_stock)
    df = add_stockout_label(df, product.current_stock, horizon_days)
    df = df.dropna(subset=FEATURE_COLUMNS)
    return df


def build_prediction_row(sales_qs, product):
    """Build the single feature row representing 'today' for a product,
    ready to feed into a trained model."""
    df = build_daily_sales_frame(sales_qs, product)
    if df.empty:
        return None
    df = add_calendar_features(df)
    df = add_rolling_and_lag_features(df)
    df = add_inventory_features(df, product.current_stock, product.supplier_lead_time, product.safety_stock)
    row = df.iloc[[-1]].copy()
    # Roll calendar features forward to "tomorrow" since that's the prediction target
    return row[FEATURE_COLUMNS]
