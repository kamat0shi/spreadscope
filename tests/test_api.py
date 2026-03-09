from fastapi.testclient import TestClient
from backend.app import app


client = TestClient(app)


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "exchanges_enabled" in data
    assert "quotes_cached" in data


def test_converter_rates_shape():
    r = client.get("/api/converter/rates")
    assert r.status_code == 200
    data = r.json()
    assert "base" in data
    assert "rates" in data
    assert isinstance(data["rates"], dict)


def test_spreads_endpoint_returns_json():
    r = client.get("/api/spreads?limit=5")
    assert r.status_code == 200
    data = r.json()
    assert "records" in data
    assert isinstance(data["records"], list)