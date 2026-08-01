"""Los modelos que compiten, todos con la misma interfaz que los baselines.

  M1  logistica segmentada con variables de dominio (ft/model.py)
  M2  logistica unica de sklearn, con interacciones explicitas
  M3  HistGradientBoosting
  M4  RandomForest

M1 encodea a mano el hallazgo del EDA: cortesia y pagada son dos fenomenos,
asi que son dos modelos. M2 hace la pregunta honesta de si eso hacia falta o
bastaba con meter las interacciones en un modelo unico. M3 y M4 buscan lo que
una forma lineal no ve.

**La calibracion no es opcional aqui.** El aforo se obtiene SUMANDO
probabilidades, asi que un modelo que ordene perfecto pero prediga 0.7 donde la
verdad es 0.5 arruina el total aunque su AUC sea inmejorable. Los arboles
tienden a eso, y por eso pasan por CalibratedClassifierCV — con folds agrupados
por evento, porque calibrar con folds aleatorios reintroduce la fuga que el
split evito.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .baselines import Baseline
from .model import Modelo as LogisticaSegmentada
from .splits import folds_por_evento

SEMILLA = 20260801

CATEGORICAS = ["tipo", "canal", "artist_id", "weekday", "city"]
NUMERICAS = ["rate_consumo", "rate_membresia", "n_boom", "n_consumo",
             "dias_anticipacion", "qty", "precio", "capacity", "confidence"]
BOOLEANAS = ["es_cortesia", "en_boom", "has_membership", "misma_ciudad",
             "is_residency", "is_paid"]


def preparar(df: pd.DataFrame) -> pd.DataFrame:
    """Columnas del modelo, con las interacciones que el EDA senalo.

    La senal de Boom solo mueve las cortesias, asi que se cruza explicitamente
    con es_cortesia: un modelo lineal no puede descubrir eso por su cuenta.
    """
    X = df[CATEGORICAS + NUMERICAS + BOOLEANAS].copy()
    for col in BOOLEANAS:
        X[col] = X[col].astype(float)
    cort = X["es_cortesia"]
    X["cort_x_rate_consumo"] = cort * X["rate_consumo"].fillna(0.75)
    X["cort_x_en_boom"] = cort * X["en_boom"]
    X["cort_x_n_boom"] = cort * np.log1p(X["n_boom"])
    X["cort_x_ciudad"] = cort * X["misma_ciudad"]
    X["cort_x_membresia"] = cort * X["has_membership"]
    X["ultimo_dia"] = (X["dias_anticipacion"].fillna(99) <= 1).astype(float)
    X["cort_x_ultimo_dia"] = cort * X["ultimo_dia"]
    return X


NUM_DERIVADAS = ["cort_x_rate_consumo", "cort_x_en_boom", "cort_x_n_boom",
                 "cort_x_ciudad", "cort_x_membresia", "ultimo_dia",
                 "cort_x_ultimo_dia"]


def _preproceso(escalar: bool) -> ColumnTransformer:
    num = NUMERICAS + BOOLEANAS + NUM_DERIVADAS
    pasos = [("imp", SimpleImputer(strategy="median"))]
    if escalar:
        pasos.append(("sc", StandardScaler()))
    return ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=30), CATEGORICAS),
        ("num", Pipeline(pasos), num),
    ])


class ModeloSklearn(Baseline):
    """Envuelve un estimador de sklearn con la interfaz fit/predict_proba."""

    def __init__(self, nombre: str, estimador, escalar: bool = False,
                 calibrar: str | None = None):
        self.nombre = nombre
        self.estimador = estimador
        self.escalar = escalar
        self.calibrar = calibrar

    def fit(self, df: pd.DataFrame):
        X, y = preparar(df), df["y"].astype(int).to_numpy()
        pipe = Pipeline([("prep", _preproceso(self.escalar)), ("clf", self.estimador)])
        if self.calibrar:
            # folds agrupados por evento: calibrar con folds aleatorios filtraria
            cv = list(folds_por_evento(df, n_splits=4))
            pipe = CalibratedClassifierCV(pipe, method=self.calibrar, cv=cv)
        self.pipe_ = pipe.fit(X, y)
        return self

    def predict_proba(self, df: pd.DataFrame) -> np.ndarray:
        return self.pipe_.predict_proba(preparar(df))[:, 1]


class M1LogisticaSegmentada(Baseline):
    """La logistica de dominio: dos modelos, uno por segmento.

    Vive en ft/model.py y trabaja con listas de dicts; aqui solo se adapta a la
    interfaz comun para que compita en igualdad de condiciones.
    """

    nombre = "M1 · logística segmentada"

    def fit(self, df: pd.DataFrame):
        self.m_ = LogisticaSegmentada(df.to_dict("records"))
        return self

    def predict_proba(self, df: pd.DataFrame) -> np.ndarray:
        return self.m_.prob(df.to_dict("records"))


def construir_todos() -> list[Baseline]:
    return [
        M1LogisticaSegmentada(),
        ModeloSklearn(
            "M2 · logística + interacciones",
            LogisticRegression(max_iter=2000, C=1.0, random_state=SEMILLA),
            escalar=True,
        ),
        ModeloSklearn(
            "M3 · gradient boosting",
            HistGradientBoostingClassifier(
                max_iter=300, learning_rate=0.06, max_leaf_nodes=15,
                min_samples_leaf=40, l2_regularization=1.0, random_state=SEMILLA,
            ),
            calibrar="isotonic",
        ),
        ModeloSklearn(
            "M4 · random forest",
            RandomForestClassifier(
                n_estimators=400, min_samples_leaf=20, max_features="sqrt",
                n_jobs=-1, random_state=SEMILLA,
            ),
            calibrar="isotonic",
        ),
    ]


if __name__ == "__main__":
    from .datos import tickets
    from .splits import split_temporal

    partes = split_temporal(tickets())
    tr, va = partes["train"], partes["val"]
    print(f"{'modelo':32} {'MAE evento (val)':>17} {'sesgo':>9}")
    for m in construir_todos():
        m.fit(tr)
        p = m.predict_proba(va)
        ev = va.assign(p=p).groupby("event_id").agg(obs=("y", "sum"), pred=("p", "sum"))
        print(f"{m.nombre:32} {(ev.obs - ev.pred).abs().mean():17.1f} "
              f"{(ev.pred - ev.obs).mean():+9.1f}")
