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
