"""Load snow removal parking lots from Ville de Montreal GeoJSON."""

import json
from pathlib import Path

from geoalchemy2 import WKTElement
from rich.console import Console
from sqlalchemy.orm import Session

from src.models import SnowRemovalLot

console = Console(force_terminal=True)


def load_snow_lots(db: Session, data_dir: Path) -> None:
    """Load snow_lots.geojson into snow_removal_lots."""
    console.print("[bold]Loading snow removal lots...[/bold]")
    geojson_path = data_dir / "snow_lots.geojson"
    if not geojson_path.exists():
        console.print("  snow_lots.geojson not found, skipping")
        return

    with open(geojson_path, encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features", [])
    count = 0
    for feat in features:
        props = feat.get("properties", {})
        geom_data = feat.get("geometry")

        lat, lon = None, None

        # Try geometry first
        if geom_data and geom_data.get("type") == "Point" and geom_data.get("coordinates"):
            coords = geom_data["coordinates"]
            lon, lat = float(coords[0]), float(coords[1])

        # If no geometry, convert X/Y from Quebec MTM zone 8 (EPSG:32188) to WGS84
        if lat is None:
            x_str = str(props.get("X", "")).replace(",", ".")
            y_str = str(props.get("Y", "")).replace(",", ".")
            try:
                from pyproj import Transformer
                transformer = Transformer.from_crs("EPSG:32188", "EPSG:4326", always_xy=True)
                x, y = float(x_str), float(y_str)
                lon, lat = transformer.transform(x, y)
            except (ValueError, TypeError, ImportError):
                pass

        wkt_geom = None
        if lat is not None and lon is not None:
            wkt_geom = WKTElement(f"POINT({lon} {lat})", srid=4326)

        nb = props.get("NBR_PLA") or props.get("nb_places")
        nb_places = None
        if nb is not None:
            try:
                nb_places = int(nb)
            except (ValueError, TypeError):
                pass

        type_pay = props.get("TYPE_PAY", "")
        if type_pay == "0":
            type_pay = "free"
        elif type_pay == "1":
            type_pay = "paid"

        lot = SnowRemovalLot(
            nom=props.get("EMPLACEMENT") or props.get("LOCATION") or props.get("nom"),
            adresse=props.get("LOCATION") or props.get("EMPLACEMENT") or props.get("adresse"),
            latitude=lat,
            longitude=lon,
            geom=wkt_geom,
            type_pay=type_pay,
            nb_places=nb_places,
        )
        db.add(lot)
        count += 1

    db.commit()
    console.print(f"  Loaded {count} snow removal lots")
