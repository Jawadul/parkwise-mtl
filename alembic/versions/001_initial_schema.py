"""Initial schema with all parking tables.

Revision ID: 001
Revises:
Create Date: 2026-03-03

"""
from typing import Sequence, Union

import geoalchemy2
import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable PostGIS extension
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    # Regulations
    op.create_table(
        "regulations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("no_reglementation", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("type_reglementation", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("no_reglementation"),
    )
    op.create_index("ix_regulations_no_reglementation", "regulations", ["no_reglementation"])

    # Regulation periods
    op.create_table(
        "regulation_periods",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("regulation_id", sa.Integer(), nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=True),
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("end_time", sa.Time(), nullable=True),
        sa.Column("duration_max_minutes", sa.Integer(), nullable=True),
        sa.Column("rate_cents_per_hour", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["regulation_id"], ["regulations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_regulation_periods_regulation_id", "regulation_periods", ["regulation_id"])

    # Parking spaces
    op.create_table(
        "parking_spaces",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("no_place", sa.String(), nullable=True),
        sa.Column("no_emplacement", sa.String(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(geometry_type="POINT", srid=4326),
            nullable=True,
        ),
        sa.Column("type_place", sa.String(), nullable=True),
        sa.Column("tarif", sa.String(), nullable=True),
        sa.Column("commune", sa.String(), nullable=True),
        sa.Column("regulation_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["regulation_id"], ["regulations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_parking_spaces_no_place", "parking_spaces", ["no_place"])
    op.create_index("ix_parking_spaces_regulation_id", "parking_spaces", ["regulation_id"])
    op.create_index(
        "idx_parking_spaces_geom", "parking_spaces", ["geom"], postgresql_using="gist"
    )

    # Pay stations
    op.create_table(
        "pay_stations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("no_borne", sa.String(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(geometry_type="POINT", srid=4326),
            nullable=True,
        ),
        sa.Column("type_borne", sa.String(), nullable=True),
        sa.Column("statut", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pay_stations_no_borne", "pay_stations", ["no_borne"])
    op.create_index(
        "idx_pay_stations_geom", "pay_stations", ["geom"], postgresql_using="gist"
    )

    # Parking signs
    op.create_table(
        "parking_signs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("poteau_id", sa.String(), nullable=True),
        sa.Column("panneau_id", sa.String(), nullable=True),
        sa.Column("code_rpa", sa.String(), nullable=True),
        sa.Column("description_rpa", sa.String(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(geometry_type="POINT", srid=4326),
            nullable=True,
        ),
        sa.Column("nom_arrond", sa.String(), nullable=True),
        sa.Column("street_name", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_parking_signs_poteau_id", "parking_signs", ["poteau_id"])
    op.create_index("ix_parking_signs_panneau_id", "parking_signs", ["panneau_id"])
    op.create_index("ix_parking_signs_code_rpa", "parking_signs", ["code_rpa"])
    op.create_index("ix_parking_signs_nom_arrond", "parking_signs", ["nom_arrond"])
    op.create_index("ix_parking_signs_street_name", "parking_signs", ["street_name"])
    op.create_index(
        "idx_parking_signs_geom", "parking_signs", ["geom"], postgresql_using="gist"
    )

    # Snow removal lots
    op.create_table(
        "snow_removal_lots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nom", sa.String(), nullable=True),
        sa.Column("adresse", sa.String(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(geometry_type="POINT", srid=4326),
            nullable=True,
        ),
        sa.Column("type_pay", sa.String(), nullable=True),
        sa.Column("nb_places", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_snow_removal_lots_geom", "snow_removal_lots", ["geom"], postgresql_using="gist"
    )


def downgrade() -> None:
    op.drop_table("snow_removal_lots")
    op.drop_table("parking_signs")
    op.drop_table("pay_stations")
    op.drop_table("parking_spaces")
    op.drop_table("regulation_periods")
    op.drop_table("regulations")
