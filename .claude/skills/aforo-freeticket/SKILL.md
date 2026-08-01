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

Las rutas son relativas a esta carpeta (la de la skill), y funcionan igual
dentro del repositorio que instalada suelta:

```bash
python scripts/aforo.py "Sin Filtro"      # todos los shows de ese acto
python scripts/aforo.py ft_evt_0060       # un show por id
python scripts/aforo.py --agenda          # los 30 shows de agosto, en orden
python scripts/aforo.py --vacios          # los que van a quedar más vacíos
python scripts/aforo.py --sobreventa      # cuántas entradas más caben sin riesgo
python scripts/aforo.py --llegada         # a qué hora llega la gente y cuánta puerta
python scripts/aforo.py --modelo          # qué tan bien predice y qué supone
python scripts/aforo.py --json            # todo estructurado, para graficar
```

No hace falta token, ni `pip install`, ni correr ningún pipeline: el script es
stdlib pura y lee un solo archivo, `data/dashboard.json`. Dentro del repositorio
`python -m ft.consulta …` hace exactamente lo mismo.

Prefiere estos comandos antes que escribir tu propio script sobre los CSV: ya
resuelven los cruces y los formatos, y en PowerShell un `python -c` con
f-strings se rompe porque el shell se come las llaves.

La salida ya viene estructurada en tres bloques —el veredicto, el **porqué** y
**qué puedes hacer**— para que la reformules en el tono de la conversación. No
la pegues cruda si la pregunta era concreta: si preguntan "¿cuánta gente
entra?", responde el número y el rango, y ofrece el resto.

## De cuándo son las cifras

Cada salida abre con una línea de procedencia: de dónde salieron los datos y
cuándo se generaron. **Trasládala cuando importe**, sobre todo si el aviso dice
que están viejos: los shows siguen vendiendo, así que un dashboard de hace dos
semanas ya no refleja lo adquirido hoy.

Hay dos formas de refrescar, y **no son lo mismo**:

- `python scripts/aforo.py --actualizar` baja el dashboard **publicado** en el
  repositorio. Segundos, sin dependencias. Es el que debes sugerir.
- `python scripts/aforo.py --recalcular TU-NOMBRE` vuelve a bajar los datos
  crudos del API y **recalcula** el pronóstico entero. Refleja lo vendido hasta
  hoy, pero clona el repositorio, instala numpy/pandas/scipy/sklearn y tarda
  ~60 s. **No lo ejecutes por tu cuenta**: menciónalo y deja que el usuario
  decida, porque instala paquetes y escribe un token en su disco.

## Las tres palancas, y cuánto creerles

Cuando un show va flojo, `aforo.py` lista acciones ordenadas por impacto.
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

`python scripts/aforo.py --json` devuelve los 30 shows con aforo, rango, mezcla,
llenado, asientos libres y palancas, más la sobreventa segura, la curva de
llegada y la ficha del modelo. **Úsalo como fuente y no transcribas cifras a
mano.** (Es el mismo contenido de `data/dashboard.json`, así que también puedes
leer ese archivo directamente.)

Al construir la visualización:

- **El aforo esperado va con su rango**, no solo el punto. Una barra sin p10–p90
  esconde justo lo que hace útil el pronóstico.
- **Contrasta entradas contra personas.** Es la tesis entera: hay shows con más
  entradas y menos gente. Una barra de "vendidas" junto a una de "esperadas"
  cuenta la historia sin explicarla.
- **Colorea por proporción de cortesía**, que es lo que explica la diferencia.
- No inventes series que el JSON no trae (histórico de ventas, ingresos por
  show, comparación con años anteriores): esos datos no existen aquí.

## El techo de venta no es la capacidad

Si de cada entrada entra el 64%, vender justo hasta el aforo deja la sala a dos
tercios. El límite real es **el riesgo de que no quepan**, y eso se calcula:
`--sobreventa` dice cuántas entradas más admite cada show con un 5% de riesgo de
desborde.

Lo contraintuitivo, y conviene explicarlo cuando salga: los shows con **más
cortesías admiten más sobreventa**, porque su tasa de asistencia es más baja. La
cortesía no es papel gratis, es inventario que consume cupo de riesgo.

Al presentarlo, di siempre el riesgo asumido (5% por show) y el supuesto: que
las próximas entradas se parezcan a las ya vendidas.

## Preguntas frecuentes y dónde está la respuesta

Todos son `python scripts/aforo.py …` salvo donde se diga otra cosa:

| pregunta | comando |
|---|---|
| ¿cuánta gente entra al show del viernes? | `<artista o id>` |
| ¿cuántos vienen en total en agosto? | `--agenda` |
| ¿cuáles van a quedar vacíos? | `--vacios` |
| ¿puedo vender más entradas? | `--sobreventa` |
| ¿a qué hora llega la gente y cuánta puerta pongo? | `--llegada` |
| ¿qué tan confiable es esto? | `--modelo` |
| hazme un tablero / gráfico | `--json` y construye desde ahí |
| ¿estos datos están al día? | la línea de procedencia; refresca con `--actualizar` |
| dame el link de puerta del show | está publicado: `juandmg020407.github.io/Hackathon-Freeticket/<event_id>.html` · regenerarlo pide el repositorio (`python run.py --puerta`) |
| ¿a quién invito? | la palanca "invitar"; el detalle **por persona** solo existe en el repositorio (`python -m ft.prescribe`) |

Las dos últimas son las únicas que no se responden desde una instalación suelta:
una necesita el repositorio y la otra ya está publicada como página. Dilo en vez
de improvisar un nombre o un número.

## Lo que esta skill NO puede responder

Dilo claramente en vez de improvisar:

- **Shows de julio.** Ya pasaron: su asistencia es un dato, no una predicción.
- **Aforo final de un show que sigue vendiendo.** Solo se proyectan las entradas
  **ya adquiridas** a la fecha que dice la línea de procedencia. Para los shows
  de fin de mes hay que recalcular cerca de la fecha (`--recalcular`).
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

Un comando, en cualquier agente (Claude Code, Codex, Cursor, Copilot y ~30 más):

```bash
npx skills add juandmg020407/Hackathon-Freeticket -g
```

O como plugin nativo de Claude Code:

```
/plugin marketplace add juandmg020407/Hackathon-Freeticket
/plugin install aforo-freeticket@freeticket-hackathon
```

No hace falta nada más: **ni clonar, ni `pip install`, ni token, ni pipeline.**
La skill trae sus propios datos en `data/dashboard.json` y el script que los lee
es stdlib pura. Funciona sin conexión.

Si además tienes el repositorio abierto, los comandos detectan
`outputs/dashboard.json` y usan el dato recién calculado en vez de la copia
congelada — la línea de procedencia dice cuál está usando.
