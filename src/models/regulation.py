from sqlalchemy import Float, ForeignKey, Integer, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class Regulation(Base):
    __tablename__ = "regulations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    no_reglementation: Mapped[str | None] = mapped_column(String, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String)
    type_reglementation: Mapped[str | None] = mapped_column(String)

    periods = relationship("RegulationPeriod", back_populates="regulation")
    parking_spaces = relationship("ParkingSpace", back_populates="regulation")


class RegulationPeriod(Base):
    __tablename__ = "regulation_periods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    regulation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("regulations.id"), index=True
    )
    day_of_week: Mapped[int | None] = mapped_column(Integer)  # 1=Mon..7=Sun
    start_time = mapped_column(Time, nullable=True)
    end_time = mapped_column(Time, nullable=True)
    duration_max_minutes: Mapped[int | None] = mapped_column(Integer)
    rate_cents_per_hour: Mapped[int | None] = mapped_column(Integer)

    regulation = relationship("Regulation", back_populates="periods")
