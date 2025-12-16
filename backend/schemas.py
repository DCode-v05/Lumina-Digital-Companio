from pydantic import BaseModel, EmailStr
from typing import Optional, List

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True

# Auth Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# Chat Schemas
class CreateChatRequest(BaseModel):
    title: Optional[str] = "New Chat"

class ChatMetadata(BaseModel):
    id: str
    title: str
    created_at: float

class ChatRequest(BaseModel):
    message: str
    chat_id: str  # Mandatory now

class ChatResponse(BaseModel):
    response: str
    chat_id: str
    title: Optional[str] = None
