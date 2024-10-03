from typing import List
from fastapi import Depends, FastAPI, HTTPException, status
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

def get_current_user(token_data: dict = Depends(verify_token), db: Session = db_session):
    email = token_data.get("sub")
    user = crud.get_user_by_email(db, email=email)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=401, detail="User is inactive")
    return user


@app.get("/health-check")
def health_check(current_user: schemas.User = Depends(get_current_user)):
    return {"status": "ok"}


@app.post("/users/", response_model=schemas.UserWithToken)
def create_user(user: schemas.UserCreate, db: Session = db_session):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = crud.create_user(db=db, user=user)
    token_data = {"sub": new_user.email}
    x_api_token = create_token(token_data)
    return { **new_user.__dict__, "x_api_token":x_api_token }


@app.get("/users/", response_model=List[schemas.User])
def read_users(skip: int = 0, limit: int = 100, current_user: schemas.User = Depends(get_current_user), db: Session = db_session):
    users = crud.get_users(db, skip=skip, limit=limit)
    return users


@app.get("/users/{user_id}", response_model=schemas.User)
def read_user(user_id: int, current_user: schemas.User = Depends(get_current_user), db: Session = db_session):
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@app.delete("/users/{user_id}", response_model=schemas.User)
def delete_user(user_id: int, current_user: schemas.User = Depends(get_current_user), db: Session = db_session):
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if not db_user.is_active:
        raise HTTPException(status_code=400, detail="User is already inactive")
    
    oldest_active_user = crud.get_oldest_active_user(db)
    if oldest_active_user is None or oldest_active_user.id == user_id:
        raise HTTPException(status_code=400, detail="No active user available to transfer items")
    
    crud.transfer_items(db, from_user_id=user_id, to_user_id=oldest_active_user.id)
    deleted_user = crud.delete_user(db, user_id=user_id)
    return deleted_user


@app.post("/users/{user_id}/items/", response_model=schemas.Item)
def create_item_for_user(user_id: int, item: schemas.ItemCreate, current_user: schemas.User = Depends(get_current_user), db: Session = db_session):
    return crud.create_user_item(db=db, item=item, user_id=user_id)


@app.get("/items/", response_model=List[schemas.Item])
def read_items(skip: int = 0, limit: int = 100, current_user: schemas.User = Depends(get_current_user), db: Session = db_session):
    items = crud.get_items(db, skip=skip, limit=limit)
    return items


@app.get("/me/items", response_model=List[schemas.Item])
def read_own_items(current_user: schemas.User = Depends(get_current_user), db: Session = db_session):
    items = crud.get_items_by_user(db, user_id=current_user.id)
    return items
