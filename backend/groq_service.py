import os
import json
import re
from groq import Groq
from config import GROQ_API_KEY, MODEL_CONFIG

# Initialize Groq Client
client = Groq(api_key=GROQ_API_KEY)

# --- INTEGRATION DETECTION ---

def detect_integration_intent(user_message):
    """
    Detects if the user is requesting GitHub or OneNote actions.
    Returns: {"type": "github|onenote|none", "action": "list|create|count|get|update|delete", "params": {}}
    """
    message_lower = user_message.lower()
    
    # GitHub detection patterns
    github_patterns = {
        "count": ["how many repos", "count my repos", "total repos", "number of repositories"],
        "list": ["show repos", "list repos", "my repositories", "github repos", "what repos"],
        "create": ["create repo", "make repo", "new repository", "add repository"],
        "get": ["show repo", "details of repo", "info about repo"],
        "update": ["rename repo", "update repo", "change repo"],
        "delete": ["delete repo", "remove repo"]
    }
    
    # OneNote detection patterns (read-only)
    onenote_patterns = {
        "count": ["how many pages", "count my notes", "total pages", "number of notes", "count notes", "how many onenote"],
        "list": ["show pages", "list notes", "my onenote", "onenote pages", "what notes", "show notes", "list my notes"],
        "sections": ["show sections", "list sections", "onenote sections", "what sections"],
        "get": ["show page", "details of page", "info about note", "get page"]
    }
    
    # Check GitHub
    for action, patterns in github_patterns.items():
        if any(pattern in message_lower for pattern in patterns):
            return {"type": "github", "action": action, "params": {}}
    
    # Check OneNote  
    for action, patterns in onenote_patterns.items():
        if any(pattern in message_lower for pattern in patterns):
            return {"type": "onenote", "action": action, "params": {}}
    
    return {"type": "none", "action": None, "params": {}}

# --- PROMPTS & BEHAVIOR CONFIGURATION ---

JSON_SCHEMA_INSTRUCTION = """
### RESPONSE FORMAT (STRICT JSON ONLY)
You must output a single valid JSON object. Do not include any text before or after the JSON.
Required JSON Structure:
{
  "title": "string or null",            // Generated ONLY for the very first message of a chat (2-5 words). Otherwise null.
  "response": "string",                 // Your natural language response (markdown supported).
  "new_user_facts": ["string"] or null, // List of NEW, PERMANENT user facts (e.g., "Studying Bio", "Visual Learner"). Check Context first!
  "suggested_goal": {                   // Generate ONLY if user explicitly states a goal with a timeframe. Otherwise null.
      "title": "string",                // Concise goal title (e.g. "Learn Python")
      "duration": integer,              // Numeric value (e.g. 14)
      "duration_unit": "string",        // "days", "weeks", or "months"
      "priority": "string"              // "High", "Medium", or "Low"
  } 
}
NOTE: 'suggested_goal' must be a JSON Object or null. NEVER a string.
"""

MEMORY_INSTRUCTION = """
### MEMORY UPDATE RULES
1. Analyze the "User Profile Context" provided below.
2. If the user mentions a fact about their identity, studies, or long-term goals:
   - FAST CHECK: Is this fact already in the "User Profile Context"?
   - IF YES (even if phrased differently): Do NOT include it in 'new_user_facts'.
   - IF NO: Add it to 'new_user_facts' as a concise string.
3. Ignore temporary states ("I am hungry") or trivial likes ("I like blue").
"""

GOAL_INSTRUCTION = """
### GOAL CREATION RULES
1. Trigger: Only create a 'suggested_goal' if the user EXPLICITLY mentions wanting to achieve a specific outcome within a specific TIME.
   - Example (Trigger): "I want to learn React in 2 weeks." -> Create Goal.
   - Example (No Trigger): "I want to learn React." -> No Goal (no time).
   - Example (No Trigger): "How do I use React?" -> No Goal.
2. Structure: Ensure 'suggested_goal' is a valid object with 'title', 'duration', 'duration_unit'.
"""

PRIMARY_INSTRUCTION = f"""
You are Lumina, a Digital Student Companion designed to support students academically, emotionally, and personally.

### CORE IDENTITY
- **Role**: Trusted academic partner and mentor.
- **Tone**: Empathetic, professional, encouraging, and clear.
- **Goal**: Help students understand concepts, manage stress, and stay organized.

### KEY BEHAVIORS
1. **Empathy First**: Always acknowledge the user's emotional state (stress, excitement) before solving problems.
2. **Context Aware**: Use the conservation history. Don't repeat yourself.
3. **Structured & Clear**: Use Markdown (Bold, Lists) to make answers readable.
4. **Prerequisites**: If a topic is complex, briefly check if the user knows the basics.

{JSON_SCHEMA_INSTRUCTION}
{MEMORY_INSTRUCTION}
{GOAL_INSTRUCTION}
"""

