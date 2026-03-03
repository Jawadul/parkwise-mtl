"""Load snow removal parking lots from Ville de Montréal GeoJSON."""

import json
from pathlib import Path

from geoalchemy2 import WKTElement
from rich.console import Console
from sqlalchemy.orm import Session

from src.models import SnowRemovalLot

console = Console()


def load_snow_lots(db: Session, data_dir: Path) -> None:
    """Load snow_lots.geojson into snow_removal_lots."""
    console.print("[bold]Loading snow removal lots...[/bold]")
    geojson_path = data_dir / "snow_lots.geojson"
    if not geojson_path.exists():
        console.print("  [yellow]snow_lots.geojson not found, skipping[/yellow]")
        return

    with open(geojson_path, encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features", [])
    count = 0
    for feat in features:
        props = feat.get("properties", {})
        geom = feat.get("geometry")

        lat, lon = None, None
        if geom and geom.get("type") == "Point":
            coords = geom["coordinates"]
            lon, lat = float(coords[0]), float(coords[1])

        wkt_geom = None
        if lat is not None and lon is not None:
            wkt_geom = WKTElement(f"POINT({lon} {lat})", srid=4326)

        nb = props.get("nb_places") or props.get("PLACES")
        nb_places = None
        if nb is not None:
            try:
                nb_places = int(nb)
            except (ValueError, TypeError):
                pass

        lot = SnowRemovalLot(
            nom=props.get("nom") or props.get("NOM"),
            adresse=props.get("adresse") or props.get("ADRESSE"),
            latitude=lat,
            longitude=lon,
            geom=wkt_geom,
            type_pay=props.get("type") or props.get("TYPE") or props.get("gratuit_payant"),
            nb_places=nb_places,
        )
        db.add(lot)
        count += 1

    db.commit()
    console.print(f"  [green]Loaded {count} snow removal lots[/green]")
