# 4. Modelado

Reproducible con `python -m ft.experimento`. Números en
[`reports/metrics.json`](../reports/metrics.json).

## Formulación

Se predice **una probabilidad por entrada** y se suman por evento:

```
aforo esperado(evento) = Σ P(entra | entrada i)
```

Predecir el total del evento directamente daría 32 observaciones. A nivel de
entrada hay 6.722, y además permite responder *quién* entra — que es lo que la
capa prescriptiva necesita.

## Protocolo de validación

| paso | qué |
|---|---|
| 1 | CV agrupada por evento (5 folds) sobre train+val — 21 eventos |
| 2 | Comparación **pareada** contra el mejor baseline |
| 3 | Elección de campeón |
| 4 | Reentrenar con train+val y evaluar en test — 11 eventos, **una sola vez** |

El reparto es temporal por semana ISO: train 27–28, val 29, test 30–31. Ningún
evento aparece en dos conjuntos, y hay un test que lo verifica
(`tests/test_splits.py`).

## Los cuatro candidatos

| id | modelo | idea |
|---|---|---|
| M1 | logística segmentada, variables de dominio | dos modelos separados: cortesía y pagada son dos fenómenos |
| M2 | logística única de sklearn + interacciones | ¿hacía falta segmentar, o bastaban las interacciones? |
| M3 | HistGradientBoosting (calibrado) | no linealidades que una forma lineal no ve |
| M4 | RandomForest (calibrado) | contraste de familia |

### Por qué M1 va segmentado

El EDA mostró que el `use_rate` de Boom separa 12 puntos en cortesías y es plano
en pagadas. Un modelo único tiene que descubrir esa interacción; M1 la impone
por construcción, que es más eficiente con 6.722 observaciones.

### Por qué los árboles van calibrados

El aforo se obtiene **sumando** probabilidades. Un modelo que ordene perfecto
pero prediga 0.7 donde la verdad es 0.5 arruina el total aunque su AUC sea
inmejorable. Van con `CalibratedClassifierCV` isotónica, **con folds agrupados
por evento** — calibrar con folds aleatorios reintroduce la fuga que el split
evitó.

### El efecto de artista

Entra como dummies con L2 fuerte (λ=12), que equivale a encoger cada artista
hacia el promedio según cuántos shows suyos se vieron. Un acto de gira sin julio
propio queda en cero — sin ajuste — y para él solo habla Boom.

## Resultados en desarrollo (CV, 21 eventos)

| modelo | MAE | IC 95% | MAPE | log-loss | AUC | ECE |
|---|---|---|---|---|---|---|
| B0 · entran todos | 56.2 | [36.8, 79.9] | 38.5% | 5.308 | 0.500 | 0.256 |
| B1 · tasa global | 22.2 | [16.3, 28.9] | 18.4% | 0.571 | 0.457 | 0.057 |
| **B2 · tasa por tipo** | **8.53** | [4.7, 13.2] | 6.9% | 0.393 | 0.808 | 0.027 |
| B3 · tipo × artista | 9.57 | [6.3, 13.8] | 7.4% | 0.432 | 0.823 | 0.033 |
| **M1 · logística segmentada** | 8.79 | [5.3, 13.1] | **6.5%** | **0.392** | 0.836 | **0.022** |
| M2 · logística + interacciones | 10.45 | [5.9, 15.8] | 9.4% | 0.397 | **0.840** | 0.034 |
| M3 · gradient boosting | **8.46** | [4.8, 13.2] | 7.3% | 0.397 | 0.829 | 0.028 |
| M4 · random forest | 9.60 | [5.9, 14.1] | 8.0% | 0.397 | 0.826 | 0.033 |

### El hallazgo incómodo

**Ningún modelo bate a B2 de forma concluyente en desarrollo.** Las cuatro
comparaciones pareadas cruzan cero:

| modelo | diferencia vs B2 | IC 95% | ¿concluyente? |
|---|---|---|---|
| M1 | +0.27 | [−1.30, +2.01] | no |
| M2 | +1.92 | [−1.65, +5.74] | no |
| M3 | −0.07 | [−1.49, +1.17] | no |
| M4 | +1.08 | [−0.96, +3.63] | no |

Con 21 eventos no hay poder estadístico para distinguir 8.5 de 8.8 personas. Se
reporta así en vez de elegir el número más bonito.

Lo que **sí** se ve con claridad es que los modelos discriminan mejor a nivel de
entrada (AUC 0.836–0.840 vs 0.808) y M1 calibra mejor que todos (ECE 0.022).

## Elección del campeón: M1

Empata en MAE, y gana en lo que decide el desempate:

1. **Calibración** (ECE 0.022, la mejor). Crítico porque sumamos probabilidades.
2. **MAPE** (6.5%, el mejor). Error relativo, que no premia acertar en los shows
   grandes.
3. **Interpretabilidad.** Sus coeficientes se leen y se auditan.
4. **Habilita la capa prescriptiva.** Da probabilidad por entrada con variables
   accionables: se puede simular "¿y si invito a estos 47 fieles?". Un baseline
   de tasas no puede responder eso.

M3 iguala en MAE pero es una caja negra que no permite lo cuarto.

## Coeficientes de M1 (escala logit)

**Cortesías** — donde está la varianza:

| variable | coef. | lectura |
|---|---|---|
| compra el último día | +0.45 | pedir la cortesía el mismo día es señal de intención |
| `n_boom` (log) | +0.71 | más historial, más probable que aparezca |
| `rate_consumo` centrado | +0.23 | el fiel de Boom cumple |
| en Boom | −0.69 | estar en Boom, en neto, baja: Boom conoce al que colecciona cortesías |
| misma ciudad | +0.20 | vivir donde es el show |

**Pagadas** — casi plano: intercepto +2.67 (≈ 94%) y el resto son ajustes
menores. Ya pagó: va.

## Lo que no se hizo, y por qué

- **Sin tuning agresivo de hiperparámetros.** Con 21 eventos de desarrollo,
  optimizar sobre el MAE por evento es ajustar al ruido.
- **Sin ensemble.** Promediar M1 y M3 probablemente daría una décima, dentro del
  ruido, a cambio de perder interpretabilidad y la capa prescriptiva.
