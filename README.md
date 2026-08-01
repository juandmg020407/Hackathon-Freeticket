# ¿Cuánta gente entra realmente?

**Hackathon FreeTicket.** Cruza los compradores de la tiquetera con los usuarios
de Boom —dos plataformas que hablan de la misma gente y nunca se han mirado— y
proyecta, para cada show de agosto, cuánta gente cruza la puerta. Después dice
**qué hacer** con los shows que van flojos.

El entregable no es un CSV: es una **skill** que responde en lenguaje natural.

---

## La respuesta corta

De las **5.209 entradas ya adquiridas** para los 30 shows de agosto entran unas
**3.326 personas (63.9%)**. Julio cerró en 73.9%.

La diferencia no es que se venda peor. Es que **agosto trae 47.2% de cortesías
contra 36.3% en julio**, y una cortesía entra al 38.7% mientras una entrada
pagada entra al 94%.

El caso que lo resume: **Sin Filtro** tiene dos shows en agosto.

| show | entradas | mezcla | entran |
|---|---|---|---|
| `ft_evt_0050` | 424 | 2% cortesía | **367 personas** |
| `ft_evt_0060` | 623 | 100% cortesía | **238 personas** |

**200 entradas más, 129 personas menos.** Quien mire `tickets_sold` dimensiona
mal el segundo show por más de 350 personas.

---

## Empezar en tres minutos

```bash
git clone https://github.com/juandmg020407/Hackathon-Freeticket
cd Hackathon-Freeticket
pip install -r requirements.txt

# token del API: instantáneo, sin registro ni aprobación
curl "https://hackathon-freeticket.vercel.app/api/setup?handle=TU-NOMBRE" -o setup.json

python run.py
```

`run.py` descarga los ocho recursos, cruza las dos plataformas, proyecta agosto
y calcula las acciones recomendadas. **Unos 60 segundos la primera vez** (hay que
bajar 60.000 filas) y ~14 s después, porque `raw/` queda cacheado.

| comando | qué hace |
|---|---|
| `python run.py` | pipeline completo |
| `python run.py --force` | vuelve a bajar los datos del API |
| `python run.py --experimento` | además compara los 8 modelos y reevalúa |
| `python run.py --puerta` | además genera los links de puerta |
| `python -m pytest tests -q` | 22 pruebas de las piezas frágiles |

El token se lee de `setup.json`, de `.ft-hack.json` o de `FT_HACK_TOKEN`.

---

## Usar la skill

Es la forma pensada para el día a día. **Abre el repo en Claude Code y pregunta
en español** — la skill se carga sola porque vive en
`.claude/skills/aforo-freeticket/`.

> **Tú:** ¿cómo va el Sin Filtro del 8 de agosto?
>
> **Claude:** Va flojo. Esperamos 238 personas de 623 entradas ya adquiridas
> (rango 206–271). Capacidad 800, así que sobran 562 asientos.
>
> El problema es la mezcla: el 100% de las entradas son cortesía, y la cortesía
> entra al 38.7% mientras la pagada entra al 94%. Vender más entradas de este
> tipo no significa meter más gente.
>
> Lo que más rinde aquí es convertir 100 cortesías en pagadas (+39 personas).
> Invitar no sirve: este show ya agotó su base local de fieles de Boom.

Preguntas que responde bien:

- *¿cuánta gente entra al show del viernes?*
- *¿cuáles shows de agosto van a quedar vacíos?*
- *¿a quién invito para llenar la residencia del jueves?*
- *¿cuánta gente pongo en la puerta y a qué hora llega?*
- *¿qué tan confiable es esta predicción?*
- *¿por qué este show vendió más y va a meter menos gente?*

Y lo que **no** responde, en vez de improvisar: shows de julio (ya pasaron, su
asistencia es un dato), elasticidad de precios (no hay experimento en los datos)
y datos personales de compradores.

### Para usarla desde cualquier carpeta

```bash
cp -r .claude/skills/aforo-freeticket ~/.claude/skills/
```

### Los comandos por debajo

La skill no adivina: ejecuta estos comandos y reformula la salida. Puedes usarlos
tú directamente desde la raíz del repo.

