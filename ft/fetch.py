"""Descarga los 8 recursos completos a raw/*.json (cache local del pipeline)."""

from __future__ import annotations

import json
from pathlib import Path

from .api import ROOT, pull

RAW = ROOT / "raw"

RESOURCES = [
    ("boom", "users"),
    ("boom", "profile"),
    ("boom", "tickets"),
    ("boom", "social"),
    ("freeticket", "artists"),
    ("freeticket", "events"),
    ("freeticket", "sales"),
    ("freeticket", "tickets"),
]


def path_for(platform: str, resource: str) -> Path:
    return RAW / f"{platform}_{resource}.json"


def load(platform: str, resource: str) -> list[dict]:
    """Lee del cache; si no esta, lo descarga."""
    path = path_for(platform, resource)
    if not path.exists():
        return fetch_one(platform, resource)
    return json.loads(path.read_text(encoding="utf-8"))


def fetch_one(platform: str, resource: str) -> list[dict]:
    rows = pull(platform, resource)
    RAW.mkdir(parents=True, exist_ok=True)
    path_for(platform, resource).write_text(
        json.dumps(rows, ensure_ascii=False), encoding="utf-8"
    )
    print(f"  {platform}/{resource}: {len(rows)} filas")
    return rows


def main(force: bool = False) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    print("Descargando recursos…")
    for platform, resource in RESOURCES:
        path = path_for(platform, resource)
        if path.exists() and not force:
            n = len(json.loads(path.read_text(encoding="utf-8")))
            print(f"  {platform}/{resource}: {n} filas (cache)")
            continue
        fetch_one(platform, resource)


if __name__ == "__main__":
    import sys

    main(force="--force" in sys.argv)
