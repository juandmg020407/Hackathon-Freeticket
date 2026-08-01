"""Link de puerta: lo que abre en el celular quien está en la entrada.

Quien está en la puerta el viernes no va a abrir un notebook. Esto genera una
página por show —aforo esperado, rango, personal sugerido y curva de llegada—
más un índice para navegarlas. Un archivo por show, sin dependencias, sin
servidor: se publica en cualquier estático o se manda tal cual.

LA VIGENCIA VA ANCLADA AL SHOW, NO A LA GENERACIÓN
--------------------------------------------------
El brief pide un link que caduque solo a las 3 horas. Contar esas 3 horas desde
que se genera el archivo obliga a generarlo justo antes de abrir puertas, y
cualquier link enviado con antelación llega muerto. Anclarlo al show resuelve
las dos cosas: se puede mandar el lunes para el viernes, y sigue caducando solo.

Tres estados, y la página los distingue sola:

  ANTES     hasta 6 h antes del show: informa el aforo y avisa que aún vende
  PUERTA    de 6 h antes a 3 h después: modo operativo, lo que se usa esa noche
  VENCIDO   pasadas 3 h del inicio: el show ya pasó y la cifra no vale nada
"""

from __future__ import annotations

import csv
import html
from datetime import datetime, timedelta, timezone

from .api import OUTPUTS, ROOT
from .fetch import load
from .llegada import curva_julio, personal_sugerido

HORAS_ANTES = 6      # cuándo entra en modo puerta
HORAS_DESPUES = 3    # cuándo caduca, contadas desde el inicio del show
SALIDA = ROOT / "site"

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

CSS = """
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body { margin:0; background:#0e0f13; color:#f2f3f5;
         font:16px/1.5 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;
         padding:20px 16px 48px; }
  a { color:inherit; }
  .wrap { max-width:560px; margin:0 auto; }
  .kicker { font-size:12px; letter-spacing:.14em; text-transform:uppercase;
            color:#8b93a7; }
  h1 { font-size:23px; line-height:1.25; margin:6px 0 2px; text-wrap:balance; }
  .cuando { color:#a7aec2; font-size:14px; margin-bottom:22px; }
  .card { background:#171a21; border:1px solid #262b36; border-radius:14px;
          padding:20px; margin-bottom:14px; }
  .cifra { font-size:68px; font-weight:700; line-height:1; letter-spacing:-.03em;
           font-variant-numeric:tabular-nums; }
  .cifra small { font-size:16px; font-weight:500; color:#a7aec2; letter-spacing:0; }
  .rango { color:#a7aec2; font-size:15px; margin-top:10px; }
  .rango b { color:#f2f3f5; font-variant-numeric:tabular-nums; }
  .grid { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
  .grid .card { margin:0; padding:16px; }
  .lbl { font-size:12px; color:#8b93a7; text-transform:uppercase;
         letter-spacing:.08em; margin-bottom:6px; }
  .val { font-size:27px; font-weight:650; font-variant-numeric:tabular-nums; }
  .val small { font-size:13px; color:#a7aec2; font-weight:500; }
  .barra { display:flex; align-items:flex-end; gap:5px; height:88px; margin:14px 0 6px; }
  .barra div { flex:1; background:#3b6ef5; border-radius:4px 4px 0 0; min-height:3px; }
  .barra div.pico { background:#f5a03b; }
  .ejes { display:flex; gap:5px; font-size:10px; color:#8b93a7; }
  .ejes span { flex:1; text-align:center; }
  .nota { color:#8b93a7; font-size:13px; margin-top:16px; }
  .aviso { background:#1d1608; border-color:#4a3a12; color:#f0c987; }
  .previo { background:#0f1720; border-color:#1e3549; color:#8fc3f0; }
  .pill { display:inline-block; padding:3px 11px; border-radius:999px;
          font-size:11px; font-weight:650; letter-spacing:.06em;
          text-transform:uppercase; }
  .pill.vivo { background:#123524; color:#5ddc9a; }
  .pill.previo { background:#0f2436; color:#6fb6ef; }
  #vencido { display:none; text-align:center; padding:64px 20px; }
  #vencido .cifra { font-size:40px; }
  table { width:100%; border-collapse:collapse; font-size:14px; }
  th { text-align:left; font-size:11px; text-transform:uppercase; color:#8b93a7;
       letter-spacing:.08em; padding:0 8px 8px 0; font-weight:600; }
  td { padding:11px 8px 11px 0; border-top:1px solid #21262f;
       font-variant-numeric:tabular-nums; }
  td.show { font-weight:600; }
  .fecha { color:#a7aec2; font-size:12px; }
  .tabla-scroll { overflow-x:auto; }
"""

