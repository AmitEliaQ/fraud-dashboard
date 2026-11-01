"""Fraud analytics API consumed by the Streamlit frontend."""
import json
import os
from functools import lru_cache

from fastapi import FastAPI

from analytics import Filters, apply_filters, get_meta, load_data, predictive_features

APP_ENV = os.environ.get("APP_ENV", "local")

app = FastAPI(title="Fraud Dashboard API")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "environment": APP_ENV, "rows": len(load_data())}


@app.get("/meta")
def meta() -> dict:
    return get_meta(load_data())


@app.post("/transactions")
def transactions(filters: Filters) -> dict:
    rows = apply_filters(load_data(), filters)
    return rows.to_dict(orient="split", index=False)


@lru_cache(maxsize=64)
def _cached_predictive_features(filters_json: str) -> dict:
    filters = Filters(**json.loads(filters_json))
    return predictive_features(apply_filters(load_data(), filters))


@app.post("/predictive-features")
def predictive(filters: Filters) -> dict:
    return _cached_predictive_features(filters.model_dump_json())
