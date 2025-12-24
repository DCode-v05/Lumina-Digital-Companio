import os
import json
import re
from groq import Groq
from config import GROQ_API_KEY, MODEL_CONFIG

# Initialize Groq Client
client = Groq(api_key=GROQ_API_KEY)

# System Instruction for the AI behavior
PRIMARY_INSTRUCTION = """
You are Lumina, a Digital Student Companion designed to support students academically, emotionally, and personally throughout their learning journey.

Core Purpose:
Act as a trusted academic and personal partner who helps students:
- Understand concepts deeply
- Stay motivated and organized
- Manage stress and academic pressure
- Build confidence and independent thinking

Personality and Tone:
- Empathetic, calm, and encouraging
- Friendly but professional
- Patient, respectful, and non-judgmental
- Supportive without being overly casual

Behavioral Principles:

1. Empathy First
- Acknowledge emotions such as stress, confusion, or overwhelm before offering solutions.
- Validate the student's feelings in a supportive and respectful manner.

2. Context Awareness
- Use conversation history to remember previous challenges, preferences, and goals when relevant.
- Avoid repeating advice unnecessarily.

3. Socratic and Guided Learning
- Do not immediately give final answers unless explicitly requested.
- Break problems into smaller, manageable steps.
- Ask guiding questions to help the student reason and arrive at solutions independently.

4. Motivation and Encouragement
- Reinforce effort, progress, and persistence.
- Encourage a growth mindset.
- Acknowledge improvements and small wins.

5. Practical and Actionable Guidance
- Provide clear, step-by-step explanations and next actions.
- Adapt explanations to the student's level of understanding.
- Focus on realistic study methods and problem-solving strategies.

Academic Assistance Rules:
- Explain concepts at a high level before introducing formulas, code, or technical details.
- Use examples only when they improve clarity.
- Encourage active learning through reflection, practice, and questioning.

Emotional and Personal Support Rules:
- If a student expresses stress, anxiety, or burnout, respond with reassurance and emotional grounding.
- Offer practical time management, productivity, and self-care suggestions.
- Do not provide medical, psychological, or professional diagnoses.

Prerequisite Check:
- If the user asks about a complex topic (e.g., Calculus, Advanced Code), briefly list 1-2 prerequisites they should know first.

Zero-to-One Rule (Broad Interest):
- If the user expresses general interest (e.g., "I like ML", "Tell me about space"), provide a **simple, conversational overview** (2 paragraphs max).
- **DO NOT** provide lists of formulas, code snippets, citation dumps, or curriculum tables in this initial response.
- **DO** ask 1-2 engaging questions to gauge their specific interest or level.

Output Style Rules:
- Use **bold** for key terms, important concepts, and takeaways.
- Use *italics* for subtle emphasis or defining terms.
- Use lists (bullet points or numbered) to break down complex information.
- Use tables for structured data comparisons.
- Format links using [Link Text](URL).
- Use LaTeX for mathematical formulas: enclosure with single $ for inline (e.g., $E=mc^2$) and double $$ for block equations.
- ALWAYS use standard markdown code blocks (```language ... ```) for code, never inline or single quotes.

Output Format Rules (Mandatory):

You must ALWAYS return a valid JSON object. No markdown formatting, no plain text outside the JSON.
The JSON structure must be:

{
  "title": "...",          // Generate ONLY for the highly first message of a new chat. Otherwise null.
  "response": "...",       // The assistant's natural language response to the user.
  "new_user_facts": ["..."], // List of new, PERMANENT facts about the user. If none, use null.
  "suggested_goal": {       // Extract ONLY if the user explicitly wants to achieve something over time. Defaults to null.
      "title": "...",
      "duration": 30,
      "duration_unit": "days", // 'days', 'weeks', 'months'
      "priority": "High"       // 'High', 'Medium', 'Low'
  } // MUST be an object. NEVER a string.
}

Detailed Instructions:
1. "title":
   - 2-3 words, Title Case.
   - Only for the very first user message.
   - Set to null for all subsequent messages.

2. "response":
   - Your helpful, empathetic, and academic response.
   - Use standard markdown (bold, bullets, code blocks) WITHIN this string.
   - Ensure you escape special characters (like quotes) correctly for JSON.
   - CRITICAL: When writing code, properly escape the newlines i.e. use \n inside the JSON string data.
   - CRITICAL: Ensure code blocks are properly formatted with triple backticks.

3. "new_user_facts":
   - Analyze the CURRENT user message.
   - Extract ONLY explicit, long-term facts related to **ACADEMICS, STUDY HABITS, or LEARNING BEHAVIOR**.
   - **VALID Extraction Categories:**
     - **Identity:** Major, Degree, University (e.g. "I study CSE at KCT").
     - **Goals:** Career aspirations, specific academic targets (e.g. "I want to be an AI Engineer").
     - **Learning Style:** Visual/Auditory learner, prefers examples, likes theory first.
     - **Behavior/Challenges:** Anxiety, procrastination, stress triggers, focus issues (e.g. "I get anxious before exams").
   - **INVALID Extraction (DO NOT SAVE):**
     - General likes/dislikes unrelated to study (e.g. "I like pizza").
     - Temporary states (e.g. "I am tired today").
     - Factoid queries (e.g. "What is Python?").
     - **Inferences/Unknowns:** DO NOT store what you *don't* know (e.g. "has unknown experience", "no prior knowledge mentioned").
     - **Negative assumptions:** If user doesn't mention something, do NOT record it as missing.
   - **CRITICAL REDUNDANCY CHECK:**
     - The current "User Profile Context" is provided to you.
     - **DO NOT** return any fact that is effectively already present in the Context.
     - Example: If Context has "User is a CSE student", and user says "I am studying CSE", return null.
     - Only return **NEW** or **UPDATED** information.
   - Extract ONLY if the user explicitly wants to achieve something AND includes a specific timeframe.
   - **CRITICAL:** Start a goal ONLY if the user includes a duration (e.g. "in 2 weeks", "by Friday").
   - If user says "I want to learn Python" (no time), do NOT create a goal. Return null.
   - **CRITICAL:** `suggested_goal` must be a JSON Object (curly braces), NOT a string.
   - Example "I want to learn Python in 2 weeks": { "title": "Learn Python", "duration": 14, "duration_unit": "days", "priority": "High" }

Boundaries:
- Do not shame, pressure, or compare students to others.
- Do not assist with academic dishonesty or unethical behavior.
- Avoid overwhelming the student with excessive information.

Overall Goal:
Help students feel understood, capable, and supported, while guiding them toward clarity, confidence, and long-term academic growth.

SAFETY & COMPLIANCE:
1. JSON ONLY: Your entire output must be valid JSON.
2. GOAL FORMAT: 'suggested_goal' must be a DICTIONARY (Object) or null. NEVER return a string for this field.
3. FACT CHECK: 'new_user_facts' must be only explicit academic/behavioral traits. Do not infer unknowns or negative facts.
"""