```bash
python -m ft.consulta "Sin Filtro"      # todos los shows de ese acto
python -m ft.consulta ft_evt_0060       # un show por id
python -m ft.consulta --agenda          # los 30 shows, en orden de fecha
python -m ft.consulta --vacios          # los que van a quedar más vacíos
python -m ft.consulta --sobreventa      # cuántas entradas más caben sin riesgo
python -m ft.consulta --modelo          # error, supuestos y dónde falla
python -m ft.consulta --json            # todo estructurado, para graficar
```

---

## Pedirle tableros y visualizaciones

`--json` existe para eso. Devuelve los 30 shows con aforo, rango p10–p90, mezcla,
llenado, asientos libres y palancas, más la ficha del modelo — y lo deja en
`outputs/dashboard.json`.

Con eso, en Claude Code puedes pedir directamente:

> *Con `python -m ft.consulta --json`, hazme un dashboard de agosto: entradas
> vendidas contra personas esperadas, coloreado por proporción de cortesía, con
> el rango p10–p90 en cada barra.*

> *Hazme un artifact con los 10 shows con más asientos libres y qué palanca
> conviene en cada uno.*

> *Grafica la relación entre proporción de cortesías y tasa de asistencia
> esperada.*

Tres cosas que conviene pedir siempre, y que la skill ya sabe:

1. **El rango, no solo el punto.** Una barra sin p10–p90 esconde justo lo que
   hace útil un pronóstico.
2. **Entradas contra personas**, lado a lado. Es la tesis entera.
3. **Color por proporción de cortesía**, que es lo que explica la diferencia.

La skill tiene instrucción de **no inventar series que el JSON no trae** —
histórico de ventas, ingresos, comparación interanual—: esos datos no existen
aquí.

---

## Qué produce

```
outputs/
├─ matches.csv           sale_id, boom_user_id, confidence     ← entrega del reto
├─ forecast.csv          event_id, expected_attendance, p10, p90 ← entrega del reto
├─ acciones.csv          las 3 palancas por show, con su impacto
├─ dashboard.json        todo junto, para graficar
├─ matches_detalle.csv   la evidencia de cada cruce, para auditar
└─ forecast_detalle.csv  mezcla y compradores en Boom de cada show

reports/
├─ metrics.json          todas las métricas del experimento
└─ figures/*.png         9 figuras del EDA y la evaluación

puerta/*.html            un link por show, caduca solo a las 3 h
```

---

## Cómo funciona

### 1. El cruce (`ft/match.py`)

No hay ID compartido y las llaves están sucias a propósito: correos con alias
`+algo` o dominio mal escrito, teléfonos en cinco formatos, nombres sin tildes o
con el apellido primero.

**Solo el email y el teléfono anclan un match** — en Boom son únicos, con cero
duplicados. El **nombre no puede**: 1.144 nombres se repiten y 885 los comparten
más de tres personas. El nombre solo confirma o **desmiente**, porque un correo
exacto con un nombre ajeno es el correo de la pareja.

**Resultado: 3.963 de 6.383 ventas (62.1%).** El 37.9% restante son compradores
nuevos y se dejan vacíos deliberadamente: inventarles un match contamina justo la
señal que hace útil el cruce.

> **El falso positivo que casi entra.** Agrupar por el "núcleo" del correo
> (`juanrestrepo316` → `juanrestrepo`) sumaba 2.354 matches más. Son falsos: ese
> núcleo lo comparten entre 4 y 7 usuarios porque equivale al nombre. Se detectó
> porque el grupo se comportaba como los compradores *nuevos* (43.6% en
> cortesías) y no como los que sí están en Boom (36.4%).

### 2. La proyección (`ft/model.py`, `ft/forecast.py`)

Una probabilidad por entrada, sumadas por show. **Son dos modelos, no uno**,
porque los datos dicen que son dos fenómenos:

| | tasa | ¿importa quién compró? |
|---|---|---|
| **Entrada pagada** | 94% | no — `use_rate` bajo 92.8%, alto 94.4% |
| **Cortesía** | 38.7% | **sí** — `use_rate` bajo 26.5%, alto 38.6% |

Ya pagó: va. La cortesía depende de quién la recibió, y eso solo se sabe cruzando
con Boom. El `use_rate` se calcula **por tipo de entrada de Boom**, porque el
crudo mezcla membresía (46.5%) con consumo mínimo (74.9%) y castiga al fiel.

El efecto de cada artista sale de sus shows de julio, **encogido** hacia el
promedio según cuántos tenga. Un acto de gira sin julio propio no lleva ajuste.

### 3. Los rangos

