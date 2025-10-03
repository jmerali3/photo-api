import os
from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    aws_region: str = Field(default="us-west-2")
    aws_profile: Optional[str] = Field(default=None)
    s3_bucket_raw: str = Field(default="my-raw-upload-bucket-070703032025")
    s3_bucket_processed: str = Field(default="my-ocr-processed-bucket-070703032025")

    temporal_target: str = Field(default="localhost:7233")
    temporal_namespace: str = Field(default="default")
    temporal_task_queue: str = Field(default="recipe-process")

    presign_expires_seconds: int = Field(default=300)

    api_version: str = Field(default="0.1.0")
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")

    cors_origins: str = Field(default="*")
    max_upload_size: int = Field(default=25_000_000)

    health_check_timeout: int = Field(default=30)

    # Authentication
    api_key: str = Field(default="your-secret-api-key-here")

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://appuser:<sensitive>@photo-dev-dev-pg.cr8uowes62h6.us-west-2.rds.amazonaws.com:5432/photo_worker"
    )

    @property
    def cors_origins_list(self) -> List[str]:
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"

@lru_cache
def get_settings() -> "Settings":
    return Settings()
