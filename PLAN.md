# Canvas LMS Reviewer Generator — PLAN.md

## 1. Overview

Web app that authenticates with Canvas LMS, scrapes course modules/learning resources, and generates study reviewers (Markdown, HTML, PDF) using AI summarization.

**Target users:** Students, teachers, self-learners using Canvas LMS.

---

## 2. Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.11+ / FastAPI |
| Frontend | Vanilla HTML/CSS/JS |
| Queue | ARQ + Redis |
| Database | PostgreSQL (prod) / SQLite (dev) |
| Deployment | Docker Compose + Nginx |
| AI | Ollama (local) or free cloud APIs |

---

## 3. Authentication — Personal API Token

### How It Works

1. User logs into Canvas LMS via browser
2. Goes to Account > Settings > New Access Token
3. Generates token with note "Canvas Reviewer"
4. Enters token + Canvas URL into app
5. App validates token via `GET /api/v1/users/self`
6. Token encrypted locally with `cryptography` library (AES-256)

### Canvas API Endpoints Used

- `GET /api/v1/courses` — List user's courses
- `GET /api/v1/courses/:id` — Single course details
- `GET /api/v1/courses/:id/modules?include[]=items` — Modules with items
- `GET /api/v1/courses/:id/modules/:id/items` — Module items (paginated)
- `GET /api/v1/courses/:id/pages/:url` — Page content
- `GET /api/v1/courses/:id/files/:id` — File download URL
- `GET /api/v1/courses/:id/files` — Course files listing
- `GET /api/v1/courses/:id/assignments/:id` — Assignment details
- `GET /api/v1/courses/:id/discussion_topics/:id` — Discussion content

### Pagination

- Canvas returns 10 items by default, use `?per_page=100`
- Follow `Link` header `rel="next"` for remaining pages

### Rate Limiting

- Canvas returns `429 Too Many Requests` with `Retry-After` header
- Scraper retries with exponential backoff

---

## 4. Content Extraction — Learning Resources Only

### What We Extract

| Resource Type | Source | Content |
|---------------|--------|---------|
| Pages | Canvas Pages API | `body` (HTML → parsed) |
| Files/PDFs | Canvas Files API | Download → extract text |
| External URLs | Module items | Link extraction |
| Videos (YouTube) | External URLs | Transcript via `youtube-transcript-api` |
| Discussions | Canvas Discussion API | `message` (HTML → parsed) |

### What We Skip

- Quizzes
- Assignments (tasks, not content)
- SubHeaders
- ExternalTools
- Introductions
- Discussion replies (only topics)

### Content Extraction Pipeline

```
Canvas API → Extractor → Raw Text → AI Summarizer → Reviewer Generator
```

Each extractor returns `ExtractedContent`:

```python
@dataclass
class ExtractedContent:
    resource_id: str
    resource_type: str  # "page", "pdf", "video", "discussion", "url"
    title: str
    raw_text: str
    metadata: dict  # url, file_size, video_id, etc.
```

### PDF Extraction

- Download PDF via Canvas Files API
- Extract text with PyMuPDF (free, no AI needed)
- For scanned PDFs: extract images → Ollama vision model → OCR

```python
import pymupdf

def extract_pdf(pdf_path: str) -> str:
    doc = pymupdf.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text
```

### Video Transcript Extraction

- Extract video ID from YouTube URL
- Fetch transcript with `youtube-transcript-api` (free, no API key)

```python
from youtube_transcript_api import YouTubeTranscriptApi

def get_transcript(video_url: str) -> str:
    video_id = extract_video_id(video_url)
    transcript = YouTubeTranscriptApi.get_transcript(video_id)
    return " ".join([entry["text"] for entry in transcript])
```

### HTML Parsing

- Extract readable text from Canvas page HTML
- Remove navigation, headers, footers
- Keep: paragraphs, lists, tables, code blocks

