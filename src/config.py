import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL") or ""
if DATABASE_URL == "":
    raise Exception("DATABASE_URL environment variable is not set")

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
DEVELOPMENT_MODE = os.getenv("DEVELOPMENT_MODE", "False") == "True"
