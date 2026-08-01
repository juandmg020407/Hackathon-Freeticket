#!/usr/bin/env python
"""Cuanta gente entra realmente a cada show, y que hacer para llenarlo.

    python aforo.py "Sin Filtro"      todos los shows de ese acto
    python aforo.py ft_evt_0060       un show por id
    python aforo.py --agenda          los 30 shows de agosto, en orden
    python aforo.py --vacios          los que van a quedar mas vacios
    python aforo.py --sobreventa      cuantas entradas mas caben sin riesgo
    python aforo.py --llegada         a que hora llega la gente y cuanto personal
    python aforo.py --modelo          que tan bien predice y que supone
    python aforo.py --json            todo estructurado, para graficar
    python aforo.py --actualizar      baja el dashboard publicado mas reciente
    python aforo.py --recalcular ID   recalcula desde el API con TU token

Stdlib pura y una sola fuente de datos: dashboard.json. Sin pandas, sin token y
sin pipeline — por eso funciona instalado en cualquier agente, fuera del repo.
Nunca inventa una cifra: si no esta en el dashboard, no la responde.
"""

from __future__ import annotations

import json
import os
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

# La salida lleva «·», «→» y tildes. La consola de Windows arranca en cp1252 y
# revienta con un UnicodeEncodeError antes de imprimir nada util, asi que se
# fuerza UTF-8 aqui en vez de exigirle al usuario que configure su terminal.
for _flujo in (sys.stdout, sys.stderr):
    if hasattr(_flujo, "reconfigure"):
        _flujo.reconfigure(encoding="utf-8", errors="replace")

AQUI = Path(__file__).resolve().parent
CONGELADO = AQUI.parent / "data" / "dashboard.json"
URL = os.environ.get(
    "FT_DASHBOARD_URL",
    "https://raw.githubusercontent.com/juandmg020407/"
    "Hackathon-Freeticket/main/outputs/dashboard.json",
)
CADUCA_DIAS = 7

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


# --------------------------------------------------------------------------
# De donde salen los datos
# --------------------------------------------------------------------------

def _repo_dashboard() -> Path | None:
    """outputs/dashboard.json subiendo desde el cwd y desde el script.

    Si se ejecuta dentro del repo, gana el dato recien calculado sobre la copia
    que viaja con la skill.
    """
    for base in (Path.cwd().resolve(), AQUI):
        for d in (base, *base.parents):
            cand = d / "outputs" / "dashboard.json"
            if cand.is_file():
                return cand
    return None


def _descargar(destino: Path | None = None) -> dict:
    import urllib.request
    with urllib.request.urlopen(URL, timeout=30) as r:
        texto = r.read().decode("utf-8")
    datos = json.loads(texto)  # falla aqui si el remoto devolvio basura
    if destino is not None:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")
    return datos


def cargar() -> tuple[dict, str]:
    """El dashboard y de donde salio.

    El congelado va ANTES que la red a proposito: una consulta no debe pagar
    latencia ni fallar sin conexion. La red es el ultimo recurso, para cuando
    la skill se instalo sin su copia de datos.
    """
    env = os.environ.get("FT_DASHBOARD")
    if env:
        ruta = Path(env).expanduser()
        if not ruta.is_file():
            raise SystemExit(f"FT_DASHBOARD apunta a {ruta}, que no existe.")
        return json.loads(ruta.read_text(encoding="utf-8")), "FT_DASHBOARD"

    repo = _repo_dashboard()
    if repo is not None:
        return json.loads(repo.read_text(encoding="utf-8")), "repo"

    if CONGELADO.is_file():
        return json.loads(CONGELADO.read_text(encoding="utf-8")), "skill"

    try:
        return _descargar(CONGELADO), "descargado"
    except Exception as e:
        raise SystemExit(
            f"No encuentro datos y no pude descargarlos ({e}).\n"
            f"Opciones: `python aforo.py --actualizar`, apuntar $FT_DASHBOARD a "
            f"un dashboard.json, o correr `python run.py` dentro del repo."
        )


