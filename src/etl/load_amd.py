"""Load AMD parking data (Places, Bornes, Reglementations, Periodes)."""

from pathlib import Path

import pandas as pd
from geoalchemy2 import WKTElement
from rich.console import Console
from sqlalchemy.orm import Session

from src.models import ParkingSpace, PayStation, Regulation, RegulationPeriod

console = Console()


def _point_wkt(lat: float | None, lon: float | None) -> WKTElement | None:
    if lat is None or lon is None or pd.isna(lat) or pd.isna(lon):
        return None
    return WKTElement(f"POINT({lon} {lat})", srid=4326)


def load_regulations(db: Session, data_dir: Path) -> dict[str, int]:
    """Load Reglementations.csv. Returns mapping of no_reglementation → DB id."""
    console.print("[bold]Loading regulations...[/bold]")
    df = pd.read_csv(data_dir / "reglementations.csv", dtype=str)
    df.columns = [c.strip().lower() for c in df.columns]

    col_no = _find_col(df, ["no_reglementation", "noreglementation", "no reglementation"])
    col_desc = _find_col(df, ["description", "desc"])
    col_type = _find_col(df, ["type_reglementation", "typereglementation", "type"])

    reg_map: dict[str, int] = {}
    count = 0
    for _, row in df.iterrows():
        no = str(row.get(col_no, "")).strip()
        if not no:
            continue
        existing = db.query(Regulation).filter_by(no_reglementation=no).first()
        if existing:
            reg_map[no] = existing.id
            continue
        reg = Regulation(
            no_reglementation=no,
            description=str(row.get(col_desc, "")).strip() if col_desc else None,
            type_reglementation=str(row.get(col_type, "")).strip() if col_type else None,
        )
        db.add(reg)
        db.flush()
        reg_map[no] = reg.id
        count += 1

    db.commit()
    console.print(f"  [green]Loaded {count} regulations[/green]")
    return reg_map


def load_periods(db: Session, data_dir: Path, reg_map: dict[str, int]) -> None:
    """Load Periodes.csv + ReglementationPeriode.csv join."""
    console.print("[bold]Loading regulation periods...[/bold]")

    # Load periodes
    periodes_path = data_dir / "periodes.csv"
    reg_per_path = data_dir / "reglementation_periode.csv"

    if not periodes_path.exists():
        console.print("  [yellow]periodes.csv not found, skipping[/yellow]")
        return

    df_per = pd.read_csv(periodes_path, dtype=str)
    df_per.columns = [c.strip().lower() for c in df_per.columns]

    # Try to load the join table
    join_map: dict[str, list[str]] = {}  # no_reglementation → list of no_periode
    if reg_per_path.exists():
        df_rp = pd.read_csv(reg_per_path, dtype=str)
        df_rp.columns = [c.strip().lower() for c in df_rp.columns]
        rp_reg_col = _find_col(df_rp, ["no_reglementation", "noreglementation"])
        rp_per_col = _find_col(df_rp, ["no_periode", "noperiode"])
        if rp_reg_col and rp_per_col:
            for _, row in df_rp.iterrows():
                rno = str(row.get(rp_reg_col, "")).strip()
                pno = str(row.get(rp_per_col, "")).strip()
                if rno and pno:
                    join_map.setdefault(rno, []).append(pno)

    # Parse period details
    per_col_no = _find_col(df_per, ["no_periode", "noperiode", "no periode"])
    per_col_day = _find_col(df_per, ["jour_semaine", "joursemaine", "jour"])
    per_col_start = _find_col(df_per, ["heure_debut", "heuredebut"])
    per_col_end = _find_col(df_per, ["heure_fin", "heurefin"])
    per_col_dur = _find_col(df_per, ["duree_max", "dureemax", "duree_minutes"])
    per_col_rate = _find_col(df_per, ["tarif", "taux"])

    period_details: dict[str, dict] = {}
    for _, row in df_per.iterrows():
        pno = str(row.get(per_col_no, "")).strip() if per_col_no else ""
        if not pno:
            continue
        from datetime import time as dt_time

        start_t = _parse_time(row.get(per_col_start)) if per_col_start else None
        end_t = _parse_time(row.get(per_col_end)) if per_col_end else None
        dur = _safe_int(row.get(per_col_dur)) if per_col_dur else None
        rate = _parse_rate(row.get(per_col_rate)) if per_col_rate else None
        day = _safe_int(row.get(per_col_day)) if per_col_day else None

        period_details[pno] = {
            "day_of_week": day,
            "start_time": start_t,
            "end_time": end_t,
            "duration_max_minutes": dur,
            "rate_cents_per_hour": rate,
        }

    count = 0
    for reg_no, period_nos in join_map.items():
        reg_id = reg_map.get(reg_no)
        if not reg_id:
            continue
        for pno in period_nos:
            details = period_details.get(pno, {})
            rp = RegulationPeriod(regulation_id=reg_id, **details)
            db.add(rp)
            count += 1

    db.commit()
    console.print(f"  [green]Loaded {count} regulation periods[/green]")