Simulando cada show 20.000 veces, con dos fuentes de incertidumbre **separadas
para no contarlas dos veces**: el azar de la puerta (σ=0.189) y lo que el modelo
no sabe de esa noche (σ=0.161). **Cobertura empírica: 81%**, contra 80% de
objetivo.

### 4. Las acciones (`ft/prescribe.py`)

Tres palancas, cada una **declarando la fuerza de su supuesto causal**:

| palanca | supuesto | por qué |
|---|---|---|
| **Invitar** fieles de Boom sin entrada | **fuerte** | predice personas concretas con historial propio; es para lo que el modelo se entrenó |
| **Convertir** cortesías en pagadas | medio | la brecha es real, pero parte es que quien paga ya venía decidido (se descuenta 30%) |
| **Mover** cortesías de RRPP a taquilla | **débil** | techo optimista: el canal probablemente *selecciona*, no causa |

Los datos son observacionales: nadie asignó canales al azar. Prometer un efecto
causal con esto sería el error que un evaluador detecta primero.

---

## El insight: la capacidad no es el límite de venta

Nadie pidió esto. Sale de mirar la misma distribución desde el otro lado.

Todo el mundo trata el aforo como un techo: 800 asientos, 800 entradas. Pero si
de cada entrada entra el 64%, vender 800 llena 512 butacas y deja 288 vacías
toda la noche. **El techo real no es la capacidad: es el riesgo de que entren
más de los que caben** — y eso es una probabilidad que ya sabemos calcular,
porque el simulador devuelve una distribución completa, no un número.

> Con un riesgo de desborde del **5% por show**, en agosto se pueden vender
> **9.349 entradas más** — un **179% más de lo ya vendido** — y aun así, en 19
> de cada 20 noches, toda la gente cabe.

Lo contraintuitivo, y por eso es un insight: los shows con **más cortesías
admiten más sobreventa**, no menos, porque su tasa de asistencia es más baja.
Cuento Corto (100% cortesía) admite 1.250 extra; Sin Filtro (2%) solo 483.

La cortesía deja de ser "papel gratis" y pasa a ser **inventario que consume
cupo de riesgo**. Y la pregunta del organizador deja de ser *"¿cuántas entradas
quedan?"* para ser *"¿cuánto riesgo de desborde acepto?"*.

```bash
python -m ft.consulta --sobreventa
```

---

## Qué tan bien predice

Conjunto de prueba: **11 shows que el modelo nunca vio**, evaluado una sola vez.

| método | error por show | error relativo |
|---|---|---|
| "vendieron 500, entran 500" | 56.2 personas | 38.5% |
| tasa global de julio | 22.2 | 18.4% |
| tasa por tipo de entrada | 7.7 | 12.5% |
| **este modelo** | **3.7** (IC 95%: 1.7–6.3) | **4.4%** |

La ventaja sobre el baseline es de 3.9 personas por show, con un intervalo que
**no cruza cero**. AUC 0.864, ECE 0.016.

> **El matiz honesto.** En el conjunto de desarrollo (21 shows) ningún modelo
> batía al baseline de forma concluyente: con tan pocos eventos no hay poder para
> distinguir 8.5 de 8.8 personas. La lectura correcta es que la ventaja es real y
> del orden de 3–4 personas por show, no que el error sea 3.7 para siempre. Está
> documentado en [`docs/04-modeling.md`](docs/04-modeling.md).

**Dónde falla:** en cortesías el error por entrada es 0.446 contra 0.108 en
pagadas. Cuatro veces más. Los shows de pura cortesía son los más inciertos, y
por eso su rango sale más ancho — que es correcto, no un defecto.

### El rango es estrecho, no solo honesto

Un p10–p90 que nunca falla porque va de 0 a 500 no sirve. Se juzga con las dos
cosas a la vez, y el *Winkler score* las combina (mide el ancho y multa cuando
el valor real se sale; menor es mejor):

| intervalo | ancho | cobertura | **Winkler ↓** |
|---|---|---|---|
| de 0 a las entradas vendidas | 210.1 | 100% | 210.1 |
| ±20% sobre la predicción | 62.2 | 94% | 68.2 |
| **el nuestro** | **17.2** | **81%** | **25.9** |

