from pydantic import BaseModel

class UserLogin(BaseModel):
    username: str
    email: str
    password: str