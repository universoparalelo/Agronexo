"""
Las 20 reglas del motor de diagnóstico, en el orden exacto de cascada del
documento de referencia (sección 5): exclusiones → malezas → enfermedades
fúngicas → insectos → déficit nutricional → estrés hídrico → madurez
diferencial algodón → vigor excesivo → cierre. La primera regla que cumple
TODAS sus condiciones (cultivo, estadio, índices disponibles, condición
numérica/de patrón) gana — evaluar_zona() en engine.py no sigue evaluando
las siguientes.

Textos de accion_recomendada / como_confirmar_campo copiados literalmente
del documento (no resumidos) para que el operador reciba la misma
información que el agrónomo que escribió la referencia.
"""

from dataclasses import dataclass
from typing import Callable

from app.diagnostico.engine import ContextoZona
from app.diagnostico.models import ConfianzaEnum
from app.lotes.models import CultivoEnum


@dataclass(frozen=True)
class Regla:
    id: str
    nombre: str
    bloque: str
    cultivos: frozenset[CultivoEnum] | None      # None = todos los cultivos
    estadios: frozenset[str] | None              # None = todos los estadios (tokens normalizados)
    requiere_indices: tuple[str, ...]
    condicion: Callable[[ContextoZona], bool]
    confianza: ConfianzaEnum
    causa_indice: str
    accion_recomendada: str
    como_confirmar_campo: str
    excluye_zona: bool = False                   # True solo en R00


R00 = Regla(
    id="R00", nombre="Copa de árbol u obstáculo físico", bloque="exclusiones",
    cultivos=None, estadios=None, requiere_indices=("ndvi",),
    condicion=lambda z: z.valores["ndvi"] < 0.20 and z.patron_espacial == "circular" and z.area_ha < 0.05,
    confianza=ConfianzaEnum.alta, causa_indice="sin_problema_detectado",
    excluye_zona=True,
    accion_recomendada=(
        "La zona se excluye del análisis. No se genera diagnóstico ni recomendación de "
        "producto. Se marca como obstáculo para que el frontend la muestre diferenciada en el mapa."
    ),
    como_confirmar_campo=(
        "No requiere confirmación. Si el productor sabe que hay árboles en esa posición del "
        "lote, la regla es correcta. Si no había árboles, puede ser un charco de agua "
        "(también NDVI muy bajo) — en ese caso se descarta manualmente."
    ),
)

R01 = Regla(
    id="R01", nombre="Suelo desnudo — sin cobertura vegetal", bloque="exclusiones",
    cultivos=None, estadios=None, requiere_indices=("ndvi",),
    condicion=lambda z: z.valores["ndvi"] < 0.20,
    confianza=ConfianzaEnum.alta, causa_indice="sin_problema_detectado",
    accion_recomendada=(
        "No se genera recomendación de agroquímico. Se alerta al usuario para que verifique "
        "la implantación del cultivo en esa zona. Puede ser suelo desnudo por falla de "
        "siembra, rastrojo seco o pisoteo de maquinaria."
    ),
    como_confirmar_campo=(
        "Verificar en campo si hay plantas en esa zona. Si no hay plantas, el problema fue "
        "de implantación — no es tratable con agroquímico."
    ),
)

R10 = Regla(
    id="R10", nombre="Interferencia de malezas", bloque="malezas",
    cultivos=None, estadios=None, requiere_indices=("ndvi", "exg"),
    condicion=lambda z: z.valores["ndvi"] < 0.50 and z.valores["exg"] > 0.20,
    confianza=ConfianzaEnum.alta, causa_indice="interferencia_vegetacion",
    accion_recomendada=(
        "Aplicar herbicida selectivo según el cultivo presente. Para soja usar herbicida "
        "graminicida o de hoja ancha según el tipo de maleza. Para maíz usar atrazina u otro "
        "herbicida registrado. Para algodón usar cletodim u otro selectivo."
    ),
    como_confirmar_campo=(
        "Recorrer la zona identificada y verificar qué tipo de maleza está presente. "
        "Observar si son de hoja ancha (yuyo colorado, enredadera) o gramíneas (sorgo de "
        "alepo, gramón). Esto define el herbicida a usar."
    ),
)

