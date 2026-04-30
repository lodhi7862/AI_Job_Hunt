# AI Job Hunt

Production-ready full-stack AI platform for optimizing job applications.

## Stack
- Frontend: Next.js 15+, TypeScript, Tailwind CSS, Framer Motion
- Backend: FastAPI, PostgreSQL, Redis, Celery
- AI: DeepSeek/OpenAI abstraction, structured prompt outputs, pgvector-ready schema

## Features Implemented
- JWT auth (register/login) with role-based admin endpoint
- Resume upload and parsing (PDF, DOCX), ATS issue checks
- Job description analysis and keyword extraction
- Resume-job match scoring with strengths/weaknesses and missing skills
- Cover letter generation
- Interview question + ideal answer generation
- LinkedIn profile analysis
- Application tracker CRUD (create/list)
- Dashboard metrics
- Admin overview analytics
- Dockerized local deployment for frontend/backend/db/redis/worker

## Quick Start (Local)
1. Copy env files:
   - `cp backend/.env.example backend/.env`
   - `cp frontend/.env.example frontend/.env`
2. Start infra:
   - `docker compose up --build`
3. Open:
   - Frontend: `http://localhost:3000`
   - Backend docs: `http://localhost:8000/docs`

## Non-Docker Run
### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Set your AI provider key in `backend/.env`:
- Preferred (DeepSeek): `DEEPSEEK_API_KEY=...` with `AI_MODEL=deepseek-chat`
- Optional fallback: `OPENAI_API_KEY=...` and set `AI_MODEL` accordingly

### Frontend
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

## Seed Data
```bash
cd backend
python -m scripts.seed
```
Default admin credentials:
- Email: `admin@copilot.ai`
- Password: `AdminPass123!`

## Deployment
- Frontend (Vercel): deploy `frontend`, set `NEXT_PUBLIC_API_URL`
- Backend + PostgreSQL + Redis (Railway): deploy `backend` service and managed DB/Redis, set env values from `backend/.env.example`
- Alternative: use Docker Compose on any VM/container host

## Testing
- Backend: `cd backend && pytest`
- Frontend lint: `cd frontend && npm run lint`

## Security Notes
- SQLAlchemy parameterized queries protect against SQL injection
- File type checks and size limits for uploads
- Password hashing with bcrypt
- JWT-based API access
- CORS controlled through env
