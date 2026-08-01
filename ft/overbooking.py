"""El insight: la capacidad de la sala no es el límite de venta.

Nadie pidió esto. Sale de mirar la misma distribución desde el otro lado.

Todo el mundo trata el aforo como un techo: 800 asientos, 800 entradas. Pero si
de cada entrada entra el 64%, vender 800 llena 512 butacas y deja 288 vacías
toda la noche. El techo real no es la capacidad, es **el riesgo de que entren
más de los que caben** — y eso es una probabilidad que ya sabemos calcular,
porque el simulador no devuelve un número sino una distribución completa.

Es lo mismo que hacen las aerolíneas desde hace cuarenta años, y en un teatro
sale más barato: el coste de pasarse no es reubicar a alguien en otro vuelo,
son diez personas de pie al fondo.

    Vende hasta donde P(asistencia > capacidad) siga por debajo del riesgo que
    aceptas.

Cambia cómo se piensa el acceso:

  · La cortesía deja de ser "papel gratis" y pasa a ser inventario dirigido:
    ocupa cupo de riesgo, y ese cupo se puede medir.
  · Un show con muchas cortesías admite MÁS sobreventa, no menos, porque su
    tasa de asistencia es más baja.
  · La pregunta del organizador deja de ser "¿cuántas entradas quedan?" y pasa
    a ser "¿cuánto riesgo de desborde estoy dispuesto a correr?".
"""

from __future__ import annotations

import csv

import numpy as np

from .api import OUTPUTS, asegurar_carpetas
from .datos import eventos, tickets
from .forecast import _grupos, simular
from .model import Modelo, ShockDeShow, evaluar_loo

RIESGO = 0.05      # probabilidad máxima aceptada de que no quepan
N_SIM = 6000
SEED = 20260801


def capacidad_extra(p_base: np.ndarray, grupos: np.ndarray, sigma: float,
                    capacidad: int, rng, riesgo: float = RIESGO,
                    tope_extra: int = 4000) -> dict:
    """Cuántas entradas más caben antes de superar el riesgo de desborde.

    Las entradas nuevas se suponen del mismo perfil que las ya vendidas: se
    remuestrean sus probabilidades. Es el supuesto conservador y honesto —
    suponer que las próximas serán mejores sería hacer trampa.
    """
    if capacidad <= 0 or p_base.size == 0:
        return {"extra": 0, "riesgo_actual": 0.0}

    def riesgo_con(extra: int) -> float:
        if extra == 0:
            p, g = p_base, grupos
        else:
            idx = rng.integers(0, p_base.size, extra)
            p = np.concatenate([p_base, p_base[idx]])
            g = np.concatenate([grupos, np.arange(grupos.max() + 1,
                                                  grupos.max() + 1 + extra)])
        sims = simular(p, sigma, rng, N_SIM, g, 0.0)
        return float((sims > capacidad).mean())

    actual = riesgo_con(0)
    if actual > riesgo:
        return {"extra": 0, "riesgo_actual": actual, "ya_al_limite": True}

    # búsqueda binaria sobre el número de entradas extra
    lo, hi = 0, tope_extra
    while lo < hi:
        med = (lo + hi + 1) // 2
        if riesgo_con(med) <= riesgo:
            lo = med
        else:
            hi = med - 1
    return {"extra": int(lo), "riesgo_actual": actual}


def main() -> list[dict]:
    asegurar_carpetas()
    df = tickets()
    julio = df[df.etiquetado].to_dict("records")
    agosto = df[~df.etiquetado].to_dict("records")

    por_ev_jul: dict[str, list] = {}
    for f in julio:
        por_ev_jul.setdefault(f["event_id"], []).append(f)
    _, resid, var_azar, pct, _ = evaluar_loo(julio, por_ev_jul)
    shock = ShockDeShow(resid, var_azar, pct)
    modelo = Modelo(julio)

    meta = eventos().set_index("event_id")
    por_ev: dict[str, list] = {}
    for f in agosto:
        por_ev.setdefault(f["event_id"], []).append(f)

    rng = np.random.default_rng(SEED)
    filas = []
    for ev in sorted(por_ev):
        fs = por_ev[ev]
        cap = int(meta.loc[ev, "capacity"])
        p = modelo.prob(fs)
        pc = sum(1 for f in fs if f["es_cortesia"]) / len(fs)
        r = capacidad_extra(p, _grupos(fs), shock.sigma(pc), cap, rng)
        filas.append({
            "event_id": ev,
            "artista": fs[0]["artist_name"],
            "capacidad": cap,
            "entradas_vendidas": len(fs),
            "esperado": int(round(float(p.sum()))),
            "pct_cortesia": round(pc, 3),
            "puede_vender_mas": r["extra"],
            "riesgo_actual_desborde": round(r["riesgo_actual"], 4),
        })

    with (OUTPUTS / "overbooking.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0].keys()))
        w.writeheader()
        w.writerows(filas)

    extra = sum(f["puede_vender_mas"] for f in filas)
    vend = sum(f["entradas_vendidas"] for f in filas)
    cap = sum(f["capacidad"] for f in filas)
    print(f"Con un riesgo de desborde del {RIESGO:.0%} por show:\n")
    print(f"  entradas ya vendidas para agosto : {vend:,}")
    print(f"  capacidad total de las salas     : {cap:,}")
    print(f"  se pueden vender ADEMÁS          : {extra:,} entradas "
          f"({extra / vend:.0%} más de lo vendido)")
    print(f"\n  y aun así, en 19 de cada 20 noches, toda la gente cabe.\n")

    print(f"{'show':24} {'cap':>5} {'vend':>6} {'entran':>7} {'cortesía':>9} {'+vender':>9}")
    for f in sorted(filas, key=lambda x: -x["puede_vender_mas"])[:10]:
        print(f"{f['artista'][:24]:24} {f['capacidad']:>5} {f['entradas_vendidas']:>6} "
              f"{f['esperado']:>7} {f['pct_cortesia']:>8.0%} {f['puede_vender_mas']:>9}")
    print("\noverbooking.csv escrito")
    return filas


if __name__ == "__main__":
    main()
