"""Link efimero para la puerta.

Quien esta en la puerta el viernes no va a abrir un notebook. Esto genera una
pagina por show: aforo esperado, rango, personal sugerido y curva de llegada.
Un solo archivo sin dependencias — se sube a cualquier estatico y se manda por
WhatsApp. Caduca sola a las 3 horas: la caducidad va dentro del archivo, asi
que sigue caducando aunque el hosting no sepa de TTL.
"""

from __future__ import annotations

import csv
import html
import json
from datetime import datetime, timedelta, timezone

from .api import ROOT
from .fetch import load
from .llegada import curva_julio, personal_sugerido

VIGENCIA_HORAS = 3
SALIDA = ROOT / "puerta"

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def _fecha_larga(iso: str) -> str:
    d = datetime.fromisoformat(iso)
    return f"{DIAS[d.weekday()]} {d.day} de {MESES[d.month - 1]}, {d:%H:%M}"


PLANTILLA = """<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Puerta · {titulo}</title>
<style>
  :root {{ color-scheme: dark; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; background:#0e0f13; color:#f2f3f5;
         font:16px/1.5 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;
         padding:20px 16px 40px; }}
  .wrap {{ max-width:520px; margin:0 auto; }}
  .kicker {{ font-size:12px; letter-spacing:.14em; text-transform:uppercase;
             color:#8b93a7; }}
  h1 {{ font-size:23px; line-height:1.25; margin:6px 0 2px; }}
  .cuando {{ color:#a7aec2; font-size:14px; margin-bottom:22px; }}
  .card {{ background:#171a21; border:1px solid #262b36; border-radius:14px;
           padding:20px; margin-bottom:14px; }}
  .cifra {{ font-size:68px; font-weight:700; line-height:1; letter-spacing:-.03em;
            font-variant-numeric:tabular-nums; }}
  .cifra small {{ font-size:16px; font-weight:500; color:#a7aec2; letter-spacing:0; }}
  .rango {{ color:#a7aec2; font-size:15px; margin-top:10px; }}
  .rango b {{ color:#f2f3f5; font-variant-numeric:tabular-nums; }}
  .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:10px; }}
  .grid .card {{ margin:0; padding:16px; }}
  .lbl {{ font-size:12px; color:#8b93a7; text-transform:uppercase;
          letter-spacing:.08em; margin-bottom:6px; }}
  .val {{ font-size:27px; font-weight:650; font-variant-numeric:tabular-nums; }}
  .val small {{ font-size:13px; color:#a7aec2; font-weight:500; }}
  .barra {{ display:flex; align-items:flex-end; gap:5px; height:88px; margin:14px 0 6px; }}
  .barra div {{ flex:1; background:#3b6ef5; border-radius:4px 4px 0 0; min-height:3px; }}
  .barra div.pico {{ background:#f5a03b; }}
  .ejes {{ display:flex; gap:5px; font-size:10px; color:#8b93a7; }}
  .ejes span {{ flex:1; text-align:center; }}
  .nota {{ color:#8b93a7; font-size:13px; margin-top:16px; }}
  .aviso {{ background:#1d1608; border-color:#4a3a12; color:#f0c987; }}
  #caducado {{ display:none; text-align:center; padding:60px 20px; }}
  #caducado .cifra {{ font-size:40px; }}
</style>
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
      <div class="val">{staff} <small>personas</small></div>
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

  <div class="nota">Generado {generado} · caduca {caduca} (3 h).</div>
</div>

<div id="caducado" class="wrap">
  <div class="cifra">Link vencido</div>
  <p class="nota">Este aforo se calculó para {titulo} y ya no está vigente.<br>
     Pide uno nuevo antes de abrir puertas.</p>
</div>

<script>
  var expira = {expira_ms};
  function revisar() {{
    if (Date.now() > expira) {{
      document.getElementById('vivo').style.display = 'none';
      document.getElementById('caducado').style.display = 'block';
    }}
  }}
  revisar();
  setInterval(revisar, 30000);
</script>
"""


def generar(event_id: str | None = None, ahora: datetime | None = None) -> list:
    ahora = ahora or datetime.now(timezone.utc)
    expira = ahora + timedelta(hours=VIGENCIA_HORAS)

    eventos = {e["event_id"]: e for e in load("freeticket", "events")}
    ruta = ROOT / "forecast_detalle.csv"
    if not ruta.exists():
        raise SystemExit("Falta forecast_detalle.csv: corre antes 'python run.py'.")
    pron = {r["event_id"]: r for r in csv.DictReader(ruta.open(encoding="utf-8"))}

    curva = curva_julio()
    objetivo = [event_id] if event_id else sorted(pron)
    SALIDA.mkdir(exist_ok=True)
    escritos = []

    for eid in objetivo:
        if eid not in pron:
            raise SystemExit(f"{eid} no esta en el pronostico (solo hay eventos de agosto).")
        r, e = pron[eid], eventos[eid]
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

        pagina = PLANTILLA.format(
            titulo=html.escape(e["title"]),
            cuando=_fecha_larga(e["starts_at"]),
            venue=html.escape(e["venue"]),
            esperado=esperado,
            vendidas=vendidas,
            p10=r["p10"], p90=r["p90"],
            staff=s["staff"],
            franja_pico=html.escape(str(s["franja_pico"])),
            pico=f"{s['pico']:.0f}",
            barras=barras, ejes=ejes, aviso=aviso,
            generado=ahora.strftime("%d/%m %H:%M UTC"),
            caduca=expira.strftime("%H:%M UTC"),
            expira_ms=int(expira.timestamp() * 1000),
        )
        destino = SALIDA / f"{eid}.html"
        destino.write_text(pagina, encoding="utf-8")
        escritos.append(destino)

    print(f"Links de puerta: {len(escritos)} en {SALIDA.name}/ (vigencia {VIGENCIA_HORAS} h)")
    return escritos


if __name__ == "__main__":
    import sys

    generar(sys.argv[1] if len(sys.argv) > 1 else None)
