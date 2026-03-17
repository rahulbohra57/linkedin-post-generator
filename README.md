# LinkedIn Post Generator

🔗 **Live App:** [Coming soon — will be updated after deployment](#)

## About the App

LinkedIn Post Generator is a full-stack agentic AI app that creates polished, ready-to-post LinkedIn content in minutes. Enter a topic, choose your tone and audience, and 8 specialized AI agents research, write, edit, and verify your post — complete with Pexels stock photo suggestions. It's designed for professionals, founders, and content creators who want high-quality LinkedIn posts without the time investment.

## Architecture Overview

The app runs a sequential CrewAI pipeline on the backend: a Researcher gathers web facts via Tavily, a Tone Analyzer and Writer draft the post, an Editor refines it, a Hashtag Researcher adds trending tags, a Post Assembler scores quality, a Pexels Image Searcher fetches relevant stock photos, and a Gemini Verifier does a final quality pass. Real-time progress is streamed to the browser via WebSocket (in-memory asyncio queue, no Redis required). The Next.js frontend proxies REST calls to the FastAPI backend and lets users edit the post, pick an image, then copy the caption and download the image.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 15, React 19, Tailwind CSS, Zustand |
| Backend | FastAPI, Python 3.11, SQLAlchemy + SQLite |
| AI Agents | CrewAI, Claude Sonnet (Anthropic), Gemini Flash 2.0 |
| Search | Tavily API (web research) |
| Images | Pexels API (stock photos) |
| Streaming | WebSocket + asyncio in-memory queue |
| Deployment | Docker, Render.com |

## Key Features

- 8-agent sequential pipeline: Research → Tone → Write → Edit → Hashtags → Assemble → Images → Verify
- Real-time agent progress via WebSocket with polling fallback
- Inline Pexels image picker (7 photos) with custom search and refresh
- Editable post with character counter and Gemini quality score
- Copy caption + download image for direct LinkedIn posting
- No Redis or external queues required — runs entirely in-memory

## User Instructions

1. Enter your post topic, select tone (Professional, Conversational, Thought Leader, etc.), target audience, and post length
2. Watch the 8 AI agents work in real time — the post appears in the preview pane when complete
3. Edit the generated post text if needed, then click **Generate Image Suggestions from Pexels** to browse photos
4. Select an image (or skip for text-only), then click **Preview Post**
5. On the preview page, click **Copy Post Caption** and **Download Image**, then paste and upload directly on LinkedIn

## Note

The following API keys must be set as environment variables before the app will work:

| Key | Where to get it |
|-----|----------------|
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) |
| `GEMINI_API_KEY` | [aistudio.google.com](https://aistudio.google.com) |
| `TAVILY_API_KEY` | [tavily.com](https://tavily.com) |
| `PEXELS_API_KEY` | [pexels.com/api](https://pexels.com/api) (free tier available) |

For local development, copy `.env.example` to `.env` in the project root and fill in the values, then run `docker compose up`.
