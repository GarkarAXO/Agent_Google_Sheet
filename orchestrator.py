import json
import subprocess
from datetime import datetime
from scraper_all_products import scrape_store_by_categories, STORES, CATEGORIES

RAW_INPUT_JSON = "raw_scraped_products_debug.json"

def mostrar_menu():
    print("\n🧠 Bienvenido al Orquestador de Scraping")
    print("1️⃣  Iniciar scraping con todas las sucursales y categorías")
    print("2️⃣  Enriquecer Datos desde Descripción (Color, Compañía, Caja)")
    print("3️⃣  Enriquecer colores faltantes con GPT-4o Mini")
    print("4️⃣  Combinar colores enriquecidos con archivo original")
    print("5️⃣  Generar resumen de stock por modelo y variantes")
    print("6️⃣  Sincronizar stock con hoja de Google Sheets")
    print("7️⃣  Salir")
    return input("\nSelecciona una opción (1 a 7): ").strip()

def iniciar_scraping():
    all_products = []
    resumen = {}
    print("\n🚀 Iniciando scraping de TODAS las sucursales y categorías...\n")
    for store_id, store_name in STORES.items():
        all_products.extend(scrape_store_by_categories(store_id, store_name, CATEGORIES, resumen))
    with open(RAW_INPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(all_products, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Scraping completado. Resultados guardados en '{RAW_INPUT_JSON}'")
    print(f"📊 Total de dispositivos válidos detectados: {len(all_products)}\n")
    for (store, category), stats in resumen.items():
        print(f"🧾 {store} - {category}")
        for k, v in stats.items():
            print(f"   • {k}: {v}")
        print()

def enriquecer_datos_consolidado():
    print("\n✨ Ejecutando enriquecimiento consolidado con 'add_color_from_description.py'...")
    try:
        subprocess.run(["python3", "add_color_from_description.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error al ejecutar el script de enriquecimiento: {e}")
    except FileNotFoundError:
        print("❌ No se encontró 'add_color_from_description.py'.")

def generar_resumen_stock():
    print("\n📊 Generando resumen de stock con 'generate_stock_summary.py'...")
    try:
        subprocess.run(["python3", "generate_stock_summary.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error al ejecutar el script de resumen de stock: {e}")
    except FileNotFoundError:
        print("❌ No se encontró 'generate_stock_summary.py'.")

def enriquecer_con_gpt():
    print("\n🧠 Ejecutando enriquecimiento de color con GPT-4o Mini...")
    try:
        subprocess.run(["python3", "enrich_color_with_gpt.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error al ejecutar el script de enriquecimiento con GPT-4o: {e}")
    except FileNotFoundError:
        print("❌ No se encontró 'enrich_color_with_gpt.py'.")

def combinar_colores_enriquecidos():
    print("\n🔄 Ejecutando combinación de colores con 'merge_color_updates.py'...")
    try:
        subprocess.run(["python3", "merge_color_updates.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error al ejecutar el script de combinación: {e}")
    except FileNotFoundError:
        print("❌ No se encontró 'merge_color_updates.py'.")

def sincronizar_con_hoja():
    print("\n📤 Enviando datos a la hoja de Google Sheets con 'sync_stock_summary_to_sheets.py'...")
    try:
        subprocess.run(["python3", "sync_stock_summary_to_sheets.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error al ejecutar el script de sincronización: {e}")
    except FileNotFoundError:
        print("❌ No se encontró 'sync_stock_summary_to_sheets.py'.")

def main():
    while True:
        opcion = mostrar_menu()
        if opcion == "1":
            iniciar_scraping()
        elif opcion == "2":
            enriquecer_datos_consolidado()
        elif opcion == "3":
            enriquecer_con_gpt()
        elif opcion == "4":
            combinar_colores_enriquecidos()
        elif opcion == "5":
            generar_resumen_stock()
        elif opcion == "6":
            sincronizar_con_hoja()
        elif opcion == "7":
            print("👋 Saliste del programa.")
            break
        else:
            print("❌ Opción inválida. Intenta de nuevo.")

if __name__ == "__main__":
    main()
