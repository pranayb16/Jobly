from fastapi import APIRouter

from jobly.db.pool import get_pool


router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    with get_pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
    return {"status": "ok"}

