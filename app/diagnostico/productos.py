"""
Catálogo de productos por causa_indice — sección 6 del documento de
referencia. 21 productos en total sobre 10 causas (verificado contra el
"Total: 20 reglas · 10 causas cubiertas · 4 cultivos · 21 productos en
catálogo" del documento).
"""

CATALOGO_PRODUCTOS: dict[str, list[dict[str, str]]] = {
    "sin_problema_detectado": [],
    "interferencia_vegetacion": [
        {"nombre": "Glifosato", "tipo": "herbicida"},
        {"nombre": "2,4-D", "tipo": "herbicida"},
        {"nombre": "Atrazina", "tipo": "herbicida"},
        {"nombre": "Cletodim", "tipo": "herbicida"},
        {"nombre": "Imazetapir", "tipo": "herbicida"},
    ],
    "estres_biotico_fungico": [
        {"nombre": "Azoxistrobina", "tipo": "fungicida"},
        {"nombre": "Trifloxistrobina", "tipo": "fungicida"},
        {"nombre": "Mancozeb", "tipo": "fungicida"},
        {"nombre": "Tebuconazol", "tipo": "fungicida"},
        {"nombre": "Carbendazim", "tipo": "fungicida"},
    ],
    "estres_biotico_insecto": [
        {"nombre": "Clorpirifos", "tipo": "insecticida"},
        {"nombre": "Lambda-cihalotrina", "tipo": "insecticida"},
        {"nombre": "Imidacloprid", "tipo": "insecticida"},
        {"nombre": "Spinosad", "tipo": "insecticida"},
        {"nombre": "Thiamethoxam", "tipo": "insecticida"},
    ],
    "estres_nutricional_nitrogeno": [
        {"nombre": "Urea 46% N", "tipo": "fertilizante"},
    ],
    "estres_nutricional_micro": [
        {"nombre": "Sulfato de Magnesio", "tipo": "fertilizante_foliar"},
        {"nombre": "Boro foliar 17%", "tipo": "fertilizante_foliar"},
    ],
    "estres_nutricional_fosforo": [
        {"nombre": "Superfosfato Triple 46%", "tipo": "fertilizante"},
    ],
    "estres_hidrico": [],
    "madurez_temprana_diferencial": [
        {"nombre": "Ethephon 48%", "tipo": "acelerador_madurez"},
        {"nombre": "Tiidiazurón + Diurón", "tipo": "defoliante"},
    ],
    "vigor_excesivo": [],
}
