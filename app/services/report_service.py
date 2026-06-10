from datetime import datetime
from typing import Optional

from sqlalchemy import func, extract
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.transaction import Transaction, TransactionType
from app.schemas.report import (
    BudgetStatus,
    CategoryBreakdown,
    MonthlySummary,
    PeriodReport,
)


def _category_breakdown(
    db: Session,
    user_id: int,
    tx_type: TransactionType,
    date_from: datetime,
    date_to: datetime,
) -> list[CategoryBreakdown]:
    rows = (
        db.query(
            Category.id,
            Category.name,
            Category.color,
            Category.budget,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count"),
        )
        .outerjoin(Transaction, Transaction.category_id == Category.id)
        .filter(
            Category.user_id == user_id,
            Category.type == tx_type,
            Transaction.date >= date_from,
            Transaction.date <= date_to,
            Transaction.type == tx_type,
        )
        .group_by(Category.id)
        .all()
    )

    # Uncategorized
    uncategorized_total = (
        db.query(func.sum(Transaction.amount))
        .filter(
            Transaction.user_id == user_id,
            Transaction.type == tx_type,
            Transaction.category_id.is_(None),
            Transaction.date >= date_from,
            Transaction.date <= date_to,
        )
        .scalar()
        or 0.0
    )

    grand_total = sum(r.total or 0 for r in rows) + uncategorized_total

    result = []
    for r in rows:
        total = r.total or 0.0
        pct = round((total / grand_total * 100) if grand_total else 0, 2)
        budget_used = round((total / r.budget * 100) if r.budget else None or 0, 2) if r.budget else None
        result.append(
            CategoryBreakdown(
                category_id=r.id,
                category_name=r.name,
                category_color=r.color,
                total=round(total, 2),
                percentage=pct,
                transaction_count=r.count,
                budget=r.budget,
                budget_used_pct=budget_used,
            )
        )

    if uncategorized_total > 0:
        result.append(
            CategoryBreakdown(
                category_id=None,
                category_name="Uncategorized",
                category_color="#94a3b8",
                total=round(uncategorized_total, 2),
                percentage=round((uncategorized_total / grand_total * 100) if grand_total else 0, 2),
                transaction_count=0,
            )
        )

    return sorted(result, key=lambda x: x.total, reverse=True)


def _monthly_evolution(
    db: Session,
    user_id: int,
    date_from: datetime,
    date_to: datetime,
) -> list[MonthlySummary]:
    rows = (
        db.query(
            extract("year", Transaction.date).label("year"),
            extract("month", Transaction.date).label("month"),
            Transaction.type,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count"),
        )
        .filter(
            Transaction.user_id == user_id,
            Transaction.date >= date_from,
            Transaction.date <= date_to,
        )
        .group_by("year", "month", Transaction.type)
        .order_by("year", "month")
        .all()
    )

    # Aggregate into dict keyed by (year, month)
    months: dict[tuple, dict] = {}
    for r in rows:
        key = (int(r.year), int(r.month))
        if key not in months:
            months[key] = {"income": 0.0, "expenses": 0.0, "count": 0}
        if r.type == TransactionType.income:
            months[key]["income"] += r.total
        else:
            months[key]["expenses"] += r.total
        months[key]["count"] += r.count

    return [
        MonthlySummary(
            year=k[0],
            month=k[1],
            total_income=round(v["income"], 2),
            total_expenses=round(v["expenses"], 2),
            balance=round(v["income"] - v["expenses"], 2),
            transaction_count=v["count"],
        )
        for k, v in sorted(months.items())
    ]


def get_period_report(
    db: Session,
    user_id: int,
    date_from: datetime,
    date_to: datetime,
) -> PeriodReport:
    totals = (
        db.query(
            Transaction.type,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count"),
        )
        .filter(
            Transaction.user_id == user_id,
            Transaction.date >= date_from,
            Transaction.date <= date_to,
        )
        .group_by(Transaction.type)
        .all()
    )

    income = next((r.total for r in totals if r.type == TransactionType.income), 0.0)
    expenses = next((r.total for r in totals if r.type == TransactionType.expense), 0.0)
    tx_count = sum(r.count for r in totals)
    balance = income - expenses
    savings_rate = round((balance / income * 100) if income else 0, 2)

    avg_expense_row = (
        db.query(func.avg(Transaction.amount))
        .filter(
            Transaction.user_id == user_id,
            Transaction.type == TransactionType.expense,
            Transaction.date >= date_from,
            Transaction.date <= date_to,
        )
        .scalar()
    )

    return PeriodReport(
        period_start=date_from.strftime("%Y-%m-%d"),
        period_end=date_to.strftime("%Y-%m-%d"),
        total_income=round(income, 2),
        total_expenses=round(expenses, 2),
        balance=round(balance, 2),
        savings_rate=savings_rate,
        transaction_count=tx_count,
        avg_expense=round(avg_expense_row or 0, 2),
        income_by_category=_category_breakdown(
            db, user_id, TransactionType.income, date_from, date_to
        ),
        expenses_by_category=_category_breakdown(
            db, user_id, TransactionType.expense, date_from, date_to
        ),
        monthly_evolution=_monthly_evolution(db, user_id, date_from, date_to),
    )


def get_budget_status(
    db: Session,
    user_id: int,
    year: int,
    month: int,
) -> list[BudgetStatus]:
    date_from = datetime(year, month, 1)
    # Last day of the month
    import calendar
    last_day = calendar.monthrange(year, month)[1]
    date_to = datetime(year, month, last_day, 23, 59, 59)

    categories = (
        db.query(Category)
        .filter(
            Category.user_id == user_id,
            Category.budget.isnot(None),
            Category.type == TransactionType.expense,
        )
        .all()
    )

    result = []
    for cat in categories:
        spent = (
            db.query(func.sum(Transaction.amount))
            .filter(
                Transaction.user_id == user_id,
                Transaction.category_id == cat.id,
                Transaction.date >= date_from,
                Transaction.date <= date_to,
            )
            .scalar()
            or 0.0
        )
        used_pct = round((spent / cat.budget * 100), 2)
        remaining = round(cat.budget - spent, 2)

        if used_pct >= 100:
            budget_status = "exceeded"
        elif used_pct >= 80:
            budget_status = "warning"
        else:
            budget_status = "ok"

        result.append(
            BudgetStatus(
                category_id=cat.id,
                category_name=cat.name,
                category_color=cat.color,
                budget=cat.budget,
                spent=round(spent, 2),
                remaining=remaining,
                used_pct=used_pct,
                status=budget_status,
            )
        )

    return sorted(result, key=lambda x: x.used_pct, reverse=True)
