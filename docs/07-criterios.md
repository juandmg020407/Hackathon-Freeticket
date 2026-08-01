# Verificación contra los criterios de evaluación

Los cuatro criterios del brief, con la evidencia de cada uno y lo que no
cumplimos.

---

## 1. El cruce — «la precisión pesa más que la cobertura»

**Cobertura: 62.1%** (3.963 de 6.383 ventas). El 37.9% restante queda vacío a
propósito: son compradores que no están en Boom.

**Evidencia de precisión.** Sin ground truth no se mide directamente, así que se
mira en qué se apoya cada match aceptado:

| evidencia | matches | % |
|---|---|---|
| **al menos una llave única exacta** (email o teléfono) | 3.847 | **97.1%** |
| email exacto | 3.301 | 83.3% |
| teléfono exacto | 3.064 | 77.3% |
| **email Y teléfono exactos** | 2.515 | **63.5%** |
| nombre corrobora (≥0.9) | 3.736 | 94.3% |

En Boom el email y el teléfono son **únicos** (cero duplicados), así que anclar
en ellos es fuerte. El nombre nunca ancla —1.144 se repiten— y además
**desmiente**: correo exacto con nombre ajeno es el correo de la pareja y ahí el
match se rechaza.

**El falso positivo que se evitó.** Agrupar por el "núcleo" del correo
(`juanrestrepo316` → `juanrestrepo`) habría sumado **2.354 matches más** — un
salto del 62% al 99% de cobertura. Son falsos, y hay dos pruebas:

1. Ese núcleo lo comparten entre 4 y 7 usuarios de Boom, porque equivale al
   nombre. Los dígitos de cola son lo que discrimina.
2. El grupo se comporta como los compradores **nuevos** (43.6% de asistencia en
   cortesías) y no como los que sí están en Boom (36.4%).

Preferir el 62% con evidencia al 99% inflado es exactamente lo que pide el
criterio.

**Lo que no puedo afirmar.** Un test de permutación sobre la señal de `use_rate`
en cortesías da **p = 0.016**: significativa al 5%, no al 1%. La señal es real
pero moderada, y con matches barajados la separación entre bandas cae de 7.6 a
2.6 puntos. Es honesto decir que el cruce aporta, no que sea determinante.

---

## 2. La proyección — «un p10–p90 que nunca falla porque va de 0 a 500 no sirve»

Un intervalo se juzga por **dos cosas a la vez**: que acierte ~80% y que sea
**estrecho**. El *Winkler score* las combina — mide el ancho y cobra una multa
cuando el valor real se sale. Menor es mejor.

| intervalo | ancho | cobertura | **Winkler ↓** |
|---|---|---|---|
| de 0 a las entradas vendidas | 210.1 | 100% | 210.1 |
| ±50% sobre la predicción | 155.5 | 100% | 155.5 |
| ±20% sobre la predicción | 62.2 | 94% | 68.2 |
| **el nuestro (p10–p90)** | **17.2** | **75–81%** | **25.9** |

**8.1 veces mejor** que el intervalo trivial que el brief denuncia. Los que
"nunca fallan" (cobertura 100%) son precisamente los peores en Winkler.

### El defecto que apareció al medirlo

Con un shock único por show, la cobertura global era 78% — aparentemente
correcta. Desglosada, estaba **mal repartida**:

| shows | antes | ahora |
|---|---|---|
| poca cortesía (16) | 94% ← sobra margen | **81%** |
| mixtos (11) | 64% | **82%** |
| mucha cortesía (5) | 60% ← engaña | **80%** |

Un 78% global escondía margen de sobra donde el modelo acierta y margen de menos
justo donde el show es incierto. Como el error en cortesías es cuatro veces el
de las pagadas, **el shock ahora crece con la proporción de cortesía**: σ va de
0.010 sin cortesías a 0.341 con solo cortesías. El intervalo se estrecha a 9.3
personas en los shows fáciles y se ensancha a 28.8 en los difíciles.

