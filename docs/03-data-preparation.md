# 3. Preparación de los datos

Dos trabajos: **cruzar** las plataformas (record linkage) y **construir la tabla
de modelado** sin meter información del futuro.

## 3.1 El cruce (`ft/normalize.py`, `ft/match.py`)

No hay ID compartido y las llaves están sucias a propósito. La unidad es la
venta: `sale_id → boom_user_id` con un score de confianza.

### Normalización

| llave | qué se hace |
|---|---|
| email | minúsculas, se quita el alias `+algo`, se corrigen dominios rotos (`gmial`→`gmail`) con tabla + distancia 1 |
| teléfono | solo dígitos, se quita el indicativo 57, se toman los últimos 10 |
| nombre | sin tildes, minúsculas, tokens ordenados (absorbe "apellido primero") |

### Generación de candidatos

Comparar 6.383 ventas contra 6.000 usuarios son 38 millones de pares. Se bloquea
con índices: email exacto, local del email, teléfono exacto, y **un índice de
eliminaciones** (SymSpell) que encuentra la "letra faltante" sin comparar todo
contra todo.

### Puntuación

```
score = 0.44·email + 0.36·teléfono + 0.20·nombre   (+0.03 si coincide la ciudad)
aceptar si score ≥ 0.52 y le saca ≥ 0.06 al segundo candidato
```

Los pesos salen de la **unicidad medida en los datos**, no de la intuición: en
Boom hay 0 emails duplicados y 0 teléfonos duplicados, pero **1.144 nombres
repetidos** (885 compartidos por más de tres personas). Por eso el nombre no
puede anclar un match; solo confirma o desmiente.

> **El nombre también desmiente.** Un correo exacto con un nombre ajeno es el
> correo de la pareja — el brief lo advierte —, y ahí el match no se acepta.

### El falso positivo que casi entra

La primera versión agrupaba por el **"núcleo"** del email: `juanrestrepo316` →
`juanrestrepo`, quitando puntos y dígitos de cola. Eso sumaba **2.354 matches**.

Son falsos, y hay dos pruebas:

1. **Estructural.** Ese núcleo lo comparten entre 4 y 7 usuarios de Boom, porque
   equivale al nombre. Los dígitos de cola son justamente lo que discrimina.
2. **De comportamiento.** El grupo se comporta como los compradores *nuevos*
   (43.6% de asistencia en cortesías) y no como los que sí están en Boom (36.4%).

Ejemplo real: la venta de `juanrestrepo316@gmail.com` con teléfono 3066510402
contra el usuario `juan.restrepo67@icloud.com` con teléfono 3225194534. Dominio
distinto, dígitos distintos, teléfono distinto. **Son dos Juan Restrepo.**

Tras corregirlo, esa evidencia puntúa 0.25 y el caso cae a 0.31 — muy por debajo
del umbral, no rozándolo.

### Resultado

**3.963 de 6.383 ventas cruzadas (62.1%).** El 37.9% restante son compradores
nuevos y se dejan vacíos deliberadamente. Un falso positivo no es un error
neutro: contamina justo la señal que hace útil el cruce.

## 3.2 La tabla de modelado (`ft/features.py`)

**Una fila por entrada**, no por venta ni por evento: lo que se predice es si
*esa* entrada cruza la puerta. 11.931 filas, 6.722 con etiqueta.

### El corte temporal

El historial de Boom de un comprador se mide **con lo que se sabía antes del
show**: para julio, la fecha del evento; para agosto, hoy (1 de agosto).

Esto no es ceremonia. Boom trae `date_used` hasta el **26 de agosto**: usarlo
entero para calibrar julio sería aprender de un futuro que no existía. Se
implementa con búsqueda binaria sobre las fechas ordenadas de cada usuario.

### Variables

| grupo | variables |
|---|---|
| entrada | `tipo`, `es_cortesia`, `precio` |
| venta | `canal`, `qty`, `dias_anticipacion` |
| comprador (vía cruce) | `en_boom`, `rate_consumo`, `rate_membresia`, `n_boom`, `has_membership`, `misma_ciudad`, `confidence` |
| show | `artist_id`, `city`, `venue`, `weekday`, `capacity`, `is_residency` |

**`rate_consumo` y `rate_membresia` van separadas** porque el `use_rate` crudo
del perfil las promedia: membresía no pasa del 46.5% y consumo mínimo llega al
74.9%. Promediarlas castiga al fiel que solo usa membresía.

### Lo que se dejó fuera a propósito

| variable | por qué no |
|---|---|
| `fill_rate`, `attendance_rate`, `checked_in_count` | en julio son el valor final; en agosto, parcial o nulo. No son comparables |
| `checked_in_at` | ocurre después del hecho que se predice |
| `event_id` de Boom | universo distinto, no se cruza con `ft_evt_*` |

### Ausentes

`rate_consumo` es **nulo** cuando el comprador no está en Boom o no tiene ese
tipo de entrada — y eso no es lo mismo que "su tasa es 0". El modelo lleva una
bandera de presencia junto al valor, para que el 37.9% de compradores nuevos no
entre como si fueran fieles con tasa cero.

> Un detalle que costó un bug: `None` al pasar por pandas se vuelve `NaN`, y
> `NaN is not None` es cierto. Comprobar solo `None` dejaba entrar nulos que
> contaminaban toda la matriz. La comprobación de ausencia está centralizada en
> `ft.model.falta()`.