R20 = Regla(
    id="R20", nombre="Enfermedad fúngica en soja — estadio reproductivo", bloque="enfermedades_fungicas",
    cultivos=frozenset({CultivoEnum.soja}),
    estadios=frozenset({"r1", "r2", "r3", "r4", "r5"}),
    requiere_indices=("ndvi",),
    condicion=lambda z: z.valores["ndvi"] < 0.50 and z.patron_espacial == "circular",
    confianza=ConfianzaEnum.alta, causa_indice="estres_biotico_fungico",
    accion_recomendada=(
        "Aplicar fungicida en las zonas afectadas. Los más usados en el NEA son los "
        "triazoles (tebuconazol, propiconazol) o las mezclas estrobilurina + triazol "
        "(azoxistrobina + ciproconazol). Evaluar la severidad de la afección antes de "
        "decidir si tratar solo las zonas afectadas o todo el lote."
    ),
    como_confirmar_campo=(
        "Buscar en las hojas de la zona afectada: pústulas de color óxido o marrón en el "
        "envés de la hoja (roya asiática), o manchas circulares con centro gris rodeadas de "
        "halo amarillo (mancha marrón, ojo de rana). Para roya: rascar levemente el envés de "
        "la hoja con el dedo — si hay polvo anaranjado, confirma roya."
    ),
)

R21 = Regla(
    id="R21", nombre="Enfermedad tardía en soja — detección por GNDVI", bloque="enfermedades_fungicas",
    cultivos=frozenset({CultivoEnum.soja}),
    estadios=frozenset({"r3", "r4", "r5"}),
    requiere_indices=("gndvi",),
    condicion=lambda z: z.valores["gndvi"] < 0.40 and z.patron_espacial in {"circular", "focos_aislados"},
    confianza=ConfianzaEnum.media, causa_indice="estres_biotico_fungico",
    accion_recomendada=(
        "Evaluar si el estadio aún permite que un tratamiento fungicida sea económicamente "
        "viable. En R5 avanzado o R6, la efectividad del fungicida es baja porque el grano "
        "ya está formado. Si el estadio lo justifica, aplicar fungicida de acción rápida."
    ),
    como_confirmar_campo=(
        "Observar las hojas del tercio medio y superior de la planta. Buscar hojas con "
        "amarillamiento irregular que avanza desde los bordes hacia el centro, manchas "
        "necróticas o presencia de estructuras fúngicas visibles. Comparar con plantas "
        "sanas del lote para distinguir senescencia normal de patológica."
    ),
)

R22 = Regla(
    id="R22", nombre="Enfermedad fúngica en maíz", bloque="enfermedades_fungicas",
    cultivos=frozenset({CultivoEnum.maiz}),
    estadios=frozenset({"v7", "v8", "v9", "v10", "v11", "v12", "vt"}),
    requiere_indices=("ndvi",),
    condicion=lambda z: z.valores["ndvi"] < 0.50 and z.patron_espacial == "circular",
    confianza=ConfianzaEnum.media, causa_indice="estres_biotico_fungico",
    accion_recomendada=(
        "Si se confirma en campo, aplicar fungicida. Los triazoles tienen buena acción "
        "sobre las enfermedades foliares del maíz."
    ),
    como_confirmar_campo=(
        "Buscar en las hojas: lesiones alargadas de color gris verdoso que avanzan de forma "
        "necrótica desde el margen de la hoja hacia el nervio central (tizón foliar), o "
        "manchas de color agua que se tornan necróticas con halo amarillo (antracnosis "
        "foliar). En tizón el síntoma característico es la forma de cigarro en las lesiones."
    ),
)

R23 = Regla(
    id="R23", nombre="Enfermedad fúngica en algodón", bloque="enfermedades_fungicas",
    cultivos=frozenset({CultivoEnum.algodon}),
    estadios=frozenset({"boton_floral", "floracion", "r1", "r2"}),
    requiere_indices=("ndvi",),
    condicion=lambda z: z.valores["ndvi"] < 0.50 and z.patron_espacial in {"circular", "focos_aislados"},
    confianza=ConfianzaEnum.media, causa_indice="estres_biotico_fungico",
    accion_recomendada=(
        "Si se confirma, aplicar fungicida. El mancozeb o los triazoles son efectivos "
        "contra la alternaria. Respetar el intervalo de seguridad antes de la cosecha."
    ),
    como_confirmar_campo=(
        "Buscar en las hojas: manchas de color marrón oscuro a negro con forma irregular, a "
        "veces rodeadas por un halo clorótico amarillo (alternaria). Las manchas suelen "
        "aparecer primero en las hojas más viejas y avanzar hacia arriba. En Verticillium "
        "buscar en el tallo al cortarlo transversalmente: el tejido vascular aparece marrón "
        "oscuro o negro."
    ),
)

