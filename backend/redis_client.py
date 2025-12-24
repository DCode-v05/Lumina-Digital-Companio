import redis
import json
import uuid
import time
from config import REDIS_HOST, REDIS_PORT

try:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    redis_client.ping()
    print("Connected to Redis")
except redis.ConnectionError:
    print("Could not connect to Redis. Make sure it is running.")
    redis_client = None

def get_redis_client():
    return redis_client

# --- Chat Management ---

def create_chat(user_id: str, title: str = "New Chat"):
    if not redis_client:
        return None
    
    chat_id = str(uuid.uuid4())
    timestamp = time.time()
    
    # Store metadata
    metadata = {
        "id": chat_id,
        "title": title,
        "created_at": timestamp
    }
    
    # Add to user's list of chats (using a Hash for O(1) access/update)
    # Key: user:{user_id}:chats  Field: chat_id  Value: JSON(metadata)
    redis_client.hset(f"user:{user_id}:chats", chat_id, json.dumps(metadata))
    
    return metadata

def get_user_chats(user_id: str):
    if not redis_client:
        return []
    
    # Get all fields from the hash
    chats_raw = redis_client.hgetall(f"user:{user_id}:chats")
    
    # Convert to list and sort by created_at (descending)
    chats = [json.loads(data) for data in chats_raw.values()]
    chats.sort(key=lambda x: x['created_at'], reverse=True)
    
    return chats

def delete_chat_session(user_id: str, chat_id: str):
    if not redis_client:
        return
    
    # 1. Remove from user's list
    redis_client.hdel(f"user:{user_id}:chats", chat_id)
    
    # 2. Delete the message history
    redis_client.delete(f"chat:{chat_id}:messages")

def update_chat_title(user_id: str, chat_id: str, new_title: str):
    if not redis_client:
        return

    # Get existing meta
    raw_meta = redis_client.hget(f"user:{user_id}:chats", chat_id)
    if raw_meta:
        meta = json.loads(raw_meta)
        meta['title'] = new_title
        redis_client.hset(f"user:{user_id}:chats", chat_id, json.dumps(meta))

# --- Message History ---

def get_chat_history(chat_id: str):
    if not redis_client:
        return []
    
    # Get all messages
    # Key: chat:{chat_id}:messages
    history = redis_client.lrange(f"chat:{chat_id}:messages", 0, -1)
    return [json.loads(msg) for msg in history]

def add_message(chat_id: str, role: str, content: str):
    if not redis_client:
        return
    
    message = {"role": role, "parts": [content]}
    redis_client.rpush(f"chat:{chat_id}:messages", json.dumps(message))

# --- User Profile (Personalization) ---

def get_user_profile(user_id: str) -> str:
    """Retrieve the personalized profile string for a user."""
    if not redis_client:
        return ""
    
    # Check if we have the new structured format first
    raw_data = redis_client.get(f"user:{user_id}:profile_structured")
    if raw_data:
        facts = json.loads(raw_data)
        # Return just the text part for the AI context
        return "\n".join([f['text'] for f in facts])
    
    # Fallback to old simple string format
    return redis_client.get(f"user:{user_id}:profile") or ""

def get_user_facts_structured(user_id: str):
    """Retrieve the raw structured list of fact objects."""
    if not redis_client:
        return []
        
    raw_data = redis_client.get(f"user:{user_id}:profile_structured")
    if raw_data:
        return json.loads(raw_data)
        
    # Migration: Check if old string exists
    old_str = redis_client.get(f"user:{user_id}:profile")
    if old_str:
        # Convert old format to new on the fly
        facts_list = [line.strip() for line in old_str.split('\n') if line.strip()]
        structured = [{"text": f, "created_at": time.time(), "expiry": None} for f in facts_list]
        return structured
        
    return []

def update_user_profile(user_id: str, profile_data: str):
    """
    Update the personalized profile.
    NOW INTELLIGENT: It takes the *new* profile string (which might be appended),
    and ensures the structured storage is synced.
    
    Ideally, the caller should pass the specific NEW fact to add, but our current architecture
    passes the whole concatenated string.
    
    Workaround: We will re-save the whole string for context, AND try to update structured list.
    """
    if not redis_client:
        return
    
    # 1. Update the plain text version (for AI context speed)
    redis_client.set(f"user:{user_id}:profile", profile_data)
    
    # 2. Update metadata
    metadata = {
        "last_updated": time.time(),
        "item_count": len(profile_data.split('\n')) if profile_data else 0
    }
    redis_client.set(f"user:{user_id}:profile_meta", json.dumps(metadata))
    
    # 3. Re-sync structured data (Simple approach: Split string, check existence)
    # This is a bit inefficient but safe for now.
    current_lines = [line.strip() for line in profile_data.split('\n') if line.strip()]
    
    existing_structured = get_user_facts_structured(user_id)
    existing_map = {f['text']: f for f in existing_structured}
    
    new_structured = []
    for line in current_lines:
        if line in existing_map:
            # Keep existing metadata (timestamp, potential expiry)
            new_structured.append(existing_map[line])
        else:
            # New fact!
            # Check if it looks temporal (heuristic)
            # This is a basic check. Ideally the AI should flag "temporal" facts.
            # For now, we defaults to permanent unless specified.
            expiry = None
            if "in 2 weeks" in line.lower() or "in 1 week" in line.lower():
                 # Auto-expire in 14 days for safety
                expiry = time.time() + (14 * 24 * 3600)
            
            new_structured.append({
                "text": line,
                "created_at": time.time(),
                "expiry": expiry
            })
            
    redis_client.set(f"user:{user_id}:profile_structured", json.dumps(new_structured))

def clean_expired_facts(user_id: str):
    """Checks and removes expired facts."""
    if not redis_client:
        return
        
    facts = get_user_facts_structured(user_id)
    now = time.time()
    
    # Filter out expired items
    valid_facts = [f for f in facts if not (f.get('expiry') and f['expiry'] < now)]
    
    if len(valid_facts) < len(facts):
        print(f"🧹 Use {user_id}: Cleaned {len(facts) - len(valid_facts)} expired memories.")
        # Update Redis
        redis_client.set(f"user:{user_id}:profile_structured", json.dumps(valid_facts))
        
        # Sync plain text version
        plain_text = "\n".join([f['text'] for f in valid_facts])
        redis_client.set(f"user:{user_id}:profile", plain_text)
