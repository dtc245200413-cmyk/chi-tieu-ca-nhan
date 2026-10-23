import os

from sqlalchemy import URL


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def database_url() -> str:
    explicit_url = os.getenv("DATABASE_URL")
    if explicit_url:
        return explicit_url
    return URL.create(
        "postgresql+psycopg",
        username=os.getenv("POSTGRES_USER", "expense_user"),
        password=os.getenv("POSTGRES_PASSWORD", "local-development-only"),
        host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "expense_tracker"),
    ).render_as_string(hide_password=False)


class Config:
    SECRET_KEY = os.getenv("APP_SECRET_KEY", "development-key-change-before-deploying")
    APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
    if APP_ENV == "production":
        db_password = os.getenv("POSTGRES_PASSWORD", "")
        if not SECRET_KEY or SECRET_KEY == "development-key-change-before-deploying" or len(SECRET_KEY) < 32:
            raise RuntimeError("Set APP_SECRET_KEY to a unique random value with at least 32 characters in production.")
        if not db_password or len(db_password) < 32:
            raise RuntimeError("Set POSTGRES_PASSWORD to a unique random value with at least 32 characters in production.")

    SQLALCHEMY_DATABASE_URI = database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", False)
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 12
    TIMEZONE = os.getenv("APP_TIMEZONE", "Asia/Bangkok")
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 60 * 60
