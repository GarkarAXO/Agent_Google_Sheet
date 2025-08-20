import json
from collections import defaultdict

INPUT_FILE = "detailed_stock.json"
OUTPUT_FILE = "stock_summary.json"

def generar_resumen_stock(stock_detallado):
    resumen = {}

    for marca, modelos in stock_detallado.items():
        for modelo, variantes in modelos.items():
            clave_modelo = f"{marca} {modelo}"
            resumen_modelo = defaultdict(int)

            for var in variantes:
                color = var.get("Color", "Sin color")
                familia = var.get("Descripción", "").lower()
                
                # Detectar si es consola o celular
                if "consola" in familia:
                    caja = var.get("Caja", "No especificado")
                    clave_variante = f"{color} / Caja: {caja}"
                else:
                    compania = var.get("Compañía", "Desconocida")
                    clave_variante = f"{color} / {compania}"

                resumen_modelo[clave_variante] += 1

            resumen[clave_modelo] = dict(resumen_modelo)

    return resumen

def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        stock = json.load(f)

    resumen_stock = generar_resumen_stock(stock)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(resumen_stock, f, indent=2, ensure_ascii=False)

    print(f"\n📊 Resumen de stock guardado en: {OUTPUT_FILE}")
    print(f"🧾 Modelos totales: {len(resumen_stock)}")

if __name__ == "__main__":
    main()
