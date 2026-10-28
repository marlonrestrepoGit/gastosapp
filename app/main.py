from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models, schemas
from .database import Base, engine, get_db
from .security import create_access_token, get_current_user, hash_password, verify_password

Base.metadata.create_all(bind=engine)  # crea las tablas si no existen

app = FastAPI(title="GastosApp", description="Control de gastos personales")


# ---------- Autenticación ----------


@app.post("/auth/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def register(data: schemas.UserCreate, db: Session = Depends(get_db)):
    email = data.email.lower()
    if db.scalar(select(models.User).where(models.User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Ese correo ya está registrado")
    user = models.User(email=email, hashed_password=hash_password(data.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/auth/login", response_model=schemas.Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # OAuth2PasswordRequestForm llama "username" al campo; aquí es el correo.
    user = db.scalar(select(models.User).where(models.User.email == form.username.lower()))
    if user is None or not verify_password(form.password, user.hashed_password):
        # Mismo mensaje en ambos casos: no revelamos si el correo existe.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Correo o contraseña incorrectos")
    return schemas.Token(access_token=create_access_token(user.id))


@app.get("/me", response_model=schemas.UserOut)
def me(current_user: models.User = Depends(get_current_user)):
    return current_user


# ---------- Gastos (CRUD) ----------


def get_own_expense(db: Session, user: models.User, expense_id: int) -> models.Expense:
    """Busca un gasto que pertenezca al usuario. Si no existe o es de otro, da 404."""
    expense = db.get(models.Expense, expense_id)
    if expense is None or expense.user_id != user.id:
        # 404 (y no 403) para no revelar que ese gasto existe en la cuenta de otra persona
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Gasto no encontrado")
    return expense


@app.post("/expenses", response_model=schemas.ExpenseOut, status_code=status.HTTP_201_CREATED)
def create_expense(
    data: schemas.ExpenseCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    expense = models.Expense(**data.model_dump(), user_id=user.id)
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


@app.get("/expenses", response_model=list[schemas.ExpenseOut])
def list_expenses(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    query = (
        select(models.Expense)
        .where(models.Expense.user_id == user.id)  # solo los gastos del usuario
        .order_by(models.Expense.date.desc(), models.Expense.id.desc())
    )
    return db.scalars(query).all()


@app.put("/expenses/{expense_id}", response_model=schemas.ExpenseOut)
def update_expense(
    expense_id: int,
    data: schemas.ExpenseCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    expense = get_own_expense(db, user, expense_id)
    for field, value in data.model_dump().items():
        setattr(expense, field, value)
    db.commit()
    db.refresh(expense)
    return expense


@app.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    expense = get_own_expense(db, user, expense_id)
    db.delete(expense)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
