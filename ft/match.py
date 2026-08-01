"""Cruce sale_id -> boom_user_id.

Regla del negocio antes que la metrica: una parte grande de los compradores NO
existe en Boom. Inventarles un match es peor que dejarlos sin match. Por eso el
nombre nunca decide solo (1144 nombres se repiten en Boom, 885 con mas de tres
personas) y solo email y telefono -unicos en Boom- pueden anclar un match.

Evidencia -> score:
    email    0.44   exacto tras normalizar; menos si es local igual / typo
    telefono 0.36   exacto; menos si es transposicion de dos digitos
    nombre   0.20   verificador, no ancla
El nombre tambien DESMIENTE: email correcto + nombre ajeno es el correo de la
pareja, y ahi el match no se acepta.
"""

from __future__ import annotations

import csv
from collections import defaultdict

from .api import ROOT
from .fetch import load
from .normalize import (
    clave_nombre,
    edit_dist,
    local_core,
    norm_email,
    norm_phone,
    sim_nombre,
    transposiciones,
)

W_EMAIL, W_PHONE, W_NAME = 0.44, 0.36, 0.20
UMBRAL = 0.52       # por debajo: sin match
MARGEN = 0.06       # si el 2do candidato queda mas cerca que esto, es ambiguo


def _deletions(s: str) -> set[str]:
    """Variantes de s con un caracter eliminado (SymSpell distancia 1)."""
    return {s[:i] + s[i + 1 :] for i in range(len(s))}


class Indice:
    """Indices de Boom para generar candidatos baratos."""

    def __init__(self, users: list[dict]):
        self.users = {u["boom_user_id"]: u for u in users}
        self.por_email: dict[str, str] = {}
        self.por_local: dict[str, list[str]] = defaultdict(list)
        self.por_core: dict[str, list[str]] = defaultdict(list)
        self.por_core_del: dict[str, list[str]] = defaultdict(list)
        self.por_phone: dict[str, str] = {}
        self.norm: dict[str, dict] = {}

        for u in users:
            uid = u["boom_user_id"]
            email, local, dom = norm_email(u["email"])
            core = local_core(local)
            phone = norm_phone(u["phone"])
            self.norm[uid] = {
                "email": email,
                "local": local,
                "dom": dom,
                "core": core,
                "phone": phone,
                "nombre": clave_nombre(f"{u['first_name']} {u['last_name']}"),
            }
            self.por_email[email] = uid
            self.por_local[local].append(uid)
            if core:
                self.por_core[core].append(uid)
                for d in _deletions(core):
                    self.por_core_del[d].append(uid)
            if phone:
                self.por_phone[phone] = uid

    def candidatos(self, email: str, local: str, core: str, phone: str) -> set[str]:
        out: set[str] = set()
        if email in self.por_email:
            out.add(self.por_email[email])
        out.update(self.por_local.get(local, ()))
        if core:
            out.update(self.por_core.get(core, ()))
            # letra faltante en cualquiera de los dos lados
            out.update(self.por_core_del.get(core, ()))
            for d in _deletions(core):
                out.update(self.por_core_del.get(d, ()))
                out.update(self.por_core.get(d, ()))
        if phone:
            if phone in self.por_phone:
                out.add(self.por_phone[phone])
            for t in transposiciones(phone):
                if t in self.por_phone:
                    out.add(self.por_phone[t])
        return out


def _ev_email(venta: dict, cand: dict, local_unico: bool) -> float:
    """Cuanto discrimina el email.

    Medido sobre los datos: el "nucleo" del local (nombreapellido, sin puntos ni
    digitos de cola) NO identifica a nadie — 4 a 7 usuarios de Boom lo comparten,
    porque equivale al nombre. Los digitos de cola son lo que discrimina, asi que
    solo el local COMPLETO ancla.
    """
    if venta["email"] and venta["email"] == cand["email"]:
        return 1.00
    vl, cl = venta["local"], cand["local"]
    mismo_dom = venta["dom"] and venta["dom"] == cand["dom"]
    if vl and vl == cl:
        # mismo buzon, otro dominio: fuerte si el local lleva digitos propios
        if any(ch.isdigit() for ch in vl) or local_unico:
            return 0.85
        return 0.45
    if vl and cl and edit_dist(vl, cl, 1) <= 1:
        return 0.85 if mismo_dom else 0.65   # una letra faltante
    if venta["core"] and venta["core"] == cand["core"]:
        return 0.25          # solo coincide el nombre: no ancla nada
    return 0.0