R24 = Regla(
    id="R24", nombre="Enfermedad fúngica en sorgo", bloque="enfermedades_fungicas",
    cultivos=frozenset({CultivoEnum.sorgo}),
    estadios=frozenset({"v6", "v7", "v8", "v9", "espigado", "floracion"}),
    requiere_indices=("ndvi",),
    condicion=lambda z: z.valores["ndvi"] < 0.50 and z.patron_espacial in {"circular", "focos_aislados"},
    confianza=ConfianzaEnum.media, causa_indice="estres_biotico_fungico",
    accion_recomendada=(
        "Evaluar la severidad y aplicar fungicida si corresponde. Los triazoles tienen "
        "acción sobre las principales enfermedades foliares del sorgo."
    ),
    como_confirmar_campo=(
        "Buscar en las hojas del tercio medio y superior: manchas de forma oval o irregular "
        "de color rojizo a púrpura con centro gris (helmintosporiosis), o lesiones pequeñas "
        "de color rojo brillante (antracnosis foliar). En antracnosis avanzada el centro de "
        "la mancha puede mostrar masas de esporas anaranjadas."
    ),
)

R30 = Regla(
    id="R30", nombre="Ataque de insectos en soja", bloque="insectos",
    cultivos=frozenset({CultivoEnum.soja}),
    estadios=frozenset({"v4", "v5", "v6", "r1", "r2", "r3", "r4"}),
    requiere_indices=("ndvi",),
    condicion=lambda z: z.valores["ndvi"] < 0.50 and z.patron_espacial in {"manchas_irregulares", "focos_aislados"},
    confianza=ConfianzaEnum.media, causa_indice="estres_biotico_insecto",
    accion_recomendada=(
        "Aplicar insecticida solo si el monitoreo en campo confirma que se supera el umbral "
        "de daño económico: para chinche ese umbral es 1 chinche adulta o 2 ninfas grandes "
        "por metro de fila; para oruga defoliadora es 30% de defoliación o 40 orugas por "
        "metro de fila en R1-R5."
    ),
    como_confirmar_campo=(
        "Recorrer la zona afectada en zigzag. Para chinche: usar paño de batida (una tela "
        "blanca de 1 metro entre dos plantas) y sacudir la planta — contar chinches adultas "
        "y ninfas que caen. Para oruga defoliadora: revisar el porcentaje de hojas "
        "consumidas y buscar orugas en el suelo o en el follaje. Para trips o ácaro blanco "
        "en algodón: observar el envés de las hojas con lupa — tripas plateadas o "
        "deformación de hojas jóvenes."
    ),
)

R31 = Regla(
    id="R31", nombre="Ataque de insectos en maíz y sorgo", bloque="insectos",
    cultivos=frozenset({CultivoEnum.maiz, CultivoEnum.sorgo}),
    estadios=frozenset({"v6", "v7", "v8", "v9", "v10", "v11", "v12", "vt"}),
    requiere_indices=("ndvi",),
    condicion=lambda z: z.valores["ndvi"] < 0.50 and z.patron_espacial in {"manchas_irregulares", "bordes_lote"},
    confianza=ConfianzaEnum.media, causa_indice="estres_biotico_insecto",
    accion_recomendada=(
        "Monitorear en campo antes de aplicar. El umbral para chinche en maíz es variable "
        "según el momento — en VT-R1 el daño en el choclo es el más crítico."
    ),
    como_confirmar_campo=(
        "Buscar en las plantas de la zona afectada: daño en las espigas de maíz o en la "
        "panoja de sorgo (insectos chupadores). Revisar el follaje por daño mecánico (hojas "
        "con agujeros irregulares = defoliadoras). Para barrenador del tallo: buscar aserrín "
        "en la base de las hojas o en el suelo alrededor de la planta. Sacudir la planta y "
        "observar si caen insectos."
    ),
)

