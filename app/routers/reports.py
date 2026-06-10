from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.report import BudgetStatus, PeriodReport
from app.services.report_service import get_budget_status, get_period_report

router = APIRouter()


@router.get("/summary", response_model=PeriodReport)
def period_summary(
    date_from: datetime = Query(..., description="Start date (ISO 8601)"),
    date_to: datetime = Query(..., description="End date (ISO 8601)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Full financial report for a date range:
    - Total income & expenses
    - Balance and savings rate
    - Average expense ticket
    - Breakdown by category (with % and budget usage)
    - Monthly evolution chart data
    """
    return get_period_report(db, current_user.id, date_from, date_to)


@router.get("/budget", response_model=list[BudgetStatus])
def budget_status(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Monthly budget tracking per expense category.
    Returns status: `ok` (< 80%), `warning` (80–99%), `exceeded` (≥ 100%).
    """
    return get_budget_status(db, current_user.id, year, month)
