# Investigación — Restricciones ambientales e instrucciones de seguridad por producto

## AgroNexo · Tarjeta Trello "Textos legales y de seguridad" (Sprint 11, Release 3)

&nbsp;

> **Propósito:** completar los campos `restricciones_ambientales` e `instrucciones_seguridad` agregados a `productos_fitosanitarios` en la migración `0018`, para los 21 productos del catálogo (migración `0015`).

> **⚠️ Estado: borrador para validación profesional.** El texto de este documento fue armado a partir de marbetes SENASA (cuando había número de registro disponible), fichas técnicas/hojas de seguridad de fabricantes y normativa provincial. **No reemplaza la revisión de un ingeniero agrónomo matriculado ni de responsable de cumplimiento** antes de cargarlo en producción — coincide con el pedido pendiente ya anotado en [esq_datos_prod_fito.md](esq_datos_prod_fito.md) ("Revisado — pendiente") y [ind_veg_asoc_causas.md](ind_veg_asoc_causas.md) ("Validación con ingeniero agrónomo — PENDIENTE").

&nbsp;

---

## 1. Corrección importante sobre la ley provincial

En una conversación previa de este mismo trabajo se asumió, sin verificar, que la **Ley 6.312** era la ley de agroquímicos de Chaco. Es un error: la Ley 6.312 (con decreto reglamentario, publicada por CASAFE) corresponde a **Santiago del Estero**. Varias provincias reutilizan números de ley de forma independiente, así que el número solo no alcanza como identificador.

La ley vigente en **Chaco** es la **Ley 7032 — Ley de Biocidas** (sancionada 2012, en vigencia desde 2012 + 90 días, deroga la Ley 3378), texto verificado completo contra el PDF oficial publicado por CASAFE. Es la que corresponde citar para el foco NEA/Chaco del proyecto.

&nbsp;

## 2. Restricciones generales de la Ley 7032 (Chaco) — aplican a todos los productos

Estas restricciones **no son por producto** — son obligaciones legales que rigen cualquier aplicación de biocida en la provincia, independientemente del producto elegido. Quedan documentadas acá porque son la base normativa, pero **no deberían repetirse literalmente en el campo `restricciones_ambientales` de cada fila** — ver nota de diseño en la sección 4.

| Artículo | Restricción |
|---|---|
| Art. 26 | Prohibida la aplicación **aérea** a menos de **1.500 m** de centros urbanos, establecimientos educativos/sanitarios, reservas y fuentes/reservorios de agua. Prohibida la aplicación **terrestre** a menos de **500 m** de los mismos puntos. |
| Art. 30 | El aplicador debe informar la tarea al municipio y a la comunidad cercana con **48 hs de anticipación** (lugar, día, hora de inicio/fin, producto). |
| Art. 35 | Prohibida la venta y la intervención en tareas de aplicación/manipulación a **menores de 18 años** y a **mujeres embarazadas o en lactancia**. |
| Art. 21, 40–44 | Toda aplicación requiere **receta agronómica** firmada por ingeniero agrónomo matriculado, que debe especificar producto, dosis, **período de carencia (PC)** y **período de reingreso (PR)** — archivada 5 años. |
| Art. 39 | Obligación de contar permanentemente con asesoramiento técnico de un ingeniero agrónomo matriculado en el Consejo Profesional de Chaco. |
| Art. 32 | Quienes se dediquen al expendio/aplicación deben someterse a examen toxicológico y control semestral. |

