from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.database import create_tables
from app.routers import auth, transactions, categories, reports


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield


app = FastAPI(
    title="FinTrack API",
    description=(
        "Personal finance tracker API.\n\n"
        "Features:\n"
        "- JWT authentication\n"
        "- Transaction management (income & expenses)\n"
        "- Category management\n"
        "- Financial reports with aggregations\n"
        "- Budget tracking per category"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,         prefix="/auth",         tags=["Auth"])
app.include_router(transactions.router, prefix="/transactions", tags=["Transactions"])
app.include_router(categories.router,   prefix="/categories",   tags=["Categories"])
app.include_router(reports.router,      prefix="/reports",      tags=["Reports"])


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "FinTrack API v1.0.0"}
