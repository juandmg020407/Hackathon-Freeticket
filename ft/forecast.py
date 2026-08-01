"""Proyeccion de agosto: aforo esperado con p10 y p90 por evento.

La incertidumbre tiene tres fuentes y se simulan las tres:

  1. AZAR DE LA PUERTA. Cada entrada es una moneda con su propia probabilidad.
     Sumadas dan una Poisson-binomial.
  2. LA GENTE NO VIENE SUELTA, VIENE EN GRUPO. Las entradas de una misma venta
     entran o se quedan juntas: en julio, en el 11.3% de las ventas de dos o
     mas no entro nadie, cuando bajo independencia seria 4.7%. Se modela con un
     shock por venta, calibrado para reproducir esa proporcion.
  3. LO QUE EL MODELO NO SABE. Cada show tiene su noche: lluvia, un partido, el
     humor del acto. Se mide con los residuos de dejar-un-evento-fuera en julio
     y entra como un shock comun a todas las entradas del mismo show.

Sin la 2 y la 3 los intervalos saldrian demasiado angostos y la puerta se
dimensionaria mal justo en las noches raras.
"""

from __future__ import annotations

import csv
from collections import defaultdict

import numpy as np

from .api import OUTPUTS, asegurar_carpetas
from .features import construir
from .model import Modelo, evaluar_loo, sigma_show

N_SIM = 20_000
SEED = 20260801


def _logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def _sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))


def simular(p: np.ndarray, sigma: float, rng, n_sim: int = N_SIM,
            grupos: np.ndarray | None = None, sigma_grupo: float = 0.0) -> np.ndarray:
    """Aforo simulado n_sim veces para un evento.

    'grupos' indexa a que venta pertenece cada entrada; las de la misma venta
    comparten shock, que es como se comporta la gente que llega junta.
    El resultado se recentra en sum(p) para no mover la prediccion puntual:
    los shocks aportan dispersion, no sesgo.
    """
    z = _logit(p)[None, :] + rng.normal(0.0, sigma, size=(n_sim, 1))
    if grupos is not None and sigma_grupo > 0:
        n_g = int(grupos.max()) + 1
        z = z + rng.normal(0.0, sigma_grupo, size=(n_sim, n_g))[:, grupos]
    sims = (rng.random((n_sim, p.size)) < _sigmoid(z)).sum(axis=1)
    return sims - sims.mean() + p.sum()


def calibrar_sigma_grupo(filas_julio, probs, rng, malla=np.arange(0.0, 3.01, 0.25)) -> float:
    """Busca el shock por venta que reproduce las ventas donde no entro nadie."""
    por_venta: dict[str, list[int]] = defaultdict(list)
    for i, f in enumerate(filas_julio):
        por_venta[f["sale_id"]].append(i)
    grupos = [idx for idx in por_venta.values() if len(idx) >= 2]
    if not grupos:
        return 0.0

    obs_cero = np.mean([
        1.0 if not any(filas_julio[i]["y"] for i in idx) else 0.0 for idx in grupos
    ])

    mejor, mejor_err = 0.0, float("inf")
    for s in malla:
        cero = 0.0
        for idx in grupos:
            pg = probs[idx]
            z = _logit(pg)[None, :] + rng.normal(0.0, s, size=(400, 1))
            entra = rng.random((400, pg.size)) < _sigmoid(z)
            cero += (~entra.any(axis=1)).mean()
        err = abs(cero / len(grupos) - obs_cero)
        if err < mejor_err:
            mejor, mejor_err = float(s), err
    return mejor


def _grupos(filas) -> np.ndarray:
    """Indice de venta para cada entrada."""
    orden: dict[str, int] = {}
    return np.array([orden.setdefault(f["sale_id"], len(orden)) for f in filas])


