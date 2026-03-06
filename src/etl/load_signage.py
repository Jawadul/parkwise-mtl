"""Load parking signage data from Ville de Montreal."""

from pathlib import Path

import pandas as pd
from geoalchemy2 import WKTElement
from rich.console import Console
from sqlalchemy.orm import Session

from src.models import ParkingSign

console = Console(force_terminal=True)


def load_signage(db: Session, data_dir: Path) -> None:
    """Load signage.csv into parking_signs."""
    console.print("[bold]Loading parking signs...[/bold]")
    csv_path = data_dir / "signage.csv"
    if not csv_path.exists():
        console.print("  signage.csv not found, skipping")
        return

    # Columns: POTEAU_ID_POT, PANNEAU_ID_PAN, PANNEAU_ID_RPA, DESCRIPTION_RPA,
    #          CODE_RPA, TOPONYME_PAN, Longitude, Latitude, NOM_ARROND
    df = pd.read_csv(csv_path, dtype=str, encoding="utf-8")

    count = 0
    batch = []
    for _, row in df.iterrows():
        lat = _safe_float(row.get("Latitude"))
        lon = _safe_float(row.get("Longitude"))
        geom = None
        if lat is not None and lon is not None:
            geom = WKTElement(f"POINT({lon} {lat})", srid=4326)

        sign = ParkingSign(
            poteau_id=_clean(row.get("POTEAU_ID_POT")),
            panneau_id=_clean(row.get("PANNEAU_ID_PAN")),
            code_rpa=_clean(row.get("CODE_RPA")),
            description_rpa=_clean(row.get("DESCRIPTION_RPA")),
            latitude=lat,
            longitude=lon,
            geom=geom,
            nom_arrond=_clean(row.get("NOM_ARROND")),
            street_name=_clean(row.get("TOPONYME_PAN")),
        )
        batch.append(sign)
        count += 1

        if len(batch) >= 5000:
            db.add_all(batch)
            db.commit()
            batch = []

    if batch:
        db.add_all(batch)
        db.commit()

    console.print(f"  Loaded {count} parking signs")


def _clean(val) -> str | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = str(val).strip()
    return s if s and s.lower() != "nan" else None


def _safe_float(val) -> float | None:
    try:
        v = float(val)
        return v if not pd.isna(v) else None
    except (TypeError, ValueError):
        return None
