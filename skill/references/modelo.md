# Cómo predice, con qué error y qué supone

## La idea

Se estima **una probabilidad por entrada** y se suman por show:

```
aforo esperado = Σ P(entra | entrada i)
```

No se predice el total del evento directamente porque solo hay 32 eventos
etiquetados, mientras que a nivel de entrada hay 6.722. Y sumar probabilidades
individuales permite responder *quién* entra, que es lo que hace posible
recomendar a quién invitar.

## Son dos modelos, no uno

Porque son dos fenómenos distintos, medido en julio:

| | tasa | ¿importa quién compró? |
|---|---|---|
| **Entrada pagada** | 94% | no — `use_rate` bajo 92.8%, alto 94.4% |
| **Cortesía** | 38.7% | **sí** — `use_rate` bajo 26.5%, alto 38.6% |

Ya pagó: va. La cortesía, en cambio, depende de quién la recibió — y eso solo se
sabe cruzando con Boom.

## Variables que más pesan (cortesías, escala logit)

| variable | coef. | lectura |
|---|---|---|
| `n_boom` (log) | +0.71 | más historial en Boom, más probable que aparezca |
| compra el último día | +0.45 | pedir la cortesía el mismo día es señal de intención |
| `rate_consumo` centrado | +0.23 | el fiel de Boom cumple |
| misma ciudad | +0.20 | vive donde es el show |
| en Boom (neto) | −0.69 | Boom conoce justo a quien colecciona cortesías y no aparece |

El `use_rate` se calcula **por tipo de entrada de Boom**: membresía no pasa del
46.5% y consumo mínimo llega al 74.9%. El `use_rate` crudo del perfil los
promedia y castiga al fiel que solo usa membresía.

## Qué tan bien predice

Conjunto de prueba: 11 shows que el modelo nunca vio, evaluado **una sola vez**.

| | error medio por show | error relativo |
|---|---|---|
| "vendieron 500, entran 500" | 56.2 personas | 38.5% |
| tasa global de julio | 22.2 | 18.4% |
| tasa por tipo de entrada | 7.7 | 12.5% |
| **este modelo** | **3.7** (IC 95%: 1.7–6.3) | **4.4%** |

La ventaja sobre el baseline de tasa por tipo es de 3.9 personas por show, con
un intervalo de confianza que no cruza cero.

> **Matiz honesto.** En el conjunto de desarrollo (21 shows) la ventaja **no**
> era concluyente: con tan pocos eventos no hay poder estadístico para
> distinguir 8.5 de 8.8 personas. La lectura correcta es que la ventaja es real
> y del orden de 3–4 personas por show, no que el error sea exactamente 3.7 para
> siempre.

## Los rangos p10–p90

Salen de simular cada show 20.000 veces con dos fuentes de incertidumbre
separadas, para no contar dos veces la misma:

| fuente | σ (logit) |
|---|---|
| azar de la puerta (cada entrada es una moneda) | 0.189 |
| lo que el modelo no sabe de esa noche | 0.161 |

**Cobertura empírica: 81%** de los shows de julio caen dentro de su rango,
contra un objetivo del 80%.

## Dónde falla

| segmento | error por entrada |
|---|---|
| pagadas | 0.108 |
| **cortesías** | **0.446** |

Cuatro veces más. Los shows de pura cortesía son los más inciertos — y por eso
su rango sale más ancho, lo cual es correcto, no un defecto.

## Qué supone

1. **Solo entradas ya adquiridas.** Los shows de fin de mes seguirán vendiendo.
2. **Corte temporal.** El historial de Boom se recorta a lo que se sabía antes
   del show (Boom trae `date_used` hasta el 26 de agosto).
3. **Un solo mes de historia.** Sin estacionalidad ni efecto de festivos.
4. **Datos sintéticos.** Las relaciones son las que el generador puso; con datos
   reales habría que revalidar las magnitudes.
