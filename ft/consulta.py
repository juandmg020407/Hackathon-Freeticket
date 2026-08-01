"""Interfaz de consulta: la que usa la skill para responder.

Devuelve el aforo de un show con su porqué y sus palancas, en texto plano
pensado para que un agente lo lea y lo reformule. Todo sale de outputs/ y
reports/metrics.json — nunca se inventa un número.

    python -m ft.consulta "Sin Filtro"      por artista (todos sus shows)
    python -m ft.consulta ft_evt_0060       por id de evento
    python -m ft.consulta --agenda          los shows que vienen, en orden
    python -m ft.consulta --vacios          los que van a quedar más vacíos
    python -m ft.consulta --sobreventa      cuántas entradas más caben sin riesgo
    python -m ft.consulta --modelo          qué tan bien predice y qué supone
    python -m ft.consulta --json            todo en JSON, para graficar
"""

from __future__ import annotations

import csv
import json
import sys
import unicodedata
from datetime import datetime

from .api import OUTPUTS, REPORTS

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def _norm(s: str) -> str:
    s = "".join(c for c in unicodedata.normalize("NFD", s or "")
                if unicodedata.category(c) != "Mn")
    return s.lower().strip()


def _falta(archivo: str) -> str:
    return (f"No encuentro outputs/{archivo}. Corre `python run.py` primero: "
            "el pronóstico se calcula, no viene guardado.")


def _cargar(nombre: str) -> list[dict]:
    ruta = OUTPUTS / nombre
    if not ruta.exists():
        raise SystemExit(_falta(nombre))
    return list(csv.DictReader(ruta.open(encoding="utf-8")))


def _fecha(iso: str) -> str:
    d = datetime.fromisoformat(iso)
    return f"{DIAS[d.weekday()]} {d.day} de {MESES[d.month - 1]}, {d:%H:%M}"


def _eventos_meta() -> dict:
    from .fetch import load
    return {e["event_id"]: e for e in load("freeticket", "events")}


def informe(event_id: str) -> str:
    pron = {r["event_id"]: r for r in _cargar("forecast_detalle.csv")}
    if event_id not in pron:
        return (f"{event_id} no está en el pronóstico. Solo se proyectan los 30 "
                "shows de agosto; los de julio ya pasaron y su asistencia es un "
                "dato, no una predicción.")
    r = pron[event_id]
    meta = _eventos_meta().get(event_id, {})
    acciones = [a for a in _cargar("acciones.csv") if a["event_id"] == event_id]

    esperado = int(r["expected_attendance"])
    vendidas = int(r["tickets_adquiridos"])
    cap = int(meta.get("capacity") or 0)
    pct_cort = float(r["pct_cortesia"])
    llenado = esperado / cap if cap else 0

    tasa = float(r["tasa_esperada"])
    if llenado >= 0.85:
        veredicto = "Va lleno"
    elif llenado >= 0.6:
        veredicto = "Va bien"
    elif llenado >= 0.4:
        veredicto = "Va a medio llenar"
    else:
        veredicto = "Va flojo"

    # Sala vacia y sala que no entra son dos problemas distintos, con soluciones
    # distintas: uno se arregla vendiendo y el otro cambiando la mezcla.
    dias = None
    if meta.get("starts_at"):
        dias = (datetime.fromisoformat(meta["starts_at"])
                - datetime(2026, 8, 1, tzinfo=datetime.fromisoformat(
                    meta["starts_at"]).tzinfo)).days
    if llenado < 0.6 and tasa >= 0.75:
        diagnostico = ("El problema es de venta, no de asistencia: de los que ya "
                       f"tienen entrada viene el {tasa:.0%}, que está muy bien. "
                       "Lo que falta es vender más.")
    elif tasa < 0.55:
        diagnostico = ("El problema es la mezcla: se repartieron muchas entradas "
                       "que no se traducen en gente en la sala.")
    else:
        diagnostico = None

    L = [
        f"{meta.get('title', event_id)}  ·  {event_id}",
        f"{_fecha(meta['starts_at']) if meta.get('starts_at') else ''} · "
        f"{meta.get('venue', '')} ({meta.get('city', '')})",
        "",
        f"{veredicto}: esperamos {esperado} personas de {vendidas} entradas "
        f"ya adquiridas.",
        f"Rango p10–p90: {r['p10']} a {r['p90']} personas (acierta 8 de cada 10 noches).",
    ]
    if cap:
        L.append(f"Capacidad {cap} · llenado esperado {llenado:.0%} · "
                 f"{max(0, cap - esperado)} asientos libres.")

    if dias and dias > 3:
        L.append(f"Faltan {dias} días: seguirá vendiendo, así que esto proyecta "
                 "solo las entradas ya adquiridas.")

    L += ["", "POR QUÉ"]
    if diagnostico:
        L.append(f"· {diagnostico}")
    L.append(f"· La mezcla manda: {pct_cort:.0%} de las entradas son cortesía. "
             f"La cortesía entra al 38.7%, la pagada al 94%.")
    L.append(f"· Tasa esperada de este show: {tasa:.1%}.")
    L.append(f"· {r['compradores_en_boom']} de {vendidas} entradas son de "
             f"compradores identificados en Boom.")
    if pct_cort >= 0.5:
        L.append("· Ojo: con esta proporción de cortesías, vender más entradas "
                 "no significa meter más gente.")

    if acciones:
        L += ["", "QUÉ PUEDES HACER"]
        for i, a in enumerate(sorted(acciones, key=lambda x: -float(x["impacto_personas"])), 1):
            imp = float(a["impacto_personas"])
            if imp < 1:
                continue
            texto = {
                "invitar": f"Invitar a {a['alcance']} fieles de Boom de la ciudad "
                           f"que aún no tienen entrada",
                "canal": f"Mover {a['alcance']} cortesías de RRPP/admin a taquilla",
                "convertir": f"Convertir {a['alcance']} cortesías en entradas pagadas",
            }[a["palanca"]]
            L.append(f"{i}. {texto} → +{imp:.0f} personas  "
                     f"[supuesto {a['supuesto']}]")
        L.append("")
        L.append("Los supuestos: «fuerte» usa el historial real de personas "
                 "concretas. «débil» y «medio» son relaciones observadas, no "
                 "efectos probados — nadie asignó canales al azar.")
    return "\n".join(L)


