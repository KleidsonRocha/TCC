import asyncio
from urllib.error import URLError
from urllib.request import urlopen

from app.config import Settings
from app.infra.postgres_conninfo import build_catalog_conninfo, build_erp_conninfo

try:
    import psycopg
except Exception:  # pragma: no cover - optional local dependency
    psycopg = None  # type: ignore[assignment]


def _postgres_status(*, conninfo: str, timeout_s: float) -> dict[str, str]:
    if psycopg is None:
        return {"status": "unavailable"}
    try:
        with psycopg.connect(conninfo, connect_timeout=max(1, int(timeout_s))) as conn:  # type: ignore[union-attr]
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
    except Exception:
        return {"status": "unavailable"}
    return {"status": "ready"}


def _ollama_status(*, base_url: str, timeout_s: float) -> dict[str, str]:
    try:
        with urlopen(f"{base_url.rstrip('/')}/api/tags", timeout=timeout_s) as response:
            if 200 <= response.status < 300:
                return {"status": "ready"}
    except (OSError, URLError, ValueError):
        pass
    return {"status": "unavailable"}


def check_readiness(settings: Settings) -> dict[str, object]:
    timeout_s = max(0.1, settings.readiness_timeout_s)
    dependencies: dict[str, dict[str, str]] = {}
    if settings.catalog_db_enabled:
        dependencies["catalog"] = _postgres_status(
            conninfo=build_catalog_conninfo(settings), timeout_s=timeout_s
        )
    else:
        dependencies["catalog"] = {"status": "disabled"}
    if settings.erp_db_enabled:
        dependencies["erp"] = _postgres_status(
            conninfo=build_erp_conninfo(settings), timeout_s=timeout_s
        )
    else:
        dependencies["erp"] = {"status": "disabled"}
    dependencies["inference"] = _ollama_status(
        base_url=settings.llm_base_url, timeout_s=timeout_s
    )
    is_ready = all(item["status"] in {"ready", "disabled"} for item in dependencies.values())
    return {
        "status": "ready" if is_ready else "degraded",
        "dependencies": dependencies,
    }


async def check_readiness_async(settings: Settings) -> dict[str, object]:
    return await asyncio.to_thread(check_readiness, settings)
