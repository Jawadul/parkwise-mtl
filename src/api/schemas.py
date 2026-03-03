from datetime import time
from pydantic import BaseModel


class ParkingSpaceOut(BaseModel):
    id: int
    no_place: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    type_place: str | None = None
    tarif: str | None = None
    commune: str | None = None
    regulation_description: str | None = None

    model_config = {"from_attributes": True}


class ParkingSummaryOut(BaseModel):
    street: str
    borough: str | None = None
    paid_space_count: int
    pay_station_count: int
    spaces: list[ParkingSpaceOut]


class RegulationPeriodOut(BaseModel):
    day_of_week: int | None = None
    start_time: str | None = None
    end_time: str | None = None
    duration_max_minutes: int | None = None
    rate_cents_per_hour: int | None = None


class ParkingRulesOut(BaseModel):
    latitude: float
    longitude: float
    at: str
    nearest_regulations: list[dict]
    is_parking_allowed: bool | None = None
    payment_required: bool | None = None
    rate_cents_per_hour: int | None = None
    max_duration_minutes: int | None = None


class ParkingSignOut(BaseModel):
    id: int
    code_rpa: str | None = None
    description_rpa: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    nom_arrond: str | None = None
    street_name: str | None = None

    model_config = {"from_attributes": True}


class SnowLotOut(BaseModel):
    id: int
    nom: str | None = None
    adresse: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    type_pay: str | None = None
    nb_places: int | None = None
    distance_km: float | None = None

    model_config = {"from_attributes": True}


class HealthOut(BaseModel):
    status: str
    db_connected: bool
