"""HTTP router composition."""

from fastapi import APIRouter

from app.api.endpoints import auth, knowledge, learning

router = APIRouter()
router.include_router(auth.router)
router.include_router(learning.router)
router.include_router(knowledge.router)
