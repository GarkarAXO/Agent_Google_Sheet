import json
import re
from collections import defaultdict

INPUT_FILE = "products_with_color.json"
OUTPUT_FILE = "detailed_stock.json"

COMPANIAS = ["telcel", "att", "at&t", "movistar", "unefon", "liberado", "libre"]
PALABRAS_CAJA = ["con caja", "incluye caja", "caja original", "trae caja", "se entrega en caja"]
PALABRAS_SIN_CAJA = ["sin caja", "no incluye caja", "no se entrega caja", "sin su caja"]

def detectar_compania(descripcion):
    descripcion = descripcion.lower()
    for comp in COMPANIAS:
        if comp in descripcion:
            if comp in ["att", "at&t"]:
                return "AT&T"
            elif comp == "libre" or comp == "liberado":
                return "Liberado"
            else:
                return comp.capitalize()
    return "Desconocida"

def detectar_caja(descripcion):
    descripcion = descripcion.lower()
    for sin in PALABRAS_SIN_CAJA:
        if sin in descripcion:
            return "No"
    for con in PALABRAS_CAJA:
        if con in descripcion:
            return "Sí"
    return "No especificado"

def agrupar_productos(productos):
    agrupados = defaultdict(lambda: defaultdict(list))

    for p in productos:
        marca = p.get("Marca", "Desconocida").strip().upper()
        modelo = p.get("Modelo", "Desconocido").strip().upper()
        descripcion = p.get("Descripción", "")
        familia = p.get("Familia", "").lower()
        categoria = p.get("Categoría", "").lower()

        variante = {
            "SKU": p.get("SKU"),
            "Color": p.get("Color"),
            "Sucursal": p.get("Sucursal"),
            "Precio Promoción": p.get("Precio Promoción"),
            "Descripción": descripcion
        }

        # Enriquecimiento
        if "celular" in familia:
            variante["Compañía"] = detectar_compania(descripcion)
        elif "consola" in familia:
            variante["Caja"] = detectar_caja(descripcion)

        agrupados[marca][modelo].append(variante)

    return agrupados

def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        productos = json.load(f)

    stock = agrupar_productos(productos)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(stock, f, indent=2, ensure_ascii=False)

    print(f"\n📦 Stock detallado guardado en: {OUTPUT_FILE}")
    print(f"🧾 Marcas totales: {len(stock)}")
    total_modelos = sum(len(modelos) for modelos in stock.values())
    print(f"🔢 Modelos totales: {total_modelos}")

if __name__ == "__main__":
    main()
