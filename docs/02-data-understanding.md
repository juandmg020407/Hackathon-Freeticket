# 2. Comprensión de los datos

Detalle visual y reproducible en [`notebooks/01_eda.ipynb`](../notebooks/01_eda.ipynb).

## Inventario

Ocho recursos, dos plataformas que no se pueden consultar juntas.

| plataforma | recurso | filas | qué aporta |
|---|---|---|---|
| Boom | `users` | 6.000 | identidad y membresía |
| Boom | `profile` | 6.000 | `use_rate` ya calculado (mezcla los dos tipos: ojo) |
| Boom | `tickets` | 22.325 | **el historial real**: `used` y `date_used` por entrada |
| Boom | `social` | 6.000 | `friends_count` |
| FreeTicket | `artists` | 14 | residencia y asistencia de julio |
| FreeTicket | `events` | 62 | 32 de julio, 30 de agosto |
| FreeTicket | `sales` | 6.383 | comprador, canal, fecha de compra |
| FreeTicket | `tickets` | 11.931 | **una fila por entrada**, con la etiqueta |

**La tabla que convierte esto en un problema con etiquetas es `freeticket/tickets`:**
6.722 entradas de julio traen `checked_in` true/false y 5.209 de agosto lo traen
nulo. La unidad de análisis es la entrada, no la venta ni el evento.

## Los seis hallazgos

### 1. El tipo de entrada manda, y manda solo

| tipo | n | entra |
|---|---|---|
| VIP | 545 | 94.9% |
| Preferencial | 954 | 93.9% |
| General | 2.785 | 93.8% |
| **Cortesía** | **2.438** | **38.7%** |

Las tres pagadas son estadísticamente indistinguibles. Lo que separa no es el
precio sino **si hubo plata de por medio**. 55 puntos de diferencia.

### 2. Agosto no se parece a julio

Cortesías: **36.3% en julio, 47.2% en agosto**. Solo por el cambio de mezcla, la
asistencia esperada baja ~5 puntos sin que cambie nada más. Cualquier baseline
basado en la tasa global de julio sobreestima agosto de forma sistemática.

### 3. Boom sirve para la mitad difícil

| `use_rate` de consumo mínimo | pagadas | cortesías |
|---|---|---|
| bajo (<0.4) | 92.8% | **26.5%** |
| medio (0.4–0.7) | 92.0% | **35.6%** |
| alto (>0.7) | 94.4% | **38.6%** |

En pagadas es plano; en cortesías separa 12 puntos. **El cruce con Boom no
predice todo: predice lo que el tipo de entrada no puede.**

Y hay que calcular el `use_rate` **por tipo de entrada de Boom**: membresía no
pasa del 46.5% y consumo mínimo llega al 74.9%. El `use_rate` crudo del perfil
los promedia y castiga al fiel que solo usa membresía.

### 4. Señales secundarias (medidas dentro de cortesías)

| señal | separa |
|---|---|
| canal | taquilla 50% · web 38% · admin 30% · RRPP 29% |
| ciudad | vive donde es el show 42.7% vs 33.8% |
| anticipación | pedida el mismo día 50% vs 8+ días 37% |

⚠️ Son diferencias **observacionales**. Que las cortesías de taquilla entren más
probablemente refleja *a quién* se las dan, no que el canal cause la asistencia.
Válidas para predecir; para prescribir hay que declarar el supuesto.

### 5. El error residual se concentra en un sitio

Prediciendo cada show de julio **solo** con la tasa por tipo, el MAE es de 7.5
personas — y los residuos grandes están todos en shows con 100% de cortesías
(Mala Hora +0.195, Micrófono Suelto −0.119). Es exactamente donde el brief dice
que manda el *quién*.

### 6. Cada acto tiene su público

El factor por artista va de **0.84** (Micrófono Suelto) a **1.09** (Mala Hora)
sobre lo que predice la mezcla. Señal real, pero algunos actos tienen un solo
show en julio, así que hay que encogerla.

## Calidad de los datos

| problema | alcance | tratamiento |
|---|---|---|
| dominios mal escritos | 338 correos (`gmial`, `hotmial`, `outlok`) | tabla de corrección + distancia 1 |
| teléfonos vacíos | 591 ventas | evidencia neutra, no penaliza |
| cinco formatos de teléfono | todas | normalización a 10 dígitos sin indicativo |
| nombres repetidos en Boom | 1.144 (885 con >3 personas) | el nombre nunca ancla un match |
| `date_used` posterior a hoy | Boom llega al 26 de agosto | corte temporal al construir features |

## La restricción metodológica que condiciona todo

Los tickets de un mismo evento comparten artista, venue, noche y política de
cortesías: **no son independientes**. Un split aleatorio a nivel entrada pondría
tickets del mismo show en entrenamiento y en prueba, filtrando información y
produciendo métricas optimistas.

→ Todo split de aquí en adelante es **por evento**, y además temporal.