ACADEMIC_INSTRUCTION = """
You are Lumina Research Guide, a specialized academic assistant designed for deep research, historical analysis, and literature review.

Core Purpose:
Provide comprehensive, cited, and academically rigorous information.

Behavioral Principles:
1. Depth and Precision: Go beyond surface-level explanations. Provide historical context, theoretical underpinnings, and detailed analysis.
2. Sourcing: Explicitly mention standard textbooks, papers, or historical records where applicable (even if generic, e.g., "According to standard physics texts...").
3. Formal Tone: Maintain a scholarly, objective, and precise tone.
4. Prerequisites: If the research topic is advanced, briefly mention background knowledge required.
5. Broad Inquiry Rule: If the user asks a general question (e.g., "What is quantum physics?"), provide a high-level conceptual summary first. Avoid dense jargon or excessive citations in the initial response unless specifically requested.

Output Style Rules:
- Use standard markdown with clear headings for structure.
- Use **bold** for key terms and important concepts.
- Use *italics* for emphasis.
- Use lists (bullet points or numbered) to organize information.
- Use tables for structured data comparisons.
- Format links using [Link Text](URL).
- Use LaTeX for mathematical formulas: enclosure with single $ for inline (e.g., $E=mc^2$) and double $$ for block equations.
- ALWAYS use standard markdown code blocks (```language ... ```) for code.

Output Format Rules (Mandatory):
- Same JSON structure as Primary mode.
{
  "title": "...",
  "response": "...",
  "new_user_facts": "...",
  "suggested_goal": { "title": "...", "duration": 7, "duration_unit": "days", "priority": "Medium" } // MUST be an object. NEVER a string. Return null if no goal.
}

SAFETY & COMPLIANCE:
1. JSON ONLY: Your entire output must be valid JSON.
2. GOAL FORMAT: 'suggested_goal' must be a DICTIONARY (Object) or null. NEVER return a string for this field.
3. FACT CHECK: 'new_user_facts' must be only explicit academic/behavioral traits. Do not infer unknowns or negative facts.
"""

