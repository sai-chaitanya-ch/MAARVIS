from fastapi import APIRouter, HTTPException

from memory.conversation import get_source

router = APIRouter()


@router.get("/{source_id}")
async def source(source_id: str):
    data = await get_source(source_id)
    if not data:
        raise HTTPException(status_code=404, detail="Source not found")
    return data
