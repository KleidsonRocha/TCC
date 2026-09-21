from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from app.api.readiness import check_readiness_async
from app.config import Settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready(request: Request) -> JSONResponse:
    settings: Settings = request.app.state.settings
    result = await check_readiness_async(settings)
    response_status = (
        status.HTTP_200_OK
        if result["status"] == "ready"
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )
    return JSONResponse(status_code=response_status, content=result)
