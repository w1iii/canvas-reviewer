from app.config import settings
from app.models import User


async def check_course_limit(user: User) -> bool:
    if user.is_premium:
        return True
    return user.courses_generated < settings.free_course_limit
