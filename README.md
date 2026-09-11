# Canvas LMS Reviewer Generator

Web app that authenticates with Canvas LMS, scrapes course modules/learning resources, and generates study reviewers (Markdown, HTML, PDF) using AI summarization.

## Tech Stack

- **Backend:** Python 3.11+ / FastAPI
- **Frontend:** Vanilla HTML/CSS/JS
- **Queue:** ARQ + Redis
- **Database:** PostgreSQL (prod) / SQLite (dev)
- **Deployment:** Docker Compose + Nginx
- **AI:** Ollama (local) or free cloud APIs (Groq, Gemini)

## Quick Start

### 1. Clone and configure

```bash
cp .env.example .env
# Edit .env with your settings
```

### 2. Start with Docker Compose

```bash
docker compose up -d
```

### 3. Pull Ollama model (first time)

```bash
docker compose exec ollama ollama pull qwen3:4b
```

### 4. Open in browser

```
http://localhost
```

## Local Development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

Serve the `frontend/` directory with any static server, or use the FastAPI backend at `http://localhost:8000`.

## How It Works

1. Enter your Canvas URL and API token
2. Select courses to generate reviewers for
3. App scrapes modules, pages, PDFs, and videos
4. AI summarizes content into study reviewers
5. Download as Markdown, HTML, or PDF

## API Token

1. Log in to Canvas LMS
2. Go to Account > Settings > New Access Token
3. Generate token with note "Canvas Reviewer"
4. Enter token into the app

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/validate` | Validate Canvas token |
| GET | `/courses` | List user's courses |
| POST | `/scrape/batch` | Queue courses for scraping |
| GET | `/status/{batch_id}` | Check batch job status |
| GET | `/download/{course_id}/{format}` | Download reviewer |

## Project Structure

```
canvas_reviewer/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI routes
│   │   ├── config.py        # Settings
│   │   ├── auth.py          # Token validation + encryption
│   │   ├── scraper.py       # Canvas API client
│   │   ├── ai_client.py     # AI provider abstraction
│   │   ├── reviewer.py      # MD/HTML/PDF generation
│   │   ├── tasks.py         # ARQ worker tasks
│   │   ├── models.py        # Database models
│   │   ├── db.py            # Database connection
│   │   ├── freemium.py      # Course limit logic
│   │   └── extractors/      # Content extraction
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── style.css
├── nginx/
│   └── nginx.conf
├── docker-compose.yml
├── .env.example
├── PLAN.md
└── TASKS.md
```

## Freemium

- **Free:** 3 courses
- **Premium:** Unlimited

## License

MIT
