"""
Integration tests for FinTrack API.
Uses an in-memory SQLite database — no side effects.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.main import app

# ── Test DB ───────────────────────────────────────────────────────────────────
TEST_DATABASE_URL = "sqlite:///./test_fintrack.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Patch the dependency
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Create tables ONCE at module level using the test engine
Base.metadata.create_all(bind=engine)

client = TestClient(app, raise_server_exceptions=True)


@pytest.fixture(autouse=True)
def reset_db():
    """Delete all rows between tests (tables persist, just clear data)."""
    yield
    # Teardown: clear all rows in reverse dependency order to respect FK constraints
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


# ── Helpers ────────────────────────────────────────────────────────────────────
def register_and_login(email="test@fintrack.dev", password="secret123"):
    client.post("/auth/register", json={"name": "Test User", "email": email, "password": password})
    r = client.post("/auth/login", json={"email": email, "password": password})
    return r.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


# ── Auth ───────────────────────────────────────────────────────────────────────
class TestAuth:
    def test_register_success(self):
        r = client.post(
            "/auth/register",
            json={"name": "Lucas", "email": "lucas@test.com", "password": "abc123"},
        )
        assert r.status_code == 201
        assert r.json()["email"] == "lucas@test.com"

    def test_register_duplicate_email(self):
        payload = {"name": "A", "email": "dup@test.com", "password": "abc123"}
        client.post("/auth/register", json=payload)
        r = client.post("/auth/register", json=payload)
        assert r.status_code == 409

    def test_register_weak_password(self):
        r = client.post(
            "/auth/register",
            json={"name": "A", "email": "x@x.com", "password": "123"},
        )
        assert r.status_code == 422

    def test_login_success(self):
        client.post("/auth/register", json={"name": "A", "email": "a@a.com", "password": "pass123"})
        r = client.post("/auth/login", json={"email": "a@a.com", "password": "pass123"})
        assert r.status_code == 200
        assert "access_token" in r.json()

    def test_login_wrong_password(self):
        client.post("/auth/register", json={"name": "A", "email": "b@b.com", "password": "pass123"})
        r = client.post("/auth/login", json={"email": "b@b.com", "password": "wrong"})
        assert r.status_code == 401

    def test_me_authenticated(self):
        token = register_and_login()
        r = client.get("/auth/me", headers=auth(token))
        assert r.status_code == 200
        assert r.json()["email"] == "test@fintrack.dev"

    def test_me_unauthenticated(self):
        r = client.get("/auth/me")
        assert r.status_code == 401


# ── Categories ─────────────────────────────────────────────────────────────────
class TestCategories:
    def test_create_category(self):
        token = register_and_login()
        r = client.post(
            "/categories/",
            json={"name": "Food", "type": "expense", "color": "#ef4444"},
            headers=auth(token),
        )
        assert r.status_code == 201
        assert r.json()["name"] == "Food"

    def test_duplicate_category(self):
        token = register_and_login()
        payload = {"name": "Food", "type": "expense"}
        client.post("/categories/", json=payload, headers=auth(token))
        r = client.post("/categories/", json=payload, headers=auth(token))
        assert r.status_code == 409

    def test_list_categories_filtered_by_type(self):
        token = register_and_login()
        client.post("/categories/", json={"name": "Salary", "type": "income"}, headers=auth(token))
        client.post("/categories/", json={"name": "Food", "type": "expense"}, headers=auth(token))
        r = client.get("/categories/?type=income", headers=auth(token))
        assert r.status_code == 200
        assert all(c["type"] == "income" for c in r.json())

    def test_delete_category_with_transactions_blocked(self):
        token = register_and_login()
        cat = client.post(
            "/categories/", json={"name": "Food", "type": "expense"}, headers=auth(token)
        ).json()
        client.post(
            "/transactions/",
            json={
                "type": "expense",
                "amount": 50.0,
                "description": "Lunch",
                "date": "2024-06-01T12:00:00",
                "category_id": cat["id"],
            },
            headers=auth(token),
        )
        r = client.delete(f"/categories/{cat['id']}", headers=auth(token))
        assert r.status_code == 409


# ── Transactions ───────────────────────────────────────────────────────────────
class TestTransactions:
    def test_create_income(self):
        token = register_and_login()
        r = client.post(
            "/transactions/",
            json={"type": "income", "amount": 5000.0, "description": "Salary", "date": "2024-06-01T00:00:00"},
            headers=auth(token),
        )
        assert r.status_code == 201
        assert r.json()["amount"] == 5000.0

    def test_negative_amount_rejected(self):
        token = register_and_login()
        r = client.post(
            "/transactions/",
            json={"type": "expense", "amount": -100, "description": "bad", "date": "2024-06-01T00:00:00"},
            headers=auth(token),
        )
        assert r.status_code == 422

    def test_category_type_mismatch_rejected(self):
        token = register_and_login()
        cat = client.post(
            "/categories/", json={"name": "Salary", "type": "income"}, headers=auth(token)
        ).json()
        r = client.post(
            "/transactions/",
            json={
                "type": "expense",
                "amount": 100,
                "description": "bad",
                "date": "2024-06-01T00:00:00",
                "category_id": cat["id"],
            },
            headers=auth(token),
        )
        assert r.status_code == 422

    def test_pagination(self):
        token = register_and_login()
        for i in range(5):
            client.post(
                "/transactions/",
                json={"type": "expense", "amount": 10, "description": f"tx{i}", "date": "2024-06-01T00:00:00"},
                headers=auth(token),
            )
        r = client.get("/transactions/?page=1&per_page=2", headers=auth(token))
        data = r.json()
        assert data["total"] == 5
        assert data["pages"] == 3
        assert len(data["items"]) == 2

    def test_description_search(self):
        token = register_and_login()
        client.post(
            "/transactions/",
            json={"type": "expense", "amount": 10, "description": "Netflix subscription", "date": "2024-06-01T00:00:00"},
            headers=auth(token),
        )
        client.post(
            "/transactions/",
            json={"type": "expense", "amount": 5, "description": "Coffee", "date": "2024-06-01T00:00:00"},
            headers=auth(token),
        )
        r = client.get("/transactions/?description=netflix", headers=auth(token))
        assert r.json()["total"] == 1

    def test_update_transaction(self):
        token = register_and_login()
        tx = client.post(
            "/transactions/",
            json={"type": "expense", "amount": 10, "description": "Old", "date": "2024-06-01T00:00:00"},
            headers=auth(token),
        ).json()
        r = client.patch(
            f"/transactions/{tx['id']}",
            json={"amount": 99.99},
            headers=auth(token),
        )
        assert r.status_code == 200
        assert r.json()["amount"] == 99.99

    def test_user_isolation(self):
        """User A cannot access User B's transactions."""
        token_a = register_and_login("a@a.com", "pass123")
        token_b = register_and_login("b@b.com", "pass123")
        tx = client.post(
            "/transactions/",
            json={"type": "expense", "amount": 100, "description": "Secret", "date": "2024-06-01T00:00:00"},
            headers=auth(token_a),
        ).json()
        r = client.get(f"/transactions/{tx['id']}", headers=auth(token_b))
        assert r.status_code == 404


