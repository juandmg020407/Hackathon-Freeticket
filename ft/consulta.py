"""Interfaz de consulta: la que usa la skill para responder.

La implementacion vive en la skill, no aqui:

    .claude/skills/aforo-freeticket/scripts/aforo.py

Ese script es stdlib pura y lee un solo archivo —dashboard.json—, que es lo que
le permite responder instalado en cualquier agente, sin repo, sin token y sin
pip install. Este modulo solo delega, para que `python -m ft.consulta` siga
funcionando desde el repo y para que no existan dos copias de la misma logica:
dos copias se desincronizan, y entonces la skill instalada responde una cosa y
el repo otra.

    python -m ft.consulta "Sin Filtro"      por artista (todos sus shows)
    python -m ft.consulta ft_evt_0060       por id de evento
    python -m ft.consulta --agenda          los shows que vienen, en orden
    python -m ft.consulta --vacios          los que van a quedar mas vacios
    python -m ft.consulta --sobreventa      cuantas entradas mas caben sin riesgo
    python -m ft.consulta --llegada         a que hora llega la gente
    python -m ft.consulta --modelo          que tan bien predice y que supone
    python -m ft.consulta --json            todo en JSON, para graficar

Dentro del repo, aforo.py encuentra outputs/dashboard.json y usa el dato recien
calculado; fuera, cae a la copia que viaja con la skill.
"""

from __future__ import annotations

import importlib.util
import sys

from .api import ROOT

SCRIPT = ROOT / ".claude" / "skills" / "aforo-freeticket" / "scripts" / "aforo.py"


def _aforo():
    if not SCRIPT.is_file():
        raise SystemExit(
            f"Falta {SCRIPT}. La implementacion vive en la skill; si borraste "
            f".claude/skills/, recuperala del repositorio."
        )
    spec = importlib.util.spec_from_file_location("aforo", SCRIPT)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def main(argv: list[str]) -> int:
    return _aforo().main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
