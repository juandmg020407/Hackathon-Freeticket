"""Tabla de features a nivel de ENTRADA (no de venta): una fila por ticket.

El objetivo es la probabilidad de que ESA entrada cruce la puerta. Sumadas por
evento dan el aforo esperado.

Corte temporal: el historial de Boom de un comprador se mide con lo que se sabia
antes del show. Para julio, el corte es la fecha del evento; para agosto, HOY
(2026-08-01). Sin esto el modelo se calibraria con informacion que en la vida
real no existia todavia — Boom trae date_used hasta el 26 de agosto.
"""

from __future__ import annotations

import bisect
import csv
from collections import defaultdict
from datetime import datetime, timezone

from .api import ROOT
from .fetch import load

HOY = datetime(2026, 8, 1, tzinfo=timezone.utc)
CORTESIA = "Cortesía"


def _dt(s: str | None):
    return datetime.fromisoformat(s) if s else None


class HistorialBoom:
    """use_rate por tipo de entrada, recortado a una fecha.

    El use_rate crudo del perfil mezcla los dos tipos y por eso se queda corto:
    consumo minimo entra al 75%, membresia no pasa del 60%. Se separan.
    """

    def __init__(self, boom_tickets: list[dict]):
        # por usuario y tipo: fechas de compra ordenadas, y fechas de uso
        self.compras: dict[str, dict[str, list[datetime]]] = defaultdict(lambda: defaultdict(list))
        self.usos: dict[str, dict[str, list[datetime]]] = defaultdict(lambda: defaultdict(list))
        for t in boom_tickets:
            uid, tipo = t["boom_user_id"], t["type"]
            c = _dt(t["created_at"])
            if c:
                self.compras[uid][tipo].append(c)
            if t["used"] and t["date_used"]:
                self.usos[uid][tipo].append(_dt(t["date_used"]))
        for d in (self.compras, self.usos):
            for u in d.values():
                for lst in u.values():
                    lst.sort()

    def stats(self, uid: str, corte: datetime) -> dict:
        """(n, usados) por tipo hasta 'corte', mas los agregados."""
        out = {}
        n_tot = u_tot = 0
        for tipo in ("consumo_minimo", "membresia"):
            n = bisect.bisect_right(self.compras.get(uid, {}).get(tipo, []), corte)
            u = bisect.bisect_right(self.usos.get(uid, {}).get(tipo, []), corte)
            u = min(u, n)
            out[f"n_{tipo}"] = n
            out[f"used_{tipo}"] = u
            out[f"rate_{tipo}"] = (u / n) if n else None
            n_tot += n
            u_tot += u
        out["n_boom"] = n_tot
        out["rate_boom"] = (u_tot / n_tot) if n_tot else None
        return out


def construir() -> list[dict]:
    tickets = load("freeticket", "tickets")
    sales = {s["sale_id"]: s for s in load("freeticket", "sales")}
    events = {e["event_id"]: e for e in load("freeticket", "events")}
    users = {u["boom_user_id"]: u for u in load("boom", "users")}
    hist = HistorialBoom(load("boom", "tickets"))

    matches = {}
    ruta = ROOT / "matches.csv"
    if ruta.exists():
        for r in csv.DictReader(ruta.open(encoding="utf-8")):
            if r["boom_user_id"]:
                matches[r["sale_id"]] = (r["boom_user_id"], float(r["confidence"]))

    filas = []
    for t in tickets:
        s = sales[t["sale_id"]]
        e = events[t["event_id"]]
        inicio = _dt(e["starts_at"])
        corte = min(inicio, HOY)

        uid, conf = matches.get(t["sale_id"], (None, 0.0))
        h = hist.stats(uid, corte) if uid else {}
        u = users.get(uid) if uid else None

        comprado = _dt(s["purchased_at"])
        dias = max(0.0, (inicio - comprado).total_seconds() / 86400) if comprado else None

        filas.append({
            "ticket_id": t["ticket_id"],
            "sale_id": t["sale_id"],
            "event_id": t["event_id"],
            "artist_id": e["artist_id"],
            "artist_name": e["artist_name"],
            "month": e["month"],
            "tipo": t["ticket_type"],
            "es_cortesia": t["ticket_type"] == CORTESIA,
            "precio": t["price"] or 0,
            "canal": s["channel"],
            "qty": s["qty"],
            "dias_anticipacion": dias,
            # senal Boom
            "en_boom": uid is not None,
            "boom_user_id": uid,
            "confidence": conf,
            "n_boom": h.get("n_boom", 0),
            "rate_boom": h.get("rate_boom"),
            "rate_consumo": h.get("rate_consumo_minimo"),
            "n_consumo": h.get("n_consumo_minimo", 0),
            "rate_membresia": h.get("rate_membresia"),
            "n_membresia": h.get("n_membresia", 0),
            "has_membership": bool(u and u["has_membership"]) if u else False,
            # vive en la ciudad del show: pesa en las cortesias (43% vs 34%)
            "misma_ciudad": bool(u and u["city"] == e["city"]) if u else False,
            # etiqueta
            "y": t["checked_in"],
        })
    return filas


if __name__ == "__main__":
    f = construir()
    jul = [x for x in f if x["y"] is not None]
    print(f"{len(f)} tickets — julio etiquetado: {len(jul)}, agosto: {len(f) - len(jul)}")
    print(f"con senal Boom: {sum(1 for x in f if x['en_boom'])}")
