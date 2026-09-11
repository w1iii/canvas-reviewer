# Canvas LMS Reviewer Generator — Implementation Tasks

## Phase 1: Project Foundation

- [x] 1.1 Create directory structure (backend/app/, frontend/, nginx/, backend/app/extractors/)
- [x] 1.2 Create `requirements.txt`
- [x] 1.3 Create `.env.example`
- [x] 1.4 Populate `.gitignore`
- [x] 1.5 Create `config.py` with pydantic-settings
- [x] 1.6 Create database models (`models.py` — User, ReviewerJob, ReviewerResult)
- [x] 1.7 Create database connection (`db.py`)

## Phase 2: Auth & Security

- [x] 2.1 Implement token validation (`GET /api/v1/users/self`)
- [x] 2.2 AES-256 encryption for Canvas tokens
- [x] 2.3 Auth routes (`POST /auth/validate`)

## Phase 3: Canvas API Client

- [x] 3.1 HTTP client with httpx
- [x] 3.2 Pagination handling (Link header parsing)
- [x] 3.3 Rate limit retry with exponential backoff
- [x] 3.4 Course listing endpoint (`GET /courses`)
- [x] 3.5 Module + item fetching with `include[]=items`

## Phase 4: Content Extractors

- [x] 4.1 HTML parser (BeautifulSoup)
- [x] 4.2 PDF extractor (PyMuPDF)
- [x] 4.3 YouTube transcript extractor
- [x] 4.4 Content router (scraper.py dispatches to extractors)

## Phase 5: AI Summarization

- [x] 5.1 AI client factory pattern
- [x] 5.2 Ollama client
- [x] 5.3 Groq client (free cloud fallback)
- [x] 5.4 No-AI fallback

## Phase 6: Reviewer Generation

- [x] 6.1 Markdown generation
- [x] 6.2 HTML template (Jinja2)
- [x] 6.3 PDF generation (WeasyPrint)

## Phase 7: Queue System

- [x] 7.1 ARQ setup + WorkerSettings
- [x] 7.2 Worker task implementation (scrape_course_task)
- [x] 7.3 Batch job management (enqueue + status tracking)
- [x] 7.4 Status polling endpoint (`GET /status/{batch_id}`)

## Phase 8: Frontend

- [x] 8.1 Login page (Canvas URL + token input)
- [x] 8.2 Course selection UI (checkboxes)
- [x] 8.3 Job status polling
- [x] 8.4 Reviewer download (md/html/pdf)

## Phase 9: Production & Deployment

- [x] 9.1 Multi-stage Dockerfile
- [x] 9.2 Docker Compose (app, worker, redis, postgres, nginx)
- [x] 9.3 Nginx reverse proxy config
- [x] 9.4 Health checks
- [x] 9.5 Monitoring (Prometheus)
- [x] 9.6 README documentation

---

**Estimated Timeline:** 18 days
**Completed:** 37/37 tasks
