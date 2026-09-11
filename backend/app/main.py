import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth import encrypt_token, validate_canvas_token
from app.config import settings
from app.db import engine, init_db
from app.freemium import check_course_limit
from app.models import ReviewerJob, ReviewerResult, User
from app.scraper import CanvasClient

app = FastAPI(title="Canvas LMS Reviewer Generator")


class ValidateRequest(BaseModel):
    canvas_url: str
    canvas_token: str


class ScrapeRequest(BaseModel):
    user_id: int
    course_ids: list[str]


@app.on_event("startup")
async def startup():
    await init_db()
    Path(settings.output_dir).mkdir(parents=True, exist_ok=True)


@app.post("/auth/validate")
async def auth_validate(req: ValidateRequest):
    try:
        user_info = await validate_canvas_token(req.canvas_url, req.canvas_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Canvas token")

    encrypted = encrypt_token(req.canvas_token, settings.encryption_key)

    async with AsyncSession(engine) as session:
        stmt = select(User).where(User.canvas_url == req.canvas_url)
        result = await session.exec(stmt)
        user = result.first()

        if user:
            user.canvas_token_encrypted = encrypted
        else:
            user = User(
                canvas_url=req.canvas_url,
                canvas_token_encrypted=encrypted,
            )
            session.add(user)

        await session.commit()
        await session.refresh(user)

    return {"user_id": user.id, "name": user_info.get("name", "Unknown")}


@app.get("/courses")
async def list_courses(user_id: int):
    async with AsyncSession(engine) as session:
        user = await session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

    from app.auth import decrypt_token

    token = decrypt_token(user.canvas_token_encrypted, settings.encryption_key)
    canvas = CanvasClient(user.canvas_url, token)

    try:
        courses = await canvas.get_courses()
        return [
            {"id": str(c["id"]), "name": c.get("name", "")}
            for c in courses
            if c.get("enrollment_state") == "active"
        ]
    finally:
        await canvas.close()


@app.post("/scrape/batch")
async def scrape_batch(req: ScrapeRequest):
    async with AsyncSession(engine) as session:
        user = await session.get(User, req.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if not await check_course_limit(user):
            raise HTTPException(
                status_code=403,
                detail=f"Free limit reached ({settings.free_course_limit} courses). Upgrade to premium.",
            )

        batch_id = str(uuid.uuid4())

        for course_id in req.course_ids:
            job = ReviewerJob(
                user_id=user.id,
                course_id=course_id,
                course_name="",
                batch_id=batch_id,
            )
            session.add(job)

        await session.commit()

    from arq import create_pool
    from arq.connections import RedisSettings

    pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    for course_id in req.course_ids:
        await pool.enqueue_job("scrape_course_task", user.id, course_id, batch_id)
    await pool.close()

    return {"batch_id": batch_id}


@app.get("/status/{batch_id}")
async def batch_status(batch_id: str):
    async with AsyncSession(engine) as session:
        stmt = select(ReviewerJob).where(ReviewerJob.batch_id == batch_id)
        result = await session.exec(stmt)
        jobs = result.all()

    if not jobs:
        raise HTTPException(status_code=404, detail="Batch not found")

    return {
        "batch_id": batch_id,
        "jobs": [
            {
                "course_id": j.course_id,
                "course_name": j.course_name,
                "status": j.status,
                "error": j.error_message,
            }
            for j in jobs
        ],
    }


@app.get("/download/{course_id}/{fmt}")
async def download_reviewer(course_id: str, fmt: str):
    async with AsyncSession(engine) as session:
        stmt = (
            select(ReviewerResult)
            .where(ReviewerResult.course_id == course_id)
            .order_by(ReviewerResult.id.desc())
        )
        result = await session.exec(stmt)
        reviewer = result.first()

    if not reviewer:
        raise HTTPException(status_code=404, detail="Reviewer not found")

    if fmt == "md":
        return StreamingResponse(
            iter([reviewer.content_markdown.encode()]),
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename={course_id}.md"},
        )
    elif fmt == "html":
        return StreamingResponse(
            iter([reviewer.content_html.encode()]),
            media_type="text/html",
            headers={"Content-Disposition": f"attachment; filename={course_id}.html"},
        )
    elif fmt == "pdf":
        if reviewer.content_pdf_path and Path(reviewer.content_pdf_path).exists():
            return StreamingResponse(
                iter([Path(reviewer.content_pdf_path).read_bytes()]),
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename={course_id}.pdf"},
            )
        raise HTTPException(status_code=404, detail="PDF not generated yet")
    else:
        raise HTTPException(status_code=400, detail="Format must be md, html, or pdf")


@app.get("/", response_class=HTMLResponse)
async def root():
    index_path = Path(__file__).parent.parent.parent / "frontend" / "index.html"
    if index_path.exists():
        return index_path.read_text()
    return "<h1>Canvas LMS Reviewer Generator</h1>"
