import json
import re
from thefuzz import process

INPUT_FILE = "raw_scraped_products_debug.json"
OUTPUT_FILE = "products_with_color.json"

# Colores base reconocidos y sus sinónimos comunes
COLORES_VALIDOS = {
    "negro": ["negro", "black", "nigro"],
    "blanco": ["blanco", "white", "blnaco"],
    "azul": ["azul", "blue", "azl"],
    "rojo": ["rojo", "red", "rojjo"],
    "verde": ["verde", "green", "vder"],
    "amarillo": ["amarillo", "yellow", "amarilo"],
    "gris": ["gris", "gray", "grey", "griz"],
    "morado": ["morado", "violeta", "purple"],
    "rosa": ["rosa", "pink", "fucsia"],
    "naranja": ["naranja", "orange"],
    "dorado": ["dorado", "oro", "gold"],
    "plateado": ["plateado", "plata", "silver"],
    "café": ["café", "marrón", "brown"],
    "turquesa": ["turquesa", "aqua"],
    "beige": ["beige", "crema"],
    "vino": ["vino", "burdeos", "burgundy"],
    "tornasol": ["tornasol", "iridiscente", "multicolor"]
}

# Aplanar variaciones para mapeo inverso
VARIACIONES_COLOR = {}
for color, variantes in COLORES_VALIDOS.items():
    for var in variantes:
        VARIACIONES_COLOR[var] = color

SIMILARITY_THRESHOLD = 90

# Prioridad si se detectan varios colores
PRIORIDAD_COLORES = ["negro", "blanco", "azul", "rojo", "gris", "verde"]

def detectar_color(texto):
    texto = texto.lower()
    palabras = re.findall(r'\b\w+\b', texto)

    # 1. Buscar coincidencias exactas primero
    for palabra in palabras:
        if palabra in VARIACIONES_COLOR:
            return VARIACIONES_COLOR[palabra]

    # 2. Buscar coincidencias difusas, recolectar candidatos
    candidatos = []
    for palabra in palabras:
        palabra = palabra.strip()
        if not palabra.isalpha():
            continue  # ignoramos símbolos, números, guiones, etc.

        mejor, score = process.extractOne(palabra, VARIACIONES_COLOR.keys())
        if score >= SIMILARITY_THRESHOLD:
            candidatos.append(VARIACIONES_COLOR[mejor])


    if candidatos:
        for preferido in PRIORIDAD_COLORES:
            if preferido in candidatos:
                return preferido
        return candidatos[0]  # Si no hay preferido, usar el primero

    return None

def enriquecer_productos_con_color():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        productos = json.load(f)

    enriquecidos = []
    sin_color = []
    con_color = 0

    for producto in productos:
        color_actual = producto.get("Color", "").strip().lower()

        # Si ya tiene un color válido, lo dejamos como está
        if color_actual and color_actual in COLORES_VALIDOS:
            enriquecidos.append(producto)
            continue

        descripcion = producto.get("Descripción", "")
        color_detectado = detectar_color(descripcion)

        if color_detectado:
            if color_detectado == "tornasol":
                color_detectado = "azul"  # Regla personalizada
            producto["Color"] = color_detectado
            con_color += 1
            enriquecidos.append(producto)
        else:
            # No se detectó color: guardar para revisión
            sin_color.append(producto)
            enriquecidos.append(producto)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(enriquecidos, f, indent=2, ensure_ascii=False)

    with open("products_without_color.json", "w", encoding="utf-8") as f:
        json.dump(sin_color, f, indent=2, ensure_ascii=False)

    print(f"\n🎨 Enriquecimiento completado.")
    print(f"🧾 Total productos procesados: {len(productos)}")
    print(f"✅ Con color detectado o ya asignado válido: {len(enriquecidos) - len(sin_color)}")
    print(f"❌ Sin color detectable: {len(sin_color)}")
    print(f"📁 Archivo principal guardado en: {OUTPUT_FILE}")
    print(f"📁 Sin color guardado en: products_without_color.json")


if __name__ == "__main__":
    enriquecer_productos_con_color()
