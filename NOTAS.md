# NOTAS

## Qué asumí

**Solo proyecto las entradas ya adquiridas.** Los shows del 28 y 29 de agosto
todavía van a vender; `ft_evt_0009` lleva 37 entradas y el 1 de agosto es
temprano. El pronóstico responde "de lo que ya está vendido, cuánto cruza la
puerta", que es lo que pide el brief. Para dimensionar la puerta del día hay
que volver a correrlo cerca de la fecha.

**No uso `fill_rate` ni `attendance_rate` del evento.** En julio son el llenado
final; en agosto, el llenado parcial de hoy. Correlacionan fuerte con asistir
(0.44 vs 0.36 en cortesías) y meterlos habría inflado la validación con una
variable que en agosto significa otra cosa.

**El historial de Boom se recorta a la fecha del show.** Boom trae `date_used`
hasta el 26 de agosto: usarlo entero para calibrar julio sería aprender del
futuro. Para agosto el corte es hoy.

**Entradas independientes dado el modelo.** Lo verifiqué: en julio, en el 11.3%
de las ventas de dos o más no entró nadie, y el modelo predice 11.5% sin
necesidad de un término de correlación. Lo que parecía "vienen en grupo" era
heterogeneidad que las variables ya explican — el cálculo ingenuo con la
probabilidad media daba 4.7% y era el que estaba mal.

## Qué señal pesó más

**El tipo de entrada, y no de cerca.** Pagada entra al 94% (General 93.8,
Preferencial 93.9, VIP 94.9); cortesía al 38.7%. Solo con la mezcla de tipos el
error baja de 54.8 a 7.5 personas por evento. Todo lo demás se reparte los 6
restantes.

**Boom sirve para las cortesías, no para las pagadas.** Es el hallazgo que
cambió el diseño: partí el modelo en dos. En las pagadas el historial del
comprador da igual (use_rate bajo 0.928, alto 0.944) — ya pagó, va. En las
cortesías manda quién la recibió: 0.265 / 0.356 / 0.386 según su use_rate de
consumo mínimo. Ese use_rate hay que calcularlo por tipo de entrada; el crudo
mezcla membresía (que no pasa del 60%) con consumo mínimo (75%) y se queda
corto, tal como avisa el brief.

**El cruce mismo es una señal.** Estar en Boom baja la asistencia a cortesías
(36.3% vs 42.6% de los compradores nuevos): Boom conoce justamente a los que
coleccionan cortesías y no aparecen.

**Agosto trae peor mezcla que julio**: 47.2% de cortesías contra 36.3%. Por eso
proyecto 69.5% de asistencia contra el 73.9% que dio julio. El caso de libro es
Sin Filtro: con 424 entradas casi todas pagadas entran 395; con 623 entradas
100% cortesía entran 234. Más vendido, mucha menos gente.

## Sobre el cruce

3.963 de 6.383 ventas (62.1%) quedan cruzadas; el 37.9% restante son
compradores nuevos, y ahí prefiero el hueco al invento. Solo email y teléfono
anclan un match: en Boom son únicos, mientras 1.144 nombres se repiten y 885 los
comparten más de tres personas.

El error que casi cometo: agrupar por "núcleo" del email (`juanrestrepo` sin
puntos ni dígitos) daba 2.354 matches más. Son falsos. Ese núcleo es el nombre
disfrazado — lo comparten entre 4 y 7 usuarios de Boom —, y el grupo se comporta
como los compradores nuevos (43.6% en cortesías) y no como los que sí están en
Boom (36.4%). Los dígitos de cola del correo son lo que discrimina. El nombre
también desmiente: correo exacto con nombre ajeno es el correo de la pareja, y
ahí no acepto el match.

## Qué tan bien funciona

Dejando cada evento de julio fuera y reentrenando:

| método | error medio por evento |
|---|---|
| "vendieron 500, entran 500" | 54.8 |
| tasa global de julio (74.3%) | 24.6 |
| solo mezcla de tipos | 7.5 |
| **modelo completo (fuera de muestra)** | **6.2** |

Error relativo del 4.8%. El intervalo p10–p90 cubre el 81% de los eventos de
julio (objetivo 80%), con 16 personas de ancho medio. Se compone del azar de la
puerta (0.189 en logit) más lo que el modelo no sabe de cada noche (0.161),
separados para no contar dos veces la misma incertidumbre.

Donde más falla es en los shows 100% cortesía: `ft_evt_0002` se queda 31
personas corto. Cuando no hay ni una entrada pagada, todo depende del "quién" y
el margen de error se duplica.

## Con cuatro horas más

1. **Proyectar la venta que falta.** Hoy solo modelo las entradas emitidas. Con
   la curva de venta de julio por día-a-la-fecha se estima cuántas más entran y
   de qué tipo, y los shows de fin de mes dejan de verse artificialmente vacíos.
2. **Revisar la zona gris del cruce con una segunda llave.** Los 2.354
   rechazados se resolverían mirando si el teléfono, aun sin coincidir, es de la
   misma ciudad, o cotejando `birthday` contra la fecha de compra.
3. **Modelar el reparto de cortesías.** Una cortesía por RRPP entra al 29% y una
   de taquilla al 50%. Con quién la entregó y a qué lista, el residuo de los
   shows de pura cortesía —el punto flaco— debería bajar.
4. **`boom_social`.** Lo miré y aporta poco por sí solo (0.344 → 0.372 según
   número de amigos), pero cruzarlo con si los amigos también tienen entrada
   para el mismo show es otra cosa: la gente va acompañada.
