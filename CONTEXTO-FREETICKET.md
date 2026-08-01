# FreeTicket — Contexto completo

> Documento de investigación generado a partir del scraping de `https://appfreeticket.com`
> **Fecha de captura:** 1 de agosto de 2026
> **Herramienta:** [Scrapling](https://github.com/D4Vinci/Scrapling) v0.4.12 (`scrape_freeticket.py`)
> **Cobertura:** 150 páginas públicas + `llms.txt` + `design.md` + 2 contratos OpenAPI + repos de GitHub
> **Datos crudos:** `./scraped/` (`pages.json`, `pages/*.txt`, `raw/*`)

---

## 1. Qué es FreeTicket en una frase

Plataforma latinoamericana (base en Colombia) de **venta de entradas + membresías de artista**, que combina una tiquetera B2C con un motor de suscripciones tipo Patreon, para que artistas independientes controlen su público, sus precios y sus datos sin intermediarios.

Su propia definición, del footer del sitio:

> *"La plataforma de tickets y membresías para artistas independientes."*

Y del `llms.txt` (el documento que ellos mismos escriben para agentes de IA):

> *"FreeTicket es la plataforma latinoamericana para descubrir eventos, comprar entradas (boletas) con código QR y suscribirse a las membresías de artistas, venues y organizadores."*

---

## 2. Identidad oficial

| Dato | Valor |
|---|---|
| Sitio oficial | `https://appfreeticket.com` |
| Subdominios de organización | `https://[slug].appfreeticket.com` (páginas públicas de cada artista) |
| Panel administrativo | `https://admin.appfreeticket.com` (privado — también es el host de la API para la CLI) |
| Correo de soporte | `soporte@freeticket.us` / `contacto@freeticket.us` |
| WhatsApp | +57 315 036 9479 |
| Instagram | [@freeticketlat](https://instagram.com/freeticketlat) |
| TikTok | [@freeticketlat](https://www.tiktok.com/@freeticketlat) |
| YouTube | [@freeticketlat](https://www.youtube.com/@freeticketlat) |
| GitHub | [github.com/AppFreeticket](https://github.com/AppFreeticket) |
| País | Colombia ("Hecho con amor en Colombia") |
| Idioma | Español neutro (LATAM), sin voseo |
| Moneda principal | COP (membresías soportan USD, MXN, EUR y más) |

**Nota de dominios:** el dominio de marca para correo es `freeticket.us`, pero el producto vive en `appfreeticket.com`. Los términos legales todavía mencionan subdominios `[artista].freeticket.us` mientras que la implementación real usa `[slug].appfreeticket.com` — inconsistencia documental vigente.

---

## 3. Historia y propuesta de valor

De la página `/nosotros`, en su propia voz:

- **13 años produciendo comedia en vivo** — "desde bares con 50 sillas hasta el Movistar Arena".
- El equipo viene de la producción, no del software. Construyeron FreeTicket *desde adentro*: primero una app para que sus propios fans descargaran entradas, luego membresías, luego una comunidad.
- La tesis central: **"Llenar un evento no es vender tickets — es construir una comunidad que quiera volver."**
- La validación que citan: *"si FreeTicket dejara de existir mañana, la comunidad seguiría."*

### Los cuatro pilares que declaran

1. **El artista controla su mundo** — su público, sus precios, sus reglas, sin pedir permiso.
2. **El fan es el protagonista** — no un número en una base de datos.
3. **Preventas sin revendedores** — las preventas llegan a quien de verdad las quiere.
4. **Los datos no se los queda nadie** — relación directa artista ↔ fan.

El punto 4 está respaldado contractualmente: la cláusula 9 del servicio B2B declara que los datos de compradores y suscriptores **son propiedad del Usuario B2B**, y FreeTicket actúa solo como encargado del tratamiento. Es un diferenciador real frente a las tiqueteras tradicionales, que retienen la base de datos.

---

## 4. Modelo de negocio

### 4.1 Suscripción B2B — tres tiers

| Tier | Incluye |
|---|---|
| **Spark** (básico) | Dashboard, creación y publicación de eventos, venta de tickets con múltiples tipos y precios, cortesías, asignación de validadores de puerta |
| **Star** (estándar) | Todo Spark + módulo de **Membresías de Artista** (sin streaming), base de datos de compradores/suscriptores exportable en CSV/Excel, mensajes directos con fans |
| **Icon** (premium) | Todo Star + **Contenido Exclusivo on demand**, **transmisiones en vivo** con integración OBS/RTMP, **página web propia en subdominio**, métricas avanzadas (top fans, top miembros), early access para suscriptores |

Facturación mensual, semestral o anual. Upgrade con efecto inmediato y prorrateo; downgrade al siguiente ciclo.
**Los precios de los tiers no están publicados en el sitio público**, pese a que los términos dicen que lo están.

### 4.2 Comisiones transaccionales

| Concepto | Comisión |
|---|---|
| **Ticket Service** | **10 %** sobre el valor base de cada ticket vendido |
| **Membresías de fans** | **20 %** sobre lo que el artista cobra a cada suscriptor |
| **Cortesías** | 10 % fijo por cada cortesía generada |

- Se descuentan automáticamente de cada transacción.
- **Liquidación a 15 días hábiles** tras el cierre del evento o período.
- El Ticket Service aplica **incluso a tickets de cortesía** (precio base $0); lo absorbe el organizador o se traslada al receptor, según configuración (`organizerAbsorbsFee` en la API).
- En caso de terminación por causa del Usuario B2B, los fondos pueden retenerse hasta **90 días**.

Modelo de ingresos resultante: **suscripción SaaS + take rate transaccional + take rate de suscripciones de fans**. El 20 % sobre membresías es notablemente más alto que el 10 % de tickets — la membresía es el motor de margen.

### 4.3 Tipos de usuario B2B

- **Artistas** — comediantes, músicos, actores, creadores de contenido.
- **Venues** — recintos; tienen un módulo extra de **productos/upsell post-compra** (combos, consumibles), activable por toggle en el registro.
- **Productores** — agencias o personas que organizan en nombre de terceros.

Un mismo correo puede tener múltiples cuentas B2B activas simultáneamente (multi-workspace).

---

## 5. Producto — qué hace hoy

### 5.1 Lado fan (B2C)

- **Descubrimiento**: catálogo de eventos con filtros por texto, ciudad y rango de fechas; páginas de artista, venue y comunidad.
- **Compra**: selección de función → tipo de ticket → resumen con precio base + Ticket Service → pago.
- **Asientos numerados**: mapa del recinto con selección de silla, reserva temporal mientras se completa la compra (rutas `/eventos/<slug>/sillas?date=<id>`). La API expone `seatsioCategoryKey`, lo que indica integración con **seats.io**.
- **Pago**: **MercadoPago** — tarjeta crédito/débito, **PSE**, Nequi, Daviplata. FreeTicket no almacena datos de tarjeta.
- **Entrega**: ticket digital con **QR único**, enviado en **PDF por correo** y disponible en "Mis entradas".
- **Transferencia de tickets**: función gratuita por correo del destinatario; el ticket original se invalida. Solo es válido el QR que se escanee primero.
- **Validación en puerta**: escaneo del QR **desde el navegador móvil** del validador — sin instalar app.
- **Membresías**: suscripción a planes de artista con beneficios (preventa exclusiva, entrada incluida, descuentos, contenido exclusivo, merch). Gestión y cancelación desde el perfil.
- **Comunidad**: feed con publicaciones, videos exclusivos, reacciones y comentarios con respuestas; las publicaciones pueden vincularse a un evento y muestran su tarjeta.

### 5.2 Lado artista/organizador (B2B)

- Dashboard con creación y publicación de eventos, múltiples fechas por evento, tipos de ticket con capacidad, precio, visibilidad y ventana de venta.
- **Zona horaria explícita por evento** (selector con buscador) — resolvieron un bug de horas desplazadas en junio de 2026.
- **Cortesías** y **validadores de puerta** asignables.
- **Cupones de descuento** (porcentaje o monto fijo, con límite de usos y vigencia).
- **Preventas y entradas exclusivas para miembros** — con cuenta regresiva visible en la página del evento.
- **Membresías**: planes con nombre libre ("Backstage", "VIP", "Inner Circle") y beneficios predeterminados; ciclos MONTHLY / QUARTERLY / ANNUAL / LIFETIME; multi-divisa.
- **Live**: transmisiones vía OBS/RTMP con Stream Key propia; videos on demand.
- **Reportes**: KPIs, ventas por función, series temporales, inventario, top fans, exports CSV/Excel de compradores, asistentes y suscriptores.
- **Liquidaciones**: resumen descargable por evento, con aviso por correo al cierre.
- **Verificación de identidad**: subida de RUT y certificación bancaria; revisión manual < 24 h; acelera el pago de liquidaciones.
- **Compartir acceso**: enlace de solo lectura a las métricas de un evento para artistas, socios o patrocinadores, sin dar acceso al panel completo.
- **Ficha de cliente**: todas las entradas compradas, historial de transacciones y dispositivos usados por cada comprador.

### 5.3 Cumplimiento normativo colombiano

- **Registro PULEP** visible en cada página de evento (ej. `DOC702`) — obligatorio para espectáculos públicos en Colombia.
- Rol **`MINCULTURA`** en el modelo de permisos de la API — acceso específico para el Ministerio de Cultura, presumiblemente para reportería regulatoria de PULEP.
- **Sin derecho de retracto** para eventos, amparado en el art. 47 num. 3 de la Ley 1480 de 2011 (Estatuto del Consumidor).
- Tratamiento de datos bajo **Ley 1581 de 2012** (habeas data).
- Referencias a **SAYCO/ACINPRO** (derechos de autor musicales) como responsabilidad del organizador.
- **Siigo** aparece en el reporte de conciliación financiera → facturación electrónica DIAN.

---

## 6. Arquitectura y stack técnico

Deducido de `design.md`, cabeceras HTTP y URLs de assets:

| Capa | Tecnología |
|---|---|
| Framework | **Next.js 16** (App Router) + **React 19**, bundler **Turbopack** |
| Hosting | **Vercel** (header `x-vercel-id`, chunks con `?dpl=dpl_...`) |
| Estilos | **Tailwind CSS v4** (`@theme inline`, sin `tailwind.config.js`) |
| Componentes | **shadcn/ui** estilo `base-nova` sobre primitivos **`@base-ui/react`** (no Radix) |
| Iconos | `@remixicon/react` + set de marca propio `BrandIcon` (WEBP pre-tintados) |
| Storage de media | **Supabase Storage** (`wfcsrawyrduewoblqdfy.supabase.co`) |
| Pagos | **MercadoPago** |
| Asientos numerados | **seats.io** (campo `seatsioCategoryKey`) |
| Facturación | **Siigo** |
| IDs | **cuid** (ej. `cmrwqimcq000104l7x9duwn5v`) |
| Toaster | `sonner` |
| Backend/API host | `admin.appfreeticket.com` |

**Multi-tenancy por host**: un middleware resuelve el tenant desde el hostname (`src/lib/tenant-host.ts`). El atributo `data-surface` en `<html>` conmuta entre dos superficies visuales fijas — **Stage** (negro, B2C) y **Dashboard** (claro, B2B) — resueltas por host, no por preferencia de usuario.

**SEO y datos estructurados**: el sitio renderiza JSON-LD en todas las páginas — `Organization`, `WebSite`, `BreadcrumbList`, y **232 bloques `Event`** con `offers`, `location` + `geo` (lat/lon), `organizer` y `performer`. El catálogo completo es extraíble sin API.

---

## 7. Superficie para agentes de IA y desarrolladores

**Este es el aspecto más relevante para un hackathon.** FreeTicket es explícitamente *AI-native*: publica su dominio como contrato consumible por agentes.

### 7.1 Documentos de descubrimiento

| Recurso | URL |
|---|---|
| `llms.txt` | `https://appfreeticket.com/llms.txt` |
| Design system | `https://appfreeticket.com/design.md` |
| OpenAPI público | `https://appfreeticket.com/api/public/openapi.json` |
| OpenAPI B2B v1 | `https://appfreeticket.com/api/v1/openapi.json` |
| Sitemap | `https://appfreeticket.com/sitemap.xml` |

### 7.2 API pública B2C — `FreeTicket Public API` v0.3.0

Base: `https://appfreeticket.com/api/public` · **Sin autenticación**, rate limit estricto, anónima.

| Método | Endpoint | Qué hace |
|---|---|---|
| `GET` | `/events` | Catálogo de eventos PUBLISHED con función futura. Filtros: `q`, `city`, `from`, `to`, `page`, `pageSize` (≤50), `sort` (`date_asc\|price_asc\|price_desc`) |
| `GET` | `/events/{slug}` | Ficha del evento: descripción, fechas con venue/ciudad/timezone, precio "desde" |
| `GET` | `/events/{slug}/availability` | **Stock en vivo** por función y tipo de ticket (capacidad − vendido − reservado) |
| `POST` | `/orders` | Crea venta PENDING + reserva de stock **30 min** y devuelve `checkoutUrl` de MercadoPago |
| `GET` | `/orders/{id}` | Estado: `pending \| paid \| expired \| cancelled`; al pagar incluye los códigos de ticket |
| `POST` | `/tickets/{code}/resend` | Reenvía el QR al correo del comprador (rate limit 1/min por código) |

Verificado en vivo el 1-ago-2026: los tres `GET` responden `200` sin credenciales, con envoltorio `{"data": ...}`.

**Restricciones de `POST /orders`** — solo admisión general (no numerado, no members-only), eventos PUBLISHED con venta abierta y de **un mismo organizador** por orden. El cupo se protege con transacción **Serializable**. *El agente nunca procesa el pago*: solo entrega el link de checkout.

### 7.3 API B2B — `FreeTicket B2B API` v1.5.0

Base: `https://appfreeticket.com/api/v1` · Auth: `Authorization: Bearer <key>` o `x-api-key`, workspace activo vía header **`X-Workspace-Id`**.

**~70 endpoints** agrupados en: `auth` (Device Flow RFC 8628), `me`, `events`, `event-dates`, `ticket-types`, `sales`, `tickets` (checkin/access/resend), `membership-plans`, `subscriptions`, `venues`, `staff`, `discounts`, `webhooks`, `api-keys`, `reports`, `customer` (SSO headless).

Detalles notables:

- **Device Authorization Grant (RFC 8628)** para login de CLI sin navegador embebido.
- **API keys con scope** `read` (solo GET/HEAD) o `write`; el secreto en claro se muestra **una sola vez**.
- **Roles**: `SUPER_ADMIN`, `ADMIN`, `STAFF`, `VIEWER`, `MINCULTURA`.
- **Webhooks** firmados con HMAC — pero solo **dos eventos disponibles**: `sale.confirmed` y `sale.refunded`.
- **Check-in de puerta** por API: `POST /tickets/{code}/checkin` (consume) y `GET /tickets/{code}/access` (consulta sin consumir).
- **Reportes**: `summary`, `by-event`, `timeseries` (day/week/month), `inventory`, `reconciliation` (conciliación CFO: MercadoPago ↔ venta ↔ factura Siigo), y exports de `attendees` / `buyers` / `subscribers` (máx 5000 filas).
- **`POST /sales/{id}/refund` solo marca la venta como REEMBOLSADA — NO ejecuta el reembolso en MercadoPago.** El reembolso real es un paso manual fuera de la plataforma.
- **SSO headless** (`/customer/me`, `/customer/tickets`, `enterprise-exchange`) para integrar la identidad del comprador en apps de terceros.

### 7.4 Herramientas oficiales (todas MIT, en GitHub)

| Repo | Qué es |
|---|---|
| [`ai-native`](https://github.com/AppFreeticket/ai-native) | Paraguas con submódulos de CLI + MCP + skills. Patrón **contract-first**: el backend define el OpenAPI y ambos clientes se regeneran desde ahí con un agente de contract-sync |
| [`freeticket-cli`](https://github.com/AppFreeticket/freeticket-cli) | Binario **`ft`** (`npm i -g @freeticket/cli`). Node ≥ 20 |
| [`freeticket-mcp`](https://github.com/AppFreeticket/freeticket-mcp) | Servidor **MCP** (`npx -y @freeticket/mcp`) |
| [`agent-skills`](https://github.com/AppFreeticket/agent-skills) | Skills instalables con `npx skills add` |

**CLI `ft`** — `ft login` (device flow, guarda en `~/.freeticket/config.json` con permisos `0600`) o `ft login --key ft_live_xxx` para CI. Grupos: `events`, `event-dates`, `ticket-types`, `tickets`, `sales`, `plans`, `subscriptions`, `discounts`, `webhooks`, `venues`, `staff`, `reports`, `workspace`. Salidas `--json`, `--csv`, `--raw`, `--columns`. Variables: `FT_API_URL` (default `https://admin.appfreeticket.com`), `FT_API_KEY`, `FT_WORKSPACE_ID`.

**MCP server** — ~40 tools B2B + **3 tools públicas B2C sin credenciales** + 13 de superadmin. Auth por sesión de `ft login`, Bearer, **OAuth 2.1** (para claude.ai) o variables de entorno. Credenciales cifradas AES-256-GCM dentro del token; el servidor es stateless. Las operaciones destructivas (`*_delete`, `*_refund`, `*_cancel`) exigen `destructiveHint` y confirmación explícita.

**Skills disponibles:**
- `freeticket-cli` — opera la CLI (auth, CRUD, publicación, refunds, conciliación CFO, exports).
- `freeticket-eventos` — asesor de eventos con la voz de marca y las reglas de producto; audita datos en vivo y recomienda estrategias de venta y retención. Invoca a `freeticket-cli` para traer los datos.

```bash
npx skills add AppFreeticket/agent-skills@freeticket-cli
npx skills add AppFreeticket/agent-skills@freeticket-eventos
```

---

## 8. Design system (resumen operativo)

Fuente completa: `scraped/raw/design.md`. Lo esencial si hay que construir UI en su marca:

**Paleta:**
- `FT Yellow` **#FFD102** — el reflector: CTAs primarios, foco, estados activos. **Siempre texto oscuro encima, nunca blanco.**
- `FT Teal` **#1EBBB2** — interactivo y dominio **Tickets**.
- `FT Purple` **#5615C1** — dominio **Membresías**, exclusividad.
- `FT Base` **#070707** — negro de marca. **Nunca `#000000` puro.**
- `Live` **#FF4D2E** — dominio de transmisiones (ember), distinto de `destructive` #E5484D.

**Dos superficies fijas (no es dark mode conmutable):** *Stage* negro para B2C, *Dashboard* claro para B2B.

**Tipografía:** **Archivo** (Google Fonts) para cuerpo y display — jerarquía por peso (400/500 → 900), no por familia. **Geist Mono** para QR, IDs, timestamps y montos.

**Forma:** botones, inputs, select-triggers, badges y tags son **pills** (`rounded-full`); cards, popovers y menús usan `radius-lg` **20px**. Excepción documentada: textarea se queda en `rounded-lg`.

**Movimiento:** easing de marca `cubic-bezier(0.22, 1, 0.36, 1)`; spring `cubic-bezier(0.34, 1.56, 0.64, 1)` para toggles y `:active`. Duraciones 120/200/360 ms. **Glow** en hover/focus es la interacción central, no un anti-patrón. Animar solo `transform`, `opacity` y `box-shadow`. Siempre respetar `prefers-reduced-motion`.

**Anti-patrones baneados:** `#000000` puro · texto blanco sobre amarillo · acentos fuera de paleta · **emojis en la UI** · spinners circulares (usar skeletons) · fila de 3 tarjetas iguales · hex hardcodeado · `<img>` crudo · `BrandIcon` en el dashboard B2B · clichés de copy AI ("Eleva", "Seamless", "Unleash", "Next-Gen") · nombres placeholder ("John Doe", "Acme").

**Copy:** español neutro, tú o impersonal, **nunca voseo**. Primera persona plural en momentos de marca, nunca "la plataforma" en tercera persona.

---

## 9. Estado real del catálogo (1-ago-2026)

Inventario efectivamente encontrado en el sitio público:

- **60 eventos** con página propia.
- **8 venues**: Boom Stand Up Bar (Bogotá), Teatro Calima (Cali), Teatro Guillermo Valencia (Popayán), Teatro Imperial UdeNar (Pasto), Teatro Sua (Soacha), Teatro Zea Mays (Chía), Auditorio Municipal Mosquera, Café Internet.
- **7 artistas/organizaciones**: CHIMUELO, Gabriel Murillo, Johana Velandia, Diego Mateus, Andrés Torres, Café Internet, Freeticket Producción.
- **4 subdominios tenant activos**: `chimuelo`, `gabriel-murillo`, `freeticket-produccion`, `cafe-internet`.
- **2 comunidades públicas**: Café Internet (1 miembro) y freekikeros (0 miembros, COP 100.000/mes).

**Composición:** el catálogo es prácticamente **100 % comedia stand-up colombiana**. Las giras dominantes son *RUMBO AL ESPECIAL* de CHIMUELO (27 fechas por todo el país) y *GORDO Y FEO* de Gabriel Murillo (~14 ciudades).

**Rango de precios:** COP 25.000 – 80.000 por entrada general.

**Cobertura geográfica:** Bogotá, Medellín, Cali, Barranquilla, Cartagena, Bucaramanga, Pereira, Manizales, Armenia, Ibagué, Pasto, Popayán, Neiva, Pitalito, Garzón, Villavicencio, Yopal, Tunja, Sogamoso, Duitama, Zipaquirá, Chía, Mosquera, Soacha, Sopó, Girardot, La Dorada, Palmira, Rionegro, Ipiales.

---

## 10. Ritmo de desarrollo (changelog público `/novedades`)

25 entradas entre marzo y julio de 2026, etiquetadas como Novedad / Mejora / Corrección. Cronología de capacidades:

| Fecha | Hito |
|---|---|
| 15-mar-2026 | Membresías con beneficios |
| 10-abr-2026 | Mapa y dirección del venue en cada evento |
| 22-abr-2026 | Preventas anticipadas para miembros, con cuenta regresiva |
| 8-may-2026 | Selección de asiento en mapa del recinto |
| 20-may-2026 | Entrada en PDF por correo |
| 2-jun-2026 | Entradas exclusivas para miembros |
| 14-jun-2026 | Refuerzo anti-overselling en lanzamientos masivos |
| 15-jun-2026 | Liquidaciones consultables y descargables |
| 17-jun-2026 | Zona horaria por evento + fix de horas desplazadas |
| 18-jun-2026 | Pago con **PSE**; liberación inmediata de cupo tras pago rechazado |
| 21-jun-2026 | Reacciones y comentarios en comunidad |
| 24-jun-2026 | Multi-divisa en membresías · compartir métricas por enlace · ganancias por función · ficha de cliente · portada 16:9 · navegación móvil |
| 30-jun-2026 | Selector de silla optimizado para móvil |
| 1-jul-2026 | Feed unificado de videos y publicaciones |
| 2-jul-2026 | Verificación de identidad (RUT + certificación bancaria) |
| 3-jul-2026 | **Transmisiones en vivo** y videos exclusivos |
| 5-jul-2026 | Autogestión de datos y membresías desde el perfil |

**Lectura:** desarrollo intenso y sostenido, con junio de 2026 como mes de mayor densidad. La plataforma es joven pero avanza rápido, y el foco del último trimestre se movió de *ticketing* hacia *comunidad, contenido y herramientas de organizador*.

---

## 11. Observaciones para el hackathon

Brechas y tensiones detectables desde el sitio público. Son hipótesis basadas en datos observables, no verdades confirmadas — el sitio público no muestra la operación interna.

**El motor de membresías está casi sin usar.** Es el diferenciador central de la marca, el que sostiene el discurso completo de `/nosotros` y el de mayor margen (20 %), pero solo hay **2 comunidades públicas con 1 y 0 miembros**. Todos los perfiles de artista muestran **0 seguidores**. La distancia entre el relato y el uso real es el hallazgo más grande del scraping.

**El catálogo es monocultivo.** 100 % comedia stand-up, concentrado en 2 giras de 2 artistas. La marca habla de "artistas" en general y el JSON-LD los marca como `MusicGroup`, pero no hay música en el inventario. Riesgo de concentración: si CHIMUELO o Gabriel Murillo se van, se va el catálogo.

**Los subdominios tenant están vacíos.** Las rutas `/eventos` y `/comunidades` de los 4 subdominios devuelven páginas sin contenido (~57 caracteres de texto), pese a que la feature "página web propia" es lo que justifica el Tier Icon.

**El reembolso no está cerrado.** `POST /sales/{id}/refund` solo marca la venta como reembolsada; el dinero se devuelve manualmente en MercadoPago. Es un hueco operativo con consecuencias reales: la política de cancelación promete devolución total en 10 días hábiles.

**Los webhooks son mínimos.** Solo `sale.confirmed` y `sale.refunded`. No hay eventos de check-in, de membresía (alta/baja/renovación), de publicación de evento ni de agotamiento de stock — lo que limita mucho las integraciones reactivas de terceros.

**Los documentos legales tienen placeholders sin resolver.** Aparecen literalmente `[10] días hábiles`, `[5] días hábiles`, `[30] días` y `[90] días` en los términos publicados. Los precios de los tiers B2B se declaran "publicados en nuestro sitio web" pero no existen en ninguna página pública.

**Falta el centro de ayuda.** Los legales remiten a `appfreeticket.com/ayuda`, que no está en el sitemap ni enlazado en la navegación.

### Superficies donde se puede construir sin fricción

1. **API pública sin auth** — descubrimiento, disponibilidad en vivo y creación de órdenes con checkout de MercadoPago. Se puede montar un cliente alterno (bot, agente, kiosco, WhatsApp) sin pedir credenciales.
2. **MCP server oficial** — el dominio B2B completo como tools; ideal si el problema se resuelve con un agente conversacional.
3. **CLI `ft`** — automatización desde terminal y CI.
4. **JSON-LD en todas las páginas** — catálogo estructurado extraíble sin API.
5. **`design.md`** — permite generar UI coherente con la marca sin adivinar tokens.
6. **Device Flow + API keys con scope** — autenticación limpia para herramientas de terceros.

---

## 12. Cómo se obtuvo este contexto

```powershell
# Entorno
python -m venv .venv
.venv\Scripts\python.exe -m pip install "scrapling[fetchers]"

# Scraping completo (150 páginas + recursos)
.venv\Scripts\python.exe scrape_freeticket.py
```

`scrape_freeticket.py` usa `Fetcher.get` de Scrapling con `stealthy_headers=True` — el sitio es Next.js con SSR, así que el HTML llega renderizado y no hace falta navegador (`StealthyFetcher` / `DynamicFetcher`). El crawler hace BFS desde el sitemap y los enlaces internos, respeta los `Disallow` de `robots.txt` para páginas privadas, y aplica 0,4 s de espera entre peticiones.

**Salidas en `./scraped/`:**

| Ruta | Contenido |
|---|---|
| `pages.json` | 150 páginas con título, headings, meta, JSON-LD, texto, links e imágenes |
| `pages/*.txt` | Texto plano legible de cada página |
| `raw/llms.txt` | Documento oficial de FreeTicket para agentes de IA |
| `raw/design.md` | Design system completo |
| `raw/openapi_public.json` | Contrato API pública B2C |
| `raw/openapi_v1.json` | Contrato API B2B (113 KB) |
| `raw/robots.txt`, `raw/sitemap.xml` | Reglas de crawling e índice de URLs |

**Nota sobre `robots.txt`:** el archivo bloquea `/api/` para crawlers genéricos, pero el propio `llms.txt` publica los dos contratos OpenAPI como recursos explícitos para agentes y desarrolladores ("*spec OpenAPI 3.1 sin autenticación; describe la forma del contrato para descubrimiento y codegen de clientes*"). Se descargaron sobre esa base. Las verificaciones en vivo contra la API se limitaron a peticiones `GET` de lectura; no se creó ninguna orden ni se mutó estado.

---

*Documento generado el 1 de agosto de 2026 a partir de datos públicos de appfreeticket.com.*
