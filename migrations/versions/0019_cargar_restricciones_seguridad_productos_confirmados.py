"""cargar restricciones_ambientales e instrucciones_seguridad — 15 productos con fuente confirmada

Revision ID: 0019
Revises: 0018
Create Date: 2026-09-14

Carga los dos campos agregados en 0018 para los 15 productos (de 21) cuyo
texto se pudo respaldar con marbete SENASA o ficha técnica/hoja de
seguridad del principio activo (ver docs/investigacion_seguridad_fitosanitaria.md,
productos marcados 🟢/🟡). Los 6 restantes (Clorpirifos, Thiamethoxam,
Ethephon 48%, Tiidiazurón + Diurón, Sulfato de Magnesio, Boro foliar 17%)
quedan en NULL a propósito — no se encontró ficha de seguridad específica
que respalde el texto, y cargar una estimación sin marcar sería peor que
dejarlo pendiente. Se completan en una migración futura una vez
confirmados.

Restricciones generales de la Ley 7032 (Chaco) — distancias mínimas de
aplicación, receta agronómica obligatoria, prohibición a menores/
embarazadas — no se repiten acá: aplican a cualquier producto, no son un
dato por fila de este catálogo (ver sección 4 del documento de
investigación).
"""

from alembic import op
import sqlalchemy as sa

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None

