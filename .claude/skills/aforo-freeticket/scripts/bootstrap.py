#!/usr/bin/env python
"""Recalcula el pronostico desde el API con TU propio token.

    python bootstrap.py TU-NOMBRE          pregunta antes de tocar nada
    python bootstrap.py TU-NOMBRE --si     sin preguntar (uso no interactivo)

`--actualizar` de aforo.py baja las cifras que estan PUBLICADAS en el repo.
Esto es distinto: baja los datos crudos del API del hackathon, vuelve a cruzar
las dos plataformas y vuelve a proyectar, asi que refleja lo que se ha vendido
hasta hoy. A cambio necesita clonar el repo, instalar numpy/pandas/scipy/sklearn
y ~60 s de pipeline.

El token se genera solo, sin registro ni aprobacion humana, en
/api/setup?handle=TU-NOMBRE — pero es TUYO: se escribe dentro de la cache de
esta skill y nunca en el repositorio ni junto a los datos que se publican.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

for _flujo in (sys.stdout, sys.stderr):
    if hasattr(_flujo, "reconfigure"):
        _flujo.reconfigure(encoding="utf-8", errors="replace")

AQUI = Path(__file__).resolve().parent
DESTINO = AQUI.parent / "data" / "dashboard.json"
CACHE = Path.home() / ".cache" / "aforo-freeticket" / "repo"
REPO = "https://github.com/juandmg020407/Hackathon-Freeticket.git"
API = "https://hackathon-freeticket.vercel.app"


def repo_cercano() -> Path | None:
    """Un clon ya existente: el que contiene esta skill, o la cache."""
    for base in (AQUI, Path.cwd().resolve()):
        for d in (base, *base.parents):
            if (d / "run.py").is_file() and (d / "ft" / "api.py").is_file():
                return d
    return CACHE if (CACHE / "run.py").is_file() else None


def conseguir_token(handle: str, repo: Path) -> str:
    """Token instantaneo del API, escrito en .ft-hack.json DENTRO del repo usado.

    urllib y no curl ni npx: curl en PowerShell es un alias de Invoke-WebRequest
    con otra sintaxis, y npx exige Node. Python ya esta aqui.
    """
    url = f"{API}/api/setup?handle={urllib.parse.quote(handle)}"
    with urllib.request.urlopen(url, timeout=30) as r:
        datos = json.loads(r.read().decode("utf-8"))
    tok = datos.get("token")
    if not tok:
        raise SystemExit(f"El API no devolvio token: {datos}")
    destino = repo / ".ft-hack.json"
    destino.write_text(json.dumps(datos, ensure_ascii=False, indent=2),
                       encoding="utf-8")
    print(f"  token de «{datos.get('handle', handle)}» → {destino}")
    return tok


def corre(cmd: list[str], cwd: Path) -> None:
    print(f"  $ {' '.join(cmd)}")
    r = subprocess.run(cmd, cwd=str(cwd))
    if r.returncode != 0:
        raise SystemExit(f"Fallo: {' '.join(cmd)} (codigo {r.returncode})")


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("-")]
    sin_preguntar = "--si" in argv or "-y" in argv
    if not args:
        print(__doc__)
        return 0
    handle = args[0]

    repo = repo_cercano()
    clonar = repo is None
    if clonar:
        repo = CACHE

    print("Voy a recalcular el pronóstico desde el API. Esto hace:")
    n = 1
    if clonar:
        print(f"  {n}. clonar {REPO}\n       en {repo}")
        n += 1
    else:
        print(f"  {n}. usar el repositorio que ya tienes en {repo}")
        n += 1
    print(f"  {n}. pedir un token a {API}/api/setup?handle={handle}")
    print(f"       y guardarlo en {repo / '.ft-hack.json'}")
    n += 1
    print(f"  {n}. instalar numpy, pandas, scipy, scikit-learn y matplotlib")
    n += 1
    print(f"  {n}. correr el pipeline completo (~60 s la primera vez)")
    n += 1
    print(f"  {n}. escribir el resultado en {DESTINO}")

    if not sin_preguntar:
        try:
            if input("\n¿Sigo? [s/N] ").strip().lower() not in ("s", "si", "sí", "y"):
                print("Cancelado. No toqué nada.")
                return 1
        except EOFError:
            print("\nSin terminal interactiva: repite con --si si estás seguro.")
            return 1

    if clonar:
        print("\n[1/4] Clonando")
        repo.parent.mkdir(parents=True, exist_ok=True)
        if not shutil.which("git"):
            raise SystemExit("No encuentro git en el PATH.")
        corre(["git", "clone", "--depth", "1", REPO, str(repo)], repo.parent)
    else:
        print(f"\n[1/4] Repositorio: {repo}")

    print("\n[2/4] Token")
    conseguir_token(handle, repo)

    print("\n[3/4] Dependencias")
    corre([sys.executable, "-m", "pip", "install", "-q", "-r",
           str(repo / "requirements.txt")], repo)

    print("\n[4/4] Pipeline")
    corre([sys.executable, "run.py"], repo)

    origen = repo / "outputs" / "dashboard.json"
    if not origen.is_file():
        raise SystemExit(f"El pipeline no dejo {origen}.")
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(origen, DESTINO)
    d = json.loads(DESTINO.read_text(encoding="utf-8"))
    r = d.get("resumen", {})
    print(f"\nListo → {DESTINO}")
    print(f"  generado {d.get('generado', '?')} · {r.get('shows', 0)} shows · "
          f"{r.get('asistencia_esperada', 0)} personas esperadas de "
          f"{r.get('entradas_adquiridas', 0)} entradas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