R32 = Regla(
    id="R32", nombre="Ataque de insectos en algodón", bloque="insectos",
    cultivos=frozenset({CultivoEnum.algodon}),
    estadios=frozenset({"boton_floral", "floracion", "r1", "r2", "r3"}),
    requiere_indices=("ndvi",),
    condicion=lambda z: z.valores["ndvi"] < 0.50 and z.patron_espacial in {"manchas_irregulares", "focos_aislados", "circular"},
    confianza=ConfianzaEnum.media, causa_indice="estres_biotico_insecto",
    accion_recomendada=(
        "Monitorear en campo para confirmar la presencia y nivel de infestación. Para oruga "
        "bellotero el umbral es 10% de daño visible en estructuras reproductivas."
    ),
    como_confirmar_campo=(
        "Buscar en los botones florales y cápsulas: agujeros circulares de entrada de la "
        "oruga (bellotero). Los botones atacados suelen caerse al suelo — buscar botones "
        "caídos con agujero. Para trips: revisar con lupa el envés de las hojas más jóvenes "
        "— insectos minúsculos de 1-2 mm amarillentos o plateados, hojas con plateado en el "
        "envés y deformación. Para picudo: buscar en la base del botón floral un pequeño "
        "agujero de oviposición."
    ),
)

R40 = Regla(
    id="R40", nombre="Déficit de nitrógeno en soja", bloque="nutricional",
    cultivos=frozenset({CultivoEnum.soja}),
    estadios=frozenset({"v4", "v5", "v6", "r1", "r2"}),
    requiere_indices=("ndre",),
    condicion=lambda z: z.valores["ndre"] < 0.20 and z.patron_espacial in {"difuso_homogeneo", "por_sectores"},
    confianza=ConfianzaEnum.alta, causa_indice="estres_nutricional_nitrogeno",
    accion_recomendada=(
        "Aplicar fertilizante nitrogenado. La forma de aplicación depende del estadio: "
        "foliar (urea al 2-3%) para correcciones rápidas en R1-R2, o granulado en suelo "
        "para estadios vegetativos donde aún puede incorporarse."
    ),
    como_confirmar_campo=(
        "Observar las hojas en la zona afectada: las plantas con déficit de N tienen hojas "
        "más viejas (las del tercio inferior de la planta) amarillentas, mientras las hojas "
        "jóvenes del tope son más verdes. Esto es la clorosis por déficit de N (el N es "
        "móvil y la planta lo saca de las hojas viejas para alimentar las jóvenes). Extraer "
        "2-3 plantas y comparar el color de las hojas del tercio inferior vs superior."
    ),
)

R41 = Regla(
    id="R41", nombre="Déficit de nitrógeno en maíz y sorgo", bloque="nutricional",
    cultivos=frozenset({CultivoEnum.maiz, CultivoEnum.sorgo}),
    estadios=frozenset({"v4", "v5", "v6", "v7", "v8"}),
    requiere_indices=("ndre",),
    condicion=lambda z: z.valores["ndre"] < 0.20 and z.patron_espacial in {"difuso_homogeneo", "por_sectores"},
    confianza=ConfianzaEnum.alta, causa_indice="estres_nutricional_nitrogeno",
    accion_recomendada=(
        "Aplicar urea u otro fertilizante nitrogenado. En V4-V6 se puede aplicar en "
        "superficie o incorporado. La dosis depende del análisis de suelo y el rendimiento "
        "objetivo."
    ),
    como_confirmar_campo=(
        "El síntoma clásico del déficit de N en maíz es el 'bandereo': la punta de las "
        "hojas más viejas (de la base de la planta) amarillea y ese amarillo avanza hacia "
        "la nervadura central formando una V invertida. En estadios avanzados las plantas "
        "parecen 'quemadas' de abajo hacia arriba. En sorgo el síntoma es similar pero "
        "menos marcado."
    ),
)

