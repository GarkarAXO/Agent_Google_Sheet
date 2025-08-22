import os
import json
import time
import requests
from openai import OpenAI, RateLimitError
from dotenv import load_dotenv

load_dotenv()

MODEL = "gpt-4o-mini"
INPUT_FILE = "products_without_color.json"
OUTPUT_FILE = "products_without_color.json"

# Inicializa cliente OpenAI
try:
    client = OpenAI()
except Exception as e:
    print(f"❌ No se pudo inicializar el cliente de OpenAI. ¿Está configurada OPENAI_API_KEY? Error: {e}")
    client = None

def fetch_efectimundo_images(sku):
    try:
        res = requests.post("https://efectimundo.com.mx/catalogo/consulta_catalogo.php", params={
            "metodo": "guardayMuestaImagenes", "prenda": sku
        }, timeout=10)
        data = res.json()
        return [
            "https://efectimundo.com.mx/catalogo" + img.get("href", "").lstrip(".")
            for img in data.get("listaImagenes", []) if "href" in img
        ]
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Error de red al buscar imágenes para SKU {sku}: {e}")
        return []
    except json.JSONDecodeError:
        print(f"⚠️ Error al decodificar JSON para SKU {sku}.")
        return []

def detect_color_in_image(image_url):
    if not client:
        print("❌ Cliente OpenAI no disponible.")
        return None

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Analiza la imagen para identificar el color principal del dispositivo electrónico que se muestra. Si el dispositivo tiene una funda, carcasa o protector, ignora el color del accesorio y enfócate en el color del dispositivo en sí. Responde solo con el nombre del color."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_url,
                            },
                        },
                    ],
                }
            ],
            max_tokens=10,
        )
        return response.choices[0].message.content.strip().capitalize()
    except RateLimitError:
        print(f"🛑 Rate limit alcanzado. Deteniendo proceso.")
        raise
    except Exception as e:
        print(f"❌ Error al analizar imagen {image_url}: {e}")
        return None

def enriquecer_colores_con_gpt():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        productos = json.load(f)

    actualizados = 0
    sin_color = 0
    sin_imagen = 0
    analizados = 0

    for producto in productos:
        color = producto.get("Color", "").strip().lower()
        if color:
            continue  # Ya tiene color válido

        sku = producto.get("SKU", "").strip()
        if not sku:
            continue

        imagenes = fetch_efectimundo_images(sku)
        if not imagenes:
            sin_imagen += 1
            continue

        image_url = imagenes[0]
        print(f"🔍 Analizando SKU {sku} con imagen: {image_url}")

        try:
            color_detectado = detect_color_in_image(image_url)
            analizados += 1

            if color_detectado:
                producto["Color"] = color_detectado
                actualizados += 1
                print(f"🎨 Color detectado: {color_detectado}")
            else:
                sin_color += 1

        except RateLimitError:
            break

        time.sleep(1.1)  # Para evitar límites de tasa

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(productos, f, indent=2, ensure_ascii=False)

    print("\n✅ Enriquecimiento completado con GPT-4o.")
    print(f"🔎 Productos analizados: {analizados}")
    print(f"🎯 Colores detectados: {actualizados}")
    print(f"🖼️ Productos sin imagen encontrada: {sin_imagen}")
    print(f"❌ Productos sin color detectable: {sin_color}")
    print(f"📁 Archivo guardado: {OUTPUT_FILE}")

if __name__ == "__main__":
    enriquecer_colores_con_gpt()
