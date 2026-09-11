from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite+aiosqlite:///./canvas_reviewer.db"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # AI Provider
    ai_provider: str = "ollama"

    # Ollama settings
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:4b"

    # Groq settings
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"

    # Gemini settings
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"

    # Freemium
    free_course_limit: int = 3

    # Output
    output_dir: str = "./output"

    # Encryption
    encryption_key: str = ""

    model_config = {"env_file": ".env"}


settings = Settings()
