from arq.connections import RedisSettings

from app.config import settings


class WorkerSettings:
    functions = ["app.tasks.scrape_course_task"]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_tries = 3
    retry_delay = 60
