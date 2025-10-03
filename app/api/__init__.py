"""Aggregate API router (no prefix here; main.py owns '/api').

Collects sub-routers: admin, enroll, identify, config.
"""
from __future__ import annotations

from fastapi import APIRouter

from .routes_admin import router as admin_router
from .routes_enroll import router as enroll_router
from .routes_identify import router as identify_router
from .routes_config import router as config_router

# Do not set a prefix here; main.py will include this router with prefix="/api".
router = APIRouter()

router.include_router(admin_router, tags=["admin"])
router.include_router(enroll_router, tags=["enroll"])
router.include_router(identify_router, tags=["identify"])
router.include_router(config_router, tags=["config"])