**8.1 veces mejor** que el intervalo trivial. Y el margen está repartido donde
hace falta: el shock crece con la proporción de cortesía (σ de 0.010 a 0.341),
así que el rango baja a 9 personas en shows fáciles y sube a 29 en los de pura
cortesía. Con un shock único, la cobertura era del 94% en los fáciles y del 60%
en los difíciles — parecía bien en el agregado y estaba mal en ambos extremos.

La verificación completa contra los cuatro criterios del brief está en
[`docs/07-criterios.md`](docs/07-criterios.md).

---

## Metodología

Proyecto estructurado en **CRISP-DM**, una nota por fase en [`docs/`](docs/):

| fase | documento |
|---|---|
| 1. Comprensión del negocio | [`01-business-understanding.md`](docs/01-business-understanding.md) — incluye qué significa que FreeTicket sea AI-native |
| 2. Comprensión de los datos | [`02-data-understanding.md`](docs/02-data-understanding.md) |
| 3. Preparación | [`03-data-preparation.md`](docs/03-data-preparation.md) |
| 4. Modelado | [`04-modeling.md`](docs/04-modeling.md) |
| 5. Evaluación | [`05-evaluation.md`](docs/05-evaluation.md) |
| 6. Despliegue | [`06-deployment.md`](docs/06-deployment.md) |

### La decisión metodológica que condiciona todo

Los tickets de un mismo evento comparten artista, venue, noche y política de
cortesías: **no son independientes**. Un split aleatorio a nivel entrada pondría
tickets del mismo show en entrenamiento y prueba, filtrando información.

El split es **por evento y temporal** (en producción siempre se predice hacia
adelante):

| conjunto | semanas ISO | eventos | entradas |
|---|---|---|---|
| entrenamiento | 27–28 | 14 | 2.941 |
| validación | 29 | 7 | 1.670 |
| **prueba** | 30–31 | 11 | 2.111 |

Hay un test que falla ruidosamente si un evento aparece en dos conjuntos.

### Notebooks

- [`01_eda.ipynb`](notebooks/01_eda.ipynb) — seis preguntas, y cada respuesta
  condiciona una decisión del modelo. No es galería de gráficos.

---

## Extras del brief

**Link de puerta** (`python run.py --puerta`). Una página por show, un archivo
sin dependencias, para el celular de quien abre la sala: aforo esperado, rango,
personal sugerido y curva de llegada. **Caduca sola a las 3 horas** — la
caducidad va dentro del archivo, así que sigue venciendo aunque se sirva desde
cualquier estático.

El personal se dimensiona al **70% de ocupación**, no al límite: planificar al
100% suena eficiente y en la práctica es una fila que crece toda la noche.

**Curva de llegada** (`python -m ft.llegada`). Medida en julio: el 27.6% ya entró
45 minutos antes, el 66.6% al cuarto de hora previo, y el pico cae entre −45 y
−30 minutos. **Lo que dimensiona la puerta es el pico, no el total.**

---

## Estructura

```
run.py                pipeline de punta a punta
ft/
├─ api.py fetch.py    cliente del API y caché (una petición = una plataforma)
├─ normalize.py       email, teléfono y nombre sucios → comparables
├─ match.py           el cruce y su evidencia
├─ features.py        una fila por entrada, con corte temporal del historial
├─ datos.py           acceso en DataFrame para notebooks
├─ splits.py          split por evento y temporal, con verificación de fuga
├─ baselines.py       la escalera B0–B3
├─ model.py           la logística segmentada (el campeón)
├─ candidatos.py      los 4 modelos que compiten, con calibración
├─ evaluate.py        métricas en dos niveles, bootstrap, comparación pareada
├─ experimento.py     el experimento completo → reports/metrics.json
├─ forecast.py        simulación e intervalos
├─ prescribe.py       las tres palancas
├─ consulta.py        lo que ejecuta la skill
├─ llegada.py         curva de llegada
└─ puerta.py          el link efímero
.claude/skills/aforo-freeticket/   la skill instalable
docs/                 una nota por fase CRISP-DM
notebooks/            EDA reproducible
tests/                22 pruebas de las piezas frágiles
```

---

## Reproducibilidad

Semillas fijas (`20260801`) en simulación, folds y bootstrap. `raw/` es caché
descartable y se reconstruye del API; `outputs/` y `reports/` son la entrega.

```bash
python run.py --force --experimento --puerta
python -m pytest tests -q
```

Los supuestos y las limitaciones están en [`NOTAS.md`](NOTAS.md).
