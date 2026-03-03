"""Run the full ETL pipeline: download data, load into PostGIS."""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rich.console import Console

from src.database import Base, sync_engine, get_sync_db
from src.etl.download import download_all
from src.etl.load_amd import load_bornes, load_periods, load_places, load_regulations
from src.etl.load_signage import load_signage
from src.etl.load_snow import load_snow_lots

console = Console()


def main():
    console.print("\n[bold blue]═══ ParkWise MTL — ETL Pipeline ═══[/bold blue]\n")

    # Step 0: Create tables (if not using Alembic migrations)
    console.print("[bold]Creating tables...[/bold]")
    from src.models import *  # noqa: F401,F403
    Base.metadata.create_all(sync_engine)
    console.print("  [green]Tables ready[/green]\n")

    # Step 1: Download
    console.print("[bold]Step 1: Download data files[/bold]")
    force = "--force" in sys.argv
    paths = download_all(force=force)
    console.print()

    # Step 2: Load
    console.print("[bold]Step 2: Load into database[/bold]")
    data_dir = Path("data")
    db = get_sync_db()

    try:
        reg_map = load_regulations(db, data_dir)
        load_periods(db, data_dir, reg_map)
        load_places(db, data_dir, reg_map)
        load_bornes(db, data_dir)
        load_signage(db, data_dir)
        load_snow_lots(db, data_dir)
    finally:
        db.close()

    # Step 3: Verify
    console.print("\n[bold]Step 3: Verify[/bold]")
    db = get_sync_db()
    try:
        from src.models import (
            ParkingSign,
            ParkingSpace,
            PayStation,
            Regulation,
            RegulationPeriod,
            SnowRemovalLot,
        )

        for model in [ParkingSpace, PayStation, Regulation, RegulationPeriod, ParkingSign, SnowRemovalLot]:
            count = db.query(model).count()
            console.print(f"  {model.__tablename__}: [cyan]{count:,}[/cyan] rows")
    finally:
        db.close()

    console.print("\n[bold green]ETL complete![/bold green]\n")


if __name__ == "__main__":
    main()
