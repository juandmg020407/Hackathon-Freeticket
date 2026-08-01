"""Evaluacion en dos niveles.

**Nivel entrada** (6.722 observaciones): log-loss, Brier, AUC y calibracion.
Dice si el modelo distingue quien entra de quien no.

**Nivel evento** (32 observaciones): MAE, MAPE y sesgo del aforo. Es la metrica
que decide, porque es la que usa el negocio — pero con 32 eventos cualquier
diferencia pequena es ruido, asi que todo va con intervalo de confianza por
bootstrap y una comparacion pareada entre modelos.

Un modelo puede ganar en AUC y perder en MAE: ordenar bien no es lo mismo que
sumar bien. Por eso se miran los dos niveles y no uno.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    log_loss,
    roc_auc_score,
)

from .splits import folds_por_evento

SEMILLA = 20260801


def ece(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float:
    """Error de calibracion esperado: |predicho − observado| por decil."""
    idx = np.argsort(p)
    total = 0.0
    for parte in np.array_split(idx, bins):
        if len(parte):
            total += len(parte) * abs(p[parte].mean() - y[parte].mean())
    return total / len(p)


def metricas_entrada(y: np.ndarray, p: np.ndarray) -> dict:
    p = np.clip(p, 1e-9, 1 - 1e-9)
    out = {
        "log_loss": float(log_loss(y, p, labels=[0, 1])),
        "brier": float(brier_score_loss(y, p)),
        "ece": float(ece(y, p)),
    }
    # AUC no existe si en el conjunto solo hay una clase
    out["auc_roc"] = float(roc_auc_score(y, p)) if len(np.unique(y)) > 1 else np.nan
    out["auc_pr"] = float(average_precision_score(y, p)) if len(np.unique(y)) > 1 else np.nan
    return out


def agregar_por_evento(df: pd.DataFrame, p: np.ndarray) -> pd.DataFrame:
    return (df.assign(_p=p)
              .groupby("event_id")
              .agg(n=("y", "size"), obs=("y", "sum"), pred=("_p", "sum"),
                   pct_cortesia=("es_cortesia", "mean"))
              .reset_index())


def metricas_evento(df: pd.DataFrame, p: np.ndarray) -> dict:
    ev = agregar_por_evento(df, p)
    err = ev["pred"] - ev["obs"]
    return {
        "mae": float(err.abs().mean()),
        "mediana_ae": float(err.abs().median()),
        "p90_ae": float(err.abs().quantile(0.9)),
        "mape": float((err.abs() / ev["obs"].clip(lower=1)).mean()),
        "sesgo": float(err.mean()),
        "eventos": int(len(ev)),
    }


def bootstrap_mae(df: pd.DataFrame, p: np.ndarray, n_rep: int = 4000,
                  semilla: int = SEMILLA) -> tuple[float, float]:
    """IC 95% del MAE remuestreando EVENTOS, que es la unidad independiente."""
    ev = agregar_por_evento(df, p)
    err = (ev["pred"] - ev["obs"]).abs().to_numpy()
    rng = np.random.default_rng(semilla)
    reps = [err[rng.integers(0, len(err), len(err))].mean() for _ in range(n_rep)]
    return float(np.percentile(reps, 2.5)), float(np.percentile(reps, 97.5))


def evaluar_cv(modelos, df: pd.DataFrame, n_splits: int = 5) -> pd.DataFrame:
    """Validacion cruzada agrupada por evento sobre todo julio.

    Da mas señal que el holdout de 7 eventos: cada modelo se mide sobre los 32,
    y la desviacion entre folds dice si la diferencia es real o es ruido.
    """
    folds = list(folds_por_evento(df, n_splits=n_splits))
    filas = []
    for m in modelos:
        por_fold, pred_total = [], np.zeros(len(df))
        for tr_idx, te_idx in folds:
            tr, te = df.iloc[tr_idx], df.iloc[te_idx]
            p = m.fit(tr).predict_proba(te)
            pred_total[te_idx] = p
            por_fold.append(metricas_evento(te, p)["mae"])
        y = df["y"].astype(int).to_numpy()
        fila = {"modelo": m.nombre}
        fila.update(metricas_entrada(y, pred_total))          # out-of-fold
        fila.update(metricas_evento(df, pred_total))
        lo, hi = bootstrap_mae(df, pred_total)
        fila["mae_ic95"] = f"[{lo:.1f}, {hi:.1f}]"
        fila["mae_std_folds"] = float(np.std(por_fold, ddof=1))
        filas.append(fila)
    return pd.DataFrame(filas)


def predicciones_oof(modelos, df: pd.DataFrame, n_splits: int = 5) -> dict[str, np.ndarray]:
    """Predicciones out-of-fold por modelo, para graficos y comparacion pareada."""
    folds = list(folds_por_evento(df, n_splits=n_splits))
    out = {}
    for m in modelos:
        pred = np.zeros(len(df))
        for tr_idx, te_idx in folds:
            pred[te_idx] = m.fit(df.iloc[tr_idx]).predict_proba(df.iloc[te_idx])
        out[m.nombre] = pred
    return out


def comparar_pareado(df: pd.DataFrame, pred_a: np.ndarray, pred_b: np.ndarray,
                     n_rep: int = 4000, semilla: int = SEMILLA) -> dict:
    """Diferencia de MAE entre dos modelos sobre los MISMOS eventos.

    Pareado porque los dos vieron los mismos shows: comparar dos intervalos
    independientes desperdicia esa informacion y hace parecer indistinguibles
    modelos que no lo son.
    """
    ea = agregar_por_evento(df, pred_a)
    eb = agregar_por_evento(df, pred_b).set_index("event_id").loc[ea["event_id"]]
    da = (ea["pred"].to_numpy() - ea["obs"].to_numpy())
    db = (eb["pred"].to_numpy() - eb["obs"].to_numpy())
    dif = np.abs(da) - np.abs(db)          # <0 => a es mejor
    rng = np.random.default_rng(semilla)
    reps = [dif[rng.integers(0, len(dif), len(dif))].mean() for _ in range(n_rep)]
    lo, hi = np.percentile(reps, [2.5, 97.5])
    return {
        "dif_media": float(dif.mean()),
        "ic95": (float(lo), float(hi)),
        "concluyente": bool(lo > 0 or hi < 0),
    }


def tabla_calibracion(y: np.ndarray, p: np.ndarray, bins: int = 10) -> pd.DataFrame:
    idx = np.argsort(p)
    filas = []
    for i, parte in enumerate(np.array_split(idx, bins), 1):
        filas.append({"decil": i, "p_medio": float(p[parte].mean()),
                      "observado": float(y[parte].mean()), "n": int(len(parte))})
    return pd.DataFrame(filas)


def error_por_segmento(df: pd.DataFrame, p: np.ndarray) -> pd.DataFrame:
    """Donde falla el modelo: por tipo de entrada, residencia y presencia en Boom."""
    d = df.assign(_p=p, _err=p - df["y"].astype(int))
    filas = []
    for nombre, col in [("cortesía vs pagada", "es_cortesia"),
                        ("residencia", "is_residency"),
                        ("comprador en Boom", "en_boom")]:
        g = d.groupby(col).agg(n=("_err", "size"), sesgo_medio=("_err", "mean"),
                               error_abs=("_err", lambda s: s.abs().mean()))
        for valor, r in g.iterrows():
            filas.append({"corte": nombre, "valor": bool(valor), "n": int(r["n"]),
                          "sesgo_medio": float(r["sesgo_medio"]),
                          "error_abs_medio": float(r["error_abs"])})
    return pd.DataFrame(filas)
