from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://supportops:supportops@postgres:5432/supportops"
    secret_key: str = "dev-only-change-me"  # override via env / SOPS secret in cloud
    token_expire_minutes: int = 480


settings = Settings()
