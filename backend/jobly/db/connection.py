import psycopg

from jobly.config import get_settings


def get_connection(**kwargs):
    return psycopg.connect(get_settings().require_database_url(), **kwargs)
