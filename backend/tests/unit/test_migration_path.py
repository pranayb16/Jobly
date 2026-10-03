from jobly.commands.migrate import (
    DEFAULT_MIGRATIONS_DIR,
)


def test_default_migration_path_contains_ordered_migrations():
    files = sorted(
        path.name
        for path
        in DEFAULT_MIGRATIONS_DIR.glob(
            "[0-9][0-9][0-9]_*.sql"
        )
    )

    assert files

    assert files[0] == (
        "001_initial.sql"
    )

    numbers = [
        int(filename[:3])
        for filename
        in files
    ]

    assert numbers == sorted(
        numbers
    )

    assert len(numbers) == len(
        set(numbers)
    )


def test_default_migration_directory_exists():
    assert (
        DEFAULT_MIGRATIONS_DIR.exists()
    )

    assert (
        DEFAULT_MIGRATIONS_DIR.is_dir()
    )