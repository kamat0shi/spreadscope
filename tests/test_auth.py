from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)


def test_register_success():
    r = client.post("/api/auth/register", json={"username": "testuser1", "password": "pass123"})
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_register_duplicate():
    client.post("/api/auth/register", json={"username": "dupuser", "password": "pass"})
    r = client.post("/api/auth/register", json={"username": "dupuser", "password": "pass"})
    assert r.status_code == 409


def test_register_short_username():
    r = client.post("/api/auth/register", json={"username": "ab", "password": "pass123"})
    assert r.status_code == 422


def test_login_success():
    client.post("/api/auth/register", json={"username": "loginuser", "password": "pass123"})
    r = client.post("/api/auth/login", json={"username": "loginuser", "password": "pass123"})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_login_wrong_password():
    client.post("/api/auth/register", json={"username": "wpuser", "password": "correct"})
    r = client.post("/api/auth/login", json={"username": "wpuser", "password": "wrong"})
    assert r.status_code == 401


def test_login_nonexistent_user():
    r = client.post("/api/auth/login", json={"username": "noone", "password": "pass"})
    assert r.status_code == 401


def test_watchlist_requires_auth():
    r = client.get("/api/watchlist")
    assert r.status_code == 403


def test_watchlist_crud():
    # регистрируемся и получаем токен
    r = client.post("/api/auth/register", json={"username": "wluser", "password": "pass123"})
    token = r.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    # добавляем пару
    r = client.post("/api/watchlist", json={"symbol": "BTC_USDT"}, headers=h)
    assert r.status_code == 200
    assert r.json()["symbol"] == "BTC_USDT"

    # получаем список
    r = client.get("/api/watchlist", headers=h)
    assert r.status_code == 200
    assert r.json()["count"] == 1
    assert r.json()["items"][0]["symbol"] == "BTC_USDT"

    # дубликат
    r = client.post("/api/watchlist", json={"symbol": "BTC_USDT"}, headers=h)
    assert r.status_code == 409

    # удаляем
    r = client.delete("/api/watchlist/BTC_USDT", headers=h)
    assert r.status_code == 200

    # проверяем что пусто
    r = client.get("/api/watchlist", headers=h)
    assert r.json()["count"] == 0


def test_watchlist_delete_nonexistent():
    r = client.post("/api/auth/register", json={"username": "wluser2", "password": "pass123"})
    token = r.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    r = client.delete("/api/watchlist/NONEXISTENT", headers=h)
    assert r.status_code == 404
