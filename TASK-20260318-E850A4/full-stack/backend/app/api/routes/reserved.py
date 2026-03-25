from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/reserved", tags=["reserved"])


@router.get("/similarity-check")
def similarity_check_reserved():
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content={
            "success": False,
            "error": {
                "code": "NOT_IMPLEMENTED",
                "message": "Feature disabled by policy",
                "details": {},
                "request_id": "",
            },
        },
    )