DATOS_CONFIRMADOS = [
    (
        "Glifosato",
        "Tóxico para organismos acuáticos. No contaminar cursos de agua, embalses ni fuentes de agua.",
        "Usar protector facial, guantes, botas de goma, camisa y pantalón de manga larga durante preparación y aplicación. No ingerir ni inhalar. Lavar la piel expuesta con agua y jabón al finalizar.",
    ),
    (
        "2,4-D",
        "Tóxico para organismos acuáticos con efectos duraderos. Alto riesgo de deriva sobre cultivos de hoja ancha sensibles (algodón, vid, hortícolas linderos) — no aplicar con viento en dirección a esos lotes.",
        "Usar equipo de protección personal completo según etiqueta (guantes, protección ocular, ropa que cubra la piel). Evitar contacto con piel, ojos y ropa.",
    ),
    (
        "Atrazina",
        "Persistente — detectada en aguas superficiales y subterráneas. Mantener franja de seguridad de 10 m en aplicación terrestre y 100 m en aplicación aérea respecto a cursos de agua. No aplicar si hay riesgo de escorrentía.",
        "Usar equipo de protección personal completo durante preparación, mezcla y aplicación. No comer, beber ni fumar durante la tarea. Almacenar en lugar seco y ventilado, no junto a alimentos.",
    ),
    (
        "Cletodim",
        "No aplicar con viento superior a 4 km/h. No aplicar si se esperan lluvias dentro de las 3 horas siguientes. Usar boquilla antideriva.",
        "Reingreso al área tratada entre 24 y 48 horas después de la aplicación según formulación comercial — confirmar en el marbete específico.",
    ),
    (
        "Imazetapir",
        "Alto efecto residual en el suelo — respetar 120 días entre la aplicación y la siembra de un cultivo subsiguiente sensible (ej. maíz no tolerante a imidazolinonas).",
        "Clasificación toxicológica Clase IV (normalmente no ofrece peligro). Usar equipo de protección personal estándar: guantes y protección ocular.",
    ),
    (
        "Azoxistrobina",
        "Muy tóxico para organismos acuáticos — evitar contaminación de cuerpos de agua. Prácticamente no tóxico para abejas.",
        "Reingreso 24 horas después de la aplicación. Usar gorro y overol de algodón, anteojos herméticos, máscara para polvo/vapores tóxicos, guantes y botas de neopreno.",
    ),
    (
        "Trifloxistrobina",
        "No contaminar fuentes ni cursos de agua. Especial atención a napas subterráneas en suelos vulnerables. Máximo 4 aplicaciones por año.",
        "Usar solo en exteriores o en lugar bien ventilado. No respirar polvo ni niebla. Usar guantes de protección. Evitar ingestión, inhalación y contacto con la piel.",
    ),
    (
        "Mancozeb",
        "Muy tóxico para organismos acuáticos con efectos duraderos. No contaminar fuentes de agua de riego o consumo. No lavar equipos de aplicación en ríos.",
        "Reingreso entre 12 y 48 horas según formulación — verificar en la etiqueta del producto específico. Usar guantes como protección mínima.",
    ),
    (
        "Tebuconazol",
        "Tóxico para peces. No contaminar agua, alimentos ni forraje por eliminación del producto.",
        "Usar guantes, ropa, gafas y máscara de protección. Lavarse concienzudamente tras la manipulación. No comer, beber ni fumar durante el uso.",
    ),
    (
        "Carbendazim",
        "Muy tóxico para organismos acuáticos. Puede causar defectos genéticos y dañar la fertilidad — no disponer producto, envases o residuos cerca de ríos, lagunas o sistemas de drenaje.",
        "Usar guantes, ropa y protección ocular/facial (puede irritar piel y ojos). No permitir el ingreso al área tratada hasta 24 horas después de la aplicación.",
    ),
    (
        "Lambda-cihalotrina",
        'Clasificación "muy tóxico" para abejas. Avisar a apicultores del área con al menos 48 horas de anticipación. Aplicar en horarios de baja actividad de abejas. No aplicar durante floración. No aplicar con viento superior a 8 km/h ni temperatura mayor a 28°C.',
        "Usar mandil resistente a químicos, ropa que cubra el cuerpo, botas y gorra. Gafas protectoras herméticas. Protección respiratoria si hay formación de aerosol o neblina.",
    ),
    (
        "Imidacloprid",
        "Categoría toxicológica II (moderadamente peligroso, franja amarilla). Muy tóxico para abejas. No aplicar durante floración. No asperjar sobre colmenas activas — si no se pueden trasladar, cubrir la entrada durante la aplicación y aplicar fuera del horario de pecoreo.",
        "Evitar respirar polvo, vapor o aspersión del producto. Triple lavado de envases tras el uso; inutilizar perforando o triturando.",
    ),
    (
        "Spinosad",
        "No aplicar durante floración ni en horario de forrajeo activo de abejas, aunque no haya floración aparente en el cultivo tratado. No aplicar sobre vegetación espontánea en flor. Máximo 2 aplicaciones por campaña, con 14 días de separación mínima entre ellas.",
        "Una vez seco (pocas horas después de la aplicación) deja de ser tóxico para abejas — igual debe evitarse aplicar durante floración activa.",
    ),
    (
        "Urea 46% N",
        "Evitar vertido a cursos de agua superficial o subterránea — riesgo de contaminación por escorrentía o lixiviación de nitrógeno si se aplica en exceso o cerca de cursos de agua.",
        "Usar gafas de seguridad, máscara con filtro si hay concentración elevada de polvo, guantes y ropa de protección. Evitar generar polvo. No comer, beber ni fumar durante la manipulación. Lavarse las manos con agua y jabón después.",
    ),
    (
        "Superfosfato Triple 46%",
        "Evitar vertidos al agua. En caso de lluvia, evitar que el producto llegue a cuerpos de agua y cubrirlo con material impermeable.",
        "Usar guantes, protección respiratoria y gafas. Asegurar ventilación adecuada o usar máscara si hay generación de polvo.",
    ),
]


def upgrade() -> None:
    bind = op.get_bind()
    stmt = sa.text("""
        UPDATE productos_fitosanitarios
        SET restricciones_ambientales = :restricciones,
            instrucciones_seguridad = :seguridad
        WHERE nombre = :nombre
    """)
    for nombre, restricciones, seguridad in DATOS_CONFIRMADOS:
        bind.execute(stmt, {"nombre": nombre, "restricciones": restricciones, "seguridad": seguridad})


def downgrade() -> None:
    bind = op.get_bind()
    stmt = sa.text("""
        UPDATE productos_fitosanitarios
        SET restricciones_ambientales = NULL,
            instrucciones_seguridad = NULL
        WHERE nombre = :nombre
    """)
    for nombre, _, _ in DATOS_CONFIRMADOS:
        bind.execute(stmt, {"nombre": nombre})
