"""Data validation & cleaning used before ML training."""
import numpy as np
import pandas as pd


def remove_duplicates(df, subset=None):
    before = len(df)
    df = df.drop_duplicates(subset=subset)
    return df, before - len(df)


def handle_missing_values(df, numeric_cols):
    report = {}
    for col in numeric_cols:
        if col not in df.columns:
            continue
        n_missing = df[col].isna().sum()
        if n_missing:
            median = df[col].median()
            df[col] = df[col].fillna(median)
            report[col] = int(n_missing)
    return df, report


def handle_outliers(df, col, method="iqr", factor=3.0):
    """Cap outliers rather than dropping rows, so we don't lose valid demand spikes
    entirely -- we just prevent a single bad data entry from dominating training."""
    if col not in df.columns or df[col].empty:
        return df, 0
    q1, q3 = df[col].quantile(0.25), df[col].quantile(0.75)
    iqr = q3 - q1
    lower, upper = q1 - factor * iqr, q3 + factor * iqr
    n_outliers = int(((df[col] < lower) | (df[col] > upper)).sum())
    df[col] = df[col].clip(lower=max(lower, 0), upper=upper if upper > 0 else df[col].max())
    return df, n_outliers


def validate_sales_dataframe(df):
    """Sanity checks used by the CSV upload endpoint before rows are trusted
    for ML training."""
    errors = []
    if df.empty:
        errors.append("Dataset is empty.")
        return errors
    if (df["quantity_sold"] < 0).any():
        errors.append("Found negative quantity_sold values.")
    if (df["unit_price"] < 0).any():
        errors.append("Found negative unit_price values.")
    if df["date"].isna().any():
        errors.append("Found rows with unparseable dates.")
    return errors
