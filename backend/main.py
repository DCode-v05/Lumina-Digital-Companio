from fastapi import FastAPI, HTTPException, Depends, status, Body, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import uvicorn
import models, schemas, auth
from database import engine, get_db
from redis_client import (
    get_chat_history, add_message, get_redis_client,
    create_chat, get_user_chats, delete_chat_session, update_chat_title,
    get_user_profile, update_user_profile
)
from groq_service import get_ai_response, generate_chat_title, decompose_goal
import json
import emotion_service



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
        raise HTTPException(
            status_code=400, 
            detail="A user with this email already exists."
        )
    
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
    # Note: form_data.username maps to email in our frontend
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User with this email does not exist.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password provided.",
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

# ----------------------------
# Goal Management Routes
# ----------------------------

@app.post("/goals", response_model=schemas.Goal)
def create_goal(goal: schemas.GoalCreate, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    db_goal = models.Goal(**goal.dict(), user_id=current_user.id)
    # Ensure subtasks is valid JSON text if provided
    if not db_goal.subtasks:
         db_goal.subtasks = json.dumps([])
    db.add(db_goal)
    db.commit()
    db.refresh(db_goal)
    return db_goal

@app.get("/goals", response_model=list[schemas.Goal])
def read_goals(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    goals = db.query(models.Goal).filter(models.Goal.user_id == current_user.id).all()
    return goals

@app.put("/goals/{goal_id}", response_model=schemas.Goal)
def update_goal(goal_id: int, goal: schemas.GoalUpdate, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    db_goal = db.query(models.Goal).filter(models.Goal.id == goal_id, models.Goal.user_id == current_user.id).first()
    if not db_goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    update_data = goal.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_goal, key, value)
    
    db.commit()
    db.refresh(db_goal)
    return db_goal

@app.delete("/goals/{goal_id}")
def delete_goal(goal_id: int, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    db_goal = db.query(models.Goal).filter(models.Goal.id == goal_id, models.Goal.user_id == current_user.id).first()
    if not db_goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    db.delete(db_goal)
    db.commit()
    return {"status": "deleted"}

@app.post("/goals/{goal_id}/decompose", response_model=schemas.Goal)
def decompose_goal_endpoint(
    goal_id: int, 
    breakdown_type: str = "daily", 
    current_user: models.User = Depends(auth.get_current_user), 
    db: Session = Depends(get_db)
):
    db_goal = db.query(models.Goal).filter(models.Goal.id == goal_id, models.Goal.user_id == current_user.id).first()
    if not db_goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    # Call AI
    subtasks_list = decompose_goal(db_goal.title, db_goal.duration, db_goal.duration_unit, breakdown_type)
    
    # Update DB
    db_goal.subtasks = json.dumps(subtasks_list)
    db.commit()
    db.refresh(db_goal)
    return db_goal

@app.delete("/chats/{chat_id}")
def delete_chat_endpoint(
    chat_id: str,
    current_user: models.User = Depends(auth.get_current_user)
):
    user_id = str(current_user.id)
    # Check ownership ideally, but for now assuming if user has ID they can delete from their list
    delete_chat_session(user_id, chat_id)
    return {"status": "deleted"}

@app.get("/users/me/profile")
def get_user_profile_endpoint(current_user: models.User = Depends(auth.get_current_user)):
    user_id = str(current_user.id)
    profile = get_user_profile(user_id)
    # Parse the newline separated string into a list for easier frontend display
    facts = [line.strip() for line in profile.split('\n') if line.strip()] if profile else []
    return {"profile_text": profile, "facts": facts}

@app.put("/users/me/profile")
def update_user_profile_endpoint(
    request: schemas.UpdateProfileRequest,
    current_user: models.User = Depends(auth.get_current_user)
):
    user_id = str(current_user.id)
    update_user_profile(user_id, request.profile_text)
    return {"status": "updated", "profile_text": request.profile_text}


# ----------------------------
# Chat Interaction Routes
# ----------------------------

@app.post("/chat", response_model=schemas.ChatResponse)
def chat_endpoint(
    request: schemas.ChatRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    user_id = str(current_user.id)
    chat_id = request.chat_id
    user_message = request.message
    
    # Clean expired memories on every interaction (or could be moved to specific login hooks)
    from redis_client import clean_expired_facts
    clean_expired_facts(user_id)
    
    # --- Emotion Tracking ---
    # Analyze and Log current emotion
    emotion, score = emotion_service.analyze_emotion(user_message)
    if emotion:
        emotion_service.log_emotion(db, current_user.id, emotion, score)
    
    # Get Recent Emotion Context
    emotion_summary = emotion_service.get_recent_emotions_summary(db, current_user.id)
    
    # Get User Profile Context
    user_profile = get_user_profile(user_id)
    
    # Combine Profile + Emotion for context
    combined_context = user_profile
    if emotion_summary:
        combined_context = (combined_context or "") + "\n\n" + emotion_summary

    # Get History (for specific chat)
    history = get_chat_history(chat_id)
    
    # Get AI Response (with combined context)
    ai_text, title_from_ai, new_facts, mode, suggested_goal = get_ai_response(
        history, 
        user_message, 
        combined_context,
        user_name=current_user.full_name
    )
    
    # Save Context
    add_message(chat_id, "user", user_message)
    add_message(chat_id, "model", ai_text)
    
    # Update Profile (Directly from response)
    memory_updated = False
    if new_facts:
        # Ensure new_facts is a string
        if isinstance(new_facts, dict):
            new_facts_str = "\n".join([f"{k}: {v}" for k, v in new_facts.items()])
        elif isinstance(new_facts, list):
             new_facts_str = "\n".join([str(f) for f in new_facts])
        else:
            new_facts_str = str(new_facts)

        # Append new facts to existing profile
        if not user_profile or new_facts_str not in user_profile:
             updated_profile = user_profile + "\n" + new_facts_str if user_profile else new_facts_str
             update_user_profile(user_id, updated_profile)
             memory_updated = True

    # Auto-Create Goal
    created_goal_title = None
    if suggested_goal:
        print(f"🎯 Auto-creating goal input: {suggested_goal}")
        try:
            # Handle case where AI returns just a string instead of dict
            if isinstance(suggested_goal, str):
                import re
                # Try to extract duration from the string itself as a fallback
                title_text = suggested_goal
                duration = 7
                unit = "days"
                
                # Regex for "1 week", "2 days", etc.
                match = re.search(r'(\d+)\s*(day|week|month)s?', title_text, re.IGNORECASE)
                if match:
                    try:
                        duration = int(match.group(1))
                        unit_str = match.group(2).lower()
                        if "day" in unit_str: unit = "days"
                        elif "week" in unit_str: unit = "weeks"
                        elif "month" in unit_str: unit = "months"
                        
                        # Convert weeks/months to days for consistency if preferred, 
                        # but our model supports units, so keep them.
                    except:
                        pass

                goal_data = {
                    "title": title_text,
                    "duration": duration,
                    "duration_unit": unit,
                    "priority": "Medium"
                }
            elif isinstance(suggested_goal, dict):
                 goal_data = suggested_goal
            else:
                 raise ValueError("Invalid format for suggested_goal")

            created_goal_title = goal_data.get("title", "New Goal")
            new_goal = models.Goal(
                user_id=current_user.id,
                title=created_goal_title,
                duration=goal_data.get("duration", 7),
                duration_unit=goal_data.get("duration_unit", "days"),
                priority=goal_data.get("priority", "Medium"),
                description="Auto-generated from chat conversation",
                subtasks=json.dumps([])
            )
            db.add(new_goal)
            db.commit()
        except Exception as e:
            print(f"❌ Failed to auto-create goal: {e}")
            created_goal_title = None

    # Generate Title (if it's the first message)
    new_title = None
    if len(history) == 0:
        if title_from_ai:
             new_title = title_from_ai
        else:
             # Fallback to local fast generation if AI didn't provide one
             new_title = generate_chat_title(user_message)
        
        update_chat_title(user_id, chat_id, new_title)

    return schemas.ChatResponse(
        response=ai_text, 
        chat_id=chat_id, 
        title=new_title, 
        mode=mode,
        memory_updated=memory_updated,
        goal_created=created_goal_title
    )

@app.get("/chats/{chat_id}/history")
def get_chat_history_endpoint(
    chat_id: str,
    current_user: models.User = Depends(auth.get_current_user)
):
    return get_chat_history(chat_id)
