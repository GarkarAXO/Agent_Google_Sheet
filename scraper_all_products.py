import json
import urllib.request
import urllib.parse
from html.parser import HTMLParser
from collections import defaultdict

STORES = {
    "154": "Atizapán Plaza Cristal",
    "155": "Azcapotzalco",
    "194": "Cancún MultiPlaza Arco Norte",
    "133": "Chalco Centro",
    "177": "Chalco Guadalupana",
    "171": "Chalco Soriana Valle",
    "151": "Chilpancingo",
    "199": "Chimalhuacán Barrio Artesanos",
    "169": "Chimalhuacán Centro",
    "196": "Chimalhuacán Las Torres",
    "186": "Coacalco Bosques del Valle",
    "95": "Coacalco Power Center",
    "192": "Coyoacán Plaza Cantil",
    "261": "Cuajimalpa",
    "165": "Cuautepec",
    "259": "Cuautepec Barrio Alto",
    "188": "Cuautitlán Izcalli Portal Cuautitlán",
    "198": "Cuautla Morelos",
    "143": "Ecatepec Center Plazas",
    "183": "Ecatepec Chiconautla",
    "193": "Ecatepec Gobernadora",
    "179": "Ecatepec Jardines de Morelos",
    "218": "Ecatepec Muzquiz",
    "181": "Ecatepec Palomas",
    "257": "Ecatepec San Agustín",
    "180": "Ecatepec Santa Clara",
    "83": "Galerías Chalco",
    "187": "Gran Patio Ecatepec",
    "189": "Gran Patio Valle de Chalco",
    "287": "Héroes Chalco",
    "80": "Héroes Ixtapaluca",
    "86": "Héroes Tecámac 1° Sección",
    "289": "Héroes Tizayuca",
    "85": "Hidalgo Patio Tepeji",
    "174": "Hidalgo Tizayuca",
    "149": "Huehuetoca Palacio Municipal",
    "142": "Huehuetoca Paseo de la Mora",
    "97": "Ixtapaluca Cortijo",
    "87": "Ixtapaluca Patio Ayotla",
    "84": "Ixtapaluca Plaza San Buenaventura",
    "206": "Iztapalapa Desarrollo urbano",
    "263": "Iztapalapa Santa Cruz Meyehualco",
    "204": "Jiutepec Morelos",
    "156": "Miramontes",
    "208": "Morelos Plan de Ayala",
    "132": "Naucalpan Urbina",
    "98": "Nezahualcóyotl Adolfo López Mateos",
    "185": "Nezahualcóyotl Cuarta Avenida",
    "176": "Nezahualcóyotl Madrugada",
    "139": "Nicolás Romero",
    "117": "Oaxaca Plaza Bella",
    "115": "Patio Texcoco",
    "195": "Playa del Carmen Plaza Sofia",
    "153": "Plaza Atizapán",
    "191": "Plaza Centenario",
    "147": "Plaza Chimalhuacán",
    "267": "Plaza Coacalco",
    "175": "Plaza del Salado",
    "216": "Plaza Ecatepec",
    "93": "Plaza Ixtapaluca",
    "265": "Plaza Tizara",
    "299": "PORTAL TULTITLAN",
    "160": "Puebla Av. Independecia",
    "172": "Puebla Misiones de San Francisco",
    "108": "Puebla Plaza Centro Sur",
    "190": "Puerta Texcoco",
    "277": "Recursos Hidráulicos Ecatepec",
    "164": "San Cosme",
    "178": "San Felipe",
    "161": "Santiago Tianguistenco Toluca",
    "197": "Serviplaza Iztapalapa",
    "162": "Tacubaya",
    "269": "Tecámac Centro",
    "114": "Tecámac Macroplaza",
    "96": "Tecámac Plaza Bella Mexiquense",
    "94": "Tecámac Power Center",
    "81": "Texcoco Fray Pedro de Gante",
    "145": "Texcoco Mercado San Antonio",
    "166": "Tláhuac San Lorenzo",
    "275": "Tláhuac Zapotitlán",
    "182": "Tlalnepantla Valle Dorado",
    "82": "Tlalpan",
    "271": "Tlaxcala Centro",
    "273": "Tlaxcala Santa Ana",
    "158": "Toluca Juan Aldama",
    "144": "Toluca Las Torres",
    "283": "Tula Hidalgo",
    "202": "Tultitlán",
    "106": "Tultitlán Lechería",
    "150": "Valle de Chalco",
    "285": "Villas de las Flores",
    "214": "Zinacantepec Toluca",
    "123": "Zumpango Plaza Centro"
}

CATEGORIES = ["CELULARES", "CONSOLAS DE JUEGOS"]
OUTPUT_JSON = "raw_scraped_products_debug.json"

class TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_table = False
        self.in_th = False
        self.in_tr = False
        self.in_td = False
        self.headers = []
        self.rows = []
        self.current_row = []

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self.in_table = True
        elif tag == 'th':
            self.in_th = True
        elif tag == 'tr':
            self.in_tr = True
            self.current_row = []
        elif tag == 'td':
            self.in_td = True

    def handle_endtag(self, tag):
        if tag == 'table':
            self.in_table = False
        elif tag == 'th':
            self.in_th = False
        elif tag == 'tr':
            self.in_tr = False
            if self.current_row:
                self.rows.append(self.current_row)
        elif tag == 'td':
            self.in_td = False

    def handle_data(self, data):
        if self.in_th:
            self.headers.append(data.strip())
        elif self.in_td:
            self.current_row.append(data.strip())

def fetch_page_data(page_number, category, store_id):
    url = f"https://efectimundo.com.mx/catalogo/consulta_catalogo.php?metodo=consulta_catalogo&salida=res&id_sucursal={store_id}"
    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'es-419,es;q=0.6',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': 'https://efectimundo.com.mx',
        'Pragma': 'no-cache',
        'Referer': 'https://efectimundo.com.mx/catalogo/catalogo.php',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
        'X-Requested-With': 'XMLHttpRequest'
    }
    data = urllib.parse.urlencode({
        "pagina": page_number,
        "ramo": "",
        "familia": category,
        "tipo": "",
        "prenda": "",
        "marca": "",
        "modelo": "",
        "descripcion": ""
    }).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            response_content = response.read().decode('utf-8')
            parsed_json = json.loads(response_content)
            return parsed_json
    except Exception as e:
        print(f"❌ Error al obtener página {page_number} de {category} en sucursal {store_id}: {e}")
        return None

def is_valid_product(product):
    familia = product.get("Familia", "").lower().strip()
    promo_price = product.get("Precio Promoción", "").replace("$", "").replace(",", "").strip()

    if "dañado" in familia or "broken" in familia:
        return False

    try:
        return float(promo_price) > 0
    except:
        return False

def scrape_store_by_categories(store_id, store_name, categories, resumen):
    all_products = []

    for category in categories:
        total_rowcount = 0
        total_rows = 0
        total_saved = 0
        total_danado = 0
        total_invalid_price = 0

        all_rows = []
        headers = []

        print(f"📦 Procesando {category} en {store_name} ({store_id})")

        try:
            initial_data = fetch_page_data(1, category, store_id)
            if not initial_data or not initial_data.get('tabla'):
                print(f"⚠️ No hay datos para {category} en {store_name}.")
                continue

            total_items = int(initial_data.get('rowCount', 0))
            page_size = 50
            total_pages = (total_items + page_size - 1) // page_size
            total_rowcount = total_items

            parser = TableParser()
            parser.feed(initial_data['tabla'])
            headers = parser.headers
            all_rows.extend(parser.rows)

            for page_num in range(2, total_pages + 1):
                data = fetch_page_data(page_num, category, store_id)
                if data and data.get("tabla"):
                    parser = TableParser()
                    parser.feed(data["tabla"])
                    all_rows.extend(parser.rows)

            total_rows = len(all_rows)

            for row in all_rows:
                product = {headers[j]: item for j, item in enumerate(row)}
                familia = product.get("Familia", "").lower().strip()
                precio = product.get("Precio Promoción", "").replace("$", "").replace(",", "").strip()

                if "dañado" in familia or "broken" in familia:
                    total_danado += 1
                    continue
                try:
                    if float(precio) <= 0:
                        total_invalid_price += 1
                        continue
                except:
                    total_invalid_price += 1
                    continue

                clean_product = {
                    "SKU": product.get("Prenda / Sku Lote", "").strip(),
                    "Marca": product.get("Marca", "").strip(),
                    "Modelo": product.get("Modelo", "").strip(),
                    "Descripción": product.get("Descripción", "").strip(),
                    "Precio Promoción": product.get("Precio Promoción", "").strip(),
                    "Sucursal": store_name.strip(),
                    "ID Sucursal": store_id,
                    "Categoría": category,
                    "Familia": product.get("Familia", "").strip()
                }

                all_products.append(clean_product)
                total_saved += 1

        except Exception as e:
            print(f"❌ Error al procesar {category} en {store_name}: {e}")

        resumen[(store_name, category)] = {
            "Esperados (rowCount)": total_rowcount,
            "Parseados": total_rows,
            "Guardados": total_saved,
            "Descartados por Familia dañada": total_danado,
            "Descartados por precio inválido": total_invalid_price
        }

    return all_products

def main():
    all_products = []
    resumen = {}

    for store_id, store_name in STORES.items():
        all_products.extend(scrape_store_by_categories(store_id, store_name, CATEGORIES, resumen))

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(all_products, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Scraping completado. Resultados guardados en '{OUTPUT_JSON}'")
    print(f"📊 Total de dispositivos válidos detectados: {len(all_products)}\n")

    for (store, category), stats in resumen.items():
        print(f"🧾 {store} - {category}")
        for k, v in stats.items():
            print(f"   • {k}: {v}")
        print()

if __name__ == "__main__":
    main()
