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
    coins: int = 0
    favorites: Optional[str] = None
    last_login: Optional[datetime] = None
    coin_history: Optional[str] = "[]"

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

class RedeemRequest(BaseModel):
    cost: int
    reward_name: str

class PurchasedReward(BaseModel):
    id: int
    reward_name: str
    reward_cost: int
    purchased_at: datetime

    class Config:
        from_attributes = True

class IntegrationBase(BaseModel):
    provider: str

class IntegrationConnect(IntegrationBase):
    access_token: str
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None

class IntegrationStatus(IntegrationBase):
    is_connected: bool
    last_synced: Optional[datetime] = None

class GitHubRepo(BaseModel):
    id: int
    name: str
    html_url: str
    description: Optional[str] = None
    stars: int
    full_name: Optional[str] = None
    private: Optional[bool] = None
    language: Optional[str] = None

class GitHubRepoDetail(BaseModel):
    id: int
    name: str
    full_name: Optional[str] = None
    html_url: str
    description: Optional[str] = None
    private: Optional[bool] = None
    stars: Optional[int] = None
    forks: Optional[int] = None
    language: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class GitHubRepoCreate(BaseModel):
    name: str
    private: bool = False
    description: str = ""

class GitHubRepoUpdate(BaseModel):
    new_name: Optional[str] = None
    description: Optional[str] = None

class OneNotePage(BaseModel):
    id: str
    title: str
    links: Optional[dict] = None
    created_at: Optional[str] = None
    modified_at: Optional[str] = None

class OneNoteSection(BaseModel):
    id: str
    name: str

class OneNotePageCreate(BaseModel):
    section_id: str
    title: str
    content: str


