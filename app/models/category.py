from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class CategoryType(str, enum.Enum):
    income  = "income"
    expense = "expense"


class Category(Base):
    __tablename__ = "categories"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False)
    name        = Column(String(100), nullable=False)
    type        = Column(Enum(CategoryType), nullable=False)
    color       = Column(String(7), default="#6366f1")   # hex color for frontend
    icon        = Column(String(50), default="tag")
    budget      = Column(Float, nullable=True)           # monthly budget cap
    created_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    transactions = relationship("Transaction", back_populates="category", lazy="dynamic")
