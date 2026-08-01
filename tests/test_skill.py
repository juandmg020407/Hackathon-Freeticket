"""La skill tiene que responder fuera del repositorio.

Instalada suelta no hay CSV, ni raw/, ni token, ni pandas: solo el script y su
copia de dashboard.json. Estas pruebas fallan ruidosamente si algo vuelve a
atarla al repo o si la copia congelada se queda atras.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / ".claude" / "skills" / "aforo-freeticket"
SCRIPT = SKILL / "scripts" / "aforo.py"
CONGELADO = SKILL / "data" / "dashboard.json"
FRESCO = ROOT / "outputs" / "dashboard.json"


def _json(ruta: Path) -> dict:
    return json.loads(ruta.read_text(encoding="utf-8"))


def _correr(args: list[str], cwd: Path, **env_extra) -> subprocess.CompletedProcess:
    """Ejecuta el script aislado.

    stdin=DEVNULL porque bajo pytest el stdin capturado no tiene un handle que
    Windows pueda heredar, y subprocess revienta antes de arrancar el proceso.
    """
    env = {k: v for k, v in os.environ.items() if k != "FT_DASHBOARD"}
    env["PYTHONIOENCODING"] = "utf-8"
    env.update(env_extra)
    return subprocess.run(
        [sys.executable, *args], capture_output=True, text=True,
        encoding="utf-8", cwd=str(cwd), env=env, stdin=subprocess.DEVNULL,
    )


def test_la_skill_trae_sus_datos():
    assert CONGELADO.is_file(), (
        "Falta data/dashboard.json: sin el, la skill instalada no responde nada."
    )


def test_congelado_al_dia_con_outputs():
    """run.py sincroniza los dos. Si divergen, la skill miente sobre el repo."""
    if not FRESCO.is_file():
        pytest.skip("no hay outputs/dashboard.json; corre python run.py")
    assert _json(CONGELADO) == _json(FRESCO), (
        "La copia de la skill no coincide con outputs/. Corre `python run.py` "
        "(el paso [6/6] las sincroniza)."
    )


def test_dashboard_completo():
    d = _json(CONGELADO)
    for clave in ("resumen", "shows", "modelo", "sobreventa", "curva_llegada"):
        assert clave in d, f"al dashboard le falta «{clave}»"
    assert len(d["shows"]) == 30, "deberian ser los 30 shows de agosto"
    assert d["curva_llegada"].get("fracciones"), "la curva viene vacia"
    assert len(d["sobreventa"]) == len(d["shows"])


def test_un_show_trae_todo_lo_que_se_responde():
    s = _json(CONGELADO)["shows"][0]
    for campo in ("event_id", "titulo", "artista", "fecha", "ciudad", "venue",
                  "capacidad", "entradas_adquiridas", "cortesias", "pct_cortesia",
                  "esperado", "p10", "p90", "tasa_esperada", "palancas"):
        assert campo in s, f"a los shows les falta «{campo}»"
    assert s["p10"] <= s["esperado"] <= s["p90"]


def test_el_script_es_stdlib_pura():
    """Ni pandas ni numpy: instalada suelta no hay pip install que valga."""
    codigo = SCRIPT.read_text(encoding="utf-8")
    for prohibido in ("import pandas", "import numpy", "import scipy", "sklearn"):
        assert prohibido not in codigo, f"{prohibido} rompe la instalacion suelta"


def test_responde_sin_repositorio(tmp_path):
    """La prueba de fuego: copiar la skill a otro sitio y preguntar."""
    destino = tmp_path / "aforo-freeticket"
    destino.mkdir()
    (destino / "scripts").mkdir()
    (destino / "data").mkdir()
    (destino / "scripts" / "aforo.py").write_bytes(SCRIPT.read_bytes())
    (destino / "data" / "dashboard.json").write_bytes(CONGELADO.read_bytes())

    # una URL que no resuelve: si la respuesta dependiera de la red, se caeria
    r = _correr([str(destino / "scripts" / "aforo.py"), "--agenda"], tmp_path,
                FT_DASHBOARD_URL="https://no-existe.invalid/x.json")
    assert r.returncode == 0, r.stderr
    assert "Total agosto" in r.stdout
    assert "la copia que trae la skill" in r.stdout


def test_declara_de_cuando_son_los_datos():
    """Una cifra vieja presentada como viva es el error que no se permite."""
    r = _correr([str(SCRIPT), "ft_evt_0060"], ROOT)
    assert r.returncode == 0, r.stderr
    assert r.stdout.startswith("datos:")
    assert "generados" in r.stdout.splitlines()[0]


def test_json_sigue_siendo_parseable():
    """La procedencia va a stderr; en stdout romperia cualquier json.load."""
    r = _correr([str(SCRIPT), "--json"], ROOT)
    assert r.returncode == 0, r.stderr
    assert len(json.loads(r.stdout)["shows"]) == 30
    assert "datos:" in r.stderr
