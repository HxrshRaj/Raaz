from __future__ import annotations

from fastapi import APIRouter

from . import assist, auth, game, ml, npc

router = APIRouter()
router.include_router(auth.router)
router.include_router(game.router)
router.include_router(npc.router)
router.include_router(assist.router)
router.include_router(ml.router)
