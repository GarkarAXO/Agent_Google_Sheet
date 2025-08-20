import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from pprint import pprint

SHEET_ID = '1kv_LaEofrVRqUW2spEBi6LNJA9Z3Sk9KLNEo2HFLuho'
SHEET_NAME = 'Articulos publicados Reventa'
STOCK_JSON_PATH = 'stock_summary.json'

# ========================
# 📤 AUTENTICACIÓN GOOGLE
# ========================
def autenticar_gspread():
    print("🔄 Autenticando con Google Sheets...")
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
    return sheet

# =======================
# 📥 CARGAR INVENTARIO
# =======================
def cargar_stock_local(path):
    print(f"📦 Cargando inventario local desde {path}...")
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    stock_dict = {}

    for modelo, variantes in data.items():
        for variante, cantidad in variantes.items():
            try:
                color, compania = [x.strip().lower() for x in variante.split("/", 1)]
                vp = compania
                vs = color
                vt = ""  # No se usa por ahora

                key = (vp, vs, vt)
                stock_dict[key] = stock_dict.get(key, 0) + cantidad
            except Exception as e:
                print(f"⚠️ Error procesando modelo '{modelo}' con variante '{variante}': {e}")

    return stock_dict

# ========================
# 🔄 ACTUALIZAR HOJA
# ========================
def actualizar_hoja(sheet, stock_dict):
    data = sheet.get_all_records()
    print(f"✅ Hoja cargada con {len(data)} filas.")

    headers = sheet.row_values(1)
    try:
        col_vp = headers.index("Variante Principal") + 1
        col_vs = headers.index("Variante Secundaria") + 1
        col_vt = headers.index("Variante Tercera") + 1
        col_inv = headers.index("Inventario Partner") + 1
    except ValueError as e:
        print("❌ Las columnas necesarias no fueron encontradas en la hoja. Asegúrate de tener: Variante Principal, Variante Secundaria, Variante Tercera, Inventario Partner.")
        return

    actualizados = 0
    for i, row in enumerate(data, start=2):  # desde fila 2 (sin encabezados)
        vp = row.get("Variante Principal", "").strip().lower()
        vs = row.get("Variante Secundaria", "").strip().lower()
        vt = row.get("Variante Tercera", "").strip().lower()

        key = (vp, vs, vt)

        if key in stock_dict:
            sheet.update_cell(i, col_inv, stock_dict[key])
            actualizados += 1

    print(f"✅ Se actualizaron {actualizados} filas con inventario.")

# ========================
# ▶️ EJECUCIÓN PRINCIPAL
# ========================
def main():
    sheet = autenticar_gspread()
    stock_dict = cargar_stock_local(STOCK_JSON_PATH)
    actualizar_hoja(sheet, stock_dict)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error al ejecutar el script de sincronización: {e}")
