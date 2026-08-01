# 6. Despliegue

## Qué se entrega, y por qué así

FreeTicket es **AI-native**, y eso es verificable: publica `llms.txt`,
`design.md`, dos contratos OpenAPI, un CLI (`ft`), un servidor MCP y un
repositorio `agent-skills` instalable con `npx skills add`. El patrón es
**contract-first**.

La consecuencia para este proyecto: **el entregable no es el modelo, es la
capacidad que el modelo habilita, empaquetada para que un agente la invoque.**

| capa | artefacto | quién lo consume |
|---|---|---|
| Skill | `skill/SKILL.md` + referencias | el agente, cuando alguien pregunta |
| Consulta | `ft/consulta.py` | la skill, y cualquiera desde terminal |
| Datos | `outputs/*.csv` | el pipeline y auditoría |
| Puerta | `puerta/*.html` | quien abre la sala el viernes |

## 1. La skill

```bash
python -m ft.consulta "Sin Filtro"      # todos los shows de ese acto
python -m ft.consulta ft_evt_0060       # un show por id
python -m ft.consulta --agenda          # los 30 shows de agosto
python -m ft.consulta --modelo          # error, supuestos y dónde falla
```

Responde en tres bloques: **veredicto**, **por qué** y **qué puedes hacer**.
Todo sale de `outputs/` y `reports/metrics.json`: si el comando no da una cifra,
no existe. La skill instruye explícitamente a no inventar números.

Dos comportamientos que se probaron a propósito:

- Un evento de **julio** responde que ya pasó y su asistencia es un dato, no una
  predicción.
- Un artista inexistente **lista los que sí hay** en vez de improvisar.

### El matiz que cambió la utilidad

La primera versión decía *"va flojo"* a un show cuya asistencia esperada era del
83%. Lo que iba flojo era la **venta**, no la asistencia. Son dos problemas
distintos con soluciones distintas —uno se arregla vendiendo y el otro cambiando
la mezcla— y ahora los separa explícitamente.

## 2. El link efímero de puerta

```bash
python run.py --puerta
```

Una página por show, un solo archivo sin dependencias, para el celular de quien
está en la entrada: aforo esperado, rango, personal sugerido y curva de llegada.
**Caduca sola a las 3 horas**; la caducidad va dentro del archivo, así que sigue
venciendo aunque se sirva desde cualquier estático.

El personal se dimensiona al **70% de ocupación**, no al límite: planificar al
100% suena eficiente y en la práctica es una fila que crece toda la noche,
porque no hay holgura para absorber una demora.

## 3. La curva de llegada

```bash
python -m ft.llegada
```

Medida en julio: el 27.6% ya entró 45 minutos antes, el 66.6% al cuarto de hora
previo, y el pico cae entre −45 y −30 minutos. **Lo que dimensiona la puerta es
ese pico, no el total.**

## Advertencia sobre las palancas prescriptivas

Los datos son **observacionales**: nadie asignó canales ni precios al azar. Cada
palanca declara la fuerza de su supuesto y la skill traslada esa etiqueta:

| palanca | supuesto | cómo se presenta |
|---|---|---|
| invitar fieles de Boom | **fuerte** | predicción sobre personas concretas con historial propio |
| convertir cortesías | medio | brecha real, descontada un 30% |
| mover de canal | **débil** | techo optimista; el canal probablemente selecciona |

Detalle en [`skill/references/playbook.md`](../skill/references/playbook.md).

## Reproducibilidad

```bash
pip install -r requirements.txt
curl "https://hackathon-freeticket.vercel.app/api/setup?handle=TU-NOMBRE" -o setup.json
python run.py --force --experimento --puerta
python -m pytest tests -q
```

Semillas fijas (`20260801`) en simulación, folds y bootstrap. `raw/` es caché
descartable; `outputs/` y `reports/` son la entrega.

## Qué haría falta para producción

1. **Reentrenar con cadencia.** El modelo se calibró con un mes. Con tres o
   cuatro habría estacionalidad y efecto de festivos.
2. **Monitorear la deriva.** Comparar aforo predicho contra real después de cada
   show y alertar si el sesgo se sostiene.
3. **Cerrar el ciclo del cruce.** Cada check-in real es una etiqueta nueva para
   el matcher, que hoy no aprende de sus aciertos.
4. **Exponerlo como MCP.** La skill funciona en local; FreeTicket ya tiene
   servidor MCP, y `ft.consulta` encaja como tool ahí.
5. **Validar las palancas con un experimento.** Un A/B de canal de cortesías
   convertiría el supuesto débil en una medición.
