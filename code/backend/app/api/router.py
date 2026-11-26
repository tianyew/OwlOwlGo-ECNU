"""HTTP router composition."""

from fastapi import APIRouter

from app.api.endpoints import auth, learning

router = APIRouter()
router.include_router(auth.router)
router.include_router(learning.router)