```python
from bs4 import BeautifulSoup

def parse_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    # Remove non-content elements
    for tag in soup.find_all(["nav", "header", "footer", "script", "style"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)
```

---

## 5. AI Summarization — Free Models

### Architecture: Local AI Stack

```
┌─────────────────────────────────────────────────────────┐
│              Free AI Stack (100% Local)                  │
├─────────────────────────────────────────────────────────┤
│  PDF Extraction:  PyMuPDF (free, no AI needed)          │
│  Video Transcripts: youtube-transcript-api (free)       │
│  Text Summarization: Ollama + Local LLM (free)          │
│  Vision/OCR: Ollama + Vision Model (free)               │
└─────────────────────────────────────────────────────────┘
```

### Ollama Setup

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull summarization model
ollama pull qwen3:4b        # 2.5 GB, good quality
ollama pull llama3.2:3b     # 2.0 GB, fast
ollama pull mistral:7b      # 4.4 GB, best instruction following

# Pull vision model (for scanned PDFs)
ollama pull gemma3:4b       # 3.3 GB, multimodal
```

### Model Recommendations

| Model | Size | RAM Needed | Quality | Speed |
|-------|------|------------|---------|-------|
| `llama3.2:3b` | 2.0 GB | 4 GB+ | Good | Fast |
| `qwen3:4b` | 2.5 GB | 6 GB+ | Better | Fast |
| `mistral:7b` | 4.4 GB | 8 GB+ | Best | Medium |
| `gemma3:4b` | 3.3 GB | 6 GB+ | Good (multimodal) | Fast |

### AI Client — Provider Abstraction

```python
def create_ai_client(settings: Settings):
    """Factory pattern - choose AI provider"""
    if settings.ai_provider == "ollama":
        return OllamaClient(url=settings.ollama_url, model=settings.ollama_model)
    elif settings.ai_provider == "groq":
        return GroqClient(api_key=settings.groq_api_key, model=settings.groq_model)
    elif settings.ai_provider == "gemini":
        return GeminiClient(api_key=settings.gemini_api_key, model=settings.gemini_model)
    elif settings.ai_provider == "none":
        return NoAIClient()
    else:
        raise ValueError(f"Unknown AI provider: {settings.ai_provider}")
```

### Ollama Client

```python
import ollama
import json

class OllamaClient:
    def __init__(self, url: str, model: str):
        self.url = url
        self.model = model

    async def summarize(self, content: str, content_type: str) -> dict:
        prompt = f"""Analyze this {content_type} and create a study reviewer.

Content:
{content[:8000]}

Provide in this exact JSON format:
{{
    "key_concepts": ["concept1", "concept2"],
    "summary": "2-3 paragraph overview",
    "key_points": ["point1", "point2"],
    "definitions": {{"term": "definition"}},
    "key_takeaways": ["takeaway1", "takeaway2"]
}}"""
        response = ollama.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        return json.loads(response["message"]["content"])
```

### Free Cloud Alternatives

| Service | Free Tier | Models |
|---------|-----------|--------|
| Groq | 30 RPM, 14,400 req/day | Llama 3, Mixtral |
| Google Gemini | 15 RPM, 1M tokens/day | Gemini 1.5 Flash |
| Hugging Face | 300 req/hour | Llama, Qwen, Gemma |
| Cloudflare Workers AI | 10K neurons/day | Llama, Mistral |

### Groq Client Example

```python
from groq import Groq

