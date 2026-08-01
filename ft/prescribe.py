"""De predecir a decidir: qué hacer con un show que va flojo.

Un pronóstico dice "entran 259 de 623". Eso dimensiona la puerta, pero no llena
la sala. Aquí se calculan tres palancas, cada una con su impacto en personas.

HONESTIDAD CAUSAL — esto importa más que la cifra
-------------------------------------------------
Los datos son observacionales. Que las cortesías de taquilla entren al 50% y las
de RRPP al 29% describe **a quién** se le dio cada una, no prueba que cambiar el
canal cause asistencia. Nadie asignó canales al azar.

Por eso cada palanca declara su supuesto y su fuerza:

  INVITAR      fuerte.  Se predice la asistencia de personas concretas usando su
                        propio historial. Es el uso para el que el modelo se
                        entrenó y validó.
  CANAL        débil.   Asume que el canal causa, cuando probablemente
                        selecciona. Es un techo optimista, no una promesa.
  CONVERTIR    media.   El salto cortesía->pagada (38.7% -> 94%) es enorme y
                        consistente, pero quien paga ya venía decidido. El
                        efecto real de cobrar es menor que la brecha observada.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from .api import OUTPUTS, asegurar_carpetas
from .datos import boom_users, eventos, tickets
from .features import HistorialBoom
from .fetch import load

HOY = datetime(2026, 8, 1, tzinfo=timezone.utc)
CANAL_INVITACION = "WEB"     # canal neutro: no se le atribuye el efecto del canal
MIN_HISTORIAL = 2            # entradas en Boom para que su tasa signifique algo

# Solo se invita a quien es mas probable que venga a que no. Sin este corte, el
# calculo "reparte cortesias hasta llenar" propone 2.000 invitaciones para 800
# asientos: aritmeticamente cierto y comercialmente absurdo. Una cortesia a
# alguien que no va no llena la sala, y de paso devalua la cortesia.
UMBRAL_INVITACION = 0.50

_HIST: HistorialBoom | None = None


def _historial() -> HistorialBoom:
    """22.325 tickets de Boom: se indexan una vez, no una por evento."""
    global _HIST
    if _HIST is None:
        _HIST = HistorialBoom(load("boom", "tickets"))
    return _HIST


# --------------------------------------------------------------- utilidades


def _ya_tienen_entrada(df: pd.DataFrame, event_id: str) -> set[str]:
    """boom_user_id que ya figuran en alguna venta de ese evento."""
    sub = df[(df.event_id == event_id) & df.boom_user_id.notna()]
    return set(sub.boom_user_id.dropna())


def _fila_sintetica(usuario: dict, evento: dict, hist: dict, dias: float) -> dict:
    """Una cortesía hipotética para ese usuario en ese show."""
    return {
        "ticket_id": f"sim_{usuario['boom_user_id']}", "sale_id": "sim",
        "event_id": evento["event_id"], "artist_id": evento["artist_id"],
        "artist_name": evento["artist_name"], "month": evento["month"],
        "tipo": "Cortesía", "es_cortesia": True, "precio": 0,
        "canal": CANAL_INVITACION, "qty": 1, "dias_anticipacion": dias,
        "en_boom": True, "boom_user_id": usuario["boom_user_id"], "confidence": 1.0,
        "n_boom": hist["n_boom"], "rate_boom": hist["rate_boom"],
        "rate_consumo": hist["rate_consumo_minimo"], "n_consumo": hist["n_consumo_minimo"],
        "rate_membresia": hist["rate_membresia"], "n_membresia": hist["n_membresia"],
        "has_membership": bool(usuario["has_membership"]),
        "misma_ciudad": usuario["city"] == evento["city"],
        "y": None, "capacity": evento["capacity"], "venue": evento["venue"],
        "city": evento["city"], "is_residency": evento["is_residency"],
        "is_paid": evento["is_paid"], "weekday": evento["weekday"],
        "starts_at": evento["starts_at"], "semana_iso": 0, "etiquetado": False,
    }


# ----------------------------------------------------------------- palancas


def palanca_invitar(modelo, df: pd.DataFrame, event_id: str,
                    asientos_libres: int | None = None) -> dict:
    """A quién invitar: fieles de Boom en la ciudad del show, sin entrada aún.

    Supuesto (FUERTE): si reciben una cortesía, su probabilidad de aparecer es la
    que el modelo estima con su propio historial. Es exactamente lo que el modelo
    aprendió y se validó fuera de muestra.

    Cuántos invitar lo fija la sala, no un número redondo: se van tomando los
    mejores candidatos hasta que la asistencia esperada cubre los asientos
    libres. Invitar de más llena la sala en el papel y la desborda en la puerta.
    """
    ev = eventos().set_index("event_id").loc[event_id]
    evento = {**ev.to_dict(), "event_id": event_id}
    inicio = pd.to_datetime(evento["starts_at"], format="mixed", utc=True).to_pydatetime()
    dias = max(0.0, (inicio - HOY).total_seconds() / 86400)

    ocupados = _ya_tienen_entrada(df, event_id)
    hist = _historial()
    users = boom_users()
    locales = users[(users.city == evento["city"]) & (~users.boom_user_id.isin(ocupados))]

    filas = []
    for u in locales.to_dict("records"):
        h = hist.stats(u["boom_user_id"], HOY)
        if h["n_consumo_minimo"] < MIN_HISTORIAL:
            continue
        filas.append(_fila_sintetica(u, evento, h, dias))
    if not filas:
        return {"palanca": "invitar", "candidatos": 0, "impacto": 0.0}

    cand = pd.DataFrame(filas)
    cand["p"] = modelo.predict_proba(cand)
    cand = cand[cand["p"] >= UMBRAL_INVITACION].sort_values("p", ascending=False)

    # cuántos hacen falta para cubrir la sala, no uno más
    if asientos_libres and asientos_libres > 0 and len(cand):
        acum = cand["p"].cumsum()
        n = int((acum < asientos_libres).sum()) + 1
        cand = cand.head(min(n, len(cand)))
    else:
        cand = cand.head(0)

    return {
        "palanca": "invitar",
        "supuesto": "fuerte",
        "candidatos": int(len(cand)),
        "impacto": float(min(cand["p"].sum(), asientos_libres or 0)),
        "tasa_media": float(cand["p"].mean()) if len(cand) else 0.0,
        "dias_de_margen": round(dias, 1),
        "detalle": cand[["boom_user_id", "p", "n_consumo", "rate_consumo"]]
                       .rename(columns={"p": "prob_asiste"}),
    }


def palanca_canal(df: pd.DataFrame, event_id: str, tasas: dict) -> dict:
    """Techo optimista de mover las cortesías de RRPP/ADMIN a taquilla.

    Supuesto (DÉBIL): asume que el canal causa la asistencia. Lo más probable es
    que seleccione — quien va físicamente por su cortesía ya venía decidido. Se
    reporta como techo, no como promesa.
    """
    cort = df[(df.event_id == event_id) & df.es_cortesia]
    flojos = cort[cort.canal.isin(["RRPP", "ADMIN"])]
    if flojos.empty:
        return {"palanca": "canal", "movibles": 0, "impacto": 0.0, "supuesto": "débil"}
    actual = sum(tasas.get(c, tasas["WEB"]) for c in flojos.canal)
    potencial = len(flojos) * tasas["BOX_OFFICE"]
    return {
        "palanca": "canal",
        "supuesto": "débil",
        "movibles": int(len(flojos)),
        "impacto": float(potencial - actual),
        "nota": "techo optimista: el canal probablemente selecciona, no causa",
    }


def palanca_convertir(df: pd.DataFrame, event_id: str, cuantas: int,
                      tasas: dict) -> dict:
    """Convertir N cortesías en entradas pagadas.

    Supuesto (MEDIO): la brecha 38.7% -> 94% es enorme y consistente, pero parte
    de ella es que quien paga ya venía decidido. El efecto real de cobrar es
    menor que la brecha observada; se aplica un descuento del 30%.
    """
    cort = df[(df.event_id == event_id) & df.es_cortesia]
    n = min(cuantas, len(cort))
    if n == 0:
        return {"palanca": "convertir", "entradas": 0, "impacto": 0.0, "supuesto": "medio"}
    bruto = n * (tasas["pagada"] - tasas["cortesia"])
    return {
        "palanca": "convertir",
        "supuesto": "medio",
        "entradas": int(n),
        "impacto": float(bruto * 0.7),
        "impacto_bruto": float(bruto),
        "nota": "descontado 30%: parte de la brecha es que quien paga ya venía decidido",
    }


# ------------------------------------------------------------------ informe


def tasas_observadas(df: pd.DataFrame) -> dict:
    lab = df[df.etiquetado]
    por_canal = lab[lab.es_cortesia].groupby("canal")["y"].mean().to_dict()
    return {
        **por_canal,
        "cortesia": float(lab[lab.es_cortesia]["y"].mean()),
        "pagada": float(lab[~lab.es_cortesia]["y"].mean()),
    }


def acciones(modelo, df: pd.DataFrame, event_id: str, esperado: float,
             capacity: int) -> dict:
    """Las tres palancas para un show, ordenadas por impacto."""
    tasas = tasas_observadas(df)
    sobran = max(0, capacity - esperado)
    pal = [
        palanca_invitar(modelo, df, event_id, asientos_libres=sobran),
        palanca_canal(df, event_id, tasas),
        palanca_convertir(df, event_id, cuantas=100, tasas=tasas),
    ]
    pal.sort(key=lambda p: -p["impacto"])
    return {"event_id": event_id, "asientos_libres": int(sobran), "palancas": pal}


def main() -> pd.DataFrame:
    """Genera outputs/acciones.csv para los shows de agosto con sitio de sobra."""
    from .candidatos import M1LogisticaSegmentada

    asegurar_carpetas()
    df = tickets()
    modelo = M1LogisticaSegmentada().fit(df[df.etiquetado])

    pron = {r["event_id"]: r for r in
            csv.DictReader((OUTPUTS / "forecast_detalle.csv").open(encoding="utf-8"))}
    ev = eventos().set_index("event_id")

    filas = []
    for event_id, r in pron.items():
        esperado = int(r["expected_attendance"])
        cap = int(ev.loc[event_id, "capacity"])
        a = acciones(modelo, df, event_id, esperado, cap)
        base = {"event_id": event_id, "artista": r["artist_name"],
                "esperado": esperado, "capacidad": cap,
                "asientos_libres": a["asientos_libres"]}
        for p in a["palancas"]:
            filas.append({**base, "palanca": p["palanca"], "supuesto": p["supuesto"],
                          "impacto_personas": round(p["impacto"], 1),
                          "alcance": p.get("candidatos", p.get("movibles",
                                                               p.get("entradas", 0)))})
    out = pd.DataFrame(filas)
    out.to_csv(OUTPUTS / "acciones.csv", index=False, encoding="utf-8")
    print(f"acciones.csv: {out.event_id.nunique()} shows x {len(out)} palancas")
    top = (out[out.palanca == "invitar"].sort_values("impacto_personas", ascending=False)
              .head(5))
    print("\nDonde mas rinde invitar fieles de Boom:")
    for _, r in top.iterrows():
        print(f"  {r.event_id} {r.artista[:22]:22} libres={r.asientos_libres:4} "
              f"-> +{r.impacto_personas:.0f} personas ({r.alcance} candidatos)")
    return out


if __name__ == "__main__":
    main()
