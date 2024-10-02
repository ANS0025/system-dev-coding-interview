from typing import List
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from . import crud, models, schemas
from .database import SessionLocal, engine
from .auth import verify_token, create_token

models.Base.metadata.create_all(bind=engine)

app = FastAPI()


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_session = Depends(get_db)


@app.get("/health-check")
def health_check(db: Session = db_session, x_api_token: str = Depends(verify_token)):
    return {"status": "ok"}

@app.post("/users/", response_model=schemas.UserWithToken)
def create_user(user: schemas.UserCreate, db: Session = db_session):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = crud.create_user(db=db, user=user)
    token_data = {"sub": new_user.email}
    x_api_token = create_token(token_data)
    return { **new_user.__dict__, "x_api_token": x_api_token}

@app.get("/users/", response_model=List[schemas.User])
def read_users(skip: int = 0, limit: int = 100, db: Session = db_session, x_api_token: str = Depends(verify_token)):
    users = crud.get_users(db, skip=skip, limit=limit)
    return users


@app.get("/users/{user_id}", response_model=schemas.User)
def read_user(user_id: int, db: Session = db_session, x_api_token: str = Depends(verify_token)):
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@app.post("/users/{user_id}/items/", response_model=schemas.Item)
def create_item_for_user(
    user_id: int, item: schemas.ItemCreate, db: Session = db_session, x_api_token: str = Depends(verify_token)
):
    return crud.create_user_item(db=db, item=item, user_id=user_id)


@app.get("/items/", response_model=List[schemas.Item])
def read_items(skip: int = 0, limit: int = 100, db: Session = db_session, x_api_token: str = Depends(verify_token)):
    items = crud.get_items(db, skip=skip, limit=limit)
    return items
