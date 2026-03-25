from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.finance import router as finance_router
from app.api.routes.quality import router as quality_router
from app.api.routes.reserved import router as reserved_router
from app.api.routes.registrations import router as registrations_router
from app.api.routes.reviews import router as reviews_router
from app.api.routes.system import router as system_router
from app.api.routes.uploads import router as uploads_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(uploads_router)
api_router.include_router(registrations_router)
api_router.include_router(reviews_router)
api_router.include_router(finance_router)
api_router.include_router(quality_router)
api_router.include_router(system_router)
api_router.include_router(reserved_router)