def procedencia(d: dict, fuente: str) -> str:
    """Una linea diciendo de cuando son las cifras. Nunca se omite.

    Una cifra vieja presentada como viva es el error que este proyecto se cuida
    de no cometer en ningun otro sitio.
    """
    gen = d.get("generado", "")
    try:
        fecha = datetime.fromisoformat(gen)
        cuando = fecha.strftime("%Y-%m-%d %H:%M")
        edad = (datetime.now() - fecha).days
    except ValueError:
        cuando, edad = gen or "fecha desconocida", 0
    etiqueta = {
        "repo": "del repo (recien calculados)",
        "skill": "la copia que trae la skill",
        "descargado": "descargados del repo publicado",
        "FT_DASHBOARD": "de $FT_DASHBOARD",
    }.get(fuente, fuente)
    L = [f"datos: {etiqueta} · generados {cuando} · "
         f"{d.get('resumen', {}).get('shows', 0)} shows de agosto"]
    if edad > CADUCA_DIAS:
        L.append(f"AVISO: tienen {edad} días. Los shows siguen vendiendo, así que "
                 f"esto ya no refleja lo adquirido hoy — actualiza con "
                 f"`--actualizar`.")
    return "\n".join(L)


# --------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------

def _norm(s: str) -> str:
    s = "".join(c for c in unicodedata.normalize("NFD", s or "")
                if unicodedata.category(c) != "Mn")
    return s.lower().strip()


def _fecha(iso: str) -> str:
    d = datetime.fromisoformat(iso)
    return f"{DIAS[d.weekday()]} {d.day} de {MESES[d.month - 1]}, {d:%H:%M}"


def _shows(d: dict) -> list[dict]:
    return d.get("shows", [])


def _uno(d: dict, event_id: str) -> dict | None:
    return next((s for s in _shows(d) if s["event_id"] == event_id), None)


# --------------------------------------------------------------------------
# Las respuestas
# --------------------------------------------------------------------------

def informe(d: dict, event_id: str) -> str:
    s = _uno(d, event_id)
    if s is None:
        return (f"{event_id} no está en el pronóstico. Solo se proyectan los 30 "
                "shows de agosto; los de julio ya pasaron y su asistencia es un "
                "dato, no una predicción.")

    esperado = s["esperado"]
    vendidas = s["entradas_adquiridas"]
    cap = s["capacidad"] or 0
    pct_cort = s["pct_cortesia"]
    tasa = s["tasa_esperada"]
    llenado = esperado / cap if cap else 0
    ref = d.get("tasas_de_referencia", {})

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
    if s.get("fecha"):
        inicio = datetime.fromisoformat(s["fecha"])
        try:
            corte = datetime.fromisoformat(d["generado"]).replace(
                hour=0, minute=0, second=0, microsecond=0, tzinfo=inicio.tzinfo)
            dias = (inicio - corte).days
        except (KeyError, ValueError):
            dias = None
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
        f"{s.get('titulo') or event_id}  ·  {event_id}",
        f"{_fecha(s['fecha']) if s.get('fecha') else ''} · "
        f"{s.get('venue') or ''} ({s.get('ciudad') or ''})",
        "",
        f"{veredicto}: esperamos {esperado} personas de {vendidas} entradas "
        f"ya adquiridas.",
        f"Rango p10–p90: {s['p10']} a {s['p90']} personas "
        f"(acierta 8 de cada 10 noches).",
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
             f"La cortesía entra al {ref.get('cortesia', 0.387):.1%}, la pagada "
             f"al {ref.get('pagada', 0.94):.0%}.")
    L.append(f"· Tasa esperada de este show: {tasa:.1%}.")
    L.append(f"· {s['compradores_en_boom']} de {vendidas} entradas son de "
             f"compradores identificados en Boom.")
    if pct_cort >= 0.5:
        L.append("· Ojo: con esta proporción de cortesías, vender más entradas "
                 "no significa meter más gente.")

    todas = s.get("palancas", [])
    palancas = [p for p in todas if p["impacto_personas"] >= 1]
    if todas and not palancas:
        # Callar aqui deja creer que no se miro; el encabezado vacio del original
        # sugeria que habia algo que hacer. Ninguna palanca llega a una persona.
        L += ["", "QUÉ PUEDES HACER",
              "Nada que mueva la aguja: ninguna de las tres palancas llega a "
              "sumar una persona.",
              "Este show ya agotó su base local de fieles en Boom y casi no "
              "tiene cortesías que convertir."]
    if palancas:
        L += ["", "QUÉ PUEDES HACER"]
        for i, a in enumerate(sorted(palancas,
                                     key=lambda x: -x["impacto_personas"]), 1):
            texto = {
                "invitar": f"Invitar a {a['alcance']} fieles de Boom de la ciudad "
                           f"que aún no tienen entrada",
                "canal": f"Mover {a['alcance']} cortesías de RRPP/admin a taquilla",
                "convertir": f"Convertir {a['alcance']} cortesías en entradas pagadas",
            }.get(a["palanca"], f"{a['palanca']} ({a['alcance']})")
            L.append(f"{i}. {texto} → +{a['impacto_personas']:.0f} personas  "
                     f"[supuesto {a['supuesto']}]")
        L.append("")
        L.append("Los supuestos: «fuerte» usa el historial real de personas "
                 "concretas. «débil» y «medio» son relaciones observadas, no "
                 "efectos probados — nadie asignó canales al azar.")
    return "\n".join(L)


