# Las dos plataformas y el cruce

## Regla que no se negocia

**Una petición toca UNA plataforma.** Boom y FreeTicket son sistemas separados
con credenciales separadas, y ningún endpoint devuelve datos del otro. El cruce
ya está hecho y vive en `outputs/matches.csv`; no hay que rehacerlo por consulta.

Los `event_id` tampoco se cruzan: `bm_evt_*` (Boom) y `ft_evt_*` (tiquetera) son
universos distintos.

## Qué hay en cada una

### Boom — membresías. La historia larga.

| recurso | filas | contenido |
|---|---|---|
| `users` | 6.000 | `boom_user_id, first_name, last_name, email, phone, city, birthday, has_membership, points` |
| `profile` | 6.000 | lo anterior + `tickets_total, tickets_used, use_rate, friends_count` |
| `tickets` | 22.325 | `boom_ticket_id, boom_user_id, event_id, type, source, used, date_used` |
| `social` | 6.000 | `friends_count` |

`type` ∈ `membresia | consumo_minimo`. **Importan por separado**: membresía entra
al 46.5%, consumo mínimo al 74.9%.

### FreeTicket — tiquetera. Julio y agosto.

| recurso | filas | contenido |
|---|---|---|
| `artists` | 14 | residencia y asistencia de julio |
| `events` | 62 | 32 de julio, 30 de agosto |
| `sales` | 6.383 | `sale_id, event_id, buyer_name, buyer_email, buyer_phone, qty, channel, purchased_at` |
| `tickets` | 11.931 | **una fila por entrada**: `ticket_type, price, checked_in` |

`ticket_type` ∈ `General | Preferencial | VIP | Cortesía`.
`channel` ∈ `WEB | BOX_OFFICE | ADMIN | RRPP`.
`checked_in` es true/false en julio y **null en agosto**.

## El cruce

No hay ID compartido y las llaves están sucias a propósito: correos con alias
`+algo` o dominio mal escrito, teléfonos en cinco formatos o con dos dígitos
cambiados, nombres sin tildes o con el apellido primero.

**Resultado: 3.963 de 6.383 ventas cruzadas (62.1%).**

### Por qué el 37.9% queda vacío a propósito

Una parte grande de los compradores **no existe en Boom**: son nuevos.
Inventarles un match no es un error neutro — contamina justo la señal que hace
útil el cruce.

Solo el **email** y el **teléfono** anclan un match: en Boom son únicos (0
duplicados). El **nombre no puede**, porque 1.144 nombres se repiten y 885 los
comparten más de tres personas. El nombre solo confirma o **desmiente**: un
correo exacto con nombre ajeno es el correo de la pareja, y ahí el match se
rechaza.

### El falso positivo que casi entra

Agrupar por el "núcleo" del correo (`juanrestrepo316` → `juanrestrepo`) sumaba
2.354 matches. Son falsos: ese núcleo lo comparten entre 4 y 7 usuarios de Boom
porque equivale al nombre. Se detectó porque el grupo se comportaba como los
compradores nuevos (43.6% en cortesías) y no como los que sí están en Boom
(36.4%).

## Privacidad

Los datos crudos traen correos y teléfonos. **No los expongas en una respuesta.**
Usa `boom_user_id` cuando haya que identificar a alguien, y agrega cuando se
pueda ("47 fieles en Bogotá" en vez de la lista con sus correos).

## Volver a bajar los datos

```bash
python run.py --force
```

El token se obtiene una vez, sin registro:

```bash
curl "https://hackathon-freeticket.vercel.app/api/setup?handle=TU-NOMBRE" -o setup.json
```
