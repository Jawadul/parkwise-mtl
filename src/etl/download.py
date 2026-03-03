"""Download open data files from AMD and Ville de Montréal."""

import os
from pathlib import Path

import httpx
from rich.console import Console

console = Console()

DATA_DIR = Path("data")

# AMD paid-parking data
AMD_BASE = "https://www.agencemobilitedurable.ca/images/data"
AMD_FILES = {
    "places.csv": f"{AMD_BASE}/Places.csv",
    "bornes.csv": f"{AMD_BASE}/BornesSurRue.csv",
    "reglementations.csv": f"{AMD_BASE}/Reglementations.csv",
    "periodes.csv": f"{AMD_BASE}/Periodes.csv",
    "reglementation_periode.csv": f"{AMD_BASE}/ReglementationPeriode.csv",
}

# Ville de Montréal open data
VDM_SIGNAGE_URL = (
    "https://donnees.montreal.ca/dataset/"
    "c0fa3762-4ea1-4b37-8d5d-0e8ab4e18ed4/resource/"
    "8a3efee6-e8db-4c2c-9e9f-8a8c77c24a07/download/"
    "signalisation-codification-rpa.csv"
)

VDM_SNOW_URL = (
    "https://donnees.montreal.ca/dataset/"
    "ab3e5765-c518-4e3a-a059-64b7ef1d42e0/resource/"
    "58d273ec-b8f6-4a5f-9b5e-c87ae2e850e5/download/"
    "stationnements-h-2025-2026.geojson"
)


def _download(url: str, dest: Path) -> None:
    """Download a file if not already cached."""
    if dest.exists():
        console.print(f"  [dim]cached:[/dim] {dest.name}")
        return
    console.print(f"  [cyan]downloading:[/cyan] {dest.name}")
    with httpx.stream("GET", url, follow_redirects=True, timeout=120) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_bytes(chunk_size=8192):
                f.write(chunk)
    console.print(f"  [green]saved:[/green] {dest.name} ({dest.stat().st_size:,} bytes)")


def download_all(force: bool = False) -> dict[str, Path]:
    """Download all data files. Returns mapping of key → local path."""
    DATA_DIR.mkdir(exist_ok=True)
    paths: dict[str, Path] = {}

    if force:
        for f in DATA_DIR.iterdir():
            if f.is_file():
                f.unlink()

    console.print("[bold]Downloading AMD data...[/bold]")
    for key, url in AMD_FILES.items():
        dest = DATA_DIR / key
        _download(url, dest)
        paths[key] = dest

    console.print("[bold]Downloading signage data...[/bold]")
    dest = DATA_DIR / "signage.csv"
    _download(VDM_SIGNAGE_URL, dest)
    paths["signage.csv"] = dest

    console.print("[bold]Downloading snow removal lots...[/bold]")
    dest = DATA_DIR / "snow_lots.geojson"
    _download(VDM_SNOW_URL, dest)
    paths["snow_lots.geojson"] = dest

    return paths