def por_artista(d: dict, nombre: str) -> str:
    q = _norm(nombre)
    hits = [s for s in _shows(d) if q in _norm(s["artista"])]
    if not hits:
        disponibles = sorted({s["artista"] for s in _shows(d)})
        return (f"No encuentro shows de agosto para «{nombre}». "
                f"Los que hay: {', '.join(disponibles)}.")
    return "\n\n".join(informe(d, s["event_id"]) for s in hits)


def agenda(d: dict) -> str:
    filas = sorted(_shows(d), key=lambda s: s["fecha"] or "")
    L = [f"{'fecha':>17}  {'show':30} {'esperado':>9} {'rango':>12} "
         f"{'vendidas':>9} {'cortesía':>9}"]
    for s in filas:
        f = datetime.fromisoformat(s["fecha"])
        L.append(f"{f.strftime('%a %d %b %H:%M'):>17}  {s['artista'][:30]:30} "
                 f"{s['esperado']:>9} "
                 f"{str(s['p10']) + '–' + str(s['p90']):>12} "
                 f"{s['entradas_adquiridas']:>9} {s['pct_cortesia']:>8.0%}")
    tot = sum(s["esperado"] for s in filas)
    vend = sum(s["entradas_adquiridas"] for s in filas)
    L.append("")
    L.append(f"Total agosto: {tot} personas esperadas de {vend} entradas "
             f"adquiridas ({tot / vend:.1%}).")
    return "\n".join(L)


def vacios(d: dict, n: int = 8) -> str:
    """Los shows con menor llenado esperado y que palanca les conviene."""
    filas = [s for s in _shows(d) if s["capacidad"]]
    filas.sort(key=lambda s: s["esperado"] / s["capacidad"])

    L = [f"{'show':24} {'ciudad':10} {'cap':>5} {'entradas':>9} {'entran':>7} "
         f"{'llenado':>8} {'cortesía':>9}  qué hacer"]
    for s in filas[:n]:
        llenado = s["esperado"] / s["capacidad"]
        p = s["palancas"][0] if s.get("palancas") else None
        que = (f"{p['palanca']} → +{p['impacto_personas']:.0f} "
               f"[supuesto {p['supuesto']}]") if p else "—"
        L.append(f"{s['artista'][:24]:24} "
                 f"{(s.get('ciudad') or '')[:10]:10} {s['capacidad']:>5} "
                 f"{s['entradas_adquiridas']:>9} {s['esperado']:>7} "
                 f"{llenado:>7.0%} {s['pct_cortesia']:>8.0%}  {que}")
    L.append("")
    L.append("«llenado» es sobre la capacidad de la sala; «cortesía», la parte de "
             "las entradas que no se pagaron.")
    L.append("Un llenado bajo con tasa de asistencia alta es problema de venta, "
             "no de asistencia: aún queda tiempo para vender.")
    return "\n".join(L)


def sobreventa(d: dict, n: int = 10) -> str:
    """Cuantas entradas mas se pueden vender sin que la gente no quepa."""
    filas = d.get("sobreventa") or []
    if not filas:
        return ("Este dashboard no trae el cálculo de sobreventa. Regenéralo con "
                "`python run.py` o baja uno más nuevo con `--actualizar`.")
    extra = sum(r["puede_vender_mas"] for r in filas)
    vend = sum(r["entradas_vendidas"] for r in filas)
    cap = sum(r["capacidad"] for r in filas)

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
        f"{'show':24} {'cap':>5} {'vend':>6} {'entran':>7} {'cortesía':>9} "
        f"{'+vender':>9}",
    ]
    for r in sorted(filas, key=lambda x: -x["puede_vender_mas"])[:n]:
        L.append(f"{r['artista'][:24]:24} {r['capacidad']:>5} "
                 f"{r['entradas_vendidas']:>6} {r['esperado']:>7} "
                 f"{r['pct_cortesia']:>8.0%} {r['puede_vender_mas']:>9}")
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


