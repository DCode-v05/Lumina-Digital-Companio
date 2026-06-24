# Lumina — Digital Student Companion

**A full-stack AI study companion: a tutor chat that remembers you, turns goals into day-by-day plans, quizzes you on them, reads your mood, and runs a coin-based reward economy on top.**

![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white) ![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white) ![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat&logo=typescript&logoColor=white) ![React](https://img.shields.io/badge/React_18-61DAFB?style=flat&logo=react&logoColor=black) ![Vite](https://img.shields.io/badge/Vite-646CFF?style=flat&logo=vite&logoColor=white) ![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-06B6D4?style=flat&logo=tailwindcss&logoColor=white) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat&logo=postgresql&logoColor=white) ![Redis](https://img.shields.io/badge/Redis-DC382D?style=flat&logo=redis&logoColor=white) ![Groq](https://img.shields.io/badge/Groq-F55036?style=flat&logo=groq&logoColor=white) ![Hugging Face](https://img.shields.io/badge/Hugging_Face-FFD21E?style=flat&logo=huggingface&logoColor=black)

## Overview

Lumina is a study companion app for students. Instead of being one more chatbot, it tries to act like a tutor that actually keeps track of you: it pulls long-term facts out of your conversations, plans your goals into concrete daily or weekly tasks, checks whether you're keeping up, generates quizzes to test what you said you wanted to learn, and reacts to the emotional tone of your messages. On top of that there's a coin economy — you earn coins for showing up and finishing things, and spend them on a set of collectible "rewards" the AI generates around your interests.

It's a real full-stack build: a FastAPI backend talking to PostgreSQL and Redis, a React 18 + TypeScript frontend, four different Groq-hosted language models behind a routing layer, a HuggingFace transformer for emotion classification, and live integrations with GitHub and Microsoft OneNote. I wrote the whole thing — backend services, prompt design, the React UI, and the integrations. It's the largest project in my portfolio: roughly 24 REST endpoints, a six-table data model, and around 250 KB of authored frontend across four large dashboards.

## Key Features

- **Routed AI chat with four personas.** Every message is first classified into one of four modes (general companion, research guide, problem solver, tutor), and each mode runs on a different Groq model with its own system prompt and tone.
- **Persistent memory ("user facts").** The model is instructed to extract durable facts about you ("studying Biology", "visual learner") and skip temporary ones ("I'm hungry"). New facts are de-duplicated against your existing profile and appended, so the assistant carries context across chats.
- **Goal planning and decomposition.** State a goal with a timeframe ("learn React in 2 weeks") and Lumina creates a Goal and breaks it into a task per day or per week, with a special hour-by-hour breakdown for single-day goals.
- **Auto-created goals from chat.** If you mention a goal with a deadline mid-conversation, the chat endpoint detects the structured `suggested_goal` in the model's JSON output and creates the goal for you automatically.
- **Accountability reminders.** A reminders endpoint compares days elapsed against the task list and generates a short, context-aware nudge — cheering you on if you're on track, gently flagging the specific pending task if you're behind.
- **Auto-generated quizzes.** For learning-type goals, Lumina generates a 5-question multiple-choice quiz to test understanding, and skips quiz generation for plain chores ("buy groceries").
- **Emotion tracking.** Each message runs through a DistilRoBERTa emotion classifier; detected emotions are logged with a confidence score and the recent emotional summary is fed back into the chat context so the assistant can respond to your mood.
- **Coin economy and gamification.** Coins for first login (+50) and daily check-ins (+20), a full transaction history, and a redeem flow that tracks purchased rewards.
- **AI-generated, interest-based rewards.** Based on your stated favorites, the model generates a catalogue of ~50 collectible items across four rarity tiers (Common / Rare / Epic / Legendary) with coin costs and icons, cached per user.
- **GitHub integration (full CRUD).** Connect a Personal Access Token and list, count, create, inspect, rename, re-describe, or delete repositories — either from the Integrations dashboard or by asking in plain English in chat ("how many repos do I have?", "create repo called my-project").
- **OneNote integration (read-only).** Connect a Microsoft Graph token to list pages, count them, browse sections, and open a specific page via the Graph API.
- **JWT auth.** Email/password registration and login with bcrypt-hashed passwords and JWT access tokens.
- **Polished chat UI.** Markdown rendering with GitHub-flavored markdown, KaTeX math, and Prism syntax highlighting; framer-motion animations; light/dark theme; per-message mode badges so you can see which persona answered.

## How It Works

The system splits into a FastAPI backend (the brains and all state) and a React/Vite frontend (chat, dashboards, auth). State lives in two places: PostgreSQL for durable records (users, goals, emotion logs, integrations, purchases) and Redis for chat sessions, message history, and the rolling user profile.

### Request routing and the four-model setup

There's no single "the model." A lightweight model (`llama-3.1-8b-instant`) acts as an intent classifier first, sorting each message into one of four modes. Each mode then runs on a model picked for the job:

| Mode | Persona | Model |
| --- | --- | --- |
| `primary` | Companion / emotional support | `llama-3.1-8b-instant` |
| `academic` | Research guide | `openai/gpt-oss-120b` |
| `reasoning` | Problem solver (math/code/logic) | `llama-3.3-70b-versatile` |
| `teaching` | Step-by-step tutor | `meta-llama/llama-4-maverick-17b-128e-instruct` |

If a model call fails, there's a fallback that retries on the reasoning model (or the primary model if reasoning itself was the one that failed), so a single bad call doesn't kill the response.

### Structured JSON outputs

Every chat call uses Groq's JSON-object response format and a strict schema instruction. The model returns one object containing the natural-language `response`, an optional chat `title` (only on the first message), `new_user_facts` to add to memory, and an optional `suggested_goal` with title/duration/unit/priority. The backend parses this, trims to the first `{`…`}` it finds for safety, and falls back to raw text if parsing fails. This is what lets memory updates and goal creation happen as a side effect of an ordinary chat turn instead of needing separate calls.

### Memory and context assembly

Before each model call the backend assembles context from three sources: the user's stored profile (their accumulated facts), a summary of recent emotions (last 15 minutes, only emotions scored above 0.5), and the trimmed chat history (last ~10 messages). After the model replies, any genuinely new facts are appended to the Redis-backed profile, and expired temporary facts are cleaned on each interaction.

### Emotion pipeline

Emotion analysis uses the HuggingFace `transformers` pipeline with `j-hartmann/emotion-english-distilroberta-base` — a DistilRoBERTa text-classification model returning scores across emotion labels. The top label and its score are logged to an `emotion_logs` table per message. The recent-emotion summary is then injected back into the chat prompt, which is how the assistant "knows" to acknowledge stress before diving into a solution.

### Goal lifecycle

A goal can be created explicitly or auto-detected from chat. Decomposition normalizes the duration to the chosen granularity (weeks→days, months→weeks, etc.), then asks the reasoning model for a labeled task list ("Day 1: …", "Week 2: …") covering every interval. Subtasks and generated quizzes are stored as JSON on the goal row. Reminders and quizzes are generated on demand from those subtasks.

### Integrations

GitHub calls hit the REST API (`api.github.com`) with the user's stored token; OneNote calls hit Microsoft Graph (`graph.microsoft.com/v1.0`) as read-only operations. The chat endpoint has an intent detector that matches phrases like "list repos" or "how many pages" and dispatches straight to the integration service — so you can manage repos conversationally without leaving the chat. Tokens are stored per provider in an `integrations` table.

### Frontend

The React app is a single-page client with routes for login/register and the main workspace. `App.tsx` holds the chat surface (message list, mode badges, markdown + math + code highlighting, profile/memory modal). Three dashboards handle the rest: `GoalDashboard` (goals, subtasks, quizzes), `RewardDashboard` (coin balance, catalogue, redeem), and `IntegrationDashboard` (connect/disconnect GitHub and OneNote). Axios wraps the API with the JWT attached; framer-motion handles transitions; a theme provider toggles light/dark.

## Results / Highlights

- **Around 24 REST endpoints** across auth, chats, goals (plus decompose / quiz / reminders), rewards/redeem, profile, chat, and the GitHub/OneNote integration routes.
- **Four-model routing** with an automatic fallback path, all behind one chat endpoint.
- **Six-table data model**: users (coins, coin history, favorites, rewards cache), emotion logs, goals, user facts, integrations, and purchased rewards.
- **~50 AI-generated reward items** per user across four rarity tiers (Common 20–50, Rare 50–150, Epic 150–500, Legendary 500–1000 coins), cached so they don't regenerate on every load.
- **Two live third-party integrations** — GitHub (full create/read/update/delete) and OneNote (read-only) — usable from both a dashboard and plain-English chat commands.
- Sizable authored frontend: `App.tsx` (~48 KB) and `GoalDashboard.tsx` (~52 KB) are the two largest components.

## Tech Stack

- **Languages:** Python (backend), TypeScript (frontend).
- **Backend frameworks / libraries:** FastAPI, Uvicorn, SQLAlchemy, Pydantic, python-jose + bcrypt (JWT auth), python-multipart.
- **Frontend frameworks / libraries:** React 18, Vite 6, Tailwind CSS, framer-motion, react-router v7, react-markdown with remark-gfm / remark-math / rehype-katex, react-syntax-highlighter, axios, lucide-react icons.
- **Data / ML:** Groq SDK (Llama 3.1 / 3.3, GPT-OSS-120B, Llama 4 Maverick), HuggingFace `transformers` + `torch` (`j-hartmann/emotion-english-distilroberta-base`).
- **Infra / services:** PostgreSQL (via psycopg2), Redis, GitHub REST API, Microsoft Graph (OneNote).

## Getting Started

### Prerequisites

- Python 3.8+
- Node.js 16+
- A running PostgreSQL instance
- A running Redis instance
- A Groq API key

### Installation

```bash
git clone https://github.com/DCode-v05/Lumina-Digital-Companio.git
cd Lumina-Digital-Companio
```

**Backend**

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt

# configure environment
cp .env.template .env
# then fill in GROQ_API_KEY, Postgres credentials, Redis host/port, SECRET_KEY
```

**Frontend**

```bash
cd ../frontend
npm install
```

### Running

Backend (from `backend/`):

```bash
uvicorn main:app --reload
# API on http://localhost:8000
```

Frontend (from `frontend/`):

```bash
npm run dev
# App on http://localhost:5173
```

The database tables are created on startup. Make sure PostgreSQL and Redis are reachable with the credentials in your `.env`.

## Usage

1. Register an account and log in — your first login drops 50 coins into your wallet, and each new day you check in adds 20 more.
2. Set your favorites in the profile so the reward catalogue gets generated around your interests.
3. Start a chat. Ask a question, ask to learn something, or mention a goal with a deadline — the assistant will route to the right persona, remember facts about you, and create a goal if you gave it a timeframe.
4. Open the Goals dashboard to see decomposed subtasks, request a quiz on a learning goal, and check reminders.
5. Open the Rewards dashboard to spend coins on collectibles.
6. Open the Integrations tab to connect GitHub (a classic PAT with `repo` scope) or OneNote (a Microsoft Graph token with `Notes.Read`), then manage repos and browse notes — from the dashboard or directly in chat ("how many repos do I have?", "list my OneNote pages").

## Project Structure

```
Lumina-Digital-Companio/
├── backend/
│   ├── main.py                 # FastAPI app, ~24 endpoints, chat orchestration
│   ├── groq_service.py         # 4-model router, prompts, goal/quiz/reward generation
│   ├── emotion_service.py      # DistilRoBERTa emotion classification + logging
│   ├── github_service.py       # GitHub REST API (list/create/get/update/delete)
│   ├── onenote_service.py      # Microsoft Graph OneNote (read-only)
│   ├── integration_service.py  # aggregator re-exporting the integration functions
│   ├── redis_client.py         # chat sessions, message history, profile/facts memory
│   ├── models.py               # SQLAlchemy tables (users, goals, emotions, etc.)
│   ├── schemas.py              # Pydantic request/response schemas
│   ├── auth.py                 # JWT + bcrypt auth
│   ├── database.py             # SQLAlchemy engine/session
│   ├── config.py               # model config, DB/Redis/auth settings
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── App.tsx                         # chat UI, routing, profile modal
│       ├── api.ts                          # axios API client (JWT attached)
│       ├── components/
│       │   ├── GoalDashboard.tsx           # goals, subtasks, quizzes
│       │   ├── RewardDashboard.tsx         # coins, catalogue, redeem
│       │   ├── IntegrationDashboard.tsx    # GitHub / OneNote connect
│       │   ├── ThemeProvider.tsx
│       │   └── ThemeToggle.tsx
│       └── pages/
│           ├── Login.tsx
│           └── Register.tsx
└── README.md
```

---

## Contact

**Portfolio:** [Denistan](https://www.denistan.me)<br>
**LinkedIn:** [Denistan](https://www.linkedin.com/in/denistanb)<br>
**GitHub:** [DCode-v05](https://github.com/DCode-v05)<br>
**LeetCode:** [Denistan_B](https://leetcode.com/u/Denistan_B)<br>
**Email:** [denistanb05@gmail.com](mailto:denistanb05@gmail.com)

Made with ❤️ by **Denistan B**