PLANTILLA = """<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Puerta · {titulo}</title>
<style>{css}</style>
<div class="wrap" id="vivo">
  <div class="kicker">Aforo estimado · puerta</div>
  <h1>{titulo}</h1>
  <div class="cuando">{cuando} · {venue}</div>

  <div class="card">
    <div class="lbl">Esperamos que entren</div>
    <div class="cifra">{esperado} <small>de {vendidas} entradas</small></div>
    <div class="rango">Entre <b>{p10}</b> y <b>{p90}</b> personas · 8 de cada 10 noches</div>
  </div>

  <div class="grid">
    <div class="card">
      <div class="lbl">Gente en puerta</div>
      <div class="val">{staff} <small>{staff_unidad}</small></div>
    </div>
    <div class="card">
      <div class="lbl">Momento más cargado</div>
      <div class="val">{franja_pico}</div>
    </div>
  </div>

  <div class="card">
    <div class="lbl">Cómo llega la gente</div>
    <div class="barra">{barras}</div>
    <div class="ejes">{ejes}</div>
    <div class="nota">Pico de <b>{pico}</b> personas en 15 minutos.</div>
  </div>

  {aviso}

  <div class="nota"><a href="index.html">← todos los shows</a> · el link caduca
  solo {caduca}.</div>
</div>

<div id="vencido" class="wrap">
  <div class="cifra">Link vencido</div>
  <p class="nota">Este aforo se calculó para {titulo} y ya pasó.<br>
     <a href="index.html">Ver los shows que vienen</a></p>
</div>

<script>
  var abre = {abre_ms}, cierra = {cierra_ms};
  function revisar() {{
    var t = Date.now();
    document.getElementById('vencido').style.display = t > cierra ? 'block' : 'none';
    document.getElementById('vivo').style.display = t > cierra ? 'none' : 'block';
    var p = document.getElementById('estado');
    if (p) {{
      var vivo = t >= abre && t <= cierra;
      p.className = 'pill ' + (vivo ? 'vivo' : 'previo');
      p.textContent = vivo ? 'en puerta' : 'faltan ' +
        Math.ceil((abre - t) / 86400000) + ' días';
    }}
  }}
  revisar();
  setInterval(revisar, 30000);
</script>
"""

INDICE = """<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Aforo · shows de agosto</title>
<style>{css}</style>
<div class="wrap">
  <div class="kicker">FreeTicket · aforo estimado</div>
  <h1>¿Cuánta gente entra realmente?</h1>
  <div class="cuando">{n} shows de agosto · {vendidas} entradas adquiridas ·
    esperamos {total} personas ({tasa})</div>

  <div class="card previo" style="margin-bottom:20px">
    Lo que manda no es cuántas entradas, es cuáles. Una entrada pagada entra al
    <b>94%</b>; una cortesía, al <b>39%</b>. Por eso hay shows con más entradas
    vendidas y menos gente en la sala.
  </div>

  <div class="card">
    <div class="tabla-scroll">
    <table>
      <thead><tr>
        <th>Show</th><th style="text-align:right">Entradas</th>
        <th style="text-align:right">Entran</th><th style="text-align:right">Rango</th>
        <th style="text-align:right">Cortesía</th>
      </tr></thead>
      <tbody>{filas}</tbody>
    </table>
    </div>
  </div>

  <div class="nota">
    Cada show abre su página de puerta, que entra en modo operativo 6 h antes y
    caduca 3 h después del inicio.<br>
    Generado el {generado}. Método y código en
    <a href="https://github.com/juandmg020407/Hackathon-Freeticket">GitHub</a>.
  </div>
</div>
"""


def _fecha_larga(d: datetime) -> str:
    return f"{DIAS[d.weekday()]} {d.day} de {MESES[d.month - 1]}, {d:%H:%M}"


def _cargar_pronostico() -> dict:
    ruta = OUTPUTS / "forecast_detalle.csv"
    if not ruta.exists():
        raise SystemExit("Falta forecast_detalle.csv: corre antes 'python run.py'.")
    return {r["event_id"]: r for r in csv.DictReader(ruta.open(encoding="utf-8"))}


