from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator, model_validator
from app.models.transaction import TransactionType


class TransactionCreate(BaseModel):
    type: TransactionType
    amount: float
    description: str
    notes: Optional[str] = None
    date: datetime
    category_id: Optional[int] = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Amount must be greater than zero")
        return round(v, 2)

    @field_validator("description")
    @classmethod
    def description_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Description cannot be empty")
        return v.strip()


class TransactionUpdate(BaseModel):
    amount: Optional[float] = None
    description: Optional[str] = None
    notes: Optional[str] = None
    date: Optional[datetime] = None
    category_id: Optional[int] = None

    @model_validator(mode="after")
    def at_least_one_field(self):
        if all(v is None for v in self.model_dump().values()):
            raise ValueError("At least one field must be provided for update")
        return self

    @field_validator("amount", mode="before")
    @classmethod
    def amount_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Amount must be greater than zero")
        return round(v, 2) if v is not None else v


class CategoryOut(BaseModel):
    id: int
    name: str
    color: str
    icon: str
    model_config = {"from_attributes": True}


class TransactionOut(BaseModel):
    id: int
    type: TransactionType
    amount: float
    description: str
    notes: Optional[str]
    date: datetime
    category_id: Optional[int]
    category: Optional[CategoryOut]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaginatedTransactions(BaseModel):
    total: int
    page: int
    per_page: int
    pages: int
    items: list[TransactionOut]
