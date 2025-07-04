from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.tables import User
from app import schemas
from typing import Optional
import os

# Security configurations
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "2400"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


async def get_user_by_username(username: str):
    try:
        user = await User.select().where(User.username == username).first()
        print(f"Database query result for {username}: {user}")
        return user
    except Exception as e:
        print(f"Database error: {e}")
        return None


async def get_user_by_id(user_id: int):
    user = await User.select().where(User.id == user_id).first()
    return user


async def create_user(user: schemas.UserCreate):
    hashed_password = get_password_hash(user.password)

    # Generate avatar URL if not provided
    avatar_url = user.avatar
    if not avatar_url:
        avatar_url = f"https://api.dicebear.com/7.x/avataaars/svg?seed={user.username}"

    # Use display_name if provided, otherwise use username
    display_name = user.display_name if user.display_name else user.username

    new_user = User(
        username=user.username, hashed_password=hashed_password, display_name=display_name, avatar=avatar_url
    )
    await new_user.save()
    return new_user


async def authenticate_user(username: str, password: str):
    user = await get_user_by_username(username)
    if not user:
        return False
    if not verify_password(password, user["hashed_password"]):
        return False
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str, credentials_exception):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = schemas.TokenData(username=username)
    except JWTError:
        raise credentials_exception
    return token_data
