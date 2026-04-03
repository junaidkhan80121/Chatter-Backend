from pydantic import BaseModel, EmailStr, field_validator, ConfigDict
from typing import Optional
from datetime import datetime
import re


class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    display_name: Optional[str] = None

    @field_validator("username")
    @classmethod
    def username_valid(cls, v):
        if not re.match(r"^[a-zA-Z0-9_]{3,50}$", v):
            raise ValueError("Username must be 3-50 chars, alphanumeric + underscore only")
        return v.lower()

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class OTPRequest(BaseModel):
    email: EmailStr


class OTPVerify(BaseModel):
    email: EmailStr
    otp: str


class TokenRefresh(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    email: str
    display_name: Optional[str]
    avatar_url: Optional[str]
    unique_share_id: Optional[str]
    status: str
    show_online_status: bool
    allow_messages_from: str
    read_receipts_enabled: bool
    two_factor_enabled: bool
    last_seen: Optional[datetime]
    created_at: datetime


class UserPublic(BaseModel):
    """Public-facing user info (for search results, chat participants)"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    display_name: Optional[str]
    avatar_url: Optional[str]
    unique_share_id: Optional[str]
    status: Optional[str]
    last_seen: Optional[datetime]


class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    show_online_status: Optional[bool] = None
    allow_messages_from: Optional[str] = None
    read_receipts_enabled: Optional[bool] = None
    two_factor_enabled: Optional[bool] = None
