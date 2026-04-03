from pydantic import BaseModel, EmailStr
from typing import Optional, List


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    avatar_url: Optional[str] = None
    status: str

    class Config:
        orm_mode = True


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class MessageCreate(BaseModel):
    conversation_id: int
    content: str
