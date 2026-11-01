"""Data access and fraud analytics, independent of the HTTP layer."""
from functools import lru_cache
from pathlib import Path
from typing import Literal

import pandas as pd
from pydantic import BaseModel
from sklearn.ensemble import RandomForestClassifier

DATA_PATH = Path(__file__).resolve().parent / "data" / "credit_card_fraud_10k.csv"

FEATURE_COLS = [
    "amount",
    "transaction_hour",
    "foreign_transaction",
    "location_mismatch",
    "device_trust_score",
    "velocity_last_24h",
    "cardholder_age",
]

MIN_ROWS_FOR_FEATURES = 20
# The free plan has 0.1 CPU, and the forest is refit whenever the filters change.
RF_TREES = 50


class Filters(BaseModel):
    """Every field defaults to "no restriction"."""

    amount: tuple[float, float] | None = None
    hour: tuple[int, int] | None = None
    categories: list[str] | None = None
    foreign: Literal["ALL", "YES", "NO"] = "ALL"
    mismatch: Literal["ALL", "YES", "NO"] = "ALL"
    trust: tuple[int, int] | None = None
    velocity: tuple[int, int] | None = None
    age: tuple[int, int] | None = None
    fraud: Literal["ALL", "FRAUD_ONLY", "LEGIT_ONLY"] = "ALL"


@lru_cache(maxsize=1)
def load_data() -> pd.DataFrame:
    return pd.read_csv(DATA_PATH)


def get_meta(df: pd.DataFrame) -> dict:
    def int_bounds(col: str) -> list[int]:
        return [int(df[col].min()), int(df[col].max())]

    return {
        "row_count": len(df),
        "amount": [float(df["amount"].min()), float(df["amount"].max())],
        "trust": int_bounds("device_trust_score"),
        "velocity": int_bounds("velocity_last_24h"),
        "age": int_bounds("cardholder_age"),
        "categories": sorted(df["merchant_category"].unique().tolist()),
    }


def apply_filters(df: pd.DataFrame, f: Filters) -> pd.DataFrame:
    mask = pd.Series(True, index=df.index)
    for col, bounds in (
        ("amount", f.amount),
        ("transaction_hour", f.hour),
        ("device_trust_score", f.trust),
        ("velocity_last_24h", f.velocity),
        ("cardholder_age", f.age),
    ):
        if bounds is not None:
            mask &= df[col].between(*bounds)
    if f.categories is not None:
        mask &= df["merchant_category"].isin(f.categories)
    if f.foreign != "ALL":
        mask &= df["foreign_transaction"] == (1 if f.foreign == "YES" else 0)
    if f.mismatch != "ALL":
        mask &= df["location_mismatch"] == (1 if f.mismatch == "YES" else 0)
    if f.fraud != "ALL":
        mask &= df["is_fraud"] == (1 if f.fraud == "FRAUD_ONLY" else 0)
    return df[mask]


def _as_rows(series: pd.Series) -> list[dict]:
    return [{"feature": k, "value": float(v)} for k, v in series.items()]


def predictive_features(filtered: pd.DataFrame) -> dict:
    """Correlation with is_fraud and RandomForest importances for a filtered set."""
    y = filtered["is_fraud"]
    if len(filtered) < MIN_ROWS_FOR_FEATURES or y.nunique() < 2:
        return {"sufficient": False, "correlation": [], "importance": []}

    dummies = pd.get_dummies(filtered["merchant_category"], prefix="cat")
    X = pd.concat([filtered[FEATURE_COLS], dummies], axis=1)

    # A filter can make a column constant, which leaves its correlation undefined.
    corr = X.assign(is_fraud=y).corr(numeric_only=True)["is_fraud"].drop("is_fraud").dropna()
    corr = corr.sort_values(key=lambda s: s.abs())

    rf = RandomForestClassifier(
        n_estimators=RF_TREES, random_state=42, class_weight="balanced", n_jobs=1
    )
    rf.fit(X, y)
    importance = pd.Series(rf.feature_importances_, index=X.columns).sort_values()

    return {"sufficient": True, "correlation": _as_rows(corr), "importance": _as_rows(importance)}
