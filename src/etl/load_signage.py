"""Load parking signage data from Ville de Montréal."""

from pathlib import Path

import pandas as pd
from geoalchemy2 import WKTElement
from rich.console import Console
from sqlalchemy.orm import Session

from src.models import ParkingSign

console = Console()


def load_signage(db: Session, data_dir: Path) -> None:
    """Load signage.csv into parking_signs."""
    console.print("[bold]Loading parking signs...[/bold]")
    csv_path = data_dir / "signage.csv"
    if not csv_path.exists():
        console.print("  [yellow]signage.csv not found, skipping[/yellow]")
        return

    df = pd.read_csv(csv_path, dtype=str)
    df.columns = [c.strip().lower() for c in df.columns]

    col_map = {
        "poteau_id": ["poteau_id_pot", "poteau_id", "id_poteau"],
        "panneau_id": ["panneau_id_pan", "panneau_id", "id_panneau"],
        "code_rpa": ["code_rpa", "coderpa"],
        "description_rpa": ["description_rpa", "descriptionrpa", "description_rep"],
        "latitude": ["latitude", "lat"],
        "longitude": ["longitude", "lon", "lng"],
        "nom_arrond": ["nom_arrond", "arrondissement", "arrond"],
        "street_name": ["nom_topographie", "rue", "street", "nom_rue"],
    }

    def _get(row, key):
        for cand in col_map[key]:
            if cand in df.columns:
                val = row.get(cand)
                if val is not None and not (isinstance(val, float) and pd.isna(val)):
                    return str(val).strip()
        return None

    count = 0
    batch = []
    for _, row in df.iterrows():
        lat = _safe_float(_get(row, "latitude"))
        lon = _safe_float(_get(row, "longitude"))
        geom = None
        if lat is not None and lon is not None:
            geom = WKTElement(f"POINT({lon} {lat})", srid=4326)

        sign = ParkingSign(
            poteau_id=_get(row, "poteau_id"),
            panneau_id=_get(row, "panneau_id"),
            code_rpa=_get(row, "code_rpa"),
            description_rpa=_get(row, "description_rpa"),
            latitude=lat,
            longitude=lon,
            geom=geom,
            nom_arrond=_get(row, "nom_arrond"),
            street_name=_get(row, "street_name"),
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

    console.print(f"  [green]Loaded {count} parking signs[/green]")


def _safe_float(val) -> float | None:
    try:
        v = float(val)
        return v if not pd.isna(v) else None
    except (TypeError, ValueError):
        return None
