# 1. Comprensión del negocio

## El problema, en una frase

Se venden 500 entradas a un show. ¿Entran 500, 380 o 240? Hoy nadie lo sabe y la
puerta se dimensiona a ojo.

## Por qué duele

No saber el aforo real tiene costo en tres sitios distintos, y ninguno es
obvio desde la hoja de ventas:

| Decisión | Si se sobreestima | Si se subestima |
|---|---|---|
| Personal de puerta | se paga gente de más | fila que no baja, gente que se va |
| Barra e insumos | producto perdido | se agota a mitad de show |
| Cortesías a repartir | la sala se ve vacía en fotos | se deja dinero en la mesa |

El caso que lo resume está en los propios datos: **Sin Filtro** tiene dos shows
en agosto. Uno vendió 424 entradas y va a meter 397 personas. El otro repartió
**623 y va a meter 259**. Más entradas, mucha menos gente. Quien mire solo
`tickets_sold` dimensiona mal el segundo show por más de 350 personas.

## Qué se decide con esto

1. **Cuánta gente poner en puerta** el día del show.
2. **Cuántas cortesías repartir**, y por qué canal, para llenar sin regalar.
3. **A quién invitar** cuando faltan dos semanas y el show va flojo.

Las tres son decisiones operativas, con dueño y con fecha. No es un informe.

## Criterio de éxito

| | Meta | Cómo se mide |
|---|---|---|
| Precisión | error < 10% del aforo real | MAE por evento sobre datos no vistos |
| Honestidad | el intervalo p10–p90 acierta 8 de cada 10 veces | cobertura empírica |
| Utilidad | responde en la puerta, sin abrir un notebook | la skill y el link efímero |
| Prudencia | no inventa personas que no existen | matches sin evidencia quedan vacíos |

El error tiene **costo asimétrico**: subestimar el aforo (fila, mala experiencia,
gente que se va) duele más que sobreestimarlo (una persona de más en puerta). Por
eso se entrega un intervalo y no solo un número, y por eso el link de puerta
dimensiona el personal al 70% de ocupación y no al límite.

## Por qué el entregable es una *skill* y no un dashboard

FreeTicket es una empresa **AI-native**, y eso no es una etiqueta de marketing:
es una decisión de arquitectura que se puede verificar. Publican
`llms.txt`, `design.md`, dos contratos OpenAPI, un CLI (`ft`), un servidor MCP y
un repositorio `agent-skills` instalable con `npx skills add`. El patrón que
siguen es **contract-first**: el backend define el contrato y los clientes —
humanos o agentes — se generan desde ahí.

La consecuencia para este proyecto:

> **El entregable no es el modelo. Es la capacidad que el modelo habilita,
> empaquetada para que un agente la invoque.**

Un `forecast.csv` obliga a alguien a abrirlo, entenderlo y decidir. Una skill
deja que el organizador pregunte *"¿cómo va el show del viernes?"* en el mismo
sitio donde ya trabaja, y reciba el número, el porqué y qué hacer.

### Predecir no es suficiente

| | Pregunta que responde | Qué permite |
|---|---|---|
| Predictivo | ¿cuántos entran? | dimensionar la puerta |
| **Prescriptivo** | **¿qué hago para que entren más?** | **llenar la sala** |

Un show que proyecta 259 de 623 no necesita un número: necesita saber que le
sobran 541 asientos, que sus cortesías fueron 100% del aforo, y que tiene 47
fieles de Boom en Bogotá sin invitar. Por eso el proyecto termina en una capa
prescriptiva (`ft/prescribe.py`) y no en el CSV.

## Restricciones que impone el negocio

- **Una consulta toca una plataforma.** Boom y FreeTicket son sistemas separados
  con credenciales separadas. Unirlos es el reto, no la infraestructura.
- **No hay ID compartido**, y las llaves de cruce están sucias a propósito.
- **Los `event_id` no se cruzan**: `bm_evt_*` y `ft_evt_*` son universos distintos.
- **Una parte grande de los compradores no existe en Boom.** Inventarles un match
  es peor que dejarlos sin match — un falso positivo contamina la señal que
  justamente hace útil el cruce.

## Alcance declarado

Se proyecta **solo sobre las entradas ya adquiridas**. Los shows de fin de mes
seguirán vendiendo, así que sus cifras se leen como "de lo que ya está vendido,
cuánto cruza la puerta" y no como el aforo final. Para el día del show hay que
volver a correr el pipeline.
