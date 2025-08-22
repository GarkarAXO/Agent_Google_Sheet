import json

BASE_FILE = "products_enriched.json"
UPDATED_FILE = "products_without_color.json"
OUTPUT_FILE = "products_with_color_merged.json"

def cargar_json(nombre_archivo):
    try:
        with open(nombre_archivo, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Archivo no encontrado: {nombre_archivo}")
        return []
    except json.JSONDecodeError:
        print(f"❌ Error de formato en JSON: {nombre_archivo}")
        return []

def merge_updates(base_products, updates):
    updates_by_sku = {
        p["SKU"]: p for p in updates
        if p.get("Color", "").strip()  # Solo si ya tiene color definido
    }

    actualizados = 0
    resultado = []

    for producto in base_products:
        sku = producto.get("SKU")
        if sku in updates_by_sku:
            resultado.append(updates_by_sku[sku])
            actualizados += 1
        else:
            resultado.append(producto)

    return resultado, actualizados

def main():
    base = cargar_json(BASE_FILE)
    updates = cargar_json(UPDATED_FILE)

    merged, actualizados = merge_updates(base, updates)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Actualización completada.")
    print(f"🔁 Productos actualizados desde '{UPDATED_FILE}': {actualizados}")
    print(f"📁 Archivo final guardado en: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
