from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from jobly.config import get_settings


_pool: ConnectionPool | None = None


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            conninfo=get_settings().require_database_url(),
            min_size=1,
            max_size=10,
            kwargs={"row_factory": dict_row},
            open=False,
        )
    return _pool


def open_pool() -> None:
    pool = get_pool()
    pool.open()
    pool.wait()


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None
