import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()  # Load environment variables from .env file

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL is None:
    raise Exception("DATABASE_URL environment variable is not set")

engine = create_engine(
    DATABASE_URL, echo=True
)  # `echo=True` for SQL logging (optional)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# Function to create all tables
def create_tables():
    Base.metadata.create_all(bind=engine)


# Pydantic model (if needed elsewhere)
from pydantic import BaseModel


class UserLogin(BaseModel):
    username: str
    password: str


def get_db():
    """
    This is a FastAPI dependency that will provide a database session.
    The session will be automatically closed after the request is completed.
    """
    db = SessionLocal()  # Create a new session instance
    try:
        yield db  # Return the session to be used in route handlers
    finally:
        db.close()  # Ensure the session is closed after use