def load_places(db: Session, data_dir: Path, reg_map: dict[str, int]) -> None:
    """Load Places.csv into parking_spaces."""
    console.print("[bold]Loading parking spaces...[/bold]")
    df = pd.read_csv(data_dir / "places.csv", dtype=str)
    df.columns = [c.strip().lower() for c in df.columns]

    col_no = _find_col(df, ["no_place", "noplace"])
    col_emp = _find_col(df, ["no_emplacement", "noemplacement"])
    col_lat = _find_col(df, ["latitude", "lat"])
    col_lon = _find_col(df, ["longitude", "lon", "lng"])
    col_type = _find_col(df, ["type_place", "typeplace", "type"])
    col_tarif = _find_col(df, ["tarif"])
    col_comm = _find_col(df, ["commune", "arrondissement"])
    col_reg = _find_col(df, ["no_reglementation", "noreglementation"])

    count = 0
    batch = []
    for _, row in df.iterrows():
        lat = _safe_float(row.get(col_lat)) if col_lat else None
        lon = _safe_float(row.get(col_lon)) if col_lon else None
        reg_no = str(row.get(col_reg, "")).strip() if col_reg else None

        space = ParkingSpace(
            no_place=str(row.get(col_no, "")).strip() if col_no else None,
            no_emplacement=str(row.get(col_emp, "")).strip() if col_emp else None,
            latitude=lat,
            longitude=lon,
            geom=_point_wkt(lat, lon),
            type_place=str(row.get(col_type, "")).strip() if col_type else None,
            tarif=str(row.get(col_tarif, "")).strip() if col_tarif else None,
            commune=str(row.get(col_comm, "")).strip() if col_comm else None,
            regulation_id=reg_map.get(reg_no) if reg_no else None,
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

    console.print(f"  [green]Loaded {count} parking spaces[/green]")


def load_bornes(db: Session, data_dir: Path) -> None:
    """Load BornesSurRue.csv into pay_stations."""
    console.print("[bold]Loading pay stations...[/bold]")
    df = pd.read_csv(data_dir / "bornes.csv", dtype=str)
    df.columns = [c.strip().lower() for c in df.columns]

    col_no = _find_col(df, ["no_borne", "noborne"])
    col_lat = _find_col(df, ["latitude", "lat"])
    col_lon = _find_col(df, ["longitude", "lon", "lng"])
    col_type = _find_col(df, ["type_borne", "typeborne", "type"])
    col_statut = _find_col(df, ["statut"])

    count = 0
    batch = []
    for _, row in df.iterrows():
        lat = _safe_float(row.get(col_lat)) if col_lat else None
        lon = _safe_float(row.get(col_lon)) if col_lon else None

        station = PayStation(
            no_borne=str(row.get(col_no, "")).strip() if col_no else None,
            latitude=lat,
            longitude=lon,
            geom=_point_wkt(lat, lon),
            type_borne=str(row.get(col_type, "")).strip() if col_type else None,
            statut=str(row.get(col_statut, "")).strip() if col_statut else None,
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

    console.print(f"  [green]Loaded {count} pay stations[/green]")


# ── helpers ──────────────────────────────────────────────


def _find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Find the first matching column name (case-insensitive)."""
    lower_cols = {c.lower().replace(" ", "_"): c for c in df.columns}
    for cand in candidates:
        norm = cand.lower().replace(" ", "_")
        if norm in lower_cols:
            return lower_cols[norm]
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


def _parse_time(val):
    from datetime import time as dt_time

    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = str(val).strip()
    if not s or s.lower() == "nan":
        return None
    parts = s.replace("h", ":").replace("H", ":").split(":")
    try:
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
        return dt_time(h, m)
    except (ValueError, IndexError):
        return None


def _parse_rate(val) -> int | None:
    """Parse rate string to cents/hour."""
    if val is None:
        return None
    try:
        f = float(str(val).replace(",", ".").replace("$", "").strip())
        return int(f * 100)
    except (ValueError, TypeError):
        return None
