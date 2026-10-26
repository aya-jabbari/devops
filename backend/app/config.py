from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://supportops:supportops@postgres:5432/supportops"
    secret_key: str = "dev-only-change-me"  # override via env / SOPS secret in cloud
    token_expire_minutes: int = 480

    # Notifications (Celery + SMTP). Mailpit captures mails in local/demo.
    notifications_enabled: bool = True  # tests turn it off so the API never needs Redis
    smtp_host: str = "mailpit"
    smtp_port: int = 1025
    mail_from: str = "supportops@supportops.local"
    mail_domain: str = "supportops.local"  # users have no email column: <username>@<mail_domain>
    overdue_check_seconds: int = 300
    notification_max_retries: int = 3


settings = Settings()
