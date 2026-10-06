import argparse
import hashlib
from pathlib import Path

from jobly.db.connection import get_connection
from jobly.logging_config import configure_logging


DEFAULT_MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "migrations"


def migration_checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    checksum TEXT
                )
                """
            )
            cur.execute("ALTER TABLE schema_migrations ADD COLUMN IF NOT EXISTS checksum TEXT")
        conn.commit()
        for migration_file in migration_files:
            with conn.cursor() as cur:
                checksum = migration_checksum(migration_file)
                cur.execute(
                    "SELECT checksum FROM schema_migrations WHERE filename = %s",
                    (migration_file.name,),
                )
                applied = cur.fetchone()
                if applied is not None:
                    existing = applied[0]
                    if existing is None:
                        cur.execute(
                            "UPDATE schema_migrations SET checksum = %s WHERE filename = %s",
                            (checksum, migration_file.name),
                        )
                        conn.commit()
                    elif existing != checksum:
                        raise RuntimeError(
                            f"Migration checksum mismatch for {migration_file.name}"
                        )
                    continue
                cur.execute(migration_file.read_text(encoding="utf-8"))
                cur.execute(
                    "INSERT INTO schema_migrations (filename, checksum) VALUES (%s, %s)",
                    (migration_file.name, checksum),
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
