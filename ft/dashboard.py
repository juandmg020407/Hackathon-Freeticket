"""Genera outputs/dashboard.json: el artefacto que la skill consume.

Todo lo proyectado en un solo archivo — los 30 shows con su aforo, rango,
mezcla y palancas, mas la sobreventa segura, la curva de llegada y la ficha del
modelo. Quien dibuje un tablero no tiene que abrir cuatro CSV ni adivinar de
donde salio un numero.

Este modulo es la mitad que VIVE EN EL REPO: necesita los CSV de outputs/ y el
cache de raw/. La otra mitad —presentar— vive en la skill y solo lee este JSON,
que es lo que le permite funcionar sin repo, sin token y sin pip install.

    python -m ft.dashboard
"""

from __future__ import annotations

import csv
import json
from datetime import datetime

from .api import OUTPUTS, REPORTS, ROOT

# La copia que viaja dentro de la skill. Se sincroniza en cada generacion: si se
# dejara a mano, envejeceria en silencio y la skill responderia cifras viejas
# creyendolas frescas.
SKILL_DATA = ROOT / ".claude" / "skills" / "aforo-freeticket" / "data"


def _cargar(nombre: str) -> list[dict]:
    ruta = OUTPUTS / nombre
    if not ruta.exists():
        raise SystemExit(f"Falta outputs/{nombre}. Corre `python run.py` primero.")
    return list(csv.DictReader(ruta.open(encoding="utf-8")))


def _eventos_meta() -> dict:
    from .fetch import load
    return {e["event_id"]: e for e in load("freeticket", "events")}


def _sobreventa() -> list[dict]:
    ruta = OUTPUTS / "overbooking.csv"
    if not ruta.exists():
        return []
    return [{
        "event_id": r["event_id"],
        "artista": r["artista"],
        "capacidad": int(r["capacidad"]),
        "entradas_vendidas": int(r["entradas_vendidas"]),
        "esperado": int(r["esperado"]),
        "pct_cortesia": float(r["pct_cortesia"]),
        "puede_vender_mas": int(r["puede_vender_mas"]),
        "riesgo_actual_desborde": float(r["riesgo_actual_desborde"]),
    } for r in csv.DictReader(ruta.open(encoding="utf-8"))]


def _curva_llegada() -> dict:
    """La curva de julio, congelada.

    Se mide sobre 60.000 tickets de raw/, asi que la skill instalada nunca
    podria recalcularla. Congelarla aqui es lo que permite responder «a que hora
    llega la gente» y «cuanto personal pongo en la puerta» sin el repo.
    """
    try:
        from .llegada import FRANJA, curva_julio
        curva = curva_julio()
    except Exception:
        return {}
    return {
        "franja_min": FRANJA,
        "fracciones": {str(k): v for k, v in sorted(curva.items())},
    }


def generar() -> dict:
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
    return {
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
        "sobreventa": _sobreventa(),
        "curva_llegada": _curva_llegada(),
    }


def main() -> None:
    texto = json.dumps(generar(), ensure_ascii=False, indent=2)
    # a disco desde Python y no con `>`: en PowerShell la redireccion mete un BOM
    # y deja el JSON ilegible para json.load
    (OUTPUTS / "dashboard.json").write_text(texto, encoding="utf-8")
    SKILL_DATA.mkdir(parents=True, exist_ok=True)
    (SKILL_DATA / "dashboard.json").write_text(texto, encoding="utf-8")
    print(f"  outputs/dashboard.json y la copia de la skill, "
          f"{len(texto) // 1024} KB")


if __name__ == "__main__":
    main()
