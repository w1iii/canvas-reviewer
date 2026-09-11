# Canvas LMS Reviewer Generator — Implementation Tasks

## Phase 1: Project Foundation

- [ ] 1.1 Create directory structure (backend/app/, frontend/, nginx/, backend/app/extractors/)
- [ ] 1.2 Create `requirements.txt`
- [ ] 1.3 Create `.env.example`
- [ ] 1.4 Populate `.gitignore`
- [ ] 1.5 Create `config.py` with pydantic-settings
- [ ] 1.6 Create database models (`models.py` — User, ReviewerJob, ReviewerResult)
- [ ] 1.7 Create database connection (`db.py`)

## Phase 2: Auth & Security

- [ ] 2.1 Implement token validation (`GET /api/v1/users/self`)
- [ ] 2.2 AES-256 encryption for Canvas tokens
- [ ] 2.3 Auth routes (`POST /auth/validate`)

## Phase 3: Canvas API Client

- [ ] 3.1 HTTP client with httpx
- [ ] 3.2 Pagination handling (Link header parsing)
- [ ] 3.3 Rate limit retry with exponential backoff
- [ ] 3.4 Course listing endpoint (`GET /courses`)
- [ ] 3.5 Module + item fetching with `include[]=items`

## Phase 4: Content Extractors

- [ ] 4.1 HTML parser (BeautifulSoup)
- [ ] 4.2 PDF extractor (PyMuPDF)
- [ ] 4.3 YouTube transcript extractor
- [ ] 4.4 Content router (scraper.py dispatches to extractors)

## Phase 5: AI Summarization

- [ ] 5.1 AI client factory pattern
- [ ] 5.2 Ollama client
- [ ] 5.3 Groq client (free cloud fallback)
- [ ] 5.4 No-AI fallback

## Phase 6: Reviewer Generation

- [ ] 6.1 Markdown generation
- [ ] 6.2 HTML template (Jinja2)
- [ ] 6.3 PDF generation (WeasyPrint)

## Phase 7: Queue System

- [ ] 7.1 ARQ setup + WorkerSettings
- [ ] 7.2 Worker task implementation (scrape_course_task)
- [ ] 7.3 Batch job management (enqueue + status tracking)
- [ ] 7.4 Status polling endpoint (`GET /status/{batch_id}`)

## Phase 8: Frontend

- [ ] 8.1 Login page (Canvas URL + token input)
- [ ] 8.2 Course selection UI (checkboxes)
- [ ] 8.3 Job status polling
- [ ] 8.4 Reviewer download (md/html/pdf)

## Phase 9: Production & Deployment

- [ ] 9.1 Multi-stage Dockerfile
- [ ] 9.2 Docker Compose (app, worker, redis, postgres, nginx)
- [ ] 9.3 Nginx reverse proxy config
- [ ] 9.4 Health checks
- [ ] 9.5 Monitoring (Prometheus)
- [ ] 9.6 README documentation

---

**Estimated Timeline:** 18 days
