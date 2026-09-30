import argparse
from pathlib import Path

from jobly.db.connection import get_connection
from jobly.logging_config import configure_logging


DEFAULT_MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "migrations"


def run_migrations(directory: Path) -> None:
    migration_files = sorted(directory.glob("[0-9][0-9][0-9]_*.sql"))
    if not migration_files:
        raise RuntimeError(f"No migrations found in {directory}")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    filename TEXT PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        conn.commit()
        for migration_file in migration_files:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM schema_migrations WHERE filename = %s",
                    (migration_file.name,),
                )
                if cur.fetchone() is not None:
                    continue
                cur.execute(migration_file.read_text(encoding="utf-8"))
                cur.execute(
                    "INSERT INTO schema_migrations (filename) VALUES (%s)",
                    (migration_file.name,),
                )
            conn.commit()
            print(f"Applied {migration_file.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply pending ordered SQL migrations.")
    parser.add_argument("--directory", type=Path, default=DEFAULT_MIGRATIONS_DIR)
    args = parser.parse_args()
    configure_logging()
    run_migrations(args.directory)


if __name__ == "__main__":
    main()
