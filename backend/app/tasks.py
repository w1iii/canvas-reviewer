import json
import logging

from app.ai_client import create_ai_client
from app.config import settings
from app.reviewer import generate_html, generate_markdown, generate_pdf
from app.scraper import CanvasClient

logger = logging.getLogger(__name__)


async def scrape_course_task(ctx, user_id: int, course_id: str, batch_id: str):
    from app.auth import decrypt_token
    from app.db import engine
    from app.models import ReviewerJob, ReviewerResult, User
    from sqlmodel.ext.asyncio.session import AsyncSession

    async with AsyncSession(engine) as session:
        user = await session.get(User, user_id)
        if not user:
            logger.error("User %d not found", user_id)
            return

        token = decrypt_token(user.canvas_token_encrypted, settings.encryption_key)
        canvas = CanvasClient(user.canvas_url, token)

        try:
            job = (
                await session.exec(
                    ReviewerJob.__table__.select().where(
                        ReviewerJob.batch_id == batch_id,
                        ReviewerJob.course_id == course_id,
                    )
                )
            ).first()
            if job:
                job.status = "processing"
                await session.commit()

            modules = await canvas.get_course_modules(course_id)

            ai_client = create_ai_client(
                settings.ai_provider,
                ollama_url=settings.ollama_url,
                ollama_model=settings.ollama_model,
                groq_api_key=settings.groq_api_key,
                groq_model=settings.groq_model,
                gemini_api_key=settings.gemini_api_key,
                gemini_model=settings.gemini_model,
            )

            summarized_modules = []
            for mod in modules:
                items = mod.get("items", [])
                resources = []
                combined_text = ""

                for item in items:
                    item_type = item.get("type", "")
                    if item_type == "Page":
                        page = await canvas.get_page_content(course_id, item["page_url"])
                        combined_text += f"\n{page.get('body', '')}"
                        resources.append({"title": item["title"], "url": item.get("html_url", "")})
                    elif item_type == "File":
                        try:
                            file_bytes = await canvas.get_file_content(course_id, str(item["id"]))
                            combined_text += f"\n[File: {item['title']}]"
                            resources.append({"title": item["title"], "url": item.get("html_url", "")})
                        except Exception:
                            pass
                    elif item_type == "ExternalUrl":
                        combined_text += f"\n{item.get('external_url', '')}"
                        resources.append({"title": item["title"], "url": item.get("external_url", "")})

                if combined_text.strip():
                    result = await ai_client.summarize(combined_text, "canvas module")
                    result["name"] = mod["name"]
                    result["resources"] = resources
                    summarized_modules.append(result)

            md = generate_markdown(mod.get("name", course_id), summarized_modules)
            html = generate_html(md)

            output_dir = settings.output_dir
            pdf_path = f"{output_dir}/{course_id}.pdf"
            generate_pdf(html, pdf_path)

            reviewer = ReviewerResult(
                job_id=job.id if job else 0,
                course_id=course_id,
                content_markdown=md,
                content_html=html,
                content_pdf_path=pdf_path,
            )
            session.add(reviewer)

            if job:
                job.status = "completed"
            user.courses_generated += 1

            await session.commit()

        except Exception as e:
            logger.exception("Failed to scrape course %s", course_id)
            if job:
                job.status = "failed"
                job.error_message = str(e)
                await session.commit()
        finally:
            await canvas.close()
