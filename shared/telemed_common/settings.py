from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "telemed-service"
    service_port: int = 8100
    environment: str = "dev"

    postgres_dsn: str = "postgresql+psycopg://telemed:telemed@postgres:5432/telemedhub"
    mongodb_url: str = "mongodb://mongo:27017"
    s3_endpoint: str = "minio:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "telemedhub"
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"
    redis_url: str = "redis://redis:6379/0"

    jwt_secret: str = "telemedhub-dev-jwt-secret"
    encryption_key: str = "telemedhub-dev-encryption-key"
    token_exp_minutes: int = 120

    video_target_latency_ms: int = 200
    emr_target_load_ms: int = 2000
    availability_target: float = 99.9
    concurrent_consultations_target: int = 1000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
