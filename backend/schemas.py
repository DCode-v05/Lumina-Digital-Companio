from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

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
    mode: str
    memory_updated: bool = False
    goal_created: Optional[str] = None

class UpdateProfileRequest(BaseModel):
    profile_text: str

# Goal Schemas
class GoalBase(BaseModel):
    title: str
    description: Optional[str] = None
    duration: int
    duration_unit: str
    priority: str

class GoalCreate(GoalBase):
    subtasks: Optional[str] = None

class GoalUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    duration: Optional[int] = None
    duration_unit: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    subtasks: Optional[str] = None

class Goal(GoalBase):
    id: int
    user_id: int
    status: str
    created_at: datetime
    subtasks: Optional[str] = None

    class Config:
        from_attributes = True
