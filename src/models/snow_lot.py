from geoalchemy2 import Geometry
from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class SnowRemovalLot(Base):
    __tablename__ = "snow_removal_lots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nom: Mapped[str | None] = mapped_column(String)
    adresse: Mapped[str | None] = mapped_column(String)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    geom = mapped_column(Geometry("POINT", srid=4326), nullable=True, index=True)
    type_pay: Mapped[str | None] = mapped_column(String)  # free / paid
    nb_places: Mapped[int | None] = mapped_column(Integer)