R42 = Regla(
    id="R42", nombre="Déficit de nitrógeno en algodón", bloque="nutricional",
    cultivos=frozenset({CultivoEnum.algodon}),
    estadios=frozenset({"v4", "v5", "v6", "v7", "v8"}),
    requiere_indices=("ndre",),
    condicion=lambda z: z.valores["ndre"] < 0.20 and z.patron_espacial in {"difuso_homogeneo", "por_sectores"},
    confianza=ConfianzaEnum.alta, causa_indice="estres_nutricional_nitrogeno",
    accion_recomendada=(
        "Aplicar fertilizante nitrogenado. En algodón del NEA se usa principalmente urea. "
        "La aplicación en V4-V6 tiene alto impacto en el rendimiento."
    ),
    como_confirmar_campo=(
        "Buscar hojas intermedias con coloración verde pálida o amarillenta, empezando por "
        "las hojas más viejas. El algodón con déficit de N también tiende a tener tallos "
        "más delgados y entrenudos más cortos. Las brácteas (hojas que rodean el botón "
        "floral) pueden ser más pequeñas de lo normal."
    ),
)

R43 = Regla(
    id="R43", nombre="Déficit de micronutrientes (Mg, B)", bloque="nutricional",
    cultivos=None, estadios=None, requiere_indices=("ndre",),
    condicion=lambda z: z.valores["ndre"] < 0.20 and z.patron_espacial in {"bordes_lote", "manchas_irregulares"},
    confianza=ConfianzaEnum.media, causa_indice="estres_nutricional_micro",
    accion_recomendada=(
        "Aplicar fertilizante foliar de micronutrientes (sulfato de magnesio o boro "
        "soluble). Confirmar con muestra foliar antes de aplicar si es posible, ya que el "
        "costo del análisis foliar es bajo comparado con el de la aplicación innecesaria."
    ),
    como_confirmar_campo=(
        "Para déficit de magnesio: buscar clorosis internerval en hojas intermedias — las "
        "nervaduras permanecen verdes mientras el tejido entre ellas amarillea (efecto "
        "mosaico o 'espina de pescado'). Se ve primero en hojas viejas porque el Mg es "
        "móvil. Para déficit de boro: buscar deformación de hojas jóvenes y brotes "
        "terminales, hojas arrugadas o en forma de copa, tallos quebradizos en "
        "prefloración de algodón. El boro NO es móvil, por lo que los síntomas aparecen en "
        "la parte nueva de la planta."
    ),
)

R44 = Regla(
    id="R44", nombre="Déficit de fósforo", bloque="nutricional",
    cultivos=frozenset({CultivoEnum.soja, CultivoEnum.maiz}),
    estadios=frozenset({"v1", "v2", "v3", "v4", "v5", "v6"}),
    requiere_indices=("ndvi", "ndre"),
    condicion=lambda z: (
        z.valores["ndvi"] < 0.50 and z.valores["ndre"] < 0.20
        and z.patron_espacial in {"por_sectores", "difuso_homogeneo"}
    ),
    confianza=ConfianzaEnum.media, causa_indice="estres_nutricional_fosforo",
    accion_recomendada=(
        "La corrección efectiva del fósforo para el ciclo actual es limitada porque el P "
        "aplicado tardíamente tiene baja disponibilidad inmediata. La recomendación "
        "principal es documentar la zona para planificar la fertilización fosfatada en la "
        "siembra de la próxima campaña. Se puede aplicar fosfato monoamónico foliar como "
        "paliativo."
    ),
    como_confirmar_campo=(
        "Buscar plantas con crecimiento retrasado comparado con el promedio del lote. La "
        "hoja más característica del déficit de P es la coloración rojiza o violácea en el "
        "envés de las hojas inferiores, especialmente en condiciones de baja temperatura. "
        "Las raíces de plantas con déficit de P son más cortas y menos ramificadas — "
        "arrancar 2-3 plantas y comparar el sistema radicular con plantas sanas."
    ),
)

R50 = Regla(
    id="R50", nombre="Estrés hídrico generalizado", bloque="hidrico",
    cultivos=None, estadios=None, requiere_indices=("ndvi",),
    condicion=lambda z: z.valores["ndvi"] < 0.50 and z.patron_espacial == "difuso_homogeneo",
    confianza=ConfianzaEnum.media, causa_indice="estres_hidrico",
    accion_recomendada=(
        "No se aplica agroquímico. Verificar las precipitaciones de los últimos 10-15 días. "
        "Si no hubo lluvia suficiente y el cultivo está en estadio crítico (R1-R3 en soja, "
        "VT-R1 en maíz, floración en algodón), evaluar la posibilidad de riego. Si hay "
        "sistema de riego, activarlo prioritariamente en las zonas con mayor caída de NDVI."
    ),
    como_confirmar_campo=(
        "Buscar en las plantas los síntomas clásicos de estrés hídrico: hojas enrolladas o "
        "curvadas hacia adentro (los bordes de la hoja se pliegan formando un tubo, "
        "mecanismo de defensa para reducir la transpiración), hojas con tonalidad "
        "azul-grisácea, plantas con turgencia reducida (se doblan o inclinan en horas de "
        "mayor calor). En soja: las hojas muestran un leve colgante en las horas más "
        "calientes del día. Presionar la hoja con los dedos — si no recupera su forma "
        "inmediatamente, hay pérdida de turgencia."
    ),
)

