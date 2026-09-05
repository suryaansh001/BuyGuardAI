from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    DATABASE_URL: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/agent_commerce",
        description="PostgreSQL connection URL"
    )
    RAZORPAY_KEY_ID: str = Field(default="", description="Razorpay Key ID")
    RAZORPAY_KEY_SECRET: str = Field(default="", description="Razorpay Key Secret")
    RAZORPAY_WEBHOOK_SECRET: str = Field(default="", description="Razorpay Webhook Secret")
    GROQ_API_KEY: str = Field(default="", description="Groq API Key")
    OPENROUTER_API_KEY: str = Field(default="", description="OpenRouter API Key")
    JWT_SECRET: str = Field(default="dev-secret-change-in-production", description="JWT secret key")
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="Access token expiry")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "allow"


settings = Settings()