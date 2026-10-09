"""
Generación de texto legible para el productor — diagnóstico explicado por zona.
Puro: sin I/O, sin DB. Recibe datos ya resueltos y devuelve strings.
"""

from __future__ import annotations

CAUSA_LABELS: dict[str, str] = {
    "sin_problema_detectado": "sin problema detectado",
    "interferencia_vegetacion": "interferencia de malezas",
    "estres_biotico_fungico": "enfermedad fúngica probable",
    "estres_biotico_insecto": "ataque de insectos probable",
    "estres_nutricional_nitrogeno": "déficit de nitrógeno",
    "estres_nutricional_micro": "déficit de micronutrientes (Mg/B)",
    "estres_nutricional_fosforo": "déficit de fósforo",
    "estres_hidrico": "estrés hídrico",
    "madurez_temprana_diferencial": "madurez temprana diferencial",
    "vigor_excesivo": "vigor excesivo",
}

PATRON_LABELS: dict[str, str] = {
    "circular": "patrón circular",
    "focos_aislados": "focos aislados",
    "manchas_irregulares": "manchas irregulares",
    "difuso_homogeneo": "patrón difuso homogéneo",
    "por_sectores": "distribución por sectores",
    "bordes_lote": "concentración en bordes del lote",
    "lineal": "patrón lineal",
}

CONFIANZA_LABELS: dict[str, str] = {
    "alta": "confianza alta",
    "media": "confianza media — requiere verificación en campo",
    "baja": "confianza baja — orientativo",
}


def calcular_severidad(
    ndvi_zona: float | None,
    ndvi_promedio_lote: float,
    causa_indice: str,
) -> str:
    if causa_indice == "sin_problema_detectado":
        return "normal"
    if ndvi_zona is None or ndvi_promedio_lote <= 0:
        return "normal"
    if causa_indice == "vigor_excesivo":
        return "vigorosa"
    ratio = (ndvi_promedio_lote - ndvi_zona) / ndvi_promedio_lote
    if ratio > 0.50:
        return "critica"
    if ratio > 0.25:
        return "moderada"
    if ratio > 0.10:
        return "leve"
    return "normal"


def generar_texto_zona(props: dict, ndvi_promedio_lote: float) -> str:
    area = props.get("area_ha", 0)
    ndvi = props.get("ndvi_promedio")
    patron = props.get("patron_espacial", "")
    causa = props.get("causa_indice", "sin_problema_detectado")
    confianza = props.get("confianza", "media")
    regla_id = props.get("regla_id", "")
    productos = props.get("productos_sugeridos", [])

    if regla_id == "R99":
        return (
            f"Zona de {area:.1f} ha sin problemas detectados. "
            f"Los valores de los índices están dentro de los rangos normales "
            f"para el cultivo y estadio fenológico registrado."
        )

    if props.get("excluida"):
        ndvi_str = f" (NDVI {ndvi:.3f})" if ndvi is not None else ""
        return (
            f"Zona de {area:.2f} ha excluida del análisis. "
            f"Se identificó como obstáculo físico (copa de árbol, charco) "
            f"por su tamaño pequeño y NDVI muy bajo{ndvi_str}."
        )

    parts = []

    patron_label = PATRON_LABELS.get(patron, patron)
    causa_label = CAUSA_LABELS.get(causa, causa)
    confianza_label = CONFIANZA_LABELS.get(confianza, confianza)

    if ndvi is not None and ndvi_promedio_lote > 0:
        desviacion_pct = abs((ndvi_promedio_lote - ndvi) / ndvi_promedio_lote * 100)
        direccion = "por debajo" if ndvi < ndvi_promedio_lote else "por encima"
        parts.append(
            f"Zona de {area:.1f} ha con {patron_label}. "
            f"NDVI de {ndvi:.3f}, un {desviacion_pct:.0f}% {direccion} "
            f"del promedio del lote ({ndvi_promedio_lote:.3f})."
        )
    else:
        parts.append(f"Zona de {area:.1f} ha con {patron_label}.")

    parts.append(f"Diagnóstico: {causa_label} ({confianza_label}).")

    if productos:
        nombres = [p["nombre"] for p in productos[:3]]
        if len(productos) > 3:
            nombres_str = ", ".join(nombres) + f" y {len(productos) - 3} más"
        else:
            nombres_str = ", ".join(nombres)
        parts.append(f"Productos sugeridos: {nombres_str}.")

    return " ".join(parts)


def generar_texto_unidad(props: dict) -> str:
    area = props.get("area_total_ha", 0)
    n_zonas = props.get("n_zonas", 1)
    causa = props.get("causa_indice", "")
    severidad = props.get("severidad", "")
    ndvi = props.get("ndvi_promedio")
    accion = props.get("accion_recomendada", "")
    productos = props.get("productos_sugeridos", [])

    causa_label = CAUSA_LABELS.get(causa, causa)
    zonas_str = f"{n_zonas} zona{'s' if n_zonas != 1 else ''} agrupada{'s' if n_zonas != 1 else ''}"

    parts = [f"Unidad de manejo de {area:.1f} ha ({zonas_str}) con {causa_label}, severidad {severidad}."]

    if ndvi is not None:
        parts.append(f"NDVI promedio: {ndvi:.3f}.")

    if accion:
        parts.append(accion)

    if productos:
        nombres = [p["nombre"] for p in productos[:3]]
        if len(productos) > 3:
            nombres_str = ", ".join(nombres) + f" y {len(productos) - 3} más"
        else:
            nombres_str = ", ".join(nombres)
        parts.append(f"Productos sugeridos: {nombres_str}.")

    return " ".join(parts)


def generar_resumen_general(features: list[dict]) -> str:
    total = len(features)
    if total == 0:
        return "No se encontraron zonas para diagnosticar."

    area_total = sum(f.get("properties", {}).get("area_ha", 0) for f in features)

    con_problema = [
        f for f in features
        if f.get("properties", {}).get("regla_id") not in ("R99", "R00")
    ]
    sin_problema = [
        f for f in features
        if f.get("properties", {}).get("regla_id") == "R99"
    ]
    excluidas = [
        f for f in features
        if f.get("properties", {}).get("regla_id") == "R00"
    ]

    area_afectada = sum(f.get("properties", {}).get("area_ha", 0) for f in con_problema)

    parts = [f"Se analizaron {total} zonas ({area_total:.1f} ha en total)."]

    if con_problema:
        causas: dict[str, int] = {}
        for f in con_problema:
            causa = f.get("properties", {}).get("causa_indice", "desconocido")
            label = CAUSA_LABELS.get(causa, causa)
            causas[label] = causas.get(label, 0) + 1

        detalle = ", ".join(f"{count} con {label}" for label, count in causas.items())
        s = "s" if len(con_problema) != 1 else ""
        n = "n" if len(con_problema) != 1 else ""
        parts.append(
            f"{len(con_problema)} zona{s} ({area_afectada:.1f} ha) "
            f"requiere{n} atención: {detalle}."
        )

    if sin_problema:
        s = "s" if len(sin_problema) != 1 else ""
        parts.append(f"{len(sin_problema)} zona{s} sin problemas detectados.")

    if excluidas:
        s = "s" if len(excluidas) != 1 else ""
        parts.append(f"{len(excluidas)} zona{s} excluida{s} del análisis.")

    return " ".join(parts)