Que el rango sea más ancho en un show de pura cortesía no es un defecto: es la
única respuesta honesta.

### Y el número tiene sentido

MAE de **3.7 personas por show** en el conjunto de prueba (11 shows nunca
vistos, evaluado una vez), 4.4% de error relativo, contra 7.7 del mejor
baseline. Calibración ECE 0.016.

---

## 3. ¿Sirve el viernes? — «si el de la puerta no lo puede usar sin ti, no está terminado»

**Está publicado: https://juandmg020407.github.io/Hackathon-Freeticket/**

Es un link real, se abre en cualquier celular y no necesita que nadie corra
nada. Un índice con los 30 shows y una página por show: aforo esperado, rango,
cuánta gente poner en la puerta y a qué hora llega.

### La vigencia va anclada al show, no a la generación

El brief pide que caduque solo a las 3 horas. Contar esas horas desde que se
genera el archivo obliga a generarlo justo antes de abrir puertas, y cualquier
link mandado con antelación llega muerto. Anclarlo al show resuelve las dos
cosas — se manda el lunes para el viernes y sigue caducando solo:

| estado | cuándo | qué muestra |
|---|---|---|
| antes | hasta 6 h antes | el aforo, y avisa que el show sigue vendiendo |
| **puerta** | de −6 h a +3 h | modo operativo, lo que se usa esa noche |
| vencido | pasadas 3 h del inicio | el show ya pasó |

La caducidad va **dentro del archivo**, así que sigue venciendo aunque el
hosting no sepa de TTL.

El personal se dimensiona al **70% de ocupación**, no al límite: planificar al
100% suena eficiente y en la práctica es una fila que crece toda la noche,
porque no queda holgura para absorber una demora.

**Lo que sigue siendo manual:** republicar tras recalcular. El sitio es estático
y hay que empujarlo a `gh-pages` (cuatro comandos, documentados en
[`06-deployment.md`](06-deployment.md)). En producción esto sería un cron o una
GitHub Action, no una persona.

---

## 4. El insight — «algo que nadie pidió y que cambia cómo pensamos el acceso»

**La capacidad de la sala no es el límite de venta.**

Todo el mundo trata el aforo como un techo: 800 asientos, 800 entradas. Pero si
de cada entrada entra el 64%, vender 800 llena 512 butacas y deja 288 vacías
toda la noche.

El techo real no es la capacidad: es **el riesgo de que entren más de los que
caben**. Y eso es una probabilidad que ya sabemos calcular, porque el simulador
no devuelve un número sino una distribución completa.

> Con un riesgo de desborde del **5% por show**, en agosto se pueden vender
> **9.349 entradas más** — un **179% más de lo ya vendido** — y aun así, en 19
> de cada 20 noches, toda la gente cabe.

Es lo que hacen las aerolíneas desde hace cuarenta años. En un teatro sale más
barato: el coste de pasarse no es reubicar a alguien en otro vuelo, son diez
personas de pie al fondo.

**Lo contraintuitivo, y por eso es un insight:** los shows con **más cortesías
admiten más sobreventa**, no menos, porque su tasa de asistencia es más baja.
Cuento Corto, con 100% de cortesías, admite 1.250 entradas extra; Sin Filtro,
con 2%, solo 483.

Cambia cómo se piensa el acceso:

- La cortesía deja de ser "papel gratis" y pasa a ser **inventario que consume
  cupo de riesgo** — y ese cupo se puede medir y asignar.
- La pregunta del organizador deja de ser *"¿cuántas entradas quedan?"* y pasa a
  ser *"¿cuánto riesgo de desborde acepto?"*.

```bash
python -m ft.consulta --sobreventa
```

**Supuesto declarado:** las entradas nuevas se parecen a las ya vendidas. Si se
venden a otro público —otro canal, otra ciudad— hay que recalcular. Y el 5% es
una perilla, no una ley: el organizador decide su tolerancia.