ACADEMIC_INSTRUCTION = f"""
You are Lumina Research Guide, a specialized academic assistant for deep research and analysis.

### CORE IDENTITY
- **Role**: Research assistant and subject matter expert.
- **Tone**: Scholarly, objective, precise, and rigorous.

### KEY BEHAVIORS
1. **Depth**: Provide comprehensive context, historical background, and theoretical foundations.
2. **Citations**: Mention standard texts, papers, or reputable sources where possible.
3. **Structure**: Use clear headings, bullet points, and definitions.
4. **No Fluff**: Get straight to the analysis.

{JSON_SCHEMA_INSTRUCTION}
{MEMORY_INSTRUCTION}
{GOAL_INSTRUCTION}
"""

REASONING_INSTRUCTION = f"""
You are Lumina Problem Solver, an expert in logic, mathematics, and computer science.

### CORE IDENTITY
- **Role**: Senior Engineer and Mathematician.
- **Tone**: Logical, structured, and precise.

### KEY BEHAVIORS
1. **Chain of Thought**: Break down complex problems into steps. Explain the 'Why'.
2. **Code Quality**: Write production-grade code. handle edge cases. Comment complex logic.
3. **Verification**: Double-check math and logic before concluding.

{JSON_SCHEMA_INSTRUCTION}
{MEMORY_INSTRUCTION}
{GOAL_INSTRUCTION}
"""

TEACHING_INSTRUCTION = f"""
You are Lumina Tutor, a patient and skilled educator.

### CORE IDENTITY
- **Role**: Personal Tutor.
- **Tone**: Patient, encouraging, simple, and Socratic.

### KEY BEHAVIORS
1. **Scaffolded Learning**: Start simple. Explain the core concept, then add details.
2. **Analogies**: Use real-world examples to explain abstract ideas.
3. **Check-ins**: Ask questions to ensure the student follows. "Does this make sense so far?"
4. **Bite-Sized**: Don't overwhelm. One concept at a time.

{JSON_SCHEMA_INSTRUCTION}
{MEMORY_INSTRUCTION}
{GOAL_INSTRUCTION}
"""

SYSTEM_INSTRUCTIONS = {
    "primary": PRIMARY_INSTRUCTION,
    "academic": ACADEMIC_INSTRUCTION,
    "reasoning": REASONING_INSTRUCTION,
    "teaching": TEACHING_INSTRUCTION
}

