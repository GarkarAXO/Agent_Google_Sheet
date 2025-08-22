import json
import re
from thefuzz import process

# --- CONFIGURATION ---
INPUT_FILE = "raw_scraped_products_debug.json"
OUTPUT_ENRICHED_FILE = "products_enriched.json"
OUTPUT_WITHOUT_COLOR_FILE = "products_without_color.json"
SIMILARITY_THRESHOLD = 90

# --- CONSTANTS FOR DETECTION ---
COLORES_VALIDOS = {
    "negro": ["negro", "black", "nigro"], "blanco": ["blanco", "white", "blnaco"], "azul": ["azul", "blue", "azl"],
    "rojo": ["rojo", "red", "rojjo"], "verde": ["verde", "green", "vder"], "amarillo": ["amarillo", "yellow", "amarilo"],
    "gris": ["gris", "gray", "grey", "griz"], "morado": ["morado", "violeta", "purple"], "rosa": ["rosa", "pink", "fucsia"],
    "naranja": ["naranja", "orange"], "dorado": ["dorado", "oro", "gold"], "plateado": ["plateado", "plata", "silver"],
    "café": ["café", "marrón", "brown"], "turquesa": ["turquesa", "aqua"], "beige": ["beige", "crema"],
    "vino": ["vino", "burdeos", "burgundy"], "tornasol": ["tornasol", "iridiscente", "multicolor"]
}
PRIORIDAD_COLORES = ["negro", "blanco", "azul", "rojo", "gris", "verde"]
COMPANIAS = ["telcel", "att", "at&t", "movistar", "unefon", "liberado", "libre"]
PALABRAS_CAJA = ["con caja", "incluye caja", "caja original", "trae caja", "se entrega en caja"]
PALABRAS_SIN_CAJA = ["sin caja", "no incluye caja", "no se entrega caja", "sin su caja"]

# --- HELPER FUNCTIONS ---
VARIACIONES_COLOR = {var: color for color, variantes in COLORES_VALIDOS.items() for var in variantes}

def detectar_color(texto):
    texto = texto.lower()
    palabras = re.findall(r'\b\w+\b', texto)
    candidatos = []
    for palabra in palabras:
        if palabra in VARIACIONES_COLOR:
            candidatos.append(VARIACIONES_COLOR[palabra])
    if candidatos:
        for preferido in PRIORIDAD_COLORES:
            if preferido in candidatos:
                return preferido
        return candidatos[0]
    
    for palabra in palabras:
        if len(palabra) > 3 and palabra.isalpha():
            mejor, score = process.extractOne(palabra, VARIACIONES_COLOR.keys())
            if score >= SIMILARITY_THRESHOLD:
                candidatos.append(VARIACIONES_COLOR[mejor])
    if candidatos:
        for preferido in PRIORIDAD_COLORES:
            if preferido in candidatos:
                return preferido
        return candidatos[0]
    return None

def detectar_compania(descripcion):
    descripcion = descripcion.lower()
    for comp in COMPANIAS:
        if comp in descripcion:
            if comp in ["att", "at&t"]: return "AT&T"
            if comp in ["libre", "liberado"]: return "Liberado"
            return comp.capitalize()
    return "Desconocida"

def detectar_caja(descripcion):
    descripcion = descripcion.lower()
    for sin in PALABRAS_SIN_CAJA:
        if sin in descripcion: return "No"
    for con in PALABRAS_CAJA:
        if con in descripcion: return "Sí"
    return "No"

# --- MAIN LOGIC ---
def enriquecer_productos_desde_descripcion():
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            productos = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"❌ Error al cargar '{INPUT_FILE}': {e}")
        return

    productos_enriquecidos = []
    productos_sin_color = []

    for producto in productos:
        descripcion = producto.get("Descripción", "")
        familia = producto.get("Familia", "").lower()

        # --- Standard Enrichment (Company and Box) ---
        if "celular" in familia:
            producto["Compañía"] = detectar_compania(descripcion)
        if "consola" in familia:
            producto["Caja"] = detectar_caja(descripcion)

        # --- Optimized Color Logic ---
        color_actual = producto.get("Color", "").strip().lower()
        if color_actual and color_actual in VARIACIONES_COLOR:
            # Color from scraping is valid, do nothing to it
            pass
        else:
            # No valid color from scraping, run detection logic
            color_detectado = detectar_color(descripcion)
            if color_detectado == "tornasol": color_detectado = "azul" # Business rule
            producto["Color"] = color_detectado if color_detectado else ""

        productos_enriquecidos.append(producto)

        # --- Register for AI step if color is still missing ---
        if not producto.get("Color"):
            productos_sin_color.append(producto)

    # --- Save results ---
    with open(OUTPUT_ENRICHED_FILE, "w", encoding="utf-8") as f:
        json.dump(productos_enriquecidos, f, indent=2, ensure_ascii=False)
    
    with open(OUTPUT_WITHOUT_COLOR_FILE, "w", encoding="utf-8") as f:
        json.dump(productos_sin_color, f, indent=2, ensure_ascii=False)

    print(f"\n✨ Enriquecimiento consolidado completado.")
    print(f"🧾 Total productos procesados: {len(productos)}")
    print(f"✅ Con color detectado o válido: {len(productos_enriquecidos) - len(productos_sin_color)}")
    print(f"🧠 Sin color (para revisión con IA): {len(productos_sin_color)}")
    print(f"📁 Archivo enriquecido guardado en: {OUTPUT_ENRICHED_FILE}")
    print(f"📁 Sin color guardado en: {OUTPUT_WITHOUT_COLOR_FILE}")

if __name__ == "__main__":
    enriquecer_productos_desde_descripcion()