class GroqClient:
    def __init__(self, api_key: str, model: str):
        self.client = Groq(api_key=api_key)
        self.model = model

    async def summarize(self, content: str, content_type: str) -> dict:
        prompt = f"""Analyze this {content_type} and create a study reviewer.

Content:
{content[:4000]}

Provide in this exact JSON format:
{{
    "key_concepts": ["concept1", "concept2"],
    "summary": "2-3 paragraph overview",
    "key_points": ["point1", "point2"],
    "definitions": {{"term": "definition"}},
    "key_takeaways": ["takeaway1", "takeaway2"]
}}"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        return json.loads(response.choices[0].message.content)
```

### No-AI Fallback

```python
class NoAIClient:
    """No AI - just return raw text"""
    async def summarize(self, content: str, content_type: str) -> dict:
        return {
            "key_concepts": [],
            "summary": content[:500],
            "key_points": [],
            "definitions": {},
            "key_takeaways": [],
            "original_content": content
        }
```

---

## 6. Freemium Model

### Limits

| Tier | Courses | Queue Priority |
|------|---------|----------------|
| Free | 3 courses | Standard |
| Premium | Unlimited | High |

### Enforcement

- Track generated reviewers per user in DB
- Check limit before allowing new scrape job
- Premium users bypass limit check
- Free users blocked at 3 courses

### Data Model

```python
class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    canvas_url: str
    canvas_token_encrypted: str
    is_premium: bool = False
    courses_generated: int = 0
    created_at: datetime

class ReviewerJob(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    course_id: str
    course_name: str
    status: str  # "queued", "processing", "completed", "failed"
    batch_id: str
    created_at: datetime
    completed_at: datetime | None
```

---

## 7. Queue System — ARQ + Redis

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Queue Architecture                    │
├─────────────────────────────────────────────────────────┤
│  Frontend → FastAPI → ARQ Queue → Worker → Canvas API  │
│                         ↓                               │
│                    Redis (broker)                        │
│                         ↓                               │
│                    PostgreSQL (state)                    │
└─────────────────────────────────────────────────────────┘
```

### Backend Processing (ARQ)

1. User submits job → FastAPI pushes to queue
2. ARQ worker pulls 1 job at a time
3. Worker processes sequentially (no parallel Canvas requests)
4. Results stored in DB immediately
5. Frontend polls `/status/{batch_id}` for progress

### Queue Characteristics

- **Sequential processing:** 1 course at a time
- **No concurrency:** Avoids rate limiting Canvas
- **State tracking:** DB stores job status
- **Progressive results:** Frontend can show completed courses
- **Batch mode:** User selects multiple courses → all queued

### Task Definition

```python
# tasks.py
from arq import cron

async def scrape_course_task(ctx, user_id: int, course_id: str, batch_id: str):
    """Process a single course"""
    user = await get_user(user_id)
    canvas = CanvasClient(user.canvas_url, user.canvas_token_encrypted)
    
    try:
        await update_job_status(batch_id, course_id, "processing")
        
        # 1. Get modules
        modules = await canvas.get_course_modules(course_id)
        
        # 2. Extract content from each module
        extracted = []
        for module in modules:
            for item in module.items:
                if item.type in ["page", "file", "externalurl", "discussion"]:
                    content = await extract_content(canvas, course_id, item)
                    extracted.append(content)
        
        # 3. AI summarize each content
        ai_client = create_ai_client(settings)
        summarized = []
        for content in extracted:
            result = await ai_client.summarize(content.raw_text, content.resource_type)
            summarized.append(AIProcessedContent(**result, original_content=content))
        
        # 4. Generate reviewer
        reviewer = generate_reviewer(course_name, summarized)
        
        # 5. Store result
        await store_reviewer(user_id, course_id, reviewer)
        await update_job_status(batch_id, course_id, "completed")
        
    except Exception as e:
        await update_job_status(batch_id, course_id, "failed", str(e))
```

### Worker Settings

```python
# tasks.py
class WorkerSettings:
    functions = [scrape_course_task]
    redis_settings = RedisSettings(host="redis", port=6379)
    max_tries = 3
    retry_delay = 60  # seconds between retries
```

---

## 8. Reviewer Output Formats

### Output Formats

| Format | Use Case | How |
|--------|----------|-----|
| Markdown | Quick view, copy-paste | Direct text output |
| HTML | Web view, styled | Jinja2 template + CSS |
| PDF | Download, print | WeasyPrint from HTML |

### Reviewer Structure

```markdown
# [Course Name] — Study Reviewer

## Overview
[AI-generated summary of the course content]

---

## Module: [Module Name]

### Key Concepts
- Concept 1
- Concept 2

### Summary
[AI-generated summary of this module]

### Key Points
- Point 1
- Point 2

### Definitions
- **Term:** Definition

### Key Takeaways
- Takeaway 1
- Takeaway 2

### Resources
- [Page Title](link)
- [PDF Title](link)
- [Video Title](link)

---
```

### PDF Generation

```python
import markdown
from weasyprint import HTML

def generate_pdf(reviewer_md: str, output_path: str):
    html_body = markdown.markdown(reviewer_md, extensions=["tables", "fenced_code"])
    full_html = f"""<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #2980b9; }}
        h3 {{ color: #27ae60; }}
        .key-point {{ background: #ecf0f1; padding: 8px; border-left: 4px solid #3498db; margin: 5px 0; }}
    </style>
</head>
<body>{html_body}</body>
</html>"""
    HTML(string=full_html).write_pdf(output_path)
```

---

## 9. Project Structure

```
canvas_lms_scraper/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app, routes
│   │   ├── config.py            # Settings via env vars
│   │   ├── auth.py              # Token validation + encrypted storage
│   │   ├── scraper.py           # Canvas API calls + content extraction
│   │   ├── ai_client.py         # Ollama/Groq/Gemini AI client
│   │   ├── reviewer.py          # Generate MD/HTML/PDF reviewers
│   │   ├── queue.py             # ARQ queue setup
│   │   ├── tasks.py             # Scrape + generate tasks for queue
│   │   ├── freemium.py          # Course selection limits (3 free)
│   │   ├── db.py                # SQLite/PostgreSQL ORM (SQLModel)
│   │   ├── models.py            # Dataclasses + DB models
│   │   └── extractors/
│   │       ├── __init__.py
│   │       ├── pdf.py           # PyMuPDF text extraction
│   │       ├── video.py         # YouTube transcript extraction
│   │       └── html.py          # HTML parsing (BeautifulSoup)
│   ├── requirements.txt
│   ├── Dockerfile
│   └── docker-compose.yml
├── frontend/
│   ├── index.html               # Login page (Canvas URL + token)
│   ├── app.js                   # Frontend API calls + UI logic
│   └── style.css                # Styling
├── ollama/
│   └── Modelfile                # Optional Ollama model config
├── .env.example
├── PLAN.md                      # This file
└── README.md
```

---

## 10. API Routes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Serve frontend HTML |
| POST | `/auth/validate` | Validate Canvas token |
| GET | `/courses` | List user's courses |
| POST | `/scrape/batch` | Queue multiple courses for scraping |
| GET | `/status/{batch_id}` | Check batch job status |
| GET | `/download/{course_id}/{format}` | Download reviewer (md/html/pdf) |

---

## 11. Configuration

```python
# config.py
class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./canvas_reviewer.db"
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    
    # AI Provider
    ai_provider: str = "ollama"  # "ollama", "groq", "gemini", "none"
    
    # Ollama settings
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:4b"
    
    # Groq settings (free cloud)
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"
    
    # Gemini settings (free cloud)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"
    
    # Freemium
    free_course_limit: int = 3
    
    # Output
    output_dir: str = "./output"
    
    # Encryption
    encryption_key: str = ""  # Generated if empty
    
    class Config:
        env_file = ".env"
```

---

## 12. Dependencies

```txt
# Core
fastapi==0.115.*
uvicorn[standard]==0.32.*
httpx==0.28.*
python-multipart==0.0.*

# Database
sqlmodel==0.0.*
aiosqlite==0.20.*
asyncpg==0.30.*

# Queue
arq==0.28.*
redis==5.*

# PDF extraction (free)
pymupdf==1.25.*
pdfplumber==0.11.*

# Video transcripts (free)
youtube-transcript-api==0.6.*

# HTML parsing (free)
beautifulsoup4==4.12.*

# AI - choose one or more
ollama==0.4.*
groq==0.13.*
google-generativeai==0.8.*

# Output
jinja2==3.*
markdown==3.*
weasyprint==62.*

# Security
cryptography==44.*

# Monitoring
structlog==25.*
prometheus-fastapi-instrumentator==7.*
```

---

## 13. Docker Compose

```yaml
services:
  app:
    build: ./backend
    ports:
      - "8000:8000"
    depends_on:
      - redis
      - ollama
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/canvas_reviewer
      - REDIS_URL=redis://redis:6379
      - OLLAMA_URL=http://ollama:11434
    volumes:
      - output_data:/app/output

  worker:
    build: ./backend
    command: arq app.tasks.WorkerSettings
    depends_on:
      - redis
      - ollama
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/canvas_reviewer
      - REDIS_URL=redis://redis:6379
      - OLLAMA_URL=http://ollama:11434
    volumes:
      - output_data:/app/output

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: canvas_reviewer
    volumes:
      - postgres_data:/var/lib/postgresql/data

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./frontend:/usr/share/nginx/html
      - ./nginx/certs:/etc/nginx/certs
    depends_on:
      - app

  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama

volumes:
  output_data:
  postgres_data:
  ollama_data:
```

---

## 14. Implementation Phases

### Phase 1: Foundation
- [ ] Project setup (structure, requirements, Docker)
- [ ] Config + env loading
- [ ] Database models + connection
- [ ] Auth module (token validation + encryption)

### Phase 2: Canvas Integration
- [ ] Canvas API client (pagination, rate limiting)
- [ ] Course listing
- [ ] Module + item extraction

### Phase 3: Content Extractors
- [ ] HTML page extraction
- [ ] PDF text extraction (PyMuPDF)
- [ ] Video transcript extraction (youtube-transcript-api)

### Phase 4: AI Summarization
- [ ] AI client factory
- [ ] Ollama client
- [ ] Groq client (free cloud fallback)
- [ ] No-AI fallback

### Phase 5: Reviewer Generation
- [ ] Markdown generation
- [ ] HTML template
- [ ] PDF generation (WeasyPrint)

### Phase 6: Queue System
- [ ] ARQ setup
- [ ] Worker task implementation
- [ ] Batch job management

### Phase 7: Frontend
- [ ] Login page (Canvas URL + token)
- [ ] Course selection
- [ ] Job status polling
- [ ] Reviewer download

### Phase 8: Production
- [ ] Docker Compose
- [ ] Nginx config
- [ ] Health checks
- [ ] Monitoring (Prometheus)
- [ ] Documentation

---

## 15. Cost Comparison

| Approach | Setup Cost | Running Cost | Quality |
|----------|------------|--------------|---------|
| **Ollama Local** | Free | Free (uses your hardware) | Good |
| **Groq Free** | Free | Free (rate limited) | Good |
| **Gemini Free** | Free | Free (1M tokens/day) | Good |
| **Claude/OpenAI** | Free | $0.25-5/MTok | Excellent |

**Recommendation:** Start with `Ollama + qwen3:4b` for full local, fallback to Groq/Gemini free tier.

---

## 16. Key Decisions Made

| Decision | Choice | Reason |
|----------|--------|--------|
| Auth method | Personal API Token | Simpler than OAuth2, no admin setup needed |
| Queue system | ARQ + Redis | Lightweight, async, Python-native |
| PDF extraction | PyMuPDF | Fast, reliable, free |
| Video transcripts | youtube-transcript-api | Free, no API key needed |
| AI summarization | Ollama (local) | Free, no data leaves machine |
| Freemium limit | 3 courses | Reasonable free tier |
| Database | PostgreSQL (prod) | Robust, scalable |
| Deployment | Docker Compose | Consistent environments |
