"""
Favorites Router
"""

from fastapi import APIRouter
from database.repository import ScanRepository
from server.schemas import FavoritePluginRequest

router = APIRouter(prefix="/api/favorites", tags=["favorites"])
repo = ScanRepository()


@router.get("")
async def list_favorites():
    return {"favorites": repo.get_favorites()}


@router.post("")
async def add_favorite(plugin: FavoritePluginRequest):
    success = repo.add_favorite(plugin.model_dump())
    return {"success": success}


@router.delete("/{slug}")
async def remove_favorite(slug: str):
    success = repo.remove_favorite(slug)
    return {"success": success}
