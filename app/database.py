from psycopg_pool import ConnectionPool

from app.config import load_settings

settings = load_settings()

pool = ConnectionPool(
    conninfo=settings.database_url,
    min_size=1,
    max_size=4,
    open=True,
)