def _ev_phone(venta: dict, cand: dict) -> float:
    vp, cp = venta["phone"], cand["phone"]
    if not vp or not cp:
        return 0.0
    if vp == cp:
        return 1.00
    if vp in transposiciones(cp):
        return 0.75          # dos digitos cambiados de orden
    return 0.0


def puntuar(venta: dict, uid: str, idx: Indice) -> tuple[float, float, float, float]:
    cand = idx.norm[uid]
    u = idx.users[uid]
    e = _ev_email(venta, cand, len(idx.por_local.get(cand["local"], ())) == 1)
    p = _ev_phone(venta, cand)
    n = sim_nombre(venta["nombre_raw"], u["first_name"], u["last_name"])
    score = W_EMAIL * e + W_PHONE * p + W_NAME * n
    if venta["city"] and u.get("city") and venta["city"] == u["city"]:
        score += 0.03
    return min(score, 1.0), e, p, n


def preparar_venta(s: dict) -> dict:
    email, local, dom = norm_email(s["buyer_email"])
    return {
        "sale_id": s["sale_id"],
        "email": email,
        "local": local,
        "dom": dom,
        "core": local_core(local),
        "phone": norm_phone(s["buyer_phone"]),
        "nombre_raw": s["buyer_name"],
        "city": None,  # la venta no trae ciudad; se deja por si el API la agrega
    }


def cruzar(sales: list[dict], users: list[dict]) -> list[dict]:
    idx = Indice(users)
    filas = []
    for s in sales:
        v = preparar_venta(s)
        puntuados = []
        for uid in idx.candidatos(v["email"], v["local"], v["core"], v["phone"]):
            sc, e, p, n = puntuar(v, uid, idx)
            puntuados.append((sc, uid, e, p, n))
        puntuados.sort(reverse=True)

        mejor = puntuados[0] if puntuados else None
        segundo = puntuados[1][0] if len(puntuados) > 1 else 0.0
        ok = bool(mejor) and mejor[0] >= UMBRAL and (mejor[0] - segundo) >= MARGEN

        filas.append({
            "sale_id": s["sale_id"],
            "boom_user_id": mejor[1] if ok else "",
            "confidence": round(mejor[0], 4) if ok else 0.0,
            "ev_email": round(mejor[2], 2) if mejor else 0.0,
            "ev_phone": round(mejor[3], 2) if mejor else 0.0,
            "ev_nombre": round(mejor[4], 2) if mejor else 0.0,
            "via": "directo" if ok else "",
        })
    return consolidar(filas, sales)


def consolidar(filas: list[dict], sales: list[dict]) -> list[dict]:
    """Un mismo comprador debe caer siempre en el mismo usuario de Boom.

    Si alguna venta de ese correo logro un match firme, se propaga a las demas
    ventas del mismo correo que quedaron sin match.
    """
    por_sale = {f["sale_id"]: f for f in filas}
    mejor_por_email: dict[str, tuple[float, str]] = {}
    for s in sales:
        f = por_sale[s["sale_id"]]
        if not f["boom_user_id"]:
            continue
        email = norm_email(s["buyer_email"])[0]
        if f["confidence"] > mejor_por_email.get(email, (0.0, ""))[0]:
            mejor_por_email[email] = (f["confidence"], f["boom_user_id"])

    for s in sales:
        f = por_sale[s["sale_id"]]
        if f["boom_user_id"]:
            continue
        email = norm_email(s["buyer_email"])[0]
        hit = mejor_por_email.get(email)
        if hit and hit[0] >= 0.70:
            f["boom_user_id"] = hit[1]
            f["confidence"] = round(hit[0] * 0.85, 4)
            f["via"] = "propagado"
    return filas


def main() -> list[dict]:
    sales = load("freeticket", "sales")
    users = load("boom", "users")
    filas = cruzar(sales, users)

    salida = ROOT / "matches.csv"
    with salida.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["sale_id", "boom_user_id", "confidence"])
        w.writeheader()
        for f in filas:
            w.writerow({k: f[k] for k in ("sale_id", "boom_user_id", "confidence")})

    # detalle con la evidencia, util para auditar el cruce
    with (ROOT / "matches_detalle.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0].keys()))
        w.writeheader()
        w.writerows(filas)

    con = sum(1 for f in filas if f["boom_user_id"])
    prop = sum(1 for f in filas if f["via"] == "propagado")
    print(f"Cruce: {con}/{len(filas)} ventas con match ({con/len(filas):.1%}), "
          f"{prop} por propagacion -> {salida.name}")
    return filas


if __name__ == "__main__":
    main()