def generar(event_id: str | None = None, ahora: datetime | None = None) -> list:
    ahora = ahora or datetime.now(timezone.utc)
    eventos = {e["event_id"]: e for e in load("freeticket", "events")}
    pron = _cargar_pronostico()
    curva = curva_julio()
    objetivo = [event_id] if event_id else sorted(pron)
    SALIDA.mkdir(exist_ok=True)
    escritos = []

    for eid in objetivo:
        if eid not in pron:
            raise SystemExit(f"{eid} no está en el pronóstico (solo hay eventos de agosto).")
        r, e = pron[eid], eventos[eid]
        inicio = datetime.fromisoformat(e["starts_at"])
        abre = inicio - timedelta(hours=HORAS_ANTES)
        cierra = inicio + timedelta(hours=HORAS_DESPUES)

        esperado = int(r["expected_attendance"])
        s = personal_sugerido(esperado, curva)
        maximo = max((f["personas"] for f in s["filas"]), default=1) or 1
        barras = "".join(
            f'<div class="{"pico" if f["etiqueta"] == s["franja_pico"] else ""}"'
            f' style="height:{max(3, round(100 * f["personas"] / maximo))}%"'
            f' title="{f["personas"]:.0f} personas"></div>'
            for f in s["filas"]
        )
        ejes = "".join(
            f"<span>{f['minuto']:+d}</span>" if f["minuto"] else "<span>inicio</span>"
            for f in s["filas"]
        )

        vendidas = int(r["tickets_adquiridos"])
        pct_cort = float(r["pct_cortesia"])
        aviso = ""
        if pct_cort >= 0.5:
            aviso = (f'<div class="card aviso"><b>Ojo con la mezcla.</b> '
                     f'{pct_cort:.0%} de las entradas son cortesía, y de esas suele '
                     f'entrar menos de la mitad. Por eso {esperado} y no {vendidas}.</div>')
        elif ahora < abre:
            dias = max(0, (inicio - ahora).days)
            aviso = (f'<div class="card previo"><b>Faltan {dias} días.</b> '
                     f'Este show sigue vendiendo, así que la cifra cubre solo las '
                     f'{vendidas} entradas ya adquiridas.</div>')

        pagina = PLANTILLA.format(
            css=CSS,
            titulo=html.escape(e["title"]),
            cuando=_fecha_larga(inicio),
            venue=html.escape(e["venue"]),
            esperado=esperado, vendidas=vendidas,
            p10=r["p10"], p90=r["p90"],
            staff=s["staff"],
            staff_unidad="persona" if s["staff"] == 1 else "personas",
            franja_pico=html.escape(str(s["franja_pico"])),
            pico=f"{s['pico']:.0f}",
            barras=barras, ejes=ejes, aviso=aviso,
            caduca=f"el {inicio.day} de {MESES[inicio.month - 1]} a las "
                   f"{cierra:%H:%M}",
            abre_ms=int(abre.timestamp() * 1000),
            cierra_ms=int(cierra.timestamp() * 1000),
        )
        (SALIDA / f"{eid}.html").write_text(pagina, encoding="utf-8")
        escritos.append(SALIDA / f"{eid}.html")

    if not event_id:
        escritos.append(generar_indice(pron, eventos, ahora))
    print(f"Sitio de puerta: {len(escritos)} páginas en {SALIDA.name}/")
    return escritos


def generar_indice(pron: dict, eventos: dict, ahora: datetime):
    filas = []
    orden = sorted(pron.values(), key=lambda r: eventos[r["event_id"]]["starts_at"])
    for r in orden:
        e = eventos[r["event_id"]]
        d = datetime.fromisoformat(e["starts_at"])
        filas.append(
            f'<tr><td class="show"><a href="{r["event_id"]}.html">'
            f'{html.escape(r["artist_name"])}</a>'
            f'<div class="fecha">{DIAS[d.weekday()][:3]} {d.day} '
            f'{MESES[d.month - 1][:3]} · {d:%H:%M} · {html.escape(e["city"])}</div></td>'
            f'<td style="text-align:right">{r["tickets_adquiridos"]}</td>'
            f'<td style="text-align:right"><b>{r["expected_attendance"]}</b></td>'
            f'<td style="text-align:right">{r["p10"]}–{r["p90"]}</td>'
            f'<td style="text-align:right">{float(r["pct_cortesia"]):.0%}</td></tr>'
        )
    total = sum(int(r["expected_attendance"]) for r in pron.values())
    vendidas = sum(int(r["tickets_adquiridos"]) for r in pron.values())
    pagina = INDICE.format(
        css=CSS, filas="".join(filas), n=len(pron),
        vendidas=f"{vendidas:,}".replace(",", "."),
        total=f"{total:,}".replace(",", "."),
        tasa=f"{total / vendidas:.0%}",
        generado=f"{ahora.day} de {MESES[ahora.month - 1]} de {ahora.year}",
    )
    destino = SALIDA / "index.html"
    destino.write_text(pagina, encoding="utf-8")
    return destino


if __name__ == "__main__":
    import sys

    generar(sys.argv[1] if len(sys.argv) > 1 else None)
