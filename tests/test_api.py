import pandas as pd
import pytest
from fastapi.testclient import TestClient

from analytics import load_data
from main import app

client = TestClient(app)


def test_health_reports_status_and_environment():
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["environment"] == "local"
    assert body["rows"] == 10_000


def test_meta_matches_dataset():
    df = load_data()
    body = client.get("/meta").json()
    assert body["amount"] == [df["amount"].min(), df["amount"].max()]
    assert body["categories"] == sorted(df["merchant_category"].unique())


def test_transactions_without_filters_returns_all_rows():
    body = client.post("/transactions", json={}).json()
    assert len(body["data"]) == 10_000
    assert "is_fraud" in body["columns"]


def test_transactions_apply_every_filter():
    payload = {
        "amount": [10, 500],
        "hour": [1, 20],
        "categories": ["Travel", "Food"],
        "foreign": "YES",
        "mismatch": "NO",
        "trust": [10, 90],
        "velocity": [0, 8],
        "age": [20, 70],
        "fraud": "LEGIT_ONLY",
    }
    body = client.post("/transactions", json=payload).json()
    rows = pd.DataFrame(body["data"], columns=body["columns"])
    df = load_data()
    expected = df[
        df["amount"].between(10, 500)
        & df["transaction_hour"].between(1, 20)
        & df["merchant_category"].isin(["Travel", "Food"])
        & (df["foreign_transaction"] == 1)
        & (df["location_mismatch"] == 0)
        & df["device_trust_score"].between(10, 90)
        & df["velocity_last_24h"].between(0, 8)
        & df["cardholder_age"].between(20, 70)
        & (df["is_fraud"] == 0)
    ]
    assert len(expected) > 0
    assert rows["transaction_id"].tolist() == expected["transaction_id"].tolist()


def test_invalid_filter_is_rejected():
    assert client.post("/transactions", json={"fraud": "MAYBE"}).status_code == 422


def test_predictive_features_ranked_by_strength():
    body = client.post("/predictive-features", json={}).json()
    assert body["sufficient"] is True
    importance = [row["value"] for row in body["importance"]]
    assert importance == sorted(importance)
    strength = [abs(row["value"]) for row in body["correlation"]]
    assert strength == sorted(strength)


def test_predictive_features_single_class_is_insufficient():
    body = client.post("/predictive-features", json={"fraud": "FRAUD_ONLY"}).json()
    assert body == {"sufficient": False, "correlation": [], "importance": []}


@pytest.mark.parametrize("flag", ["foreign", "mismatch"])
def test_constant_column_does_not_break_json(flag):
    response = client.post("/predictive-features", json={flag: "YES"})
    assert response.status_code == 200
