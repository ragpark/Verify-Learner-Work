from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # LTI (tool key only used if you later expose your JWKS; PoC validates platform tokens)
    LTI_TOOL_PRIVATE_KEY_JWK: str
    LTI_TOOL_KID: str = "tool-key-1"

    # Session
    SESSION_SECRET: str = "change-me"

    # Azure
    AZURE_STORAGE_ACCOUNT: str
    AZURE_STORAGE_KEY: str
    AZURE_BLOB_CONTAINER: str
    AZURE_BLOB_UPLOAD_CONCURRENCY: int = 4
    AZURE_BLOB_BLOCK_SIZE_MB: int = 8

    # Infra
    DATABASE_URL: Optional[str] = None
    REDIS_URL: Optional[str] = None

    # App
    APP_BASE_URL: Optional[str] = None
    ENV: str = "dev"

    model_config = {"env_file": ".env", "extra": "ignore"}

settings = Settings()
