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
from groq_service import get_ai_response, generate_chat_title, decompose_goal, generate_goal_reminder, generate_goal_quiz, generate_personalized_rewards
from datetime import datetime, timezone
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

def log_coin_transaction(user: models.User, description: str, amount: int):
    """
    Appends a new transaction to the user's coin history.
    """
    try:
        history = json.loads(user.coin_history) if user.coin_history else []
    except:
        history = []
        
    transaction = {
        "date": datetime.now().strftime("%Y-%m-%d"), # Simple date string
        # or full timestamp if preferred: datetime.now().isoformat()
        "description": description,
        "amount": amount
    }
    history.append(transaction)
    user.coin_history = json.dumps(history)


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
    
    # --- Daily Reward Logic ---
    now = datetime.now(timezone.utc)
    reward_message = None
    
    if user.last_login:
        last_date = user.last_login.date()
        today_date = now.date()
        if today_date > last_date:
            user.coins += 20 # Daily Check-in Reward (Updated to 20)
            log_coin_transaction(user, "Daily Check-in", 20)
            reward_message = "Daily check-in! +20 Coins"
    else:
        # First login ever
        user.coins += 50 # Welcome Bonus (adjusted to be moderate)
        log_coin_transaction(user, "First time login", 50)
        reward_message = "Welcome! +50 Coins"
        
    user.last_login = now
    db.commit()
    
    access_token = auth.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=schemas.User)
def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user