def classify_request(user_message):
    """
    Uses the primary model to classify the user's intent into one of the 4 modes.
    """
    try:
        messages = [
            {
                "role": "system",
                "content": """
                You are an Intent Classifier. Analyze the user's prompt and strictly categorize it into exactly one of the following 4 categories:
                
                1. "academic": Use this ONLY for deep research, specific citation requests, or historical analysis. DO NOT use for general broad interest.
                2. "reasoning": Use this for complex math problems, specific coding challenges, or logic puzzles.
                3. "teaching": Use this if the user EXPLICITLY asks to learn a new topic step-by-step (e.g., "Teach me python").
                4. "primary": Use this for everything else, including GENERAL INTEREST (e.g. "I am interested in ML"), greetings, emotional support, or vague questions.

                Output strictly valid JSON with a single key "mode".
                Example: {"mode": "reasoning"}
                """
            },
            {
                "role": "user",
                "content": user_message
            }
        ]

        completion = client.chat.completions.create(
            model=MODEL_CONFIG["primary"], # Use lightweight model for routing
            messages=messages,
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        result_text = completion.choices[0].message.content.strip()
        data = json.loads(result_text)
        return data.get("mode", "primary")

    except Exception as e:
        print(f"⚠️ Classification failed: {e}")
        return "primary"



def get_ai_response(history, user_message, user_profile="", user_name=None):
    try:
        # Dynamic Mode Selection (Router)
        # Enforce backend routing.
        
        # We only route based on the *latest* message usually.
        detected_mode = classify_request(user_message)
        print(f"🧭 Router decided mode: {detected_mode}")
        
        # Fallback if classifier returns garbage
        if detected_mode not in MODEL_CONFIG:
            detected_mode = "primary"

        # Determine Model
        model_name = MODEL_CONFIG.get(detected_mode, MODEL_CONFIG["primary"])
        
        # Select System Instruction based on Mode
        system_instruction = SYSTEM_INSTRUCTIONS.get(detected_mode, PRIMARY_INSTRUCTION)

        # Prepare Messages
        # Inject Name into System Instruction if possible, or just append strictly to user context
        if user_name:
             system_instruction += f"\n\nContext: The user's name is {user_name}. When storing 'new_user_facts', refer to them as '{user_name}' instead of 'User' if it sounds natural, or 'User' is fine."

        messages = [{"role": "system", "content": system_instruction}]
        
        # Optimization: Limit history to last 10 messages (5 turns)
        trimmed_history = history[-10:] if len(history) > 10 else history
        
        # Convert History (Gemini -> OpenAI format)
        for msg in trimmed_history:
            role = "assistant" if msg["role"] == "model" else "user"
            content = msg["parts"][0] if isinstance(msg["parts"], list) else str(msg["parts"])
            messages.append({"role": role, "content": content})
            
        # Add Current User Message with Context
        effective_message = user_message
        context_parts = []
        if user_profile:
             context_parts.append(f"User Profile Context:\n{user_profile}")
        if user_name:
             context_parts.append(f"User Name: {user_name}")
        
        if context_parts:
             effective_message = "\n\n".join(context_parts) + f"\n\nUser Query:\n{user_message}"
        
        # Explicit Title Request for First Message
        if not history:
             effective_message += "\n\n(System: This is the first message. Please generate a 'title' field in the JSON response.)"

        messages.append({"role": "user", "content": effective_message})

        # Call Groq API
        print(f"🤖 Calling Groq with model: {model_name} (Mode: {detected_mode})")
        try:
            completion = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0.7,
                stream=False,
                response_format={"type": "json_object"}
            )
            text = completion.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"⚠️ Error with model {model_name}: {e}")
            if model_name != MODEL_CONFIG["reasoning"]:
                 fallback_model = MODEL_CONFIG["reasoning"] if detected_mode != "reasoning" else MODEL_CONFIG["primary"]
                 print(f"🔄 Retrying with fallback: {fallback_model}")
                 completion = client.chat.completions.create(
                    model=fallback_model,
                    messages=messages,
                    temperature=0.7,
                    stream=False,
                    response_format={"type": "json_object"}
                 )
                 text = completion.choices[0].message.content.strip()
            else:
                 raise e

        final_response = "I had trouble processing that. Please try again."
        extracted_title = None
        new_facts = None
        suggested_goal = None

        try:
            # Enhanced JSON Cleanup
            clean_text = text.strip()
            start_index = clean_text.find('{')
            end_index = clean_text.rfind('}')
            
            if start_index != -1 and end_index != -1:
                clean_text = clean_text[start_index : end_index + 1]
                data = json.loads(clean_text)
                
                final_response = data.get("response", text)
                extracted_title = data.get("title")
                new_facts = data.get("new_user_facts")
                suggested_goal = data.get("suggested_goal")
            else:
                print("⚠️ No valid JSON found in response.")
                final_response = text

        except json.JSONDecodeError:
            print("JSON Parse Failed in get_ai_response. Raw text:", text[:100])
            final_response = text
            suggested_goal = None

        return final_response, extracted_title, new_facts, detected_mode, suggested_goal

    except Exception as e:
        print(f"Error calling Groq: {e}")
        return "I'm having trouble connecting to my brain right now.", None, None, "primary", None

def generate_chat_title(user_message):
    return user_message[:30] + "..." if len(user_message) > 30 else user_message

