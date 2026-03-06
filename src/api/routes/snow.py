"""Snow removal lot endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import SnowLotOut
from src.database import get_db
from src.models import SnowRemovalLot

router = APIRouter(prefix="/snow", tags=["snow"])


@router.get("/lots", response_model=list[SnowLotOut])
async def find_snow_lots(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    radius_km: float = Query(2.0, le=10.0, description="Search radius in km"),
    db: AsyncSession = Depends(get_db),
):
    """Find nearby snow removal parking lots."""
    point = func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326)
    radius_m = radius_km * 1000

    # Distance in meters using projected CRS
    distance_expr = func.ST_Distance(
        func.ST_Transform(SnowRemovalLot.geom, 3857),
        func.ST_Transform(point, 3857),
    )

    stmt = (
        select(SnowRemovalLot, distance_expr.label("distance_m"))
        .where(SnowRemovalLot.geom.isnot(None))
        .where(
            func.ST_DWithin(
                func.ST_Transform(SnowRemovalLot.geom, 3857),
                func.ST_Transform(point, 3857),
                radius_m,
            )
        )
        .order_by("distance_m")
        .limit(20)
    )

    result = await db.execute(stmt)
    rows = result.all()

    return [
        SnowLotOut(
            id=lot.id,
            nom=lot.nom,
            adresse=lot.adresse,
            latitude=lot.latitude,
            longitude=lot.longitude,
            type_pay=lot.type_pay,
            nb_places=lot.nb_places,
            distance_km=round(dist / 1000, 2) if dist else None,
        )
        for lot, dist in rows
    ]
