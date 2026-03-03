"""Parking sign search endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import ParkingSignOut
from src.database import get_db
from src.models import ParkingSign

router = APIRouter(prefix="/signs", tags=["signs"])


@router.get("/search", response_model=list[ParkingSignOut])
async def search_signs(
    street: str = Query(..., description="Street name"),
    borough: str | None = Query(None, description="Borough/arrondissement"),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Search parking signs by street name."""
    pattern = f"%{street}%"
    stmt = select(ParkingSign).where(
        ParkingSign.street_name.ilike(pattern)
        | ParkingSign.description_rpa.ilike(pattern)
    )
    if borough:
        stmt = stmt.where(ParkingSign.nom_arrond.ilike(f"%{borough}%"))
    stmt = stmt.limit(limit)

    result = await db.execute(stmt)
    signs = result.scalars().all()

    return [ParkingSignOut.model_validate(s) for s in signs]
