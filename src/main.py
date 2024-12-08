import re
from contextlib import asynccontextmanager
from operator import or_

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

# from models import User
from .auth import (create_access_token, hash_password, verify_access_token,
                   verify_password)
from .database import create_tables, get_db
from .models import User
from .schemas import UserLogin


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Startup code
    create_tables()
    yield


app = FastAPI(lifespan=lifespan)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


@app.get("/verify-token")
def verify_token(token: str = Depends(oauth2_scheme)):
    """
    Endpoint to verify the validity of a token.
    It returns information about the token if it is valid.
    """
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )

    return {"msg": "Token is valid", "token_info": payload}


def validate_password(password: str) -> bool:
    """
    Validate that the password meets the minimum requirements:
    - At least 8 characters long
    - Contains at least one uppercase letter
    - Contains at least one lowercase letter
    """
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):  # Check for uppercase
        return False
    if not re.search(r"[a-z]", password):  # Check for lowercase
        return False
    return True


@app.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    # Check if username or email exists
    db_user = (
        db.query(User)
        .filter(or_(User.username == user.username, User.email == user.email))
        .first()
    )

    if not db_user or not verify_password(user.password, db_user.password):  # type: ignore
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # Generate the JWT token
    access_token = create_access_token(data={"sub": db_user.username})

    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/register")
def register(user: UserLogin, db: Session = Depends(get_db)):
    # Check if username or email exists
    db_user = (
        db.query(User)
        .filter(or_(User.username == user.username, User.email == user.email))
        .first()
    )

    if db_user:
        raise HTTPException(status_code=409, detail="Username already exists!")

    # Validate email format
    if not re.match(r"[^@]+@[^@]+\.[^@]+", user.email):
        raise HTTPException(status_code=400, detail="Invalid email format")

    if not validate_password(user.password):
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters long, and include uppercase, lowercase, number, and special character",
        )

    # Hash the password before saving
    hashed_password = hash_password(user.password)

    # Create the new user
    new_user = User(
        username=user.username, email=user.email, password=hashed_password
    )

    # Add to the database
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"msg": "User created successfully"}
