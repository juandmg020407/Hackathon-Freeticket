"""Normalizacion de las llaves sucias: email, telefono, nombre.

El brief avisa como estan rotas a proposito:
  email     alias +algo, dominio mal escrito, una letra faltante, MAYUSCULAS
  telefono  cinco formatos, vacio, dos digitos cambiados de orden
  nombre    sin tildes, minuscula, apellido primero, segundo apellido, inicial
"""

from __future__ import annotations

import re
import unicodedata

# Dominios reales observados en Boom y sus variantes rotas en la tiquetera.
DOMINIOS = ["gmail.com", "hotmail.com", "outlook.com", "yahoo.com", "icloud.com", "proton.me"]

DOMINIO_FIX = {
    "gmial.com": "gmail.com",
    "gmai.com": "gmail.com",
    "gmail.co": "gmail.com",
    "gnail.com": "gmail.com",
    "hotmial.com": "hotmail.com",
    "hotmai.com": "hotmail.com",
    "hotmal.com": "hotmail.com",
    "hotmail.co": "hotmail.com",
    "outlok.com": "outlook.com",
    "outloo.com": "outlook.com",
    "outlook.co": "outlook.com",
    "yaho.com": "yahoo.com",
    "yahooo.com": "yahoo.com",
    "iclod.com": "icloud.com",
    "icloud.co": "icloud.com",
    "protonme": "proton.me",
    "proton.m": "proton.me",
}


def sin_tildes(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn"
    )


def edit_dist(a: str, b: str, tope: int = 2) -> int:
    """Levenshtein con corte temprano."""
    if abs(len(a) - len(b)) > tope:
        return tope + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        if min(cur) > tope:
            return tope + 1
        prev = cur
    return prev[-1]


# ---------------------------------------------------------------- email


def fix_dominio(dom: str) -> str:
    """Corrige el dominio: tabla de typos y, si no, el mas cercano a distancia 1."""
    if dom in DOMINIO_FIX:
        return DOMINIO_FIX[dom]
    if dom in DOMINIOS:
        return dom
    for real in DOMINIOS:
        if edit_dist(dom, real, 1) <= 1:
            return real
    return dom


def norm_email(email: str) -> tuple[str, str, str]:
    """Devuelve (email_normalizado, local_sin_alias, dominio_corregido)."""
    e = sin_tildes(email or "").strip().lower()
    if "@" not in e:
        return e, e, ""
    local, _, dom = e.rpartition("@")
    local = local.split("+", 1)[0]  # alias +algo
    dom = fix_dominio(dom)
    return f"{local}@{dom}", local, dom


def local_core(local: str) -> str:
    """Nucleo del local-part: sin puntos, guiones ni digitos de cola.

    'maria.rodriguez64' -> 'mariarodriguez'.  Sirve para agrupar variantes
    del mismo correo sin depender de la puntuacion.
    """
    l = re.sub(r"[._\-]", "", local or "")
    return re.sub(r"\d+$", "", l)


# ---------------------------------------------------------------- telefono


def norm_phone(phone: str) -> str:
    """Solo digitos, sin indicativo 57, ultimos 10."""
    d = re.sub(r"\D", "", phone or "")
    if len(d) > 10 and d.startswith("57"):
        d = d[2:]
    return d[-10:] if len(d) >= 10 else ""


def transposiciones(tel: str) -> set[str]:
    """Variantes con dos digitos adyacentes intercambiados."""
    out = set()
    for i in range(len(tel) - 1):
        if tel[i] != tel[i + 1]:
            out.add(tel[: i] + tel[i + 1] + tel[i] + tel[i + 2 :])
    return out


# ---------------------------------------------------------------- nombre

PARTICULAS = {"de", "del", "la", "las", "los", "san", "santa", "da", "do"}


def tokens_nombre(nombre: str) -> list[str]:
    n = sin_tildes(nombre or "").lower()
    n = re.sub(r"[^a-z\s]", " ", n)
    return [t for t in n.split() if t and t not in PARTICULAS]


def clave_nombre(nombre: str) -> str:
    """Tokens ordenados: absorbe 'apellido primero' y el orden invertido."""
    return " ".join(sorted(tokens_nombre(nombre)))


def sim_nombre(venta: str, first: str, last: str) -> float:
    """Similitud 0..1 entre el nombre de la venta y el par (first,last) de Boom.

    Tolera: orden invertido, segundo apellido que Boom no registro, inicial
    en lugar del nombre, y falta de tildes.
    """
    a = tokens_nombre(venta)
    b = tokens_nombre(f"{first} {last}")
    if not a or not b:
        return 0.0
    sa, sb = set(a), set(b)
    if sa == sb:
        return 1.0

    exactos = sa & sb
    # tokens de Boom cubiertos por la venta, admitiendo inicial y typo leve
    cubiertos = len(exactos)
    for tb in sb - exactos:
        for ta in sa - exactos:
            if len(ta) == 1 and tb.startswith(ta):
                cubiertos += 0.5
                break
            if len(ta) > 3 and edit_dist(ta, tb, 1) <= 1:
                cubiertos += 0.9
                break
    base = cubiertos / len(sb)  # cuanto de Boom aparece en la venta

    # penaliza tokens sobrantes solo si son muchos (un 2do apellido es normal)
    sobrantes = max(0, len(sa) - len(sb) - 1)
    return max(0.0, min(1.0, base - 0.15 * sobrantes))