# ── Reports ────────────────────────────────────────────────────────────────────
class TestReports:
    def _seed(self, token):
        cat = client.post(
            "/categories/",
            json={"name": "Food", "type": "expense", "budget": 500},
            headers=auth(token),
        ).json()
        client.post("/transactions/",
            json={"type": "income", "amount": 3000, "description": "Salary", "date": "2024-06-05T00:00:00"},
            headers=auth(token))
        client.post("/transactions/",
            json={"type": "expense", "amount": 200, "description": "Groceries",
                  "date": "2024-06-10T00:00:00", "category_id": cat["id"]},
            headers=auth(token))
        client.post("/transactions/",
            json={"type": "expense", "amount": 50, "description": "Coffee",
                  "date": "2024-06-15T00:00:00", "category_id": cat["id"]},
            headers=auth(token))
        return cat

    def test_period_report_balances(self):
        token = register_and_login()
        self._seed(token)
        r = client.get(
            "/reports/summary?date_from=2024-06-01T00:00:00&date_to=2024-06-30T23:59:59",
            headers=auth(token),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["total_income"] == 3000.0
        assert data["total_expenses"] == 250.0
        assert data["balance"] == 2750.0
        assert data["savings_rate"] > 0

    def test_budget_status(self):
        token = register_and_login()
        self._seed(token)
        r = client.get("/reports/budget?year=2024&month=6", headers=auth(token))
        assert r.status_code == 200
        budgets = r.json()
        assert len(budgets) == 1
        assert budgets[0]["category_name"] == "Food"
        assert budgets[0]["spent"] == 250.0
        assert budgets[0]["status"] == "ok"
