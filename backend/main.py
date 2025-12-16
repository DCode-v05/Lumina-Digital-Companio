from fastapi import FastAPI, HTTPException, Depends, status, Body, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import uvicorn
import models, schemas, auth
from database import engine, get_db
from redis_client import (
    get_chat_history, add_message, get_redis_client,
    create_chat, get_user_chats, delete_chat_session, update_chat_title
)
from gemini_client import get_ai_response, generate_chat_title



# ----------------------------
# App Initialization
# ----------------------------

app = FastAPI(title="Lumina - Digital Student Companion API")


# ----------------------------
# CORS
# ----------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------------
# Startup Event
# ----------------------------

@app.on_event("startup")
def on_startup():
    try:
        print("🔄 Initializing database...")
        try:
            models.Base.metadata.create_all(bind=engine)
            print("✅ Database tables created successfully")
        except Exception as e:
            print(f"❌ Error creating database tables: {e}")
            print("⚠️ Check if the database exists and credentials are correct in .env")
        print("✅ Database ready")
    except Exception as e:
        print("❌ Database startup error:", e)

    try:
        redis = get_redis_client()
        redis.ping()
        print("✅ Redis connected")
    except Exception as e:
        print("⚠️ Redis not available:", e)


# ----------------------------
# Health Check
# ----------------------------

@app.get("/")
def read_root():
    return {"status": "online", "message": "Lumina Backend Active"}


# ----------------------------
# Auth Routes
# ----------------------------

@app.post("/register", response_model=schemas.User)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = auth.get_password_hash(user.password)
    new_user = models.User(
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = auth.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=schemas.User)
def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user


# ----------------------------
# Chat Management Routes
# ----------------------------

@app.post("/chats", response_model=schemas.ChatMetadata)
def create_new_chat(
    request: schemas.CreateChatRequest,
    current_user: models.User = Depends(auth.get_current_user)
):
    user_id = str(current_user.id)
    chat_meta = create_chat(user_id, request.title)
    if not chat_meta:
         raise HTTPException(status_code=503, detail="Chat service unavailable")
    return chat_meta

@app.get("/chats", response_model=list[schemas.ChatMetadata])
def list_user_chats(current_user: models.User = Depends(auth.get_current_user)):
    user_id = str(current_user.id)
    return get_user_chats(user_id)

@app.delete("/chats/{chat_id}")
def delete_chat_endpoint(
    chat_id: str,
    current_user: models.User = Depends(auth.get_current_user)
):
    user_id = str(current_user.id)
    # Check ownership ideally, but for now assuming if user has ID they can delete from their list
    delete_chat_session(user_id, chat_id)
    return {"status": "deleted"}


# ----------------------------
# Chat Interaction Routes
# ----------------------------





@app.post("/chat", response_model=schemas.ChatResponse)
def chat_endpoint(
    request: schemas.ChatRequest,
    current_user: models.User = Depends(auth.get_current_user)
):
    user_id = str(current_user.id)
    chat_id = request.chat_id
    user_message = request.message
    
    # 1. Get History (for specific chat)
    history = get_chat_history(chat_id)
    
    # 2. Get AI Response
    ai_text, title_from_ai = get_ai_response(history, user_message)
    
    # 3. Save Context
    add_message(chat_id, "user", user_message)
    add_message(chat_id, "model", ai_text)
    
    # 4. Generate Title (if it's the first message)
    new_title = None
    if len(history) == 0:
        if title_from_ai:
             new_title = title_from_ai
        else:
             # Fallback to local fast generation if AI didn't provide one
             new_title = generate_chat_title(user_message)
        
        update_chat_title(user_id, chat_id, new_title)

    return schemas.ChatResponse(response=ai_text, chat_id=chat_id, title=new_title)

@app.get("/chats/{chat_id}/history")
def get_chat_history_endpoint(
    chat_id: str,
    current_user: models.User = Depends(auth.get_current_user)
):
    return get_chat_history(chat_id)
