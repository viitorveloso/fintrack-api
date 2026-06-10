from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class TransactionType(str, enum.Enum):
    income  = "income"
    expense = "expense"


class Transaction(Base):
    __tablename__ = "transactions"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    type        = Column(Enum(TransactionType), nullable=False)
    amount      = Column(Float, nullable=False)
    description = Column(String(255), nullable=False)
    notes       = Column(Text, nullable=True)
    date        = Column(DateTime, nullable=False)
    created_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))

    category = relationship("Category", back_populates="transactions")