Fuente: [Ley 7032 — Ley de Biocidas, Chaco (texto completo, CASAFE)](https://www.casafe.org/wp-content/uploads/recetas-agronomicas/ley-de-biocidas-7032-12-chaco.pdf).

&nbsp;

## 3. Catálogo — 21 productos

Convenciones de la tabla:
- **Restricciones ambientales** — específicas del producto (toxicidad acuática, abejas, deriva a cultivos sensibles), no repite las de la sección 2.
- **Instrucciones de seguridad** — EPP, tiempo de reingreso, manejo.
- **Confianza** — 🟢 dato con marbete/SDS específico del producto o principio activo consultado · 🟡 dato genérico del principio activo/clase química, sin marbete puntual localizado · 🔴 no se encontró ficha de seguridad específica, texto es una estimación por clase de producto y **requiere confirmación antes de cargar**.

&nbsp;

### 3.1 Herbicidas

**Glifosato** (SENASA RE-27899) 🟡
- *Restricciones:* Tóxico para organismos acuáticos — no contaminar cursos de agua, embalses ni fuentes de agua.
- *Seguridad:* Usar protector facial, guantes, botas de goma, camisa y pantalón de manga larga durante preparación y aplicación; no ingerir ni inhalar; lavar piel expuesta con agua y jabón al finalizar.
- Fuente: [CASAFE — Seguridad del Glifosato](https://www.casafe.org/pdf/Position-Paper-seguridad-Glifosato.pdf); marbete SENASA genérico (no se localizó el PDF puntual de RE-27899).

**2,4-D** (SENASA RE-11256) 🟡
- *Restricciones:* Tóxico para organismos acuáticos con efectos duraderos. Alto riesgo de deriva sobre cultivos de hoja ancha sensibles (algodón, vid, hortícolas linderos) — no aplicar con viento hacia esos lotes.
- *Seguridad:* EPP completo según etiqueta (guantes, protección ocular, ropa que cubra piel); evitar contacto con piel/ojos/ropa.
- Fuente: hojas de seguridad comerciales de 2,4-D amina 480 (Chile/Perú) — mismo principio activo, sin marbete argentino RE-11256 puntual localizado.

**Atrazina** (SENASA RE-8745) 🟡
- *Restricciones:* Persistente — detectada en aguas superficiales y subterráneas. Mantener franja de seguridad de **10 m en aplicación terrestre** y **100 m en aplicación aérea** respecto a cursos de agua; no aplicar si hay riesgo de escorrentía.
- *Seguridad:* EPP completo durante preparación, mezcla y aplicación; no comer/beber/fumar durante la tarea; almacenar en lugar seco y ventilado, no junto a alimentos.
- Fuente: fichas técnicas Invesa/Tridente (genéricas por principio activo).

**Cletodim** (SENASA RE-32104) 🟡
- *Restricciones:* No aplicar con viento superior a 4 km/h; no aplicar si se esperan lluvias dentro de las 3 hs siguientes; usar boquilla antideriva.
- *Seguridad:* Reingreso al área tratada entre 24 y 48 hs después de la aplicación (varía según formulación comercial — confirmar en marbete específico).
- Fuente: fichas técnicas YPF Agro / Agrospec.

**Imazetapir** (sin RE localizado — fuente INTA NEA 2023) 🟡
- *Restricciones:* Alto efecto residual en el suelo — respetar 120 días entre la aplicación y la siembra de un cultivo subsiguiente sensible (ej. maíz no tolerante a imidazolinonas).
- *Seguridad:* Clasificación toxicológica Clase IV (normalmente no ofrece peligro) — EPP estándar: guantes y protección ocular.
- Fuente: FDS Formulagro / Hortus (Imazetapir 10-10.6%).

&nbsp;

### 3.2 Fungicidas

**Azoxistrobina** (sin RE localizado — fuente INTA EEA Reconquista 2022) 🟡
- *Restricciones:* Muy tóxico para organismos acuáticos — evitar contaminación de cuerpos de agua. Prácticamente no tóxico para abejas.
- *Seguridad:* Reingreso 24 hs después de la aplicación. EPP: gorro y overol de algodón, anteojos herméticos, máscara para polvo/vapores tóxicos, guantes y botas de neopreno.
- Fuente: fichas técnicas comerciales de combinaciones Azoxistrobina + Ciproconazol (ROBINZOL/AMISTAR ZTRA).

**Trifloxistrobina** (SENASA RE-40612) 🟡
- *Restricciones:* No contaminar fuentes ni cursos de agua; especial atención a napas subterráneas en suelos vulnerables. Máximo 4 aplicaciones por año (dato de Propiconazol, principio activo acompañante).
- *Seguridad:* Usar solo en exteriores o lugar bien ventilado; no respirar polvo/niebla; guantes de protección; evitar ingestión, inhalación y contacto con piel.
- Fuente: ficha técnica Propiconazol 250 EC (Agrospec/SAG Chile) — genérica por principio activo acompañante, no de la combinación específica.

**Mancozeb** (sin RE localizado — fuente INTA EEA Sáenz Peña 2021) 🟡
- *Restricciones:* Muy tóxico para organismos acuáticos con efectos duraderos — no contaminar fuentes de agua de riego/consumo, no lavar equipos en ríos.
- *Seguridad:* Reingreso entre 12 y 48 hs según formulación (verificar etiqueta del producto específico); usar guantes como mínimo.
- Fuente: fichas Nufarm/Sumitomo/SAG Chile.

**Tebuconazol** (SENASA RE-36218) 🟡
- *Restricciones:* Tóxico para peces — no contaminar agua, alimentos ni forraje por eliminación del producto.
- *Seguridad:* Guantes, ropa, gafas y máscara de protección; lavarse concienzudamente tras la manipulación; no comer/beber/fumar durante el uso.
- Fuente: FDS Agrolac / SAG Chile.

**Carbendazim** (SENASA RE-28901) 🟡
- *Restricciones:* Muy tóxico para organismos acuáticos; puede causar defectos genéticos y dañar la fertilidad — no disponer producto, envases o residuos cerca de ríos, lagunas o sistemas de drenaje.
- *Seguridad:* Guantes, ropa y protección ocular/facial (puede irritar piel y ojos); no permitir el ingreso al área tratada hasta 24 hs después de la aplicación.
- Fuente: FDS Fidemax/Nufarm/Point.

&nbsp;

### 3.3 Insecticidas

**Clorpirifos** (sin RE localizado — fuente INTA NEA MIP soja 2023) 🟡
- *Restricciones:* Muy peligroso para abejas y para peces. No aplicar con abejas presentes; avisar a apicultores antes de aplicar para que cierren colmenas; no asperjar sobre apiarios activos; aplicar temprano en la mañana o al atardecer, fuera del horario de pecoreo. No contaminar lagos ni cursos de agua.
- *Seguridad:* No se localizó el detalle de EPP en las fuentes consultadas — usar EPP estándar de insecticida organofosforado (guantes, protección respiratoria, ropa que cubra el cuerpo) hasta confirmar en el marbete del producto comercial específico. 🔴 EPP sin confirmar.
- Fuente: proyecto de marbete Lanther / FDS Proquimur.

**Lambda-cihalotrina** (SENASA RE-31742) 🟢
- *Restricciones:* Clasificación "muy tóxico" para abejas — avisar a apicultores del área con al menos 48 hs de anticipación; aplicar en horarios de baja actividad de abejas; no aplicar durante floración; no aplicar con viento superior a 8 km/h ni temperatura mayor a 28°C.
- *Seguridad:* Mandil resistente a químicos, ropa que cubra el cuerpo, botas y gorra; gafas protectoras herméticas; protección respiratoria si hay formación de aerosol o neblina.
- Fuente: ficha técnica Agrospec / Sharda México.

**Imidacloprid** (SENASA RE-29876) 🟢
- *Restricciones:* Categoría toxicológica II (moderadamente peligroso, franja amarilla) — muy tóxico para abejas. No aplicar durante floración; no asperjar sobre colmenas activas (si no se pueden trasladar, cubrir la entrada durante la aplicación y aplicar fuera del horario de pecoreo).
- *Seguridad:* Evitar respirar polvo, vapor o aspersión del producto. Triple lavado de envases tras el uso, inutilizar perforando o triturando.
- Fuente: SAG Chile / contaminantesambientales.github.io.

**Spinosad** (sin RE localizado — fuente INTA EEA Sáenz Peña 2022) 🟡
- *Restricciones:* No aplicar durante floración ni en horario de forrajeo activo de abejas (aunque no haya floración aparente en el cultivo tratado); no aplicar sobre vegetación espontánea en flor. Máximo 2 aplicaciones por campaña, con 14 días de separación mínima entre ellas.
- *Seguridad:* Una vez seco (pocas horas después de la aplicación) deja de ser tóxico para abejas — igual debe evitarse aplicar durante floración activa.
- Fuente: guía de evaluación de riesgo para abejas (EPA) / Depto. de Agricultura de Florida.

**Thiamethoxam** (SENASA RE-41203) 🟡
- *Restricciones:* Altamente tóxico para abejas — no aplicar en floración ni cerca de colmenas, evitar aplicación al menos 15 días antes de la floración; avisar a apicultores con 48 hs de anticipación; franja de seguridad de 10 m en aplicaciones terrestres respecto a cursos de agua; nocivo para fauna benéfica.
- *Seguridad:* No se localizó el detalle específico de EPP en las fuentes consultadas. 🔴 EPP sin confirmar.
- Fuente: fichas técnicas Vecol / Actara / Engeo.

&nbsp;

### 3.4 Defoliantes

**Ethephon 48%** (sin RE localizado — fuente INTA EEA Sáenz Peña 2022) 🔴
- *Restricciones:* No se localizó ficha de seguridad específica del producto comercial. Clasificación toxicológica general del principio activo: moderadamente peligroso.
- *Seguridad:* No se localizó el detalle de EPP/reingreso — pendiente confirmar en marbete SENASA del producto comercial específico antes de cargar en BD.
- Fuente: EPA fact sheet Ethephon (genérico, sin marbete argentino localizado).

**Tiidiazurón + Diurón (TDZ+D)** (sin RE localizado — fuente INTA Chaco 2023) 🔴
- *Restricciones:* El Diurón es un herbicida residual — riesgo de persistencia en suelo y de deriva a cultivos vecinos sensibles. En España la autorización de tidiazurón como defoliante de algodón está acotada a una ventana de aplicación de pre-cosecha muy estrecha y una sola aplicación por ciclo — referencia de manejo prudente, no dato argentino.
- *Seguridad:* No se localizó ficha de seguridad de la combinación específica en esta búsqueda — **requiere investigación adicional o consulta directa al fabricante/CASAFE antes de cargar en producción**.
- Fuente: resoluciones del Ministerio de Agricultura de España (autorización excepcional) — sin marbete argentino localizado.

&nbsp;

### 3.5 Fertilizantes

**Urea 46% N** (sin RE localizado — fuente INTA NEA 2023) 🟢
- *Restricciones:* Evitar vertido a cursos de agua superficial o subterránea — riesgo de contaminación por escorrentía/lixiviación de nitrógeno si se aplica en exceso o cerca de cursos de agua.
- *Seguridad:* Gafas de seguridad, máscara con filtro si hay concentración elevada de polvo, guantes y ropa de protección; evitar generar polvo; no comer/beber/fumar durante la manipulación; lavarse las manos con agua y jabón después.
- Fuente: FDS Profertil / CIAFA.

**Superfosfato Triple 46%** (sin RE localizado — fuente INTA 2022) 🟢
- *Restricciones:* Evitar vertidos al agua; en caso de lluvia, evitar que el producto llegue a cuerpos de agua y cubrirlo con material impermeable.
- *Seguridad:* Guantes, protección respiratoria y gafas; ventilación adecuada o máscara si hay generación de polvo.
- Fuente: FDS Profertil / CIAFA.

**Sulfato de Magnesio** (sin RE localizado — fuente INTA NEA 2021) 🔴
- *Restricciones:* No se localizó ficha de seguridad específica. Por ser una sal mineral de baja toxicidad, la restricción ambiental esperable es baja (evitar verter grandes volúmenes en cursos de agua) — **estimado, no confirmado con FDS del fabricante**.
- *Seguridad:* Almacenar alejado de humedad, luz solar directa y fuentes de calor. EPP estándar de manejo de sales (guantes, gafas) — **sin confirmar**.
- Fuente: ficha comercial K+S Kali (EPSO Top) — sin FDS completa localizada.

**Boro foliar 17%** (sin RE localizado — fuente INTA EEA Sáenz Peña 2023) 🔴
- *Restricciones:* No se localizó ficha de seguridad específica. El boro es fitotóxico en exceso — respetar estrictamente la dosis de referencia para no dañar el cultivo tratado ni cultivos linderos por deriva. **Estimado, no confirmado.**
- *Seguridad:* EPP estándar (guantes, gafas) — **sin confirmar con FDS del fabricante específico**.
- Fuente: sin ficha de seguridad específica localizada en esta búsqueda.

&nbsp;

## 4. Nota de diseño para quien cargue estos datos

- Los campos `restricciones_ambientales`/`instrucciones_seguridad` de `productos_fitosanitarios` (migración `0018`) deberían guardar **solo lo específico de cada producto** (columnas de arriba). Las restricciones generales de la Ley 7032 (sección 2 — distancias, receta agronómica, prohibición a menores/embarazadas) aplican a **cualquier** aplicación y no dependen del producto — tiene más sentido mostrarlas una sola vez a nivel de la orden de trabajo completa (o del lote/campaña) que repetirlas 21 veces en la base. Queda como decisión de diseño para quien conecte esto a `app/diagnostico/orden_trabajo.py` o al futuro endpoint/PDF.
- Los 8 productos marcados 🔴 (Clorpirifos EPP, Thiamethoxam EPP, Ethephon, Tiidiazurón+Diurón, Sulfato de Magnesio, Boro foliar) no tienen ficha de seguridad específica confirmada — **no cargar en BD tal cual sin que un ingeniero agrónomo los revise**; puede ser el próximo paso antes de dar por cerrada la tarjeta de Trello.
- Antes de cargar, valdría la pena confirmar los 10 números de registro SENASA (RE-XXXXX) que sí figuran en [esq_datos_prod_fito.md](esq_datos_prod_fito.md) contra el Registro Nacional de Terapéutica Vegetal, para bajar el texto oficial exacto en vez del texto genérico por principio activo que se usó acá como aproximación.

&nbsp;
