"""Load AMD parking data (Places, Bornes, Reglementations, Periodes)."""

from datetime import time as dt_time
from pathlib import Path

import pandas as pd
from geoalchemy2 import WKTElement
from rich.console import Console
from sqlalchemy.orm import Session

from src.models import ParkingSpace, PayStation, Regulation, RegulationPeriod

console = Console(force_terminal=True)

# AMD CSVs use Latin-1 encoding (French accents)
CSV_ENCODING = "latin-1"


def _point_wkt(lat, lon) -> WKTElement | None:
    if lat is None or lon is None:
        return None
    try:
        la, lo = float(lat), float(lon)
        if pd.isna(la) or pd.isna(lo):
            return None
        return WKTElement(f"POINT({lo} {la})", srid=4326)
    except (TypeError, ValueError):
        return None


def _safe_float(val) -> float | None:
    try:
        v = float(val)
        return v if not pd.isna(v) else None
    except (TypeError, ValueError):
        return None


def _safe_int(val) -> int | None:
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return None


def load_regulations(db: Session, data_dir: Path) -> dict[str, int]:
    """Load Reglementations.csv. Returns mapping of Name -> DB id."""
    console.print("[bold]Loading regulations...[/bold]")
    # Columns: Name, Type, DateDebut, DateFin, maxHeures
    df = pd.read_csv(data_dir / "reglementations.csv", dtype=str, encoding=CSV_ENCODING)

    reg_map: dict[str, int] = {}
    count = 0
    for _, row in df.iterrows():
        name = str(row.get("Name", "")).strip()
        if not name:
            continue
        existing = db.query(Regulation).filter_by(no_reglementation=name).first()
        if existing:
            reg_map[name] = existing.id
            continue

        max_h = row.get("maxHeures", "")
        desc = f"Type: {row.get('Type', '')}, {row.get('DateDebut', '')}-{row.get('DateFin', '')}"
        if max_h and str(max_h).strip() and str(max_h).strip() != "nan":
            desc += f", max {max_h}h"

        reg = Regulation(
            no_reglementation=name,
            description=desc,
            type_reglementation=str(row.get("Type", "")).strip() or None,
        )
        db.add(reg)
        db.flush()
        reg_map[name] = reg.id
        count += 1

    db.commit()
    console.print(f"  Loaded {count} regulations")
    return reg_map


def load_periods(db: Session, data_dir: Path, reg_map: dict[str, int]) -> None:
    """Load Periodes.csv + ReglementationPeriode.csv (join table)."""
    console.print("[bold]Loading regulation periods...[/bold]")

    # ReglementationPeriode.csv: sCode, noPeriode, sDescription
    rp_path = data_dir / "reglementation_periode.csv"
    df_rp = pd.read_csv(rp_path, dtype=str, encoding=CSV_ENCODING)

    # Periodes.csv: nID, dtHeureDebut, dtHeureFin, bLun..bDim
    per_path = data_dir / "periodes.csv"
    df_per = pd.read_csv(per_path, dtype=str, encoding=CSV_ENCODING)

    # Build period details by nID
    period_details: dict[str, dict] = {}
    for _, row in df_per.iterrows():
        pid = str(row.get("nID", "")).strip()
        if not pid:
            continue
        start = _parse_time(row.get("dtHeureDebut"))
        end = _parse_time(row.get("dtHeureFin"))

        # Days: bLun=Mon(1)..bDim=Sun(7)
        day_cols = [("bLun", 1), ("bMar", 2), ("bMer", 3), ("bJeu", 4),
                    ("bVen", 5), ("bSam", 6), ("bDim", 7)]
        active_days = []
        for col, day_num in day_cols:
            val = str(row.get(col, "0")).strip()
            if val == "1":
                active_days.append(day_num)

        period_details[pid] = {
            "start_time": start,
            "end_time": end,
            "active_days": active_days if active_days else list(range(1, 8)),
        }

    # Link regulations to periods
    count = 0
    for _, row in df_rp.iterrows():
        code = str(row.get("sCode", "")).strip()
        per_id = str(row.get("noPeriode", "")).strip()
        reg_id = reg_map.get(code)
        if not reg_id or not per_id:
            continue

        details = period_details.get(per_id, {})
        active_days = details.get("active_days", list(range(1, 8)))

        for day in active_days:
            rp = RegulationPeriod(
                regulation_id=reg_id,
                day_of_week=day,
                start_time=details.get("start_time"),
                end_time=details.get("end_time"),
            )
            db.add(rp)
            count += 1

    db.commit()
    console.print(f"  Loaded {count} regulation periods")


def load_places(db: Session, data_dir: Path, reg_map: dict[str, int]) -> None:
    """Load Places.csv into parking_spaces."""
    console.print("[bold]Loading parking spaces...[/bold]")
    # Columns: sNoPlace, nLongitude, nLatitude, ..., sNomRue, nTarifHoraire, sLocalisation, nTarifMax
    df = pd.read_csv(data_dir / "places.csv", dtype=str, encoding=CSV_ENCODING)

    count = 0
    batch = []
    for _, row in df.iterrows():
        lat = _safe_float(row.get("nLatitude"))
        lon = _safe_float(row.get("nLongitude"))

        space = ParkingSpace(
            no_place=str(row.get("sNoPlace", "")).strip() or None,
            no_emplacement=str(row.get("sLocalisation", "")).strip() or None,
            latitude=lat,
            longitude=lon,
            geom=_point_wkt(lat, lon),
            type_place=str(row.get("sType", "")).strip() or None,
            tarif=str(row.get("nTarifHoraire", "")).strip() or None,
            commune=str(row.get("sNomRue", "")).strip() or None,
            regulation_id=None,  # Will link via signs/rules later if needed
        )
        batch.append(space)
        count += 1

        if len(batch) >= 5000:
            db.add_all(batch)
            db.commit()
            batch = []

    if batch:
        db.add_all(batch)
        db.commit()

    console.print(f"  Loaded {count} parking spaces")


def load_bornes(db: Session, data_dir: Path) -> None:
    """Load BornesSurRue.csv into pay_stations."""
    console.print("[bold]Loading pay stations...[/bold]")
    # Columns: nNoBorne, sStatut, sNomRue, sZoneGroupeCode, nLongitude, nLatitude, sTypeExploitation
    df = pd.read_csv(data_dir / "bornes.csv", dtype=str, encoding=CSV_ENCODING)

    count = 0
    batch = []
    for _, row in df.iterrows():
        lat = _safe_float(row.get("nLatitude"))
        lon = _safe_float(row.get("nLongitude"))

        station = PayStation(
            no_borne=str(row.get("nNoBorne", "")).strip() or None,
            latitude=lat,
            longitude=lon,
            geom=_point_wkt(lat, lon),
            type_borne=str(row.get("sTypeExploitation", "")).strip() or None,
            statut=str(row.get("sStatut", "")).strip() or None,
        )
        batch.append(station)
        count += 1

        if len(batch) >= 5000:
            db.add_all(batch)
            db.commit()
            batch = []

    if batch:
        db.add_all(batch)
        db.commit()

    console.print(f"  Loaded {count} pay stations")


def _parse_time(val) -> dt_time | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = str(val).strip()
    if not s or s.lower() == "nan":
        return None
    # Handle formats like "9:00", "17:30", "9h00"
    parts = s.replace("h", ":").replace("H", ":").split(":")
    try:
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
        if h >= 24:
            h = 23
            m = 59
        return dt_time(h, m)
    except (ValueError, IndexError):
        return None
