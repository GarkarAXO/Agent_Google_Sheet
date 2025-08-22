import json
import re
from collections import defaultdict

INPUT_FILE = "products_with_color_merged.json"
OUTPUT_FILE = "stock_summary.json"

def extract_storage_capacity(model_string):
    match = re.search(r'(?:MEM|DD):(\d+(?:GB|TB))', model_string, re.IGNORECASE)
    if match:
        return match.group(1)
    match = re.search(r'(\d+\s*GB|\d+\s*TB)', model_string, re.IGNORECASE)
    if match:
        return match.group(1).replace(" ", "")
    return ""



def create_variant_summary(products):
    variant_counts = defaultdict(int)

    for product in products:
        model_original = product.get("Modelo", "")
        if not model_original:
            continue

        # Get color and check if it's valid. If not, skip the product.
        color = product.get("Color", "").strip()
        if not color or color.lower() == 'sin color':
            continue

        storage = extract_storage_capacity(model_original)
        description = product.get("Descripción", "").lower()
        familia = "CONSOLAS" if "consola" in description else "CELULARES"
        
        compania = ""
        if familia == "CELULARES":
            compania = product.get("Compañía", "Desconocida").strip()
            if compania == "Desconocida":
                continue
        
        caja = "c-caja" if product.get("Caja") == "Sí" else "s-caja"

        variant_key = (model_original, storage, color, compania, familia, caja)
        variant_counts[variant_key] += 1

    summary_list = []
    for variant_key, stock in variant_counts.items():
        summary_list.append({
            "model_original": variant_key[0],
            "storage": variant_key[1],
            "color": variant_key[2],
            "compania": variant_key[3],
            "familia": variant_key[4],
            "caja": variant_key[5],
            "stock": stock
        })

    return summary_list

def main():
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            products_list = json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: El archivo de entrada '{INPUT_FILE}' no fue encontrado.")
        return
    except json.JSONDecodeError:
        print(f"❌ Error: El archivo '{INPUT_FILE}' no es un JSON válido.")
        return

    stock_summary = create_variant_summary(products_list)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(stock_summary, f, indent=2, ensure_ascii=False)

    print(f"\n📊 Resumen de stock por variantes únicas guardado en: {OUTPUT_FILE}")
    print(f"🧾 Variantes únicas encontradas: {len(stock_summary)}")

if __name__ == "__main__":
    main()
