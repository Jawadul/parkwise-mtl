"""Parking search, summary, and rules endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.schemas import ParkingRulesOut, ParkingSpaceOut, ParkingSummaryOut
from src.database import get_db
from src.models import ParkingSpace, PayStation, Regulation, RegulationPeriod

router = APIRouter(prefix="/parking", tags=["parking"])


@router.get("/search", response_model=list[ParkingSpaceOut])
async def search_parking(
    street: str = Query(..., description="Street name to search"),
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Search parking spaces by street name."""
    pattern = f"%{street}%"
    stmt = (
        select(ParkingSpace)
        .outerjoin(Regulation)
        .where(
            ParkingSpace.no_place.ilike(pattern)
            | ParkingSpace.commune.ilike(pattern)
            | ParkingSpace.no_emplacement.ilike(pattern)
        )
        .limit(limit)
    )
    result = await db.execute(stmt)
    spaces = result.scalars().all()

    return [
        ParkingSpaceOut(
            id=s.id,
            no_place=s.no_place,
            latitude=s.latitude,
            longitude=s.longitude,
            type_place=s.type_place,
            tarif=s.tarif,
            commune=s.commune,
            regulation_description=(
                s.regulation.description if s.regulation else None
            ),
        )
        for s in spaces
    ]


@router.get("/summary", response_model=ParkingSummaryOut)
async def parking_summary(
    street: str = Query(..., description="Street name"),
    borough: str | None = Query(None, description="Borough/arrondissement"),
    db: AsyncSession = Depends(get_db),
):
    """Summary of paid parking on a street."""
    pattern = f"%{street}%"

    # Count paid spaces
    space_stmt = select(ParkingSpace).where(
        ParkingSpace.no_place.ilike(pattern)
        | ParkingSpace.commune.ilike(pattern)
        | ParkingSpace.no_emplacement.ilike(pattern)
    )
    if borough:
        space_stmt = space_stmt.where(ParkingSpace.commune.ilike(f"%{borough}%"))

    result = await db.execute(space_stmt)
    spaces = result.scalars().all()

    # Count pay stations (approximate by matching nearby stations)
    station_count_stmt = select(func.count(PayStation.id)).where(
        PayStation.no_borne.ilike(pattern)
    )
    station_result = await db.execute(station_count_stmt)
    station_count = station_result.scalar() or 0

    return ParkingSummaryOut(
        street=street,
        borough=borough,
        paid_space_count=len(spaces),
        pay_station_count=station_count,
        spaces=[
            ParkingSpaceOut(
                id=s.id,
                no_place=s.no_place,
                latitude=s.latitude,
                longitude=s.longitude,
                type_place=s.type_place,
                tarif=s.tarif,
                commune=s.commune,
                regulation_description=None,
            )
            for s in spaces[:20]
        ],
    )


@router.get("/rules", response_model=ParkingRulesOut)
async def parking_rules(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    at: str = Query(None, description="ISO datetime (default: now)"),
    db: AsyncSession = Depends(get_db),
):
    """Get parking rules for a location at a given time."""
    if at:
        check_time = datetime.fromisoformat(at)
    else:
        check_time = datetime.now()

    day_of_week = check_time.isoweekday()  # 1=Mon..7=Sun
    current_time = check_time.time()

    # Find nearest parking spaces with regulations
    point = func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326)
    stmt = (
        select(
            ParkingSpace,
            func.ST_Distance(
                func.ST_Transform(ParkingSpace.geom, 3857),
                func.ST_Transform(point, 3857),
            ).label("distance_m"),
        )
        .where(ParkingSpace.geom.isnot(None))
        .where(ParkingSpace.regulation_id.isnot(None))
        .order_by("distance_m")
        .limit(5)
    )
    result = await db.execute(stmt)
    nearest = result.all()

    regulations_info = []
    is_allowed = True
    payment_required = False
    rate = None
    max_dur = None

    for space, dist in nearest:
        # Load regulation and periods
        reg_stmt = (
            select(Regulation)
            .options(selectinload(Regulation.periods))
            .where(Regulation.id == space.regulation_id)
        )
        reg_result = await db.execute(reg_stmt)
        reg = reg_result.scalar_one_or_none()
        if not reg:
            continue

        reg_info = {
            "no_reglementation": reg.no_reglementation,
            "description": reg.description,
            "type": reg.type_reglementation,
            "distance_m": round(dist, 1) if dist else None,
            "periods": [],
        }

        for p in reg.periods:
            period_info = {
                "day_of_week": p.day_of_week,
                "start_time": str(p.start_time) if p.start_time else None,
                "end_time": str(p.end_time) if p.end_time else None,
                "duration_max_minutes": p.duration_max_minutes,
                "rate_cents_per_hour": p.rate_cents_per_hour,
            }
            reg_info["periods"].append(period_info)

            # Check if this period applies now
            if p.day_of_week and p.day_of_week != day_of_week:
                continue
            if p.start_time and p.end_time:
                if p.start_time <= current_time <= p.end_time:
                    if p.rate_cents_per_hour and p.rate_cents_per_hour > 0:
                        payment_required = True
                        rate = p.rate_cents_per_hour
                    if p.duration_max_minutes:
                        max_dur = p.duration_max_minutes

        regulations_info.append(reg_info)

    return ParkingRulesOut(
        latitude=lat,
        longitude=lon,
        at=check_time.isoformat(),
        nearest_regulations=regulations_info,
        is_parking_allowed=is_allowed,
        payment_required=payment_required,
        rate_cents_per_hour=rate,
        max_duration_minutes=max_dur,
    )
