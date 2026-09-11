from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    canvas_url: str
    canvas_token_encrypted: str
    is_premium: bool = False
    courses_generated: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ReviewerJob(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    course_id: str
    course_name: str
    status: str = "queued"
    batch_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class ReviewerResult(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="reviewerjob.id")
    course_id: str
    content_markdown: str
    content_html: Optional[str] = None
    content_pdf_path: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
