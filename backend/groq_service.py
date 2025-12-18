import os
import json
import re
from groq import Groq
from config import GROQ_API_KEY, MODEL_CONFIG

# Initialize Groq Client
client = Groq(api_key=GROQ_API_KEY)

# System Instruction for the AI behavior
SYSTEM_INSTRUCTION = """
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

Output Style Rules:
- Use **bold** for key terms, important concepts, and takeaways.
- Use *italics* for subtle emphasis or defining terms.
- Use lists (bullet points or numbered) to break down complex information.
- ALWAYS use standard markdown code blocks (```language ... ```) for code, never inline or single quotes.
- Use tables for structured data comparisons.

Output Format Rules (Mandatory):

You must ALWAYS return a valid JSON object. No markdown formatting, no plain text outside the JSON.
The JSON structure must be:

{
  "title": "...",          // Generate ONLY for the highly first message of a new chat. Otherwise null.
  "response": "...",       // The assistant's natural language response to the user.
  "new_user_facts": "..."  // Extract any NEW, PERMANENT facts about the user from THIS message (e.g., "User studies CS"). If none, use null.
}

Detailed Instructions:
1. "title":
   - 3-6 words, Title Case.
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
   - specific facts? (e.g., "User is struggling with Arrays", "User's name is Deni").
   - If found, return them as a concise string.
   - If the message is generic ("hi", "thanks", "explain this"), return null.
   - DO NOT repeat facts already in the "User Profile Context".

Boundaries:
- Do not shame, pressure, or compare students to others.
- Do not assist with academic dishonesty or unethical behavior.
- Avoid overwhelming the student with excessive information.

Overall Goal:
Help students feel understood, capable, and supported, while guiding them toward clarity, confidence, and long-term academic growth.
"""

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
                
                1. "academic": Use this for deep research, history, literature, finding citations, or specific complex factual questions.
                2. "reasoning": Use this for complex math problems, coding challenges, logic puzzles, or multi-step deductions.
                3. "teaching": Use this if the user explicitly asks to learn a new topic, needs a step-by-step tutorial, or wants to be taught something from scratch.
                4. "primary": Use this for everything else: general conversation, greeting, emotional support, simple questions, or if unsure.

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



def get_ai_response(history, user_message, user_profile=""):
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
        
        # Prepare Messages
        messages = [{"role": "system", "content": SYSTEM_INSTRUCTION}]
        
        # Optimization: Limit history to last 10 messages (5 turns)
        trimmed_history = history[-10:] if len(history) > 10 else history
        
        # Convert History (Gemini -> OpenAI format)
        for msg in trimmed_history:
            role = "assistant" if msg["role"] == "model" else "user"
            content = msg["parts"][0] if isinstance(msg["parts"], list) else str(msg["parts"])
            messages.append({"role": role, "content": content})
            
        # Add Current User Message with Context
        effective_message = user_message
        if user_profile:
             effective_message = f"User Profile Context:\n{user_profile}\n\nUser Query:\n{user_message}"
        
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

        except json.JSONDecodeError:
            print("JSON Parse Failed in get_ai_response. Raw text:", text[:100])
            final_response = text

        return final_response, extracted_title, new_facts, detected_mode

    except Exception as e:
        print(f"Error calling Groq: {e}")
        return "I'm having trouble connecting to my brain right now.", None, None, "primary"

def generate_chat_title(user_message):
    return user_message[:30] + "..." if len(user_message) > 30 else user_message
