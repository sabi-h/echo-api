from fastapi import APIRouter, HTTPException, status, Depends
from datetime import timedelta
from app import auth, schemas
from app.dependencies import get_current_user
from app.tables import User

router = APIRouter()


@router.post("/register", response_model=schemas.UserResponse)
async def register_user(user: schemas.UserCreate):
    # Check if user already exists
    db_user = await auth.get_user_by_username(username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    # Create new user
    new_user = await auth.create_user(user=user)
    return new_user.to_dict()


@router.post("/login", response_model=schemas.Token)
async def login_user(login_data: schemas.LoginRequest):
    user = await auth.authenticate_user(login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(data={"sub": user["username"]}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=schemas.UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/users", response_model=list[schemas.UserResponse])
async def get_all_users(current_user: User = Depends(get_current_user)):
    """Get all users - requires authentication"""
    users = await User.select()
    return users
