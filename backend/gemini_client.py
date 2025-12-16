import google.generativeai as genai
from config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)

# System logic or specific model configuration
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

Output Format Rules (Mandatory):
- For the first user message of every new chat, generate both:
  1. A concise chat title
  2. The assistant's response
- The title must be:
  - 3 to 6 words long
  - Title Case
  - Based only on the user's first message
  - Clear and descriptive
- Return the output strictly in the following JSON format and nothing else:

{
  "title": "<generated chat title>",
  "response": "<full assistant response>"
}

Boundaries:
- Do not shame, pressure, or compare students to others.
- Do not assist with academic dishonesty or unethical behavior.
- Avoid overwhelming the student with excessive information.

Overall Goal:
Help students feel understood, capable, and supported, while guiding them toward clarity, confidence, and long-term academic growth.
"""

model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=SYSTEM_INSTRUCTION)

import json
import re

def get_ai_response(history, user_message):
    try:
        # Optimization: Limit history to last 6 messages (3 turns)
        trimmed_history = history[-6:] if len(history) > 6 else history
        chat = model.start_chat(history=trimmed_history)
        
        response = chat.send_message(user_message)
        text = response.text
        
        # Check if this is the first interaction (history was empty)
        # We can infer it if the function returns JSON, or strictly check history arg.
        # However, the prompt instruction says it returns JSON for the *first* message.
        # Since 'history' here is the list passed from main.py *before* appending current message,
        # if len(history) == 0, it is the first message.
        
        extracted_title = None
        final_response = text

        if len(history) == 0:
            try:
                # Attempt to parse JSON. It might be wrapped in ```json ... ```
                # Clean up markdown code blocks if present
                clean_text = text.strip()
                if clean_text.startswith("```"):
                    clean_text = re.sub(r"^```json\s*", "", clean_text)
                    clean_text = re.sub(r"^```\s*", "", clean_text)
                    clean_text = re.sub(r"```$", "", clean_text)
                
                data = json.loads(clean_text)
                final_response = data.get("response", text)
                extracted_title = data.get("title")
            except Exception:
                # If parsing fails, just use the raw text and no title (fallback will handle it)
                print("Failed to parse JSON from first response. Using raw text.")
                pass

        return final_response, extracted_title

    except Exception as e:
        print(f"Error calling Gemini: {e}")
        return "I'm having trouble connecting to my brain right now. Please check my API key or internet connection.", None

def generate_chat_title(user_message):
    return user_message[:30] + "..." if len(user_message) > 30 else user_message
