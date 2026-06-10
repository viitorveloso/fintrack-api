from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.category import Category
from app.models.transaction import Transaction, TransactionType
from app.models.user import User
from app.schemas.transaction import (
    PaginatedTransactions,
    TransactionCreate,
    TransactionOut,
    TransactionUpdate,
)

router = APIRouter()


@router.post("/", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def create_transaction(
    payload: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.category_id:
        cat = (
            db.query(Category)
            .filter(Category.id == payload.category_id, Category.user_id == current_user.id)
            .first()
        )
        if not cat:
            raise HTTPException(status_code=404, detail="Category not found")
        if cat.type.value != payload.type.value:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Category type '{cat.type}' does not match transaction type '{payload.type}'",
            )

    transaction = Transaction(**payload.model_dump(), user_id=current_user.id)
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return db.query(Transaction).options(joinedload(Transaction.category)).get(transaction.id)


@router.get("/", response_model=PaginatedTransactions)
def list_transactions(
    type: Optional[TransactionType] = None,
    category_id: Optional[int] = None,
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    description: Optional[str] = Query(None, description="Search by description (case-insensitive)"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        db.query(Transaction)
        .options(joinedload(Transaction.category))
        .filter(Transaction.user_id == current_user.id)
    )

    if type:
        query = query.filter(Transaction.type == type)
    if category_id:
        query = query.filter(Transaction.category_id == category_id)
    if date_from:
        query = query.filter(Transaction.date >= date_from)
    if date_to:
        query = query.filter(Transaction.date <= date_to)
    if description:
        query = query.filter(Transaction.description.ilike(f"%{description}%"))

    total = query.count()
    pages = max(1, -(-total // per_page))  # ceil division
    items = (
        query.order_by(Transaction.date.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return PaginatedTransactions(
        total=total, page=page, per_page=per_page, pages=pages, items=items
    )


@router.get("/{transaction_id}", response_model=TransactionOut)
def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    transaction = (
        db.query(Transaction)
        .options(joinedload(Transaction.category))
        .filter(Transaction.id == transaction_id, Transaction.user_id == current_user.id)
        .first()
    )
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction


@router.patch("/{transaction_id}", response_model=TransactionOut)
def update_transaction(
    transaction_id: int,
    payload: TransactionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    transaction = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id, Transaction.user_id == current_user.id)
        .first()
    )
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if payload.category_id:
        cat = (
            db.query(Category)
            .filter(Category.id == payload.category_id, Category.user_id == current_user.id)
            .first()
        )
        if not cat:
            raise HTTPException(status_code=404, detail="Category not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(transaction, field, value)

    db.commit()
    db.refresh(transaction)
    return db.query(Transaction).options(joinedload(Transaction.category)).get(transaction.id)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    transaction = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id, Transaction.user_id == current_user.id)
        .first()
    )
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    db.delete(transaction)
    db.commit()
