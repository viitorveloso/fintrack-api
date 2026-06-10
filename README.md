# FinTrack API

Personal finance tracker REST API built with **FastAPI**, **SQLAlchemy**, and **Pydantic v2**.

## Features

- **JWT authentication** — register, login, protected routes
- **Transactions** — income & expenses with CRUD, pagination, date range and text search filters
- **Categories** — custom categories with optional monthly budget cap and hex color/icon
- **Reports** — period summary (balance, savings rate, avg expense, monthly evolution) and budget status (`ok` / `warning` / `exceeded`)
- **User isolation** — every resource is scoped to the authenticated user
- **20 integration tests** — cover auth, validation edge cases, pagination, cross-user isolation, and report calculations

## Tech stack

| Layer | Library |
|---|---|
| Framework | FastAPI 0.115 |
| ORM | SQLAlchemy 2.0 |
| Validation | Pydantic v2 |
| Auth | python-jose (JWT) + passlib/bcrypt |
| DB | SQLite (dev) — swap `DATABASE_URL` for Postgres in production |
| Tests | pytest + httpx TestClient |

## Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the server
uvicorn app.main:app --reload

# 3. Open interactive docs
open http://localhost:8000/docs
```

## Running tests

```bash
pytest tests/ -v
```

## Project structure

```
fintrack/
├── app/
│   ├── main.py              # FastAPI app, lifespan, router registration
│   ├── core/
│   │   ├── database.py      # SQLAlchemy engine, session factory, Base
│   │   └── security.py      # JWT encode/decode, password hashing, auth dependency
│   ├── models/
│   │   ├── user.py
│   │   ├── category.py      # CategoryType enum, budget field
│   │   └── transaction.py   # TransactionType enum
│   ├── schemas/
│   │   ├── auth.py          # UserRegister, UserLogin, TokenResponse, UserOut
│   │   ├── category.py      # CategoryCreate/Update/Out
│   │   ├── transaction.py   # TransactionCreate/Update/Out, PaginatedTransactions
│   │   └── report.py        # PeriodReport, CategoryBreakdown, BudgetStatus
│   ├── routers/
│   │   ├── auth.py          # POST /auth/register, /login, GET /me
│   │   ├── categories.py    # Full CRUD /categories/
│   │   ├── transactions.py  # Full CRUD + filtering /transactions/
│   │   └── reports.py       # GET /reports/summary, /reports/budget
│   └── services/
│       └── report_service.py  # Aggregation logic (category breakdown, monthly evolution)
└── tests/
    └── test_api.py          # 20 integration tests
```

## API overview

### Auth
| Method | Path | Description |
|---|---|---|
| POST | `/auth/register` | Create account |
| POST | `/auth/login` | Get JWT token |
| GET | `/auth/me` | Current user info |

### Transactions
| Method | Path | Description |
|---|---|---|
| POST | `/transactions/` | Create transaction |
| GET | `/transactions/` | List with filters + pagination |
| GET | `/transactions/{id}` | Get one |
| PATCH | `/transactions/{id}` | Partial update |
| DELETE | `/transactions/{id}` | Delete |

Query params: `type`, `category_id`, `date_from`, `date_to`, `description`, `page`, `per_page`

### Categories
| Method | Path | Description |
|---|---|---|
| POST | `/categories/` | Create category |
| GET | `/categories/` | List (optional `?type=income\|expense`) |
| GET | `/categories/{id}` | Get one |
| PATCH | `/categories/{id}` | Partial update |
| DELETE | `/categories/{id}` | Delete (blocked if has transactions) |

### Reports
| Method | Path | Description |
|---|---|---|
| GET | `/reports/summary` | Full period report (`date_from`, `date_to`) |
| GET | `/reports/budget` | Monthly budget status (`year`, `month`) |
