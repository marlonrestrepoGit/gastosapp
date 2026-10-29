import datetime

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=8, max_length=72)


class UserOut(BaseModel):
    id: int
    email: str

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ExpenseCreate(BaseModel):
    """Lo que el usuario envía para crear o editar un gasto."""

    description: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=50)
    amount_cop: float = Field(gt=0)  # el monto debe ser mayor que cero
    date: datetime.date


class ExpenseOut(ExpenseCreate):
    """Lo que la API devuelve: lo mismo, más el id."""

    id: int

    model_config = {"from_attributes": True}


class CategoryTotal(BaseModel):
    category: str
    total_cop: float
    total_usd: float


class Summary(BaseModel):
    month: str
    cop_per_usd: float
    rate_source: str  # "live" = tasa actual de la API, "fallback" = valor de respaldo
    total_cop: float
    total_usd: float
    by_category: list[CategoryTotal]
