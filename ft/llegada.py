"""Curva de llegada: a que hora entra la gente, no solo cuanta.

Se mide en julio con checked_in_at contra starts_at, en franjas de 15 minutos.
Lo que dimensiona la puerta no es el total sino el PICO: cuantas personas caen
en el cuarto de hora mas cargado.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from .fetch import load

FRANJA = 15  # minutos


def curva_julio() -> dict[int, float]:
    """Fraccion de asistentes que llega en cada franja, relativa a starts_at."""
    events = {e["event_id"]: e for e in load("freeticket", "events")}
    cuenta: dict[int, int] = defaultdict(int)
    total = 0
    for t in load("freeticket", "tickets"):
        if not t["checked_in"] or not t.get("checked_in_at"):
            continue
        e = events[t["event_id"]]
        delta = (
            datetime.fromisoformat(t["checked_in_at"])
            - datetime.fromisoformat(e["starts_at"])
        ).total_seconds() / 60
        cuenta[int(delta // FRANJA) * FRANJA] += 1
        total += 1
    return {k: v / total for k, v in sorted(cuenta.items())} if total else {}


def perfil(esperado: float, curva: dict[int, float] | None = None) -> list[dict]:
    """Reparte el aforo esperado en franjas y marca el pico."""
    curva = curva if curva is not None else curva_julio()
    filas = []
    acum = 0.0
    for minuto, frac in sorted(curva.items()):
        personas = esperado * frac
        acum += personas
        filas.append({
            "minuto": minuto,
            "etiqueta": f"{minuto:+d} min" if minuto else "hora de inicio",
            "fraccion": frac,
            "personas": personas,
            "acumulado": acum,
        })
    return filas


def personal_sugerido(esperado: float, curva: dict[int, float] | None = None,
                      por_persona_min: float = 0.25) -> dict:
    """Staff de puerta a partir del pico, no del total.

    por_persona_min: minutos que toma revisar una entrada (15 s por defecto).
    """
    filas = perfil(esperado, curva)
    if not filas:
        return {"pico": 0.0, "staff": 1, "franja_pico": None}
    pico = max(filas, key=lambda f: f["personas"])
    # personas del pico x minutos por persona, repartido en la franja
    staff = max(1, int(-(-pico["personas"] * por_persona_min // FRANJA)))
    return {
        "pico": pico["personas"],
        "franja_pico": pico["etiqueta"],
        "staff": staff,
        "filas": filas,
    }


if __name__ == "__main__":
    c = curva_julio()
    print("Curva de llegada medida en julio:")
    acum = 0.0
    for m, f in sorted(c.items()):
        acum += f
        print(f"  {m:+4d} min  {f:6.1%}   acumulado {acum:6.1%}")
    for esperado in (100, 400):
        s = personal_sugerido(esperado, c)
        print(f"\nShow de {esperado} personas -> pico {s['pico']:.0f} en {s['franja_pico']}, "
              f"{s['staff']} personas en puerta")