def cobertura_julio(filas_julio, por_evento, sigma, sigma_grupo) -> tuple[float, float]:
    """Que fraccion de los eventos de julio cae dentro de su [p10, p90]."""
    rng = np.random.default_rng(SEED)
    dentro = ancho = 0
    for ev, fs in por_evento.items():
        train = [f for f in filas_julio if f["event_id"] != ev]
        p = Modelo(train).prob(fs)
        sims = simular(p, sigma, rng, 4000, _grupos(fs), sigma_grupo)
        lo, hi = np.percentile(sims, [10, 90])
        obs = sum(1 for f in fs if f["y"])
        dentro += lo <= obs <= hi
        ancho += hi - lo
    return dentro / len(por_evento), ancho / len(por_evento)


def main() -> list[dict]:
    filas = construir()
    julio = [f for f in filas if f["y"] is not None]
    agosto = [f for f in filas if f["y"] is None]

    por_ev_jul = defaultdict(list)
    for f in julio:
        por_ev_jul[f["event_id"]].append(f)

    print("Calibrando sobre julio (dejando un evento fuera)…")
    errs, resid, var_azar, _ = evaluar_loo(julio, por_ev_jul)
    sigma = sigma_show(resid, var_azar)
    print(f"  MAE {errs.mean():.1f} personas por evento")
    print(f"  residuo total {resid.std(ddof=1):.3f} logit = azar de puerta "
          f"{np.sqrt(var_azar.mean()):.3f} + shock de show {sigma:.3f}")

    modelo = Modelo(julio)
    rng_cal = np.random.default_rng(SEED)
    sigma_grupo = calibrar_sigma_grupo(julio, modelo.prob(julio), rng_cal)
    print(f"  shock por venta (la gente llega en grupo): {sigma_grupo:.2f} (logit)")

    cob, ancho = cobertura_julio(julio, por_ev_jul, sigma, sigma_grupo)
    print(f"  cobertura del intervalo p10-p90 en julio: {cob:.0%} (objetivo 80%), "
          f"ancho medio {ancho:.0f} personas")

    por_ev_ago = defaultdict(list)
    for f in agosto:
        por_ev_ago[f["event_id"]].append(f)

    rng = np.random.default_rng(SEED)
    filas_out = []
    for ev in sorted(por_ev_ago, key=lambda e: por_ev_ago[e][0]["event_id"]):
        fs = por_ev_ago[ev]
        p = modelo.prob(fs)
        sims = simular(p, sigma, rng, N_SIM, _grupos(fs), sigma_grupo)
        lo, hi = np.percentile(sims, [10, 90])
        cortesias = sum(1 for f in fs if f["es_cortesia"])
        en_boom = sum(1 for f in fs if f["en_boom"])
        filas_out.append({
            "event_id": ev,
            "expected_attendance": int(round(float(p.sum()))),
            "p10": int(round(float(lo))),
            "p90": int(round(float(hi))),
            "artist_name": fs[0]["artist_name"],
            "tickets_adquiridos": len(fs),
            "cortesias": cortesias,
            "pct_cortesia": round(cortesias / len(fs), 4),
            "compradores_en_boom": en_boom,
            "tasa_esperada": round(float(p.mean()), 4),
        })

    asegurar_carpetas()
    with (OUTPUTS / "forecast.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["event_id", "expected_attendance", "p10", "p90"])
        w.writeheader()
        for f in filas_out:
            w.writerow({k: f[k] for k in ("event_id", "expected_attendance", "p10", "p90")})

    with (OUTPUTS / "forecast_detalle.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas_out[0].keys()))
        w.writeheader()
        w.writerows(filas_out)

    tot = sum(f["expected_attendance"] for f in filas_out)
    vend = sum(f["tickets_adquiridos"] for f in filas_out)
    print(f"\nAgosto: {len(filas_out)} eventos, {vend} entradas adquiridas -> "
          f"{tot} personas esperadas ({tot/vend:.1%})")
    print("forecast.csv y forecast_detalle.csv escritos")
    return filas_out


if __name__ == "__main__":
    main()
