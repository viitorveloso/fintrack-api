from typing import Optional
from pydantic import BaseModel


class MonthlySummary(BaseModel):
    year: int
    month: int
    total_income: float
    total_expenses: float
    balance: float
    transaction_count: int


class CategoryBreakdown(BaseModel):
    category_id: Optional[int]
    category_name: str
    category_color: str
    total: float
    percentage: float
    transaction_count: int
    budget: Optional[float] = None
    budget_used_pct: Optional[float] = None


class PeriodReport(BaseModel):
    period_start: str
    period_end: str
    total_income: float
    total_expenses: float
    balance: float
    savings_rate: float               # (balance / income) * 100
    transaction_count: int
    avg_expense: float
    income_by_category: list[CategoryBreakdown]
    expenses_by_category: list[CategoryBreakdown]
    monthly_evolution: list[MonthlySummary]


class BudgetStatus(BaseModel):
    category_id: int
    category_name: str
    category_color: str
    budget: float
    spent: float
    remaining: float
    used_pct: float
    status: str                       # "ok" | "warning" | "exceeded"
