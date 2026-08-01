"""Cliente del API del hackathon.

Una peticion toca UNA plataforma. Este cliente no cruza nada: solo pagina y
devuelve filas crudas.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = os.environ.get("FT_HACK_API", "https://hackathon-freeticket.vercel.app")
ROOT = Path(__file__).resolve().parent.parent
PAGE = 1000  # tope del API


def token() -> str:
    """Token desde env var, .ft-hack.json o setup.json (en ese orden)."""
    tok = os.environ.get("FT_HACK_TOKEN")
    if tok:
        return tok
    for name in (".ft-hack.json", "setup.json"):
        path = ROOT / name
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("token"):
                return data["token"]
    raise SystemExit(
        "Falta el token. Corre:\n"
        "  curl 'https://hackathon-freeticket.vercel.app/api/setup?handle=TU-NOMBRE' -o setup.json\n"
        "o exporta FT_HACK_TOKEN."
    )


def _request(url: str, tok: str, retries: int = 4) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {tok}"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.load(resp)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            if attempt == retries - 1:
                raise
            time.sleep(1.5 * (attempt + 1))
            _ = exc
    raise RuntimeError("inalcanzable")


def get(platform: str, resource: str, **params) -> dict:
    """Una pagina cruda del recurso."""
    q = {"resource": resource, **{k: v for k, v in params.items() if v is not None}}
    url = f"{API}/api/{platform}?" + urllib.parse.urlencode(q)
    return _request(url, token())


def pull(platform: str, resource: str, **params) -> list[dict]:
    """El recurso completo, paginado con offset hasta agotar count."""
    rows: list[dict] = []
    offset = 0
    while True:
        page = get(platform, resource, limit=PAGE, offset=offset, **params)
        batch = page.get("rows", [])
        rows.extend(batch)
        total = page.get("count", len(rows))
        offset += PAGE
        if not batch or len(rows) >= total or offset > 500_000:
            break
    return rows
