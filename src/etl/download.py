"""Download open data files from AMD and Ville de Montréal."""

import os
from pathlib import Path

import httpx
from rich.console import Console

console = Console(force_terminal=True)

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
    "8ac6dd33-b0d3-4eab-a334-5a6283eb7940/resource/"
    "7f1d4ae9-1a12-46d7-953e-6b9c18c78680/download/"
    "signalisation_stationnement.csv"
)

VDM_SNOW_URL = (
    "https://donnees.montreal.ca/fr/dataset/"
    "575ecf37-9097-44cd-817f-a2fbd8de314b/resource/"
    "def63739-6295-4745-97e9-74755ee0bf92/download/"
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