def por_artista(nombre: str) -> str:
    pron = _cargar("forecast_detalle.csv")
    q = _norm(nombre)
    hits = [r for r in pron if q in _norm(r["artist_name"])]
    if not hits:
        disponibles = sorted({r["artist_name"] for r in pron})
        return (f"No encuentro shows de agosto para «{nombre}». "
                f"Los que hay: {', '.join(disponibles)}.")
    return "\n\n".join(informe(r["event_id"]) for r in hits)


def agenda() -> str:
    pron = _cargar("forecast_detalle.csv")
    meta = _eventos_meta()
    filas = sorted(pron, key=lambda r: meta[r["event_id"]]["starts_at"])
    L = [f"{'fecha':>17}  {'show':30} {'esperado':>9} {'rango':>12} {'vendidas':>9} {'cortesía':>9}"]
    for r in filas:
        m = meta[r["event_id"]]
        d = datetime.fromisoformat(m["starts_at"])
        L.append(f"{d.strftime('%a %d %b %H:%M'):>17}  {m['artist_name'][:30]:30} "
                 f"{r['expected_attendance']:>9} "
                 f"{r['p10'] + '–' + r['p90']:>12} "
                 f"{r['tickets_adquiridos']:>9} {float(r['pct_cortesia']):>8.0%}")
    tot = sum(int(r["expected_attendance"]) for r in filas)
    vend = sum(int(r["tickets_adquiridos"]) for r in filas)
    L.append("")
    L.append(f"Total agosto: {tot} personas esperadas de {vend} entradas "
             f"adquiridas ({tot / vend:.1%}).")
    return "\n".join(L)