def decompose_goal(title, duration, duration_unit, breakdown_type="daily"):
    """
    Decomposes a goal into subtasks based on duration and preferred breakdown.
    breakdown_type: 'daily' or 'weekly'
    """
    try:
        # Determine the granularity instruction
        granularity = "day" if breakdown_type == "daily" else "week"

        # Normalize duration to match granularity
        normalized_duration = duration
        if granularity == "day":
            if "week" in duration_unit.lower():
                normalized_duration = duration * 7
            elif "month" in duration_unit.lower():
                normalized_duration = duration * 30
        elif granularity == "week":
             if "month" in duration_unit.lower():
                normalized_duration = duration * 4
             # If unit is days but we want weeks, usually uncommon for long goals, but handle simple case
             elif "day" in duration_unit.lower():
                  normalized_duration = max(1, duration // 7)

        if normalized_duration == 1 and granularity == "day":
             # Special handling for single day goals -> Hourly/Session breakdown
             prompt = f"""
             You are an expert planner. The user has a 1-day goal: "{title}".
             Create a detailed schedule broken down by DURATION.
             
             Rules:
             1. Break the day into 4-6 distinct working sessions.
             2. DO NOT use "Day 1" or specific clock times (like 9:00 AM) as the start of the label.
             3. Labels format example: "1 Hr: Task Name" or "30 Mins: Task Name" or "2 Hrs: Task Name".
             4. Ensure the total time adds up to a reasonable work day (e.g. 4-8 hours).
             
             Return strictly a JSON object with a key "subtasks" containing a list of objects.
             Each object must have:
             - "text": The task description (starting with the duration label)
             - "completed": false
             
             Example: {{ "subtasks": [ {{ "text": "1 Hr: Research core concepts", "completed": false }} ] }}
             """
        else:
             # Standard multi-day/week breakdown
             prompt = f"""
             You are an expert planner. The user has a goal: "{title}" to be completed in {duration} {duration_unit}.
             Create a detailed, step-by-step roadmap broken down by {granularity}.
             
             Rules:
             1. You MUST generate a plan that covers EXACTLY {normalized_duration} {granularity}s.
             2. There must be distinct task(s) for EVERY single {granularity} from 1 to {normalized_duration}.
             3. Do NOT skip any {granularity}s.
             4. Label tasks clearly as "{granularity.capitalize()} 1:", "{granularity.capitalize()} 2:", etc.
             
             Return strictly a JSON object with a key "subtasks" containing a list of objects.
             Each object must have:
             - "text": The task description (including the Day/Week label)
             - "completed": false
             
             Example: {{ "subtasks": [ {{ "text": "Day 1: Setup env", "completed": false }}, {{ "text": "Day 2: ...", "completed": false }} ] }}
             """
        
        completion = client.chat.completions.create(
            model=MODEL_CONFIG["reasoning"],
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        text = completion.choices[0].message.content.strip()
        data = json.loads(text)
        return data.get("subtasks", [])
        
    except Exception as e:
        print(f"⚠️ Goal decomposition failed: {e}")
        return [{"text": "Could not decompose goal automatically.", "completed": False}]

def generate_goal_reminder(goal_title, subtasks, days_elapsed, duration):
    """
    Generates a context-aware reminder for the user based on their goal progress.
    """
    try:
        # Calculate progress
        total_tasks = len(subtasks)
        completed_tasks = sum(1 for t in subtasks if t.get("completed", False))
        
        # Find the current expected task (Day X)
        # Assuming subtasks are ordered Day 1, Day 2...
        # If days_elapsed is 4, we expect task index 3 (Day 4) to be active or done.
        
        target_task_index = min(days_elapsed - 1, total_tasks - 1)
        if target_task_index < 0: target_task_index = 0
        
        current_task = subtasks[target_task_index] if subtasks else None
        
        completion_status = f"User has completed {completed_tasks}/{total_tasks} tasks."
        if current_task:
            completion_status += f" It is Day {days_elapsed}. The task for today is: '{current_task.get('text', 'Unknown')}'."
            if current_task.get("completed"):
                completion_status += " This task is already marked as completed."
            else:
                completion_status += " This task is NOT yet completed."
        
        prompt = f"""
        You are an accountability partner. The user has a goal: "{goal_title}".
        Goal Duration: {duration} days.
        Current Status: {completion_status}
        
        Task: Write a short, encouraging, and specific reminder message (max 2 sentences).
        - If the user is on track (completed previous days), cheer them on for today's task.
        - If the user is behind (e.g., it's Day 5 but they haven't finished Day 3), gently remind them to catch up on the specific pending task.
        - If they are ahead, congratulate them.
        
        Return ONLY the raw string message. No JSON.
        """
        
        completion = client.chat.completions.create(
            model=MODEL_CONFIG["primary"],
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        
        return completion.choices[0].message.content.strip()

    except Exception as e:
        print(f"⚠️ Reminder generation failed: {e}")
        return f"Don't forget to work on your goal: {goal_title}!"

def generate_goal_quiz(goal_title, subtasks):
    """
    Generates a 5-question MCQ quiz if the goal is learning-related.
    Returns None if not learning related.
    """
    try:
        # Flatten subtasks text for context
        content_context = "\n".join([t.get("text", "") for t in subtasks])
        
        prompt = f"""
        Analyze this goal: "{goal_title}" and its subtasks:
        {content_context}
        
        1. Determine if this goal involves ANY form of learning, skill development, planning a project, or achieving something that requires knowledge.
           - Learning goals: Languages, coding, history, science, etc.
           - Project planning goals: Creating something, organizing an event, developing a plan
           - Skill development: Any activity that requires practice or understanding
           
        2. If this is just a simple chore with no learning aspect (e.g., "buy groceries", "clean room"), return: {{ "is_learning": false }}
        
        3. Otherwise, generate a quiz with EXACTLY 5 Multiple Choice Questions (MCQs) that test understanding of the goal or project planning process.
           - For learning goals: Test the actual knowledge
           - For project goals: Test project management concepts, planning steps, or goal-specific knowledge
        
        Be LENIENT - if there's any educational or skill-building aspect, treat it as a learning goal.
        
        CRITICAL: You MUST generate exactly 5 questions - no more, no less.
        
        Output Format (JSON Only):
        {{
            "is_learning": true,
            "questions": [
                {{
                    "question": "...",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": "Option Text" 
                }},
                {{
                    "question": "...",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": "Option Text" 
                }},
                {{
                    "question": "...",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": "Option Text" 
                }},
                {{
                    "question": "...",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": "Option Text" 
                }},
                {{
                    "question": "...",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": "Option Text" 
                }}
            ]
        }}
        """
        
        completion = client.chat.completions.create(
            model=MODEL_CONFIG["academic"], # Use academic model for better quality questions
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            response_format={"type": "json_object"}
        )
        
        text = completion.choices[0].message.content.strip()
        print(f"📝 Quiz generation response: {text[:200]}...")
        data = json.loads(text)
        
        if not data.get("is_learning"):
            print(f"ℹ️  Goal '{goal_title}' not detected as a learning goal")
            return None
        
        # Validate that we have questions
        if not data.get("questions") or len(data["questions"]) < 5:
            print(f"⚠️  Quiz generated but has {len(data.get('questions', []))} questions (expected 5)")
            
        return data

    except json.JSONDecodeError as e:
        print(f"⚠️ Quiz generation failed - Invalid JSON: {e}")
        print(f"   Response text: {text if 'text' in locals() else 'N/A'}")
        return None
    except Exception as e:
        print(f"⚠️ Quiz generation failed: {e}")
        return None

def generate_personalized_rewards(interests_text):
    """
    Generates 50-75 unique reward items based on user interests using AI.
    Returns a list of dicts: { "name": str, "cost": int, "icon": str, "category": str }
    """
    try:
        prompt = f"""
        Generate a list of 50 purchasable 'virtual items' or 'collectibles' for a user who loves: "{interests_text}".
        These items should be things they would want to 'own' or 'collect' in the app to show their fandom.
        
        Rules:
        1. Items should be specific objects, people, or assets related to the interest.
           - If Cricket: "Signed Bat", "Leather Ball", "Season Ticket", "Virat Kohli Card", "Stadium Model".
           - If Coding: "Mech Keyboard", "Dual Monitors", "Server Rack", "Linus Torvalds Card".
        2. Create 4 Distinct Rarity Tiers with specific costs:
           - "Common": 20-50 coins (Everyday items)
           - "Rare": 50-150 coins (Special gear/items)
           - "Epic": 150-500 coins (Famous players, pro venues, high-end tech)
           - "Legendary": 500-1000 coins (History-making moments, GOAT players, dream setups)
        3. "icon" MUST be one of: [trophy, star, gift, shopping, heart, game, coffee, music, sun]. 
           - Use 'trophy' or 'star' for high-value items/people.
           - Use 'shopping' or 'gift' for gear/objects.
        4. "category" should be the Rarity Tier ("Common", "Rare", "Epic", "Legendary").
        
        Output stricly Valid JSON format:
        {{
            "rewards": [
                {{ "name": "Standard Cricket Ball", "cost": 30, "icon": "shopping", "category": "Common" }},
                {{ "name": "Signed Jersey", "cost": 200, "icon": "trophy", "category": "Epic" }},
                ...
            ]
        }}
        """
        
        completion = client.chat.completions.create(
            model=MODEL_CONFIG["reasoning"],
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            response_format={"type": "json_object"}
        )
        
        text = completion.choices[0].message.content.strip()
        data = json.loads(text)
        return data.get("rewards", [])

    except Exception as e:
        print(f"⚠️ Reward generation failed: {e}")
        return []
