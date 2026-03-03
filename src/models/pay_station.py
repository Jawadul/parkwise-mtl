from geoalchemy2 import Geometry
from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class PayStation(Base):
    __tablename__ = "pay_stations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    no_borne: Mapped[str | None] = mapped_column(String, index=True)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    geom = mapped_column(Geometry("POINT", srid=4326), nullable=True, index=True)
    type_borne: Mapped[str | None] = mapped_column(String)
    statut: Mapped[str | None] = mapped_column(String)