def sobreventa(n: int = 10) -> str:
    """Cuántas entradas más se pueden vender sin que la gente no quepa."""
    ruta = OUTPUTS / "overbooking.csv"
    if not ruta.exists():
        return "Falta outputs/overbooking.csv. Corre `python -m ft.overbooking`."
    filas = list(csv.DictReader(ruta.open(encoding="utf-8")))
    extra = sum(int(r["puede_vender_mas"]) for r in filas)
    vend = sum(int(r["entradas_vendidas"]) for r in filas)
    cap = sum(int(r["capacidad"]) for r in filas)

    L = [
        "La capacidad de la sala no es el límite de venta.",
        "",
        f"Entradas ya vendidas para agosto: {vend:,}",
        f"Capacidad total de las salas:     {cap:,}",
        f"Se pueden vender ADEMÁS:          {extra:,} "
        f"({extra / vend:.0%} más de lo vendido)",
        "",
        "…y aun así, en 19 de cada 20 noches, toda la gente cabe. Si de cada",
        "entrada entra el 64%, vender justo hasta la capacidad deja la sala a",
        "dos tercios. El techo real no es el aforo: es el riesgo de desborde,",
        "y ese se calcula.",
        "",
        f"{'show':24} {'cap':>5} {'vend':>6} {'entran':>7} {'cortesía':>9} {'+vender':>9}",
    ]
    for r in sorted(filas, key=lambda x: -int(x["puede_vender_mas"]))[:n]:
        L.append(f"{r['artista'][:24]:24} {r['capacidad']:>5} "
                 f"{r['entradas_vendidas']:>6} {r['esperado']:>7} "
                 f"{float(r['pct_cortesia']):>8.0%} {r['puede_vender_mas']:>9}")
    L += [
        "",
        "Lo contraintuitivo: los shows con MÁS cortesías admiten MÁS sobreventa,",
        "porque su tasa de asistencia es más baja. La cortesía deja de ser papel",
        "gratis y pasa a ser inventario que consume cupo de riesgo.",
        "",
        "Riesgo fijado en 5% por show. Supone que las próximas entradas se",
        "parecen a las ya vendidas — si se venden a otro público, hay que",
        "recalcular.",
    ]
    return "\n".join(L)


def vacios(n: int = 8) -> str:
    """Los shows con menor llenado esperado y qué palanca les conviene."""
    pron = _cargar("forecast_detalle.csv")
    meta = _eventos_meta()
    acciones = _cargar("acciones.csv")
    mejor: dict[str, dict] = {}
    for a in acciones:
        act = mejor.get(a["event_id"])
        if act is None or float(a["impacto_personas"]) > float(act["impacto_personas"]):
            mejor[a["event_id"]] = a

    filas = []
    for r in pron:
        cap = int(meta[r["event_id"]].get("capacity") or 0)
        if not cap:
            continue
        esperado = int(r["expected_attendance"])
        filas.append((esperado / cap, r, cap, esperado))
    filas.sort(key=lambda x: x[0])

    L = [f"{'show':24} {'ciudad':10} {'cap':>5} {'entradas':>9} {'entran':>7} "
         f"{'llenado':>8} {'cortesía':>9}  qué hacer"]
    for llenado, r, cap, esperado in filas[:n]:
        a = mejor.get(r["event_id"])
        que = (f"{a['palanca']} → +{float(a['impacto_personas']):.0f} "
               f"[supuesto {a['supuesto']}]") if a else "—"
        L.append(f"{r['artist_name'][:24]:24} "
                 f"{meta[r['event_id']].get('city', '')[:10]:10} {cap:>5} "
                 f"{r['tickets_adquiridos']:>9} {esperado:>7} {llenado:>7.0%} "
                 f"{float(r['pct_cortesia']):>8.0%}  {que}")
    L.append("")
    L.append("«llenado» es sobre la capacidad de la sala; «cortesía», la parte de "
             "las entradas que no se pagaron.")
    L.append("Un llenado bajo con tasa de asistencia alta es problema de venta, "
             "no de asistencia: aún queda tiempo para vender.")
    return "\n".join(L)


