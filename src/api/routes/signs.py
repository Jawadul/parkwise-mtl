"""Parking sign search endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import ParkingSignOut
from src.database import get_db
from src.models import ParkingSign

router = APIRouter(prefix="/signs", tags=["signs"])


@router.get("/search", response_model=list[ParkingSignOut])
async def search_signs(
    street: str | None = Query(None, description="Street name or keyword"),
    borough: str | None = Query(None, description="Borough/arrondissement"),
    code: str | None = Query(None, description="RPA code to search"),
    lat: float | None = Query(None, description="Latitude for nearby search"),
    lon: float | None = Query(None, description="Longitude for nearby search"),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Search parking signs by keyword, borough, code, or location."""
    conditions = []

    if street:
        pattern = f"%{street}%"
        conditions.append(
            or_(
                ParkingSign.description_rpa.ilike(pattern),
                ParkingSign.code_rpa.ilike(pattern),
                ParkingSign.street_name.ilike(pattern),
            )
        )

    if borough:
        conditions.append(ParkingSign.nom_arrond.ilike(f"%{borough}%"))

    if code:
        conditions.append(ParkingSign.code_rpa.ilike(f"%{code}%"))

    # If lat/lon provided, find nearest signs
    if lat is not None and lon is not None:
        point = func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326)
        distance = func.ST_Distance(
            func.ST_Transform(ParkingSign.geom, 3857),
            func.ST_Transform(point, 3857),
        )
        stmt = (
            select(ParkingSign)
            .where(ParkingSign.geom.isnot(None))
        )
        for cond in conditions:
            stmt = stmt.where(cond)
        stmt = stmt.order_by(distance).limit(limit)
    else:
        if not conditions:
            # Need at least one search criteria
            return []
        stmt = select(ParkingSign)
        for cond in conditions:
            stmt = stmt.where(cond)
        stmt = stmt.limit(limit)

    result = await db.execute(stmt)
    signs = result.scalars().all()

    return [ParkingSignOut.model_validate(s) for s in signs]