R60 = Regla(
    id="R60", nombre="Madurez temprana diferencial en algodón", bloque="madurez",
    cultivos=frozenset({CultivoEnum.algodon}),
    estadios=frozenset({"r4", "r5", "apertura_de_capsulas"}),
    requiere_indices=("ndvi",),
    condicion=lambda z: (
        z.valores["ndvi"] < 0.25
        and z.valores["ndvi"] < 0.40 * z.ndvi_promedio_lote
        and z.patron_espacial in {"focos_aislados", "manchas_irregulares"}
    ),
    confianza=ConfianzaEnum.media, causa_indice="madurez_temprana_diferencial",
    accion_recomendada=(
        "Evaluar la aplicación de defoliante localizado solo en las zonas con madurez "
        "temprana para uniformizar la apertura de cápsulas y facilitar la cosecha "
        "mecanizada. Confirmar visualmente antes de aplicar. Los productos disponibles son "
        "Ethephon (acelerador de madurez) o la mezcla Tiidiazurón + Diurón (defoliante "
        "propiamente dicho)."
    ),
    como_confirmar_campo=(
        "Recorrer la zona identificada y contar el porcentaje de cápsulas abiertas vs "
        "cerradas. Si el 60-70% de las cápsulas están abiertas en esa zona mientras el "
        "resto del lote está en R3-R4, confirma madurez diferencial. Verificar también que "
        "no haya insectos o enfermedad que haya forzado la madurez prematura (buscar "
        "agujeros en cápsulas = oruga bellotero, o cápsulas ennegrecidas = enfermedad). La "
        "temperatura debe ser mayor a 18°C para que los defoliantes actúen correctamente."
    ),
)

R70 = Regla(
    id="R70", nombre="Vigor excesivo en maíz", bloque="vigor",
    cultivos=frozenset({CultivoEnum.maiz}),
    estadios=frozenset({"vt", "r1"}),
    requiere_indices=("ndvi",),
    condicion=lambda z: z.valores["ndvi"] > 0.85 and z.patron_espacial == "difuso_homogeneo",
    confianza=ConfianzaEnum.baja, causa_indice="vigor_excesivo",
    accion_recomendada=(
        "No se aplica ningún agroquímico. Es una alerta informativa para que el productor "
        "esté atento a las condiciones climáticas. Si se esperan tormentas con viento "
        "fuerte, considerar medidas preventivas como reducir la densidad de siembra para "
        "futuros ciclos."
    ),
    como_confirmar_campo=(
        "No requiere confirmación de campo para esta regla. Si el productor observa plantas "
        "con tallos muy gruesos y hojas anchas que se superposician, el diagnóstico de alto "
        "vigor es correcto. Verificar el estado de los tallos — deben ser firmes, no huecos "
        "(un tallo hueco es señal de barrenador, no de vigor)."
    ),
)

R99 = Regla(
    id="R99", nombre="Sin problema detectado", bloque="cierre",
    cultivos=None, estadios=None, requiere_indices=(),
    condicion=lambda z: True,
    confianza=ConfianzaEnum.alta, causa_indice="sin_problema_detectado",
    accion_recomendada=(
        "No se requiere ninguna intervención. La zona está dentro de los rangos normales "
        "para el cultivo y estadio fenológico registrado."
    ),
    como_confirmar_campo=(
        "No requiere confirmación en campo. Si el productor tiene dudas, puede verificar "
        "visualmente que las plantas de esa zona se ven sanas, con buen color y tamaño "
        "normal para el estadio."
    ),
)

REGLAS: list[Regla] = [
    R00, R01, R10,
    R20, R21, R22, R23, R24,
    R30, R31, R32,
    R40, R41, R42, R43, R44,
    R50, R60, R70, R99,
]