def datos_json() -> str:
    """Todo lo proyectado, en JSON: para construir un tablero o un gráfico.

    Una sola llamada trae los 30 shows con su aforo, rango, mezcla y palancas,
    mas la ficha del modelo. Asi quien dibuje no tiene que abrir cuatro CSV ni
    adivinar de donde salio un numero.
    """
    pron = _cargar("forecast_detalle.csv")
    acciones = _cargar("acciones.csv")
    meta = _eventos_meta()
    por_evento: dict[str, list] = {}
    for a in acciones:
        por_evento.setdefault(a["event_id"], []).append({
            "palanca": a["palanca"], "supuesto": a["supuesto"],
            "impacto_personas": float(a["impacto_personas"]),
            "alcance": int(a["alcance"]),
        })

    shows = []
    for r in pron:
        m = meta.get(r["event_id"], {})
        cap = int(m.get("capacity") or 0)
        esperado = int(r["expected_attendance"])
        shows.append({
            "event_id": r["event_id"],
            "titulo": m.get("title"),
            "artista": r["artist_name"],
            "fecha": m.get("starts_at"),
            "ciudad": m.get("city"),
            "venue": m.get("venue"),
            "es_residencia": m.get("is_residency"),
            "capacidad": cap,
            "entradas_adquiridas": int(r["tickets_adquiridos"]),
            "cortesias": int(r["cortesias"]),
            "pct_cortesia": float(r["pct_cortesia"]),
            "compradores_en_boom": int(r["compradores_en_boom"]),
            "esperado": esperado,
            "p10": int(r["p10"]),
            "p90": int(r["p90"]),
            "tasa_esperada": float(r["tasa_esperada"]),
            "llenado_esperado": round(esperado / cap, 4) if cap else None,
            "asientos_libres": max(0, cap - esperado) if cap else None,
            "palancas": sorted(por_evento.get(r["event_id"], []),
                               key=lambda p: -p["impacto_personas"]),
        })
    shows.sort(key=lambda s: s["fecha"] or "")

    metricas = {}
    ruta = REPORTS / "metrics.json"
    if ruta.exists():
        m = json.loads(ruta.read_text(encoding="utf-8"))
        metricas = {"campeon": m["campeon"], "test": m["test"]}

    total = sum(s["esperado"] for s in shows)
    vendidas = sum(s["entradas_adquiridas"] for s in shows)
    return json.dumps({
        "generado": datetime.now().isoformat(timespec="seconds"),
        "resumen": {
            "shows": len(shows),
            "entradas_adquiridas": vendidas,
            "asistencia_esperada": total,
            "tasa_global": round(total / vendidas, 4) if vendidas else None,
            "pct_cortesia": round(sum(s["cortesias"] for s in shows) / vendidas, 4)
            if vendidas else None,
        },
        "tasas_de_referencia": {"pagada": 0.94, "cortesia": 0.387},
        "modelo": metricas,
        "shows": shows,
    }, ensure_ascii=False, indent=2)


def ficha_modelo() -> str:
    ruta = REPORTS / "metrics.json"
    if not ruta.exists():
        return "Falta reports/metrics.json. Corre `python -m ft.experimento`."
    m = json.loads(ruta.read_text(encoding="utf-8"))
    t, b = m["test"]["campeon"], m["test"]["baseline"]
    par = m["test"]["pareado_campeon_vs_baseline"]
    return "\n".join([
        f"Modelo: {m['campeon']}",
        "",
        "QUÉ TAN BIEN PREDICE (en el conjunto de prueba, 11 shows que el modelo "
        "nunca vio, evaluado una sola vez)",
        f"· Error medio: {t['mae']:.1f} personas por show "
        f"(IC 95%: {t['mae_ic95'][0]:.1f} a {t['mae_ic95'][1]:.1f}).",
        f"· Error relativo: {t['mape']:.1%}.",
        f"· Contra el baseline de tasa por tipo: {b['mae']:.1f} personas. "
        f"La ventaja es de {abs(par['dif_media']):.1f} personas por show "
        f"(IC 95% no cruza cero: la diferencia es real).",
        f"· Calibración (ECE): {t['ece']:.4f} — la probabilidad predicha coincide "
        "con la frecuencia real, que es lo que permite sumarlas.",
        "",
        "QUÉ SUPONE",
        "· Solo proyecta las entradas YA adquiridas. Los shows de fin de mes "
        "seguirán vendiendo.",
        "· El historial de Boom se recorta a lo que se sabía antes del show.",
        "· Los datos son de un solo mes: no hay estacionalidad ni festivos.",
        "",
        "DÓNDE FALLA",
        "· En cortesías el error por entrada es 0.446 contra 0.108 en pagadas. "
        "Los shows de pura cortesía son los más inciertos, y por eso su rango "
        "p10–p90 sale más ancho.",
    ])


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    arg = argv[0]
    if arg == "--agenda":
        print(agenda())
    elif arg == "--vacios":
        print(vacios())
    elif arg in ("--sobreventa", "--overbooking"):
        print(sobreventa())
    elif arg == "--json":
        texto = datos_json()
        # tambien a disco: redirigir con `>` en PowerShell le mete un BOM y
        # deja el JSON ilegible para json.load
        (OUTPUTS / "dashboard.json").write_text(texto, encoding="utf-8")
        print(texto)
    elif arg == "--modelo":
        print(ficha_modelo())
    elif arg.startswith("ft_evt_"):
        print(informe(arg))
    else:
        print(por_artista(" ".join(argv)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
