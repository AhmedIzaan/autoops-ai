from fastapi import APIRouter, Depends

from app.dependencies import get_settings

router = APIRouter()


@router.get("/status", tags=["system"])
async def status(settings=Depends(get_settings)) -> dict[str, str]:
    return {"status": "ready", "env": settings.env}
