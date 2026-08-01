"""Escalera de baselines: contra que hay que ganar.

Un modelo no se juzga contra cero, se juzga contra lo que ya se podria hacer
sin el. Aqui hay cuatro escalones de dificultad creciente:

  B0  entran todos            lo que se hace hoy: dimensionar por lo vendido
  B1  la tasa global          "en julio entro el 74%, asumamos eso"
  B2  la tasa por tipo        la mezcla manda — este es el rival de verdad
  B3  tipo x artista          ademas, cada acto tiene su publico

B2 no es un hombre de paja: con la tasa por tipo el error ya baja a ~7 personas
por evento. Si el modelo entrenado no lo bate con claridad, ese es el resultado
y hay que decirlo.

Todos se ajustan SOLO con train. Un baseline que use la tasa de todo julio ya
esta mirando el test.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

K_SHRINK = 60.0  # entradas "virtuales" que empujan cada artista hacia su tipo


class Baseline:
    """Interfaz comun con los modelos: fit / predict_proba."""

    nombre = "baseline"

    def fit(self, df: pd.DataFrame) -> "Baseline":
        return self

    def predict_proba(self, df: pd.DataFrame) -> np.ndarray:
        raise NotImplementedError


class B0TodosEntran(Baseline):
    nombre = "B0 · entran todos"

    def predict_proba(self, df):
        return np.ones(len(df))


class B1TasaGlobal(Baseline):
    nombre = "B1 · tasa global"

    def fit(self, df):
        self.tasa_ = float(df["y"].mean())
        return self

    def predict_proba(self, df):
        return np.full(len(df), self.tasa_)


class B2TasaPorTipo(Baseline):
    nombre = "B2 · tasa por tipo"

    def fit(self, df):
        self.global_ = float(df["y"].mean())
        self.por_tipo_ = df.groupby("tipo")["y"].mean().to_dict()
        return self

    def predict_proba(self, df):
        return df["tipo"].map(self.por_tipo_).fillna(self.global_).to_numpy(dtype=float)


class B3TipoPorArtista(Baseline):
    """Tasa por tipo, corregida por artista con suavizado bayesiano.

    Un artista con 40 entradas en train no puede mover su tasa tanto como uno
    con 400. El suavizado lo encoge hacia la tasa de su tipo, y un artista que
    no aparecio en train se queda exactamente en ella.
    """

    nombre = "B3 · tipo x artista"

    def fit(self, df):
        self.global_ = float(df["y"].mean())
        self.por_tipo_ = df.groupby("tipo")["y"].mean().to_dict()
        base = df["tipo"].map(self.por_tipo_).to_numpy(dtype=float)
        # factor multiplicativo por artista, suavizado
        aux = df.assign(_base=base)
        g = aux.groupby("artist_id").agg(obs=("y", "sum"), esp=("_base", "sum"),
                                         n=("y", "size"))
        self.factor_ = ((g["obs"] + K_SHRINK) / (g["esp"] + K_SHRINK)).to_dict()
        return self

    def predict_proba(self, df):
        base = df["tipo"].map(self.por_tipo_).fillna(self.global_).to_numpy(dtype=float)
        fac = df["artist_id"].map(self.factor_).fillna(1.0).to_numpy(dtype=float)
        return np.clip(base * fac, 1e-6, 1 - 1e-6)


TODOS = [B0TodosEntran, B1TasaGlobal, B2TasaPorTipo, B3TipoPorArtista]


def construir_todos() -> list[Baseline]:
    return [cls() for cls in TODOS]


if __name__ == "__main__":
    from .datos import tickets
    from .splits import split_temporal

    partes = split_temporal(tickets())
    tr, va = partes["train"], partes["val"]
    print(f"{'baseline':22} {'MAE evento (val)':>17} {'sesgo':>9}")
    for b in construir_todos():
        b.fit(tr)
        p = b.predict_proba(va)
        ev = va.assign(p=p).groupby("event_id").agg(obs=("y", "sum"), pred=("p", "sum"))
        mae = (ev.obs - ev.pred).abs().mean()
        sesgo = (ev.pred - ev.obs).mean()
        print(f"{b.nombre:22} {mae:17.1f} {sesgo:+9.1f}")
