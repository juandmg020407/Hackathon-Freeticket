"""Modelo de asistencia por entrada, calibrado sobre julio.

Dos modelos separados en vez de uno con interacciones, porque los datos dicen
que son dos fenomenos distintos:

  PAGADA    entra ~94% y el historial del comprador casi no mueve la aguja
            (use_rate bajo 0.928 / alto 0.944). Ya pago: va.
  CORTESIA  entra ~39% y ahi SI manda quien la recibio
            (use_rate bajo 0.265 / medio 0.356 / alto 0.386).

El efecto del artista entra como dummies con L2 fuerte: equivale a encoger cada
artista hacia el promedio segun cuantos shows suyos vimos en julio. Un acto de
gira sin julio propio queda en 0 — sin ajuste — y para el solo habla Boom.

No se usa fill_rate: en julio es el llenado final y en agosto el llenado
parcial de hoy. Compararlos meteria un sesgo que no se puede corregir.
"""

from __future__ import annotations

import numpy as np

CORTESIA = "Cortesía"
L2_BASE = 1e-3      # apenas regulariza las señales principales
L2_ARTISTA = 12.0   # encoge el efecto de artista hacia 0


def fit_logistic(X, y, penal, iters=60, tol=1e-9):
    """Logistica por IRLS (Newton) con L2 por columna."""
    n, k = X.shape
    w = np.zeros(k)
    P = np.diag(penal)
    for _ in range(iters):
        z = X @ w
        p = 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))
        s = np.clip(p * (1 - p), 1e-7, None)
        grad = X.T @ (y - p) - P @ w
        H = (X * s[:, None]).T @ X + P
        try:
            paso = np.linalg.solve(H, grad)
        except np.linalg.LinAlgError:
            paso = np.linalg.lstsq(H, grad, rcond=None)[0]
        w += paso
        if np.max(np.abs(paso)) < tol:
            break
    return w


def predict(X, w):
    return 1.0 / (1.0 + np.exp(-np.clip(X @ w, -30, 30)))


class Disenio:
    """Convierte filas de features en la matriz X de cada segmento."""

    def __init__(self, filas, segmento):
        self.segmento = segmento
        self.artistas = sorted({f["artist_id"] for f in filas})
        self.idx_art = {a: i for i, a in enumerate(self.artistas)}
        self.nombres = self._nombres()

    def _nombres(self):
        base = (["intercepto", "en_boom", "tiene_consumo", "rate_consumo_c",
                 "n_boom_log", "membresia", "misma_ciudad", "compra_ultimo_dia",
                 "canal_taquilla", "canal_admin", "canal_rrpp"]
                if self.segmento == "cortesia" else
                ["intercepto", "preferencial", "vip", "compra_ultimo_dia",
                 "canal_taquilla", "canal_admin", "canal_rrpp"])
        return base + [f"art:{a}" for a in self.artistas]

    def matriz(self, filas):
        n_art = len(self.artistas)
        out = []
        for f in filas:
            canal = [
                1.0 if f["canal"] == "BOX_OFFICE" else 0.0,
                1.0 if f["canal"] == "ADMIN" else 0.0,
                1.0 if f["canal"] == "RRPP" else 0.0,
            ]
            if self.segmento == "cortesia":
                rc = f["rate_consumo"]
                base = [
                    1.0,
                    1.0 if f["en_boom"] else 0.0,
                    1.0 if rc is not None else 0.0,
                    (rc - 0.75) if rc is not None else 0.0,   # centrado en el 75% del brief
                    np.log1p(f["n_boom"]) / 3.0,
                    1.0 if f["has_membership"] else 0.0,
                    1.0 if f["misma_ciudad"] else 0.0,
                    1.0 if (f["dias_anticipacion"] or 99) <= 1 else 0.0,
                ] + canal
            else:
                base = [
                    1.0,
                    1.0 if f["tipo"] == "Preferencial" else 0.0,
                    1.0 if f["tipo"] == "VIP" else 0.0,
                    1.0 if (f["dias_anticipacion"] or 99) <= 1 else 0.0,
                ] + canal
            art = [0.0] * n_art
            i = self.idx_art.get(f["artist_id"])
            if i is not None:
                art[i] = 1.0
            out.append(base + art)
        return np.asarray(out, dtype=float)

    def penal(self):
        n_base = len(self.nombres) - len(self.artistas)
        p = [L2_BASE] * n_base + [L2_ARTISTA] * len(self.artistas)
        p[0] = 0.0  # el intercepto no se penaliza
        return np.asarray(p)


class Modelo:
    def __init__(self, filas_julio):
        self.dis = {}
        self.w = {}
        for seg, sel in (("cortesia", True), ("pagada", False)):
            sub = [f for f in filas_julio if f["es_cortesia"] is sel]
            d = Disenio(sub, seg)
            X = d.matriz(sub)
            y = np.array([1.0 if f["y"] else 0.0 for f in sub])
            self.dis[seg] = d
            self.w[seg] = fit_logistic(X, y, d.penal())

    def prob(self, filas):
        """Probabilidad de cruzar la puerta, por fila, en el orden dado."""
        p = np.zeros(len(filas))
        for seg, sel in (("cortesia", True), ("pagada", False)):
            ids = [i for i, f in enumerate(filas) if f["es_cortesia"] is sel]
            if not ids:
                continue
            sub = [filas[i] for i in ids]
            p[ids] = predict(self.dis[seg].matriz(sub), self.w[seg])
        return p

    def coeficientes(self, seg):
        return list(zip(self.dis[seg].nombres, self.w[seg]))


def evaluar_loo(filas_julio, por_evento):
    """Deja un evento fuera, reentrena y predice ese evento. MAE honesto.

    Devuelve tambien, por evento, la varianza en logit que explica el puro azar
    de la puerta. El residuo observado mezcla ese azar con lo que el modelo no
    sabe; para el intervalo hay que separarlos o la incertidumbre se cuenta dos
    veces.
    """
    eventos = sorted(por_evento)
    errores, resid_logit, var_azar, detalle = [], [], [], []
    for ev in eventos:
        train = [f for f in filas_julio if f["event_id"] != ev]
        test = por_evento[ev]
        m = Modelo(train)
        p = m.prob(test)
        pred = float(p.sum())
        obs = float(sum(1 for f in test if f["y"]))
        errores.append(abs(pred - obs))
        n = len(test)
        # residuo en escala logit, para el shock de evento del intervalo
        a, b = np.clip(obs / n, 1e-3, 1 - 1e-3), np.clip(pred / n, 1e-3, 1 - 1e-3)
        resid_logit.append(np.log(a / (1 - a)) - np.log(b / (1 - b)))
        # varianza binomial de la tasa, propagada a logit por delta-method
        var_tasa = float((p * (1 - p)).sum()) / n ** 2
        var_azar.append(var_tasa / (b * (1 - b)) ** 2)
        detalle.append((ev, n, obs, pred))
    return np.array(errores), np.array(resid_logit), np.array(var_azar), detalle


def sigma_show(resid_logit, var_azar) -> float:
    """Desviacion del shock por show, ya descontado el azar de la puerta."""
    var_total = float(np.var(resid_logit, ddof=1))
    var = max(var_total - float(np.mean(var_azar)), 1e-4)
    return float(np.sqrt(var))