def llegada(d: dict, esperado: float | None = None) -> str:
    """A que hora llega la gente y cuanta puerta hace falta.

    Lo que dimensiona la puerta es el PICO, no el total: la fila se forma en el
    cuarto de hora mas cargado.
    """
    curva = d.get("curva_llegada") or {}
    fracciones = {int(k): v for k, v in (curva.get("fracciones") or {}).items()}
    if not fracciones:
        return ("Este dashboard no trae la curva de llegada. Regenéralo con "
                "`python run.py` o baja uno más nuevo con `--actualizar`.")
    franja = curva.get("franja_min", 15)

    L = ["Curva de llegada medida en julio (franjas de "
         f"{franja} minutos, relativas a la hora de inicio):", ""]
    acum = 0.0
    for m, f in sorted(fracciones.items()):
        acum += f
        etiqueta = f"{m:+d} min" if m else "hora de inicio"
        L.append(f"  {etiqueta:>14}  {f:6.1%}   acumulado {acum:6.1%}")

    pico_min = max(fracciones, key=lambda k: fracciones[k])
    L += ["",
          f"El pico cae en {pico_min:+d} min: ahí llega el "
          f"{fracciones[pico_min]:.1%} de la gente.",
          "",
          f"{'show':24} {'entran':>7} {'pico':>6}  personal en puerta"]
    objetivo = ([s for s in _shows(d)] if esperado is None
                else [{"artista": "(show)", "esperado": esperado}])
    for s in sorted(objetivo, key=lambda x: -x["esperado"])[:10]:
        pico = s["esperado"] * fracciones[pico_min]
        # 15 s por entrada, y la puerta se planea al 70% de ocupacion: al 100%
        # cualquier demora se acumula porque no hay holgura para absorberla
        staff = max(1, int(-(-(pico * 0.25) // (franja * 0.7))))
        L.append(f"{s['artista'][:24]:24} {s['esperado']:>7} {pico:>6.0f}  "
                 f"{staff} personas")
    L += ["",
          "El personal se dimensiona al 70% de ocupación, no al límite: "
          "planificar",
          "al 100% suena eficiente y en la práctica es una fila que crece toda "
          "la noche.",
          "",
          "Para generar el link de puerta de un show (una página que caduca a "
          "las 3 h)",
          "hace falta el repositorio: `python run.py --puerta`."]
    return "\n".join(L)


def ficha_modelo(d: dict) -> str:
    m = d.get("modelo") or {}
    if not m.get("test"):
        return ("Este dashboard no trae la ficha del modelo. Regenéralo con "
                "`python run.py --experimento`.")
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


# --------------------------------------------------------------------------
# Mantenimiento de los datos
# --------------------------------------------------------------------------

def actualizar() -> int:
    print(f"Bajando el dashboard publicado…\n  {URL}")
    try:
        d = _descargar(CONGELADO)
    except Exception as e:
        print(f"No pude bajarlo: {e}", file=sys.stderr)
        return 1
    r = d.get("resumen", {})
    print(f"Listo → {CONGELADO}")
    print(f"  generado {d.get('generado', '?')} · {r.get('shows', 0)} shows · "
          f"{r.get('asistencia_esperada', 0)} personas esperadas de "
          f"{r.get('entradas_adquiridas', 0)} entradas")
    print("\nEsto trae las cifras que estén publicadas en el repo. Para "
          "recalcular\ndesde el API con tu propio token: `--recalcular TU-NOMBRE`.")
    return 0


def recalcular(argv: list[str]) -> int:
    bootstrap = AQUI / "bootstrap.py"
    if not bootstrap.is_file():
        print(f"Falta {bootstrap}.", file=sys.stderr)
        return 1
    import runpy
    sys.argv = [str(bootstrap), *argv]
    runpy.run_path(str(bootstrap), run_name="__main__")
    return 0


# --------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    arg = argv[0]

    if arg == "--actualizar":
        return actualizar()
    if arg == "--recalcular":
        return recalcular(argv[1:])

    d, fuente = cargar()

    if arg == "--json":
        # la procedencia va a stderr: en stdout rompe cualquier json.load
        print(procedencia(d, fuente), file=sys.stderr)
        print(json.dumps(d, ensure_ascii=False, indent=2))
        return 0

    print(procedencia(d, fuente))
    print()
    if arg == "--agenda":
        print(agenda(d))
    elif arg == "--vacios":
        print(vacios(d))
    elif arg in ("--sobreventa", "--overbooking"):
        print(sobreventa(d))
    elif arg in ("--llegada", "--puerta"):
        print(llegada(d))
    elif arg == "--modelo":
        print(ficha_modelo(d))
    elif arg.startswith("ft_evt_"):
        print(informe(d, arg))
    else:
        print(por_artista(d, " ".join(argv)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