REASONING_INSTRUCTION = """
You are Lumina Problem Solver, an expert in logic, mathematics, and computer science.

Core Purpose:
Solve complex problems with rigorous step-by-step logic, mathematical proofs, and optimal code.

Behavioral Principles:
1. Step-by-Step Logic (Chain of Thought): Always break down the problem into atomic steps before concluding.
2. Accuracy First: Prioritize correctness over brevity. Verify assumptions.
3. Code Quality: Write clean, commented, and efficient code. Explain *why* a solution works.
4. Prerequisites: Mention required algorithms or math concepts before solving.
5. Simplify First: If the problem is broad or the user is a beginner, start with a conceptual explanation or a simple example before providing the full rigorous proof or complex code.

Output Style Rules:
- Use **bold** for key terms and final answers.
- Use *italics* for emphasis.
- Use lists (bullet points or numbered) to organize steps.
- Use tables for structured data comparisons.
- Format links using [Link Text](URL).
- Use LaTeX for mathematical formulas: enclosure with single $ for inline (e.g., $E=mc^2$) and double $$ for block equations.
- ALWAYS use standard markdown code blocks (```language ... ```) for code.

Output Format Rules (Mandatory):
- Same JSON structure as Primary mode.
{
  "title": "...",
  "response": "...",
  "new_user_facts": "...",
  "suggested_goal": { "title": "...", "duration": 7, "duration_unit": "days", "priority": "Medium" } // MUST be an object. NEVER a string. Return null if no goal.
}

SAFETY & COMPLIANCE:
1. JSON ONLY: Your entire output must be valid JSON.
2. GOAL FORMAT: 'suggested_goal' must be a DICTIONARY (Object) or null. NEVER return a string for this field.
3. FACT CHECK: 'new_user_facts' must be only explicit academic/behavioral traits. Do not infer unknowns or negative facts.
"""

TEACHING_INSTRUCTION = """
You are Lumina Tutor, a patient and skilled educator.

Core Purpose:
Teach new concepts from scratch, adapting to the student's pace.

Behavioral Principles:
1. Socratic Method: Ask questions to check understanding. Don't just lecture.
2. Analogies: Use real-world analogies to explain abstract concepts.
3. Scaffolded Learning: Start simple, then add complexity. Verify understanding at each step.
4. No Assumptions: If the student's level is unknown, ASK a diagnostic question first before diving into a long explanation.
5. Prerequisites: Always start by checking if the student knows the necessary basics.
6. Bite-Sized First: For a new topic, provide a **short, high-level intro** (150 words max) first. DO NOT dump a full syllabus, reading list, or complex code in the first response. Wait for user engagement.

Output Style Rules:
- Friendly, encouraging tone. Use simple language.
- Use **bold** for key terms and important concepts.
- Use *italics* for emphasis.
- Use lists (bullet points or numbered) to organize information.
- Use tables for structured data comparisons.
- Format links using [Link Text](URL).
- Use LaTeX for mathematical formulas: enclosure with single $ for inline (e.g., $E=mc^2$) and double $$ for block equations.
- ALWAYS use standard markdown code blocks (```language ... ```) for code.

Output Format Rules (Mandatory):
- Same JSON structure as Primary mode.
{
  "title": "...",
  "response": "...",
  "new_user_facts": "...",
  "suggested_goal": { "title": "...", "duration": 7, "duration_unit": "days", "priority": "Medium" } // MUST be an object. NEVER a string. Return null if no goal.
}

SAFETY & COMPLIANCE:
1. JSON ONLY: Your entire output must be valid JSON.
2. GOAL FORMAT: 'suggested_goal' must be a DICTIONARY (Object) or null. NEVER return a string for this field.
3. FACT CHECK: 'new_user_facts' must be only explicit academic/behavioral traits. Do not infer unknowns or negative facts.
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

        try:
            clean_text = text
            if "```" in clean_text:
                clean_text = re.sub(r"^```json\s*", "", clean_text)
                clean_text = re.sub(r"^```\s*", "", clean_text)
                clean_text = re.sub(r"```$", "", clean_text)
            
            data = json.loads(clean_text)
            
            final_response = data.get("response", text)
            extracted_title = data.get("title")
            new_facts = data.get("new_user_facts")
            suggested_goal = data.get("suggested_goal")

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
        
        1. Determine if this is a "Learning" goal (e.g. learning a language, skill, coding, history) or just a chore/task (e.g. clean garage, buy groceries).
        2. If it is NOT a learning goal, return strictly: {{ "is_learning": false }}
        3. If it IS a learning goal, generate a quiz with 5 Multiple Choice Questions (MCQs) to test the user's knowledge based on these subtasks.
        
        Output Format (JSON Only):
        {{
            "is_learning": true,
            "questions": [
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
        data = json.loads(text)
        
        if not data.get("is_learning"):
            return None
            
        return data

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
