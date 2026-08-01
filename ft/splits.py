"""Particion de julio en entrenamiento, validacion y prueba.

Dos reglas, y las dos vienen de como son los datos, no del manual:

1. **Por evento, nunca por entrada.** Los tickets de un mismo show comparten
   artista, venue, noche y politica de cortesias. Repartirlos al azar mete
   tickets del mismo show en train y en test: el modelo ve la respuesta y las
   metricas salen infladas.

2. **Temporal.** En produccion siempre se predice hacia adelante, sobre shows
   que no existian cuando el modelo se ajusto. Un split aleatorio por evento
   seria valido estadisticamente pero optimista frente al uso real, porque
   permitiria aprender de agosto para predecir julio.

Julio reparte 32 eventos en 5 semanas ISO casi uniformes (7/7/7/7/4), asi que
el corte por semana sale limpio.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

SEMANAS_TRAIN = (27, 28)
SEMANAS_VAL = (29,)
SEMANAS_TEST = (30, 31)


def split_temporal(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Divide las entradas etiquetadas de julio por semana ISO del show."""
    lab = df[df["etiquetado"]].copy()
    partes = {
        "train": lab[lab["semana_iso"].isin(SEMANAS_TRAIN)],
        "val": lab[lab["semana_iso"].isin(SEMANAS_VAL)],
        "test": lab[lab["semana_iso"].isin(SEMANAS_TEST)],
    }
    verificar_sin_fuga(partes)
    return partes


def verificar_sin_fuga(partes: dict[str, pd.DataFrame]) -> None:
    """Ningun evento puede aparecer en dos conjuntos. Falla ruidosamente."""
    vistos: dict[str, str] = {}
    for nombre, parte in partes.items():
        for ev in parte["event_id"].unique():
            if ev in vistos:
                raise AssertionError(
                    f"fuga: el evento {ev} esta en '{vistos[ev]}' y en '{nombre}'"
                )
            vistos[ev] = nombre


def resumen(partes: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Tabla para documentar el reparto."""
    filas = []
    for nombre, p in partes.items():
        filas.append({
            "conjunto": nombre,
            "semanas": sorted(p["semana_iso"].unique().tolist()),
            "eventos": p["event_id"].nunique(),
            "entradas": len(p),
            "cortesias": round(float(p["es_cortesia"].mean()), 3),
            "tasa_real": round(float(p["y"].mean()), 4),
        })
    return pd.DataFrame(filas)


def grupos(df: pd.DataFrame) -> np.ndarray:
    """Vector de grupo (event_id) para GroupKFold."""
    return df["event_id"].to_numpy()


def folds_por_evento(df: pd.DataFrame, n_splits: int = 5, semilla: int = 20260801):
    """GroupKFold barajado: reparte EVENTOS entre folds, no entradas.

    sklearn.GroupKFold no baraja, asi que se barajan los eventos a mano y se
    reparten en bloques. Con 32 eventos y 5 folds quedan 6-7 eventos por fold.
    """
    # a numpy de objetos: barajar el StringArray de pandas puede duplicar
    eventos = np.asarray(df["event_id"].unique(), dtype=object)
    rng = np.random.default_rng(semilla)
    rng.shuffle(eventos)
    bloques = np.array_split(eventos, n_splits)
    idx = np.arange(len(df))
    col = df["event_id"].to_numpy()
    for bloque in bloques:
        test_mask = np.isin(col, bloque)
        yield idx[~test_mask], idx[test_mask]


if __name__ == "__main__":
    from .datos import tickets

    partes = split_temporal(tickets())
    print(resumen(partes).to_string(index=False))
    print("\nsin fuga entre conjuntos: OK")
