from fastapi import APIRouter

router = APIRouter()


@router.get("/health/", summary="Health check")
async def health_check():
    """Health check."""
    return {
        "success": True,
        "data": {"status": "ok"},
        "message": "Workspace Management Service healthy"
    } 