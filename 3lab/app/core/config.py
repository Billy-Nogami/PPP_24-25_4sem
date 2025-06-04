from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///app.db"  # Значение по умолчанию
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str = "secret-key"  # На продакшене через .env
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
settings = Settings()