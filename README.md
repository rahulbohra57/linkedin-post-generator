# LinkedIn Post Generator — Industry-Grade Agentic AI App

A full-stack production app that generates and publishes LinkedIn posts using 7 specialized AI agents.

## Architecture

```
Next.js UI → FastAPI (REST + WebSocket) → 7 CrewAI Agents → LinkedIn API
                                        ↘ DALL-E 3 + Pexels images
                                        ↘ SQLite + Redis
```

## User Flow

1. **Enter topic** — choose tone, audience, post length
2. **Watch agents work** — real-time WebSocket progress for each of 7 agents
3. **Edit the post** — rich text editor with character counter + quality score
4. **Pick an image** — 3 AI-generated (DALL-E 3) + 3 stock (Pexels) options
5. **Publish** — one-click direct publish to LinkedIn via OAuth

## Agent Pipeline

| Agent | LLM | Role |
|-------|-----|------|
| Researcher | claude-sonnet-4-6 | Web research via Tavily (10 results, advanced depth) |
| Tone Analyzer | gemini-2.5-flash | Audience & tone strategy brief |
| Writer | claude-sonnet-4-6 | Draft post from research + tone brief |
| Editor | claude-sonnet-4-6 | Polish hook, body, CTA |
| Hashtag Researcher | gemini-2.5-flash | Research trending LinkedIn hashtags |
| Post Assembler | gemini-2.5-flash | Validate length, score quality (1-10), package output |
| Image Prompt Generator | claude-sonnet-4-6 | Generate 3 DALL-E 3 prompts in different visual styles |

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- Redis (or Docker)

### 1. Configure environment

```bash
cp .env.example .env
# Fill in your API keys (see .env.example for instructions)
```

**Required API keys:**
- `ANTHROPIC_API_KEY` — [console.anthropic.com](https://console.anthropic.com)
- `GEMINI_API_KEY` — [aistudio.google.com](https://aistudio.google.com) (already have this)
- `OPENAI_API_KEY` — [platform.openai.com](https://platform.openai.com)
- `TAVILY_API_KEY` — [tavily.com](https://tavily.com) (already have this)
- `PEXELS_API_KEY` — [pexels.com/api](https://pexels.com/api) (free)
- `LINKEDIN_CLIENT_ID` + `LINKEDIN_CLIENT_SECRET` — [developer.linkedin.com](https://developer.linkedin.com)

> **Important:** Apply for LinkedIn's "Share on LinkedIn" API product immediately — approval takes 2-7 days.

### 2. Start with Docker (recommended)

```bash
docker compose up
```

Open [http://localhost:3000](http://localhost:3000)

### 3. Start manually

**Backend:**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Redis (required for WebSocket streaming):**
```bash
redis-server
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## API Reference

```
POST /api/generate          — Start post generation
GET  /api/drafts/{id}       — Get draft
PATCH /api/drafts/{id}      — Update draft (post text, selected image)
GET  /api/images            — Get image options (AI + stock)
POST /api/images/upload     — Upload custom image
POST /api/publish           — Publish to LinkedIn
GET  /api/auth/linkedin/login     — Start LinkedIn OAuth
GET  /api/auth/linkedin/callback  — OAuth callback
GET  /api/auth/linkedin/status    — Check if connected
WS   /ws/progress/{session_id}   — Real-time agent progress
```

## LinkedIn API Setup

1. Go to [developer.linkedin.com](https://developer.linkedin.com) → Create app
2. Request OAuth scopes: `w_member_social`, `r_liteprofile`, `r_emailaddress`
3. Apply for **"Share on LinkedIn"** product (required for posting)
4. Set redirect URI: `http://localhost:8000/api/auth/linkedin/callback`
5. For local dev, use [ngrok](https://ngrok.com) to expose your local server

## Project Structure

```
linkedin-post-generator/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entrypoint
│   │   ├── config.py            # Environment settings
│   │   ├── agents/              # CrewAI agents + crew assembly
│   │   ├── tools/               # Tavily, DALL-E 3, Pexels tools
│   │   ├── services/            # LinkedIn API, image service
│   │   ├── api/routes/          # REST endpoints
│   │   ├── db/                  # SQLAlchemy models + migrations
│   │   └── core/                # WebSocket, progress emitter, middleware
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── app/                 # Next.js pages (4-step flow)
│       ├── hooks/               # useWebSocket
│       ├── store/               # Zustand state
│       └── lib/                 # API client, utilities
├── docker-compose.yml
└── .env.example
```
