"""Acceso en DataFrame para notebooks y evaluacion.

Una sola puerta de entrada a los datos ya cruzados y enriquecidos, para que los
notebooks narren el analisis en vez de repetir plomeria.
"""

from __future__ import annotations

import pandas as pd

from .features import construir
from .fetch import load

CORTESIA = "Cortesía"
PAGADAS = ("General", "Preferencial", "VIP")


def tickets() -> pd.DataFrame:
    """Una fila por entrada, con las features y la etiqueta.

    `y` es True/False en julio y NaN en agosto. `split_mes` distingue los dos.
    """
    df = pd.DataFrame(construir())
    ev = eventos()[["event_id", "starts_at", "capacity", "venue", "city",
                    "is_residency", "is_paid", "weekday"]]
    df = df.merge(ev, on="event_id", how="left")
    df["starts_at"] = pd.to_datetime(df["starts_at"], format="mixed", utc=True)
    df["semana_iso"] = df["starts_at"].dt.isocalendar().week.astype(int)
    df["etiquetado"] = df["y"].notna()
    return df


def eventos() -> pd.DataFrame:
    df = pd.DataFrame(load("freeticket", "events"))
    return df


def ventas() -> pd.DataFrame:
    return pd.DataFrame(load("freeticket", "sales"))


def artistas() -> pd.DataFrame:
    return pd.DataFrame(load("freeticket", "artists"))


def boom_users() -> pd.DataFrame:
    return pd.DataFrame(load("boom", "users"))


def boom_profile() -> pd.DataFrame:
    return pd.DataFrame(load("boom", "profile"))


def boom_tickets() -> pd.DataFrame:
    return pd.DataFrame(load("boom", "tickets"))


def tasa(df: pd.DataFrame, por, minimo: int = 25) -> pd.DataFrame:
    """Tasa de check-in agrupada, ocultando celdas sin muestra suficiente."""
    lab = df[df["etiquetado"]]
    g = lab.groupby(por, observed=True)["y"].agg(n="size", entran="sum")
    g["tasa"] = g["entran"] / g["n"]
    return g[g["n"] >= minimo].sort_values("tasa", ascending=False)
