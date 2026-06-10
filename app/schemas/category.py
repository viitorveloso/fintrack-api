from typing import Optional
from pydantic import BaseModel, field_validator
from app.models.category import CategoryType


class CategoryCreate(BaseModel):
    name: str
    type: CategoryType
    color: str = "#6366f1"
    icon: str = "tag"
    budget: Optional[float] = None

    @field_validator("color")
    @classmethod
    def valid_hex_color(cls, v: str) -> str:
        v = v.strip()
        if not (v.startswith("#") and len(v) in (4, 7)):
            raise ValueError("Color must be a valid hex code (e.g. #fff or #ffffff)")
        return v

    @field_validator("budget", mode="before")
    @classmethod
    def budget_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Budget must be greater than zero")
        return v

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    budget: Optional[float] = None


class CategoryOut(BaseModel):
    id: int
    name: str
    type: CategoryType
    color: str
    icon: str
    budget: Optional[float]

    model_config = {"from_attributes": True}
