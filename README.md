# Lumina - Digital Student Companion

Lumina is a full-stack AI-powered student companion application designed to help with studying, goal tracking, and productivity.

## Project Structure

- **Backend**: FastAPI (Python)
- **Frontend**: React + Vite (TypeScript)
- **Database**: PostgreSQL (via SQLAlchemy)
- **AI Engine**: Groq
- **Integrations**: GitHub, OneNote

## Getting Started

### Prerequisites

- Python 3.8+
- Node.js 16+
- PostgreSQL
- Redis

### Backend Setup

1. **Navigate to the backend directory:**
   ```bash
   cd backend
   ```

2. **Create and activate a virtual environment (optional but recommended):**
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS/Linux
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration:**
   - Copy `.env.template` to `.env`.
   - Fill in your API keys (GROQ_API_KEY) and database credentials.

5. **Run the server:**
   ```bash
   uvicorn main:app --reload
   ```
   The API will be available at `http://localhost:8000`.

### Frontend Setup

1. **Navigate to the frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Run the development server:**
   ```bash
   npm run dev
   ```
   The application will be available at `http://localhost:5173`.

## Integrations

To use GitHub and OneNote features:
- **GitHub**: Generate a Personal Access Token (Classic) with `repo` scope.
- **OneNote**: Obtain a Microsoft Graph OAuth token with `Notes.Read` scope.
- Connect these services via the "Integrations" tab in the application sidebar.
