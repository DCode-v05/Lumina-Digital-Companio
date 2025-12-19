from transformers import pipeline
from sqlalchemy.orm import Session
from sqlalchemy import desc
import models
from datetime import datetime, timedelta

try:
    classifier = pipeline(
        "text-classification", 
        model="j-hartmann/emotion-english-distilroberta-base", 
        return_all_scores=True
    )
    print("✅ Emotion analysis model loaded successfully")
except Exception as e:
    print(f"⚠️ Failed to load emotion model: {e}")
    classifier = None

def analyze_emotion(text: str):
    """
    Analyzes the text and returns the top emotion and its score.
    """
    if not classifier or not text.strip():
        return None, 0.0
    
    try:
        results = classifier(text)
        scores = results[0]
        top_emotion = max(scores, key=lambda x: x["score"])
        print(top_emotion)
        return top_emotion['label'], top_emotion['score']
    except Exception as e:
        print(f"Error analyzing emotion: {e}")
        return None, 0.0

def log_emotion(db: Session, user_id: int, emotion: str, score: float):
    """
    Stores the detected emotion in the database.
    """
    if not emotion:
        return

    new_log = models.EmotionLog(
        user_id=user_id,
        emotion=emotion,
        score=score
    )
    db.add(new_log)
    db.commit()

def get_recent_emotions_summary(db: Session, user_id: int, minutes: int = 15) -> str:
    """
    Retrieves emotions from the last N minutes and returns a summary string.
    """
    time_threshold = datetime.now() - timedelta(minutes=minutes)
    
    logs = db.query(models.EmotionLog)\
        .filter(models.EmotionLog.user_id == user_id)\
        .filter(models.EmotionLog.timestamp >= time_threshold)\
        .order_by(desc(models.EmotionLog.timestamp))\
        .all()
        
    if not logs:
        return ""
        
    # Create a frequency map or just a chronological list
    # Let's do a chronological list of significant emotions (> 0.5 score)
    significant_logs = [log for log in logs if log.score > 0.5]
    
    if not significant_logs:
        return ""

    emotions = [f"{log.emotion} ({int(log.score*100)}%)" for log in significant_logs[:5]] # Limit to last 5
    return "Recent User Emotions: " + ", ".join(emotions) if emotions else ""
