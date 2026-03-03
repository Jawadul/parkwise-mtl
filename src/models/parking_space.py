from geoalchemy2 import Geometry
from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class ParkingSpace(Base):
    __tablename__ = "parking_spaces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    no_place: Mapped[str | None] = mapped_column(String, index=True)
    no_emplacement: Mapped[str | None] = mapped_column(String)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    geom = mapped_column(Geometry("POINT", srid=4326), nullable=True, index=True)
    type_place: Mapped[str | None] = mapped_column(String)
    tarif: Mapped[str | None] = mapped_column(String)
    commune: Mapped[str | None] = mapped_column(String)
    regulation_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("regulations.id"), index=True
    )

    regulation = relationship("Regulation", back_populates="parking_spaces")
