# ¿Cuánta gente entra realmente?

Hackathon FreeTicket. Cruza los compradores de la tiquetera con los usuarios de
Boom y proyecta, para cada show de agosto, cuánta gente cruza la puerta.

**Respuesta corta:** de las 5.209 entradas ya adquiridas para agosto entran unas
**3.622 personas (69.5%)**. Julio cerró en 73.9%. La diferencia no es que se
venda peor: es que agosto trae 47.2% de cortesías contra 36.3% de julio, y una
cortesía entra al 38.7% mientras una entrada pagada entra al 94%.

## Correrlo

```bash
curl "https://hackathon-freeticket.vercel.app/api/setup?handle=TU-NOMBRE" -o setup.json
pip install numpy
python run.py
```

`run.py` descarga los ocho recursos (con caché en `raw/`), cruza las dos
plataformas y proyecta agosto. Tarda unos 9 segundos con los datos ya bajados.

| opción | qué hace |
|---|---|
| `python run.py` | pipeline completo |
| `python run.py --force` | vuelve a bajar los datos del API |
| `python run.py --puerta` | genera además los links de puerta |

El token se lee de `setup.json`, de `.ft-hack.json` o de `FT_HACK_TOKEN`.

## Qué produce

| archivo | contenido |
|---|---|
| `matches.csv` | `sale_id, boom_user_id, confidence` — 3.963 de 6.383 ventas cruzadas |
| `forecast.csv` | `event_id, expected_attendance, p10, p90` — los 30 shows de agosto |
| `NOTAS.md` | supuestos, qué señal pesó más, qué falta |
| `matches_detalle.csv` | la evidencia de cada cruce (email/teléfono/nombre), para auditar |
| `forecast_detalle.csv` | mezcla de tipos y compradores en Boom de cada show |
| `puerta/*.html` | un link por show para quien abre la puerta |

## Cómo funciona

**El cruce** (`ft/match.py`). No hay id compartido y las llaves están sucias a
propósito. Solo el email y el teléfono anclan un match — en Boom son únicos —,
mientras el nombre apenas confirma o desmiente: 1.144 nombres se repiten en
Boom. Un correo correcto con un nombre ajeno es el correo de la pareja, y ese
match no se acepta. Ante la duda queda vacío: 37.9% de los compradores
simplemente no está en Boom, e inventarles un match sale más caro.

**La proyección** (`ft/model.py`, `ft/forecast.py`). Una probabilidad por
entrada, sumadas por show. Son dos modelos, no uno, porque son dos fenómenos:

- **Entrada pagada** → entra al 94% y da igual quién la compró.
- **Cortesía** → entra al 38.7% y ahí sí manda quién la recibió: su use_rate en
  Boom (calculado por tipo de entrada, que el crudo se queda corto), si vive en
  la ciudad del show y por qué canal la recibió.

El efecto de cada acto sale de sus shows de julio, encogido hacia el promedio
según cuántos haya. Un acto de gira sin julio propio no lleva ajuste y para él
solo habla Boom.

**Los intervalos** salen de simular cada show 20.000 veces, con dos fuentes de
ruido separadas: el azar de la puerta y lo que el modelo no sabe de cada noche.

## Qué tan bien predice

Dejando cada evento de julio fuera y reentrenando sin él:

| método | error medio por evento |
|---|---|
| "vendieron 500, entran 500" | 54.8 personas |
| tasa global de julio | 24.6 |
| solo la mezcla de tipos | 7.5 |
| **este modelo** | **6.2** |

El intervalo p10–p90 cubre el 81% de los eventos de julio, con 80% de objetivo.

## Extras

**Link de puerta** (`python run.py --puerta`). Una página por show, un solo
archivo sin dependencias, pensada para el celular de quien está en la entrada:
cuánta gente se espera, el rango, cuántas personas conviene poner y a qué hora
llega la gente. Caduca sola a las 3 horas — la caducidad va dentro del archivo,
así que sigue venciendo aunque se sirva desde cualquier estático.

**Curva de llegada** (`python -m ft.llegada`). Medida en julio: el 27.6% ya
entró 45 minutos antes, el 66.6% al cuarto de hora previo y el pico cae entre
-45 y -30 minutos. Lo que dimensiona la puerta es ese pico, no el total.

## Estructura

```
run.py              pipeline de punta a punta
ft/api.py           cliente del API (una petición toca una plataforma)
ft/fetch.py         descarga y caché de los ocho recursos
ft/normalize.py     email, teléfono y nombre sucios -> comparables
ft/match.py         el cruce y su evidencia
ft/features.py      una fila por entrada, con corte temporal del historial
ft/model.py         las dos logísticas y la validación dejando un evento fuera
ft/forecast.py      simulación e intervalos
ft/llegada.py       curva de llegada
ft/puerta.py        el link efímero
```