@app.put("/users/me/favorites")
def update_user_favorites(
    favorites: str = Body(..., embed=True),
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not favorites or not favorites.strip():
        current_user.favorites = ""
        current_user.rewards_cache = None
        current_user.coins = 0
        current_user.coin_history = "[]" # Clear History
        db.commit()
        return {"status": "cleared", "favorites": "", "coins": 0}

    was_empty = not current_user.favorites
    current_user.favorites = favorites
    current_user.rewards_cache = None # Clear cache
    
    if was_empty:
         current_user.coins += 100 # Updated: 100 points for setting favorites
         log_coin_transaction(current_user, "Preference Set", 100)
         
    db.commit()
    return {"status": "updated", "favorites": favorites, "coins": current_user.coins}



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
    # Check for duplicate goals with same name, description, and priority
    existing_goal = db.query(models.Goal).filter(
        models.Goal.user_id == current_user.id,
        models.Goal.title == goal.title,
        models.Goal.description == goal.description,
        models.Goal.priority == goal.priority,
        models.Goal.status != "Completed"  # Allow duplicates only if previous is completed
    ).first()
    
    if existing_goal:
        raise HTTPException(
            status_code=400, 
            detail="A goal with the same name, description, and priority already exists"
        )
    
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

    # Reward for Completion (Strict Check)
    if update_data.get('status') == 'completed' and not db_goal.rewarded:
        current_user.coins += 50 # Updated: 50 points for goal completion
        log_coin_transaction(current_user, f"Task '{db_goal.title}' Completed", 50)
        db_goal.rewarded = True 
        db.commit()
        print(f"💰 User rewarded 50 coins for completing goal {goal_id}")

    # Check for breakdown completion and generate quiz if needed
    if db_goal.subtasks:
        try:
             subtasks = json.loads(db_goal.subtasks)
             # Check if all subtasks are completed
             all_completed = subtasks and all(t.get("completed", False) for t in subtasks if isinstance(t, dict))
             
             # Generate quiz if all tasks completed and no quiz exists yet
             if all_completed and not db_goal.quiz_content:
                 print(f"🎉 Goal {goal_id} - All tasks completed! Generating quiz...")
                 quiz_data = generate_goal_quiz(db_goal.title, subtasks)
                 if quiz_data:
                     print(f"✅ Quiz generated successfully for goal {goal_id}")
                     db_goal.quiz_content = json.dumps(quiz_data)
                     db.commit()
                     db.refresh(db_goal)
                 else:
                     print(f"❌ Quiz generation returned None (might not be a learning goal)")
        except json.JSONDecodeError as e:
            print(f"Error parsing subtasks JSON for goal {goal_id}: {e}")
        except Exception as e:
            print(f"Error checking goal completion for quiz: {e}")

    return db_goal

@app.get("/goals/reminders")
def get_goal_reminders(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    """
    Checks active goals and returns daily reminders based on progress.
    """
    active_goals = db.query(models.Goal).filter(
        models.Goal.user_id == current_user.id,
        models.Goal.status != "completed"
    ).all()
    
    reminders = []
    today = datetime.now(timezone.utc)
    
    for goal in active_goals:
        # Calculate days elapsed since creation
        if not goal.created_at:
             continue
             
        # simplistic day diff
        created_at = goal.created_at.replace(tzinfo=timezone.utc) if goal.created_at.tzinfo is None else goal.created_at
        days_elapsed = (today - created_at).days + 1
        
        if days_elapsed > goal.duration:
             days_elapsed = goal.duration # Cap at max duration
        
        if days_elapsed <= 0: days_elapsed = 1
        
        # Only meaningful to send reminder if we have a breakdown or at least active
        subtasks = json.loads(goal.subtasks) if goal.subtasks else []
        
        # Generate Reminder
        message = generate_goal_reminder(goal.title, subtasks, days_elapsed, goal.duration)
        
        reminders.append({
            "goal_id": goal.id,
            "goal_title": goal.title,
            "day": days_elapsed,
            "message": message
        })
        
    return reminders

@app.get("/goals/{goal_id}/quiz")
def get_goal_quiz(goal_id: int, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    db_goal = db.query(models.Goal).filter(models.Goal.id == goal_id, models.Goal.user_id == current_user.id).first()
    if not db_goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    print(f"🔍 Quiz request for goal {goal_id}")
    print(f"   Quiz content exists: {bool(db_goal.quiz_content)}")
    print(f"   Quiz content preview: {db_goal.quiz_content[:100] if db_goal.quiz_content else 'None'}")
    
    if not db_goal.quiz_content:
        # Check if all tasks are completed
        if db_goal.subtasks:
            try:
                subtasks = json.loads(db_goal.subtasks)
                all_completed = all(t.get("completed", False) for t in subtasks if isinstance(t, dict))
                print(f"   All tasks completed: {all_completed}")
                if not all_completed:
                    return {"available": False, "message": "Complete all tasks first"}
            except:
                pass
        return {"available": False, "message": "No quiz available yet"}
    
    try:
        quiz_data = json.loads(db_goal.quiz_content)
        print(f"✅ Returning quiz with {len(quiz_data.get('questions', []))} questions")
        return {"available": True, "quiz": quiz_data}
    except Exception as e:
        print(f"❌ Error parsing quiz content: {e}")
        return {"available": False, "message": "Quiz data corrupted"}

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
    db_goal.status = "in_progress" # Reset status if it was completed
    db_goal.quiz_content = None   # Reset quiz since tasks changed
    # We do NOT reset 'rewarded' status typically to prevent farming, or reset it if meaningful change? 
    # For now, let's keep rewarded=True if they already got it once for this goal ID.
    db.commit()
    db.refresh(db_goal)
    return db_goal

# --- Rewards ---

@app.get("/users/me/rewards")
def get_user_rewards(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    """
    Generates a large list of 50+ reward items.
    Uses AI to generate based on favorites if available and not cached.
    """
    
    if current_user.rewards_cache:
        try:
             cached_items = json.loads(current_user.rewards_cache)
             if isinstance(cached_items, list) and len(cached_items) > 0:
                  return {
                      "coins": current_user.coins, 
                      "items": cached_items,
                      "history": json.loads(current_user.coin_history) if current_user.coin_history else []
                  }
        except:
             pass 

    favs = current_user.favorites
    items = []
    
    def get_id(idx): return f"rew_{idx}"
    idx_counter = 0

    if favs and len(favs.strip()) > 0:
        print(f"Generating personalized rewards for: {favs}")
        ai_rewards = generate_personalized_rewards(favs)
        
        if ai_rewards:
            for r in ai_rewards:
                items.append({
                    "id": get_id(idx_counter),
                    "name": r.get("name", "Reward"),
                    "cost": r.get("cost", 50),
                    "icon": r.get("icon", "gift"), 
                    "category": r.get("category", "General")
                })
                idx_counter += 1
    
    current_user.rewards_cache = json.dumps(items)
    db.commit()
            
    current_history = json.loads(current_user.coin_history) if current_user.coin_history else []
    
    if not current_history and current_user.coins > 0:
        backfilled_txns = []
        remaining = current_user.coins
        
        if remaining >= 50:
            backfilled_txns.append({
                "date": datetime.now().strftime("%Y-%m-%d"),
                "description": "Welcome Bonus (Legacy)",
                "amount": 50
            })
            remaining -= 50
            
        if remaining > 0:
            if remaining >= 100:
                backfilled_txns.append({
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "description": "Preferences Set (Legacy)",
                    "amount": 100
                })
                remaining -= 100
            
            if remaining > 0:
                backfilled_txns.append({
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "description": "Previous Earnings",
                    "amount": remaining
                })
        
        # Save inferred history
        current_user.coin_history = json.dumps(backfilled_txns)
        db.commit()
        current_history = backfilled_txns

    return {"coins": current_user.coins, "items": items, "history": current_history}

@app.post("/users/me/redeem")
def redeem_reward(
    request: schemas.RedeemRequest, 
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.coins < request.cost:
        raise HTTPException(status_code=400, detail="Insufficient coins")
    
    current_user.coins -= request.cost
    log_coin_transaction(current_user, "Reward Redeemed", -request.cost)
    
    # Track purchased reward
    purchased_reward = models.PurchasedReward(
        user_id=current_user.id,
        reward_name=request.reward_name,
        reward_cost=request.cost
    )
    db.add(purchased_reward)
    db.commit()
    
    return {"status": "success", "new_balance": current_user.coins}

@app.get("/users/me/purchased-rewards", response_model=list[schemas.PurchasedReward])
def get_purchased_rewards(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    purchased = db.query(models.PurchasedReward).filter(
        models.PurchasedReward.user_id == current_user.id
    ).order_by(models.PurchasedReward.purchased_at.desc()).all()
    return purchased

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
    
    # --- CHECK FOR INTEGRATION REQUESTS ---
    from groq_service import detect_integration_intent
    integration_intent = detect_integration_intent(user_message)
    
    if integration_intent["type"] != "none":
        # Handle Integration Request
        integration_type = integration_intent["type"]
        action = integration_intent["action"]
        
        # Check if integration is connected
        integration = db.query(models.Integration).filter(
            models.Integration.user_id == current_user.id,
            models.Integration.provider == integration_type
        ).first()
        
        if not integration or not integration.access_token:
            ai_text = f"❌ You haven't connected your {integration_type.capitalize()} account yet. Please connect it first from the Integrations page."
            add_message(chat_id, "user", user_message)
            add_message(chat_id, "model", ai_text)
            return schemas.ChatResponse(
                response=ai_text,
                chat_id=chat_id,
                title=None,
                mode="primary",
                memory_updated=False,
                goal_created=None
            )
        
        # Call the appropriate service
        try:
            if integration_type == "github":
                from github_service import (
                    fetch_github_repos, get_github_repo_count,
                    create_github_repo, get_github_repo,
                    update_github_repo, delete_github_repo
                )
                
                if action == "count":
                    result = get_github_repo_count(integration.access_token)
                    if "error" in result:
                        ai_text = f"❌ Error: {result['error']}"
                    else:
                        ai_text = f"📊 You have **{result['count']} repositories** on GitHub!"
                
                elif action == "list":
                    result = fetch_github_repos(integration.access_token)
                    if isinstance(result, dict) and "error" in result:
                        ai_text = f"❌ Error: {result['error']}"
                    else:
                        ai_text = f"## Your GitHub Repositories ({len(result)} total)\n\n"
                        for repo in result[:10]:  # Show first 10
                            ai_text += f"### 📦 [{repo['name']}]({repo['html_url']})\n"
                            ai_text += f"- **Description:** {repo['description'] or 'No description'}\n"
                            ai_text += f"- **Stars:** ⭐ {repo['stars']} | **Language:** {repo['language'] or 'N/A'} | **Private:** {'🔒 Yes' if repo['private'] else '🌍 No'}\n\n"
                
                elif action == "create":
                    # Extract repo name from message
                    import re
                    match = re.search(r'(?:create|make|new)\s+(?:repo|repository)\s+(?:called|named)?\s*["\']?([a-zA-Z0-9_-]+)["\']?', user_message, re.IGNORECASE)
                    if match:
                        repo_name = match.group(1)
                        result = create_github_repo(integration.access_token, repo_name)
                        if "error" in result:
                            ai_text = f"❌ Error: {result['error']}"
                        else:
                            ai_text = f"✅ Successfully created repository **[{result['name']}]({result['html_url']})**!"
                    else:
                        ai_text = "❌ Please specify a repository name. Example: 'Create repo called my-project'"
                
                elif action == "update":
                    # Extract repo info: "rename X to Y" or "update X description to Z"
                    import re
                    
                    # Pattern 1: "rename repo-name to new-name"
                    rename_match = re.search(r'rename\s+(?:repo\s+)?([a-zA-Z0-9_-]+)\s+to\s+([a-zA-Z0-9_-]+)', user_message, re.IGNORECASE)
                    
                    # Pattern 2: "update repo-name description to 'text'"
                    desc_match = re.search(r'update\s+([a-zA-Z0-9_-]+)\s+description\s+to\s+["\'](.+?)["\']', user_message, re.IGNORECASE)
                    
                    if rename_match:
                        old_name = rename_match.group(1)
                        new_name = rename_match.group(2)
                        
                        # Get owner from token (assuming it's the authenticated user)
                        user_repos = fetch_github_repos(integration.access_token, per_page=1)
                        if user_repos and len(user_repos) > 0:
                            owner = user_repos[0]['full_name'].split('/')[0]
                            result = update_github_repo(integration.access_token, owner, old_name, new_name=new_name)
                            if "error" in result:
                                ai_text = f"❌ Error: {result['error']}"
                            else:
                                ai_text = f"✅ Successfully renamed repository to **[{result['name']}]({result['html_url']})**!"
                        else:
                            ai_text = "❌ Could not determine your GitHub username."
                    
                    elif desc_match:
                        repo_name = desc_match.group(1)
                        new_desc = desc_match.group(2)
                        
                        user_repos = fetch_github_repos(integration.access_token, per_page=1)
                        if user_repos and len(user_repos) > 0:
                            owner = user_repos[0]['full_name'].split('/')[0]
                            result = update_github_repo(integration.access_token, owner, repo_name, description=new_desc)
                            if "error" in result:
                                ai_text = f"❌ Error: {result['error']}"
                            else:
                                ai_text = f"✅ Successfully updated **{result['name']}** description!"
                        else:
                            ai_text = "❌ Could not determine your GitHub username."
                    else:
                        ai_text = "❌ Please specify update details. Examples:\n- 'Rename old-repo to new-repo'\n- 'Update my-repo description to \"New description\"'"
                
                elif action == "delete":
                    # Extract repo name: "delete repo-name"
                    import re
                    match = re.search(r'(?:delete|remove)\s+(?:repo|repository)?\s*([a-zA-Z0-9_-]+)', user_message, re.IGNORECASE)
                    
                    if match:
                        repo_name = match.group(1)
                        
                        # Get owner
                        user_repos = fetch_github_repos(integration.access_token, per_page=1)
                        if user_repos and len(user_repos) > 0:
                            owner = user_repos[0]['full_name'].split('/')[0]
                            result = delete_github_repo(integration.access_token, owner, repo_name)
                            if "error" in result:
                                ai_text = f"❌ Error: {result['error']}"
                            else:
                                ai_text = f"✅ Successfully deleted repository **{repo_name}**!"
                        else:
                            ai_text = "❌ Could not determine your GitHub username."
                    else:
                        ai_text = "❌ Please specify a repository name. Example: 'Delete repo called test-repo'"
                
                else:
                    ai_text = f"⚠️ Action '{action}' is not fully implemented yet for GitHub."
            
            elif integration_type == "onenote":
                from onenote_service import (
                    fetch_onenote_pages, get_onenote_page_count,
                    get_onenote_sections, get_onenote_page
                )
                
                if action == "count":
                    result = get_onenote_page_count(integration.access_token)
                    if "error" in result:
                        ai_text = f"❌ Error: {result['error']}"
                    else:
                        ai_text = f"📊 You have **{result['count']} pages** in OneNote!"
                
                elif action == "list":
                    result = fetch_onenote_pages(integration.access_token)
                    if isinstance(result, dict) and "error" in result:
                        ai_text = f"❌ Error: {result['error']}"
                    else:
                        ai_text = f"## Your OneNote Pages ({len(result)} total)\n\n"
                        for page in result[:10]:  # Show first 10
                            ai_text += f"### 📄 {page['title']}\n"
                            ai_text += f"- **Created:** {page.get('created_at', 'N/A')[:10]}\n"
                            ai_text += f"- **Modified:** {page.get('modified_at', 'N/A')[:10]}\n\n"
                
                elif action == "sections":
                    result = get_onenote_sections(integration.access_token)
                    if isinstance(result, dict) and "error" in result:
                        ai_text = f"❌ Error: {result['error']}"
                    else:
                        ai_text = f"## Your OneNote Sections ({len(result)} total)\n\n"
                        for section in result:
                            ai_text += f"- 📁 **{section['name']}** (ID: `{section['id']}`)\n"
                
                elif action == "get":
                    # Extract page ID
                    import re
                    match = re.search(r'(?:show|get|details)\s+(?:page|note)\s+(\S+)', user_message, re.IGNORECASE)
                    
                    if match:
                        page_id = match.group(1)
                        result = get_onenote_page(integration.access_token, page_id)
                        if "error" in result:
                            ai_text = f"❌ Error: {result['error']}"
                        else:
                            ai_text = f"## 📄 {result['title']}\n\n"
                            ai_text += f"- **Created:** {result.get('created_at', 'N/A')[:10]}\n"
                            ai_text += f"- **Modified:** {result.get('modified_at', 'N/A')[:10]}\n"
                            ai_text += f"- **Page ID:** `{result['id']}`\n"
                            if result.get('links', {}).get('oneNoteWebUrl'):
                                ai_text += f"- **[Open in OneNote]({result['links']['oneNoteWebUrl']['href']})**\n"
                    else:
                        ai_text = "❌ Please specify a page ID. Example: 'Show page {page-id}'"
                
                else:
                    ai_text = f"⚠️ OneNote integration is read-only. Available commands: count, list, sections, get."
        
        except Exception as e:
            ai_text = f"❌ An error occurred: {str(e)}"
        
        # Save messages
        add_message(chat_id, "user", user_message)
        add_message(chat_id, "model", ai_text)
        
        return schemas.ChatResponse(
            response=ai_text,
            chat_id=chat_id,
            title=None,
            mode="primary",
            memory_updated=False,
            goal_created=None
        )
    
    # --- REGULAR CHAT FLOW (Non-integration) ---
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

# ----------------------------
# Integration Routes
# ----------------------------

@app.post("/integrations/connect", response_model=schemas.IntegrationStatus)
def connect_integration(
    request: schemas.IntegrationConnect,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    # Check if integration already exists
    integration = db.query(models.Integration).filter(
        models.Integration.user_id == current_user.id,
        models.Integration.provider == request.provider
    ).first()

    if not integration:
        integration = models.Integration(
            user_id=current_user.id,
            provider=request.provider
        )
        db.add(integration)

    # Update tokens
    integration.access_token = request.access_token
    integration.refresh_token = request.refresh_token
    
    if request.expires_in:
        integration.expires_at = datetime.now(timezone.utc) + timedelta(seconds=request.expires_in)
    
    db.commit()
    db.refresh(integration)
    
    return {"provider": request.provider, "is_connected": True, "last_synced": datetime.now()}

@app.get("/integrations", response_model=list[schemas.IntegrationStatus])
def list_integrations(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    integrations = db.query(models.Integration).filter(models.Integration.user_id == current_user.id).all()
    results = []
    
    # We want to show status for supported providers even if not connected
    supported = ["github", "onenote"]
    connected_map = {i.provider: i for i in integrations}
    
    for prov in supported:
        if prov in connected_map:
            results.append({
                "provider": prov,
                "is_connected": True,
                "last_synced": connected_map[prov].created_at # approximate
            })
        else:
             results.append({
                "provider": prov,
                "is_connected": False,
                "last_synced": None
            })
    return results

@app.delete("/integrations/{provider}")
def disconnect_integration(
    provider: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Disconnect an integration by deleting the access token from the database."""
    integration = db.query(models.Integration).filter(
        models.Integration.user_id == current_user.id,
        models.Integration.provider == provider
    ).first()
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found or not connected")
    
    db.delete(integration)
    db.commit()
    
    return {"message": f"{provider} integration disconnected successfully"}

# --- Service Proxies ---

# GitHub Endpoints

@app.get("/integrations/github/repos", response_model=list[schemas.GitHubRepo])
def get_user_github_repos(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    integration = db.query(models.Integration).filter(
        models.Integration.user_id == current_user.id,
        models.Integration.provider == "github"
    ).first()
    
    if not integration or not integration.access_token:
        raise HTTPException(status_code=400, detail="GitHub not connected")

    from github_service import fetch_github_repos
    result = fetch_github_repos(integration.access_token)
    
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
        
    return result

@app.get("/integrations/github/repos/count")
def get_github_repo_count(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    integration = db.query(models.Integration).filter(
        models.Integration.user_id == current_user.id,
        models.Integration.provider == "github"
    ).first()
    
    if not integration or not integration.access_token:
        raise HTTPException(status_code=400, detail="GitHub not connected")

    from github_service import get_github_repo_count
    result = get_github_repo_count(integration.access_token)
    
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
        
    return result

@app.post("/integrations/github/repos", response_model=schemas.GitHubRepoDetail)
def create_github_repo(
    request: schemas.GitHubRepoCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    integration = db.query(models.Integration).filter(
        models.Integration.user_id == current_user.id,
        models.Integration.provider == "github"
    ).first()
    
    if not integration or not integration.access_token:
        raise HTTPException(status_code=400, detail="GitHub not connected")

    from github_service import create_github_repo
    result = create_github_repo(
        integration.access_token,
        request.name,
        request.private,
        request.description
    )
    
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
        
    return result

@app.get("/integrations/github/repos/{owner}/{repo}", response_model=schemas.GitHubRepoDetail)
def get_specific_github_repo(
    owner: str,
    repo: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    integration = db.query(models.Integration).filter(
        models.Integration.user_id == current_user.id,
        models.Integration.provider == "github"
    ).first()
    
    if not integration or not integration.access_token:
        raise HTTPException(status_code=400, detail="GitHub not connected")

    from github_service import get_github_repo
    result = get_github_repo(integration.access_token, owner, repo)
    
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
        
    return result

@app.put("/integrations/github/repos/{owner}/{repo}", response_model=schemas.GitHubRepoDetail)
def update_github_repo_endpoint(
    owner: str,
    repo: str,
    request: schemas.GitHubRepoUpdate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    integration = db.query(models.Integration).filter(
        models.Integration.user_id == current_user.id,
        models.Integration.provider == "github"
    ).first()
    
    if not integration or not integration.access_token:
        raise HTTPException(status_code=400, detail="GitHub not connected")

    from github_service import update_github_repo
    result = update_github_repo(
        integration.access_token,
        owner,
        repo,
        request.new_name,
        request.description
    )
    
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
        
    return result

@app.delete("/integrations/github/repos/{owner}/{repo}")
def delete_github_repo_endpoint(
    owner: str,
    repo: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    integration = db.query(models.Integration).filter(
        models.Integration.user_id == current_user.id,
        models.Integration.provider == "github"
    ).first()
    
    if not integration or not integration.access_token:
        raise HTTPException(status_code=400, detail="GitHub not connected")

    from github_service import delete_github_repo
    result = delete_github_repo(integration.access_token, owner, repo)
    
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
        
    return result

# OneNote Endpoints

@app.get("/integrations/onenote/pages", response_model=list[schemas.OneNotePage])
def get_user_onenote_pages(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    integration = db.query(models.Integration).filter(
        models.Integration.user_id == current_user.id,
        models.Integration.provider == "onenote"
    ).first()
    
    if not integration or not integration.access_token:
        raise HTTPException(status_code=400, detail="OneNote not connected")

    from onenote_service import fetch_onenote_pages
    result = fetch_onenote_pages(integration.access_token)
    
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
        
    return result

@app.get("/integrations/onenote/pages/count")
def get_onenote_page_count(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    integration = db.query(models.Integration).filter(
        models.Integration.user_id == current_user.id,
        models.Integration.provider == "onenote"
    ).first()
    
    if not integration or not integration.access_token:
        raise HTTPException(status_code=400, detail="OneNote not connected")

    from onenote_service import get_onenote_page_count
    result = get_onenote_page_count(integration.access_token)
    
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
        
    return result

@app.get("/integrations/onenote/sections", response_model=list[schemas.OneNoteSection])
def get_onenote_sections(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    integration = db.query(models.Integration).filter(
        models.Integration.user_id == current_user.id,
        models.Integration.provider == "onenote"
    ).first()
    
    if not integration or not integration.access_token:
        raise HTTPException(status_code=400, detail="OneNote not connected")

    from onenote_service import get_onenote_sections
    result = get_onenote_sections(integration.access_token)
    
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
        
    return result

@app.get("/integrations/onenote/pages/{page_id}", response_model=schemas.OneNotePage)
def get_specific_onenote_page(
    page_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    integration = db.query(models.Integration).filter(
        models.Integration.user_id == current_user.id,
        models.Integration.provider == "onenote"
    ).first()
    
    if not integration or not integration.access_token:
        raise HTTPException(status_code=400, detail="OneNote not connected")

    from onenote_service import get_onenote_page
    result = get_onenote_page(integration.access_token, page_id)
    
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
        
    return result

