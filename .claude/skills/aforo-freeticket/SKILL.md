---
name: aforo-freeticket
description: Responde cuánta gente va a entrar realmente a un show y qué hacer para llenarlo. Úsala cuando pregunten por el aforo, la asistencia esperada, cuánta gente entra, si un show va a llenar, cuánto personal poner en la puerta, a quién invitar, qué hacer con un show flojo, o cuántas cortesías repartir. También cuando mencionen forecast de asistencia, no-show, tasa de check-in, cortesías vs entradas pagadas, el cruce de compradores con Boom, o pidan explicar por qué un show con muchas entradas vendidas va a meter poca gente.
---

# Aforo FreeTicket

Se venden 500 entradas a un show. ¿Entran 500, 380 o 240? Esta skill responde
eso para los shows de agosto de 2026, explica **por qué**, y dice **qué hacer**
si el show va flojo.

## Lo primero que hay que entender

**Lo que manda no es cuántas entradas, es cuáles.** Medido sobre julio:

| tipo de entrada | entra |
|---|---|
| General / Preferencial / VIP | **~94%** |
| Cortesía | **~39%** |

Un show que "vendió" 500 con la mitad en cortesías no llena. El caso de libro
está en los datos: **Sin Filtro** tiene dos shows en agosto. Uno con 424
entradas casi todas pagadas mete ~367 personas. Otro con **623 entradas 100%
cortesía mete ~238**. Doscientas entradas más, 129 personas menos.

(Estas dos cifras son ilustrativas y pueden moverse al reejecutar el pipeline.
Para responder, saca siempre el número del comando, no de aquí.)

Si alguien pregunta "¿cómo va la venta?", la respuesta útil no es el total
vendido: es el aforo esperado y la mezcla que lo explica.

## Cómo responder

Todo sale de comandos. **Nunca inventes una cifra**: si el comando no la da, no
existe.

```bash
python -m ft.consulta "Sin Filtro"      # todos los shows de ese acto
python -m ft.consulta ft_evt_0060       # un show por id
python -m ft.consulta --agenda          # los 30 shows de agosto, en orden
python -m ft.consulta --vacios          # los que van a quedar más vacíos
python -m ft.consulta --modelo          # qué tan bien predice y qué supone
python -m ft.consulta --json            # todo estructurado, para graficar
```

Prefiere estos comandos antes que escribir tu propio script sobre los CSV: ya
resuelven los cruces y los formatos, y en PowerShell un `python -c` con
f-strings se rompe porque el shell se come las llaves.

La salida ya viene estructurada en tres bloques —el veredicto, el **porqué** y
**qué puedes hacer**— para que la reformules en el tono de la conversación. No
la pegues cruda si la pregunta era concreta: si preguntan "¿cuánta gente
entra?", responde el número y el rango, y ofrece el resto.

Si falta el pronóstico, el comando lo dice: hay que correr `python run.py`
antes. No lo estimes tú.

## Las tres palancas, y cuánto creerles

Cuando un show va flojo, `ft.consulta` lista acciones ordenadas por impacto.
Cada una viene con la **fuerza de su supuesto**, y eso hay que trasladarlo al
usuario:

| palanca | supuesto | cómo presentarla |
|---|---|---|
| **Invitar** fieles de Boom sin entrada | **fuerte** | es una predicción sobre personas concretas con historial propio; se puede afirmar |
| **Convertir** cortesías en pagadas | medio | la brecha es real, pero parte es que quien paga ya venía decidido |
| **Mover** cortesías de RRPP a taquilla | **débil** | es un techo optimista: el canal probablemente *selecciona* en vez de causar |

**Esto no es letra pequeña.** Los datos son observacionales: nadie asignó
canales al azar. Presentar "mueve el canal y ganas 10 personas" como una promesa
sería engañar. Di "lo que se observó", no "lo que va a pasar".

## Si piden un tablero, un gráfico o un artifact

`python -m ft.consulta --json` devuelve los 30 shows con aforo, rango, mezcla,
llenado, asientos libres y palancas, más la ficha del modelo. También lo deja en
`outputs/dashboard.json`. **Úsalo como fuente y no transcribas cifras a mano.**

Al construir la visualización:

- **El aforo esperado va con su rango**, no solo el punto. Una barra sin p10–p90
  esconde justo lo que hace útil el pronóstico.
- **Contrasta entradas contra personas.** Es la tesis entera: hay shows con más
  entradas y menos gente. Una barra de "vendidas" junto a una de "esperadas"
  cuenta la historia sin explicarla.
- **Colorea por proporción de cortesía**, que es lo que explica la diferencia.
- No inventes series que el JSON no trae (histórico de ventas, ingresos por
  show, comparación con años anteriores): esos datos no existen aquí.

## Preguntas frecuentes y dónde está la respuesta

| pregunta | comando |
|---|---|
| ¿cuánta gente entra al show del viernes? | `ft.consulta <artista o id>` |
| ¿cuántos vienen en total en agosto? | `ft.consulta --agenda` |
| ¿cuáles van a quedar vacíos? | `ft.consulta --vacios` |
| ¿cuánta gente pongo en la puerta? | `python -m ft.puerta <event_id>` genera la página |
| ¿a qué hora llega la gente? | `python -m ft.llegada` |
| ¿qué tan confiable es esto? | `ft.consulta --modelo` |
| ¿a quién invito? | la palanca "invitar"; el detalle por persona está en `ft.prescribe` |
| hazme un tablero / gráfico | `ft.consulta --json` y construye desde ahí |

## Lo que esta skill NO puede responder

Dilo claramente en vez de improvisar:

- **Shows de julio.** Ya pasaron: su asistencia es un dato, no una predicción.
- **Aforo final de un show que sigue vendiendo.** Solo se proyectan las entradas
  **ya adquiridas**. Para los shows de fin de mes hay que volver a correr el
  pipeline cerca de la fecha.
- **Qué pasa si subo el precio.** No hay experimento de precios en los datos.
- **Datos de una plataforma consultando la otra.** Una petición toca una sola
  plataforma; el cruce ya está hecho y vive en `outputs/matches.csv`.
- **Quién es una persona concreta.** Los `boom_user_id` son identificadores; no
  expongas correos ni teléfonos aunque estén en los datos crudos.

## Referencias

- [`references/modelo.md`](references/modelo.md) — cómo predice, con qué error y qué supone
- [`references/datos.md`](references/datos.md) — las dos plataformas, el cruce y el diccionario
- [`references/playbook.md`](references/playbook.md) — las palancas y cómo leerlas

## Instalación

```bash
git clone https://github.com/juandmg020407/Hackathon-Freeticket
cd Hackathon-Freeticket && pip install -r requirements.txt
curl "https://hackathon-freeticket.vercel.app/api/setup?handle=TU-NOMBRE" -o setup.json
python run.py
```

Esta skill vive en `.claude/skills/aforo-freeticket/`, así que Claude Code la
carga sola al abrir el proyecto. Para usarla desde cualquier carpeta, copia esa
carpeta a `~/.claude/skills/`.

Todos los comandos se ejecutan **desde la raíz del repositorio**, que es donde
están `outputs/` y `raw/`.
