from geoalchemy2 import Geometry
from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class ParkingSign(Base):
    __tablename__ = "parking_signs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    poteau_id: Mapped[str | None] = mapped_column(String, index=True)
    panneau_id: Mapped[str | None] = mapped_column(String, index=True)
    code_rpa: Mapped[str | None] = mapped_column(String, index=True)
    description_rpa: Mapped[str | None] = mapped_column(String)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    geom = mapped_column(Geometry("POINT", srid=4326), nullable=True, index=True)
    nom_arrond: Mapped[str | None] = mapped_column(String, index=True)
    street_name: Mapped[str | None] = mapped_column(String, index=True)
