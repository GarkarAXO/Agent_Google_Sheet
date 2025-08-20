import gspread
import json
import re
from collections import defaultdict
from oauth2client.service_account import ServiceAccountCredentials

# === CONFIGURATION ===
SPREADSHEET_ID = '1aX1yUvj2kJFv331P9P2xgzdVwD2Miadb47wEJVMI4TQ'
SHEET_NAME = 'Articulos publicados Reventa'
AUX_SHEET_NAME = 'Auxiliar'
PRODUCTS_JSON_PATH = 'stock_summary.json'

# === AUTHENTICATION & DATA LOADING ===
def authenticate_gspread():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
        client = gspread.authorize(creds)
        print("✅ Autenticación con Google Sheets exitosa.")
        return client
    except Exception as e:
        print(f"❌ Falló la autenticación: {e}")
        exit()

def load_sheet_data(client, spreadsheet_id, sheet_name):
    try:
        sheet = client.open_by_key(spreadsheet_id).worksheet(sheet_name)
        all_data = sheet.get_all_values()
        headers = all_data[1] if len(all_data) > 1 else []
        rows = all_data[2:] if len(all_data) > 2 else []
        print(f"🔍 Se encontraron {len(headers)} encabezados y {len(rows)} filas de datos en la hoja.")
        return sheet, headers, rows
    except Exception as e:
        print(f"❌ Falló la carga de datos de la hoja: {e}")
        exit()

def load_local_products(json_path):
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Falló la carga del archivo de productos JSON: {e}")
        exit()

# === DATA PROCESSING HELPERS ===
def find_column_index(headers, column_title):
    import re
    normalized_column_title = re.sub(r'[^a-z0-9]', '', column_title.lower())
    for i, header in enumerate(headers):
        normalized_header = re.sub(r'[^a-z0-9]', '', header.lower())
        if normalized_column_title == normalized_header:
            return i
    raise ValueError(f"No se pudo encontrar la columna: {column_title}")

def extract_storage_capacity(model_string):
    match = re.search(r'(?:MEM|DD):(\d+(?:GB|TB))', model_string, re.IGNORECASE)
    if match:
        return match.group(1)
    match = re.search(r'(\d+\s*GB|\d+\s*TB)', model_string, re.IGNORECASE)
    if match:
        return match.group(1).replace(" ", "")
    return ""

def col_to_letter(col_idx):
    letter = ''
    temp_idx = col_idx
    while temp_idx >= 0:
        temp_idx, remainder = divmod(temp_idx, 26)
        letter = chr(65 + remainder) + letter
        temp_idx -= 1
    return letter

# === NEW CLEANUP & AUX SHEET LOGIC ===
def clean_column_brackets(sheet, column_index):
    col_letter = col_to_letter(column_index)
    print(f"🧼 Limpiando datos antiguos con corchetes en la columna {col_letter}...")
    updates_to_clean = []
    try:
        col_values = sheet.col_values(column_index + 1)
    except gspread.exceptions.APIError as e:
        print(f"⚠️ No se pudo leer la columna para limpiar. Es posible que no exista. Error: {e}")
        return

    for i, value in enumerate(col_values):
        if i < 2: continue
        if isinstance(value, str) and ('[' in value or ']' in value):
            cleaned_value = value.replace('[', '').replace(']', '')
            updates_to_clean.append({'range': f'{col_letter}{i + 1}', 'values': [[cleaned_value]]})
    
    if updates_to_clean:
        print(f"-> Se encontraron {len(updates_to_clean)} celdas para limpiar. Actualizando...")
        sheet.batch_update(updates_to_clean, value_input_option='USER_ENTERED')
        print("✅ Datos antiguos limpiados.")
    else:
        print("-> No se encontraron datos con corchetes para limpiar.")

def update_aux_sheet(spreadsheet, aux_sheet_name, products_by_model):
    print(f"📋 Actualizando la hoja '{aux_sheet_name}' con opciones de variantes...")
    vp_options, vs_options, vt_options = set(), set(), set()
    for model, product_list in products_by_model.items():
        for product in product_list:
            familia = product.get("Familia", "").upper()
            if "CELULARES" in familia:
                vp_options.add(extract_storage_capacity(model))
                vs_options.add(product.get("Color", "").strip())
                vt_options.add(product.get("Compañía", "").strip())
            elif "CONSOLAS" in familia:
                vp_options.add(extract_storage_capacity(model))
                vs_options.add("c-caja" if product.get("Con Caja") else "s-caja") # Use new format
    try:
        aux_sheet = spreadsheet.worksheet(aux_sheet_name)
        aux_sheet.batch_clear(['E:G'])
    except gspread.exceptions.WorksheetNotFound:
        aux_sheet = spreadsheet.add_worksheet(title=aux_sheet_name, rows=100, cols=26)
    
    headers = ["Opciones Variante Primaria", "Opciones Variante Secundaria", "Opciones Variante Terciaria"]
    vp_list = sorted([opt for opt in vp_options if opt])
    vs_list = sorted([opt for opt in vs_options if opt])
    vt_list = sorted([opt for opt in vt_options if opt])
    max_len = max(len(vp_list), len(vs_list), len(vt_list))
    data_to_write = [headers] + list(zip(vp_list + [''] * (max_len - len(vp_list)), vs_list + [''] * (max_len - len(vs_list)), vt_list + [''] * (max_len - len(vt_list))))
    aux_sheet.update(values=data_to_write, range_name='E1', value_input_option='USER_ENTERED')
    print(f"✅ Hoja '{aux_sheet_name}' actualizada.")

# === FORMATTING ===
def apply_data_validation_rule(spreadsheet, sheet, column_index, end_row, rule_dict, column_name):
    print(f"🎨 Aplicando regla de validación a la columna '{column_name}'...")
    try:
        request = {"setDataValidation": {"range": {"sheetId": sheet.id, "startRowIndex": 2, "endRowIndex": end_row, "startColumnIndex": column_index, "endColumnIndex": column_index + 1}, "rule": rule_dict}}
        spreadsheet.batch_update({"requests": [request]})
        print(f"✅ Regla de validación aplicada a '{column_name}'.")
    except Exception as e:
        print(f"⚠️ No se pudo aplicar la regla de validación a '{column_name}'. Error: {e}")

def apply_cell_format(spreadsheet, sheet, column_index, end_row, format_payload, column_name):
    print(f"🎨 Aplicando formato de celda a la columna '{column_name}'...")
    try:
        fields = "userEnteredFormat(" + ",".join(format_payload.keys()) + ")"
        if 'textFormat' in format_payload: fields = "userEnteredFormat(horizontalAlignment,numberFormat,textFormat.fontSize)"
        request = {"repeatCell": {"range": {"sheetId": sheet.id, "startRowIndex": 2, "endRowIndex": end_row, "startColumnIndex": column_index, "endColumnIndex": column_index + 1}, "cell": {"userEnteredFormat": format_payload}, "fields": fields}}
        spreadsheet.batch_update({"requests": [request]})
        print(f"✅ Formato de celda aplicado a '{column_name}'.")
    except Exception as e:
        print(f"⚠️ No se pudo aplicar el formato de celda a '{column_name}'. Error: {e}")

# === CORE LOGIC ===
def aggregate_local_stock(products_by_model):
    print("📦 Agregando el stock local por variante única...")
    local_variants = defaultdict(lambda: {"count": 0, "data": {}})
    # Colores comunes a ignorar para celulares, en formato capitalizado.
    colores_comunes = {"Azul", "Negro", "Blanco"}

    for model, product_list in products_by_model.items():
        for product in product_list:
            familia = product.get("Familia", "").upper()
            storage = extract_storage_capacity(model)
            color = product.get("Color", "").strip()
            carrier = product.get("Compañía", "").strip()
            box_status = "c-caja" if product.get("Con Caja") else "s-caja"  # Use new format

            # --- Lógica de exclusión de colores para celulares ---
            if "CELULARES" in familia:
                # Si el color no está especificado, no se puede procesar la variante.
                if not color:
                    continue
                # Si el color está en la lista de colores comunes, se ignora el producto.
                if color in colores_comunes:
                    continue
            # ----------------------------------------------------

            variant_key, variant_data = None, {}
            if "CELULARES" in familia:
                variant_key = f"{model.lower()}::{storage.lower()}::{color.lower()}::{carrier.lower()}"
                variant_data = {"vp": storage, "vs": color, "vt": carrier, "familia": familia}
            elif "CONSOLAS" in familia:
                variant_key = f"{model.lower()}::{storage.lower()}::{box_status.lower()}"
                variant_data = {"vp": storage, "vs": box_status, "vt": "", "familia": familia}
            
            if variant_key:
                local_variants[variant_key]["count"] += 1
                if not local_variants[variant_key]["data"]:
                    local_variants[variant_key]["data"] = variant_data
                    local_variants[variant_key]["data"]["model"] = model
                    local_variants[variant_key]["data"]["color"] = color
                    
    print(f"-> Se encontraron {len(local_variants)} variantes únicas en los archivos locales (filtrando colores comunes).")
    return local_variants

def map_sheet_variants(rows, headers, indices):
    print("📊 Mapeando variantes existentes en la hoja de Google...")
    sheet_variants, models_in_sheet = {}, set()
    for i, row in enumerate(rows, start=3):
        try:
            model, familia = row[indices["model"]].strip(), row[indices["familia"]].strip().upper()
            vp = row[indices["vp"]].strip().replace("[", "").replace("]", "")
            vs, vt = row[indices["vs"]].strip(), row[indices["vt"]].strip()
            if not model: continue
            models_in_sheet.add(model)
            variant_key = None
            if "CELULARES" in familia: variant_key = f"{model.lower()}::{vp.lower()}::{vs.lower()}::{vt.lower()}"
            elif "CONSOLAS" in familia: variant_key = f"{model.lower()}::{vp.lower()}::{vs.lower()}"
            if variant_key: sheet_variants[variant_key] = i
        except IndexError: continue
    print(f"-> Se mapearon {len(sheet_variants)} variantes de la hoja de Google.")
    return sheet_variants, models_in_sheet

def main():
    client = authenticate_gspread()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    
    sheet = spreadsheet.worksheet(SHEET_NAME)
    all_values = sheet.get_all_values()
    headers = all_values[1] if len(all_values) > 1 else []
    
    try:
        indices = {
            "model": find_column_index(headers, "Modelo"), "inventory": find_column_index(headers, "Inventario Partner"),
            "familia": find_column_index(headers, "Familia"), "vp": find_column_index(headers, "Variante Primaria"),
            "vs": find_column_index(headers, "Variante Secundaria"), "vt": find_column_index(headers, "Variante Terciaria"),
            "principal_extra": find_column_index(headers, "¿Principal o Extra?"), "cert": find_column_index(headers, "¿Certificado?"),
            "pub_exitosa": find_column_index(headers, "¿Publicación exitosa?"), "tiene_ventas": find_column_index(headers, "Tiene ventas?"),
            "ads_primaria": find_column_index(headers, "Pagamos Ads? (primaria)"), "ads_secundaria": find_column_index(headers, "Pagamos Ads? (secundaria)")
        }
        inventory_col_letter = col_to_letter(indices["inventory"])
    except ValueError as e:
        print(f"❌ Error crítico: {e}. Revisa los nombres de las columnas en tu hoja."); exit()

    # Clean up old bracketed data before any processing
    clean_column_brackets(sheet, indices["vp"])
    # We need to re-read the data after cleaning it
    rows = sheet.get_all_values()[2:] if len(sheet.get_all_values()) > 2 else []

    local_products_by_model = load_local_products(PRODUCTS_JSON_PATH)
    update_aux_sheet(spreadsheet, AUX_SHEET_NAME, local_products_by_model)

    local_variants = aggregate_local_stock(local_products_by_model)
    sheet_variants_map, models_in_sheet = map_sheet_variants(rows, headers, indices)

    batch_updates, rows_to_append = [], []
    print("\n🔄 Sincronizando datos locales con la hoja de Google...")

    for key, local_data in local_variants.items():
        stock_count, variant_details = local_data["count"], local_data["data"]
        if key in sheet_variants_map:
            row_index = sheet_variants_map[key]
            batch_updates.append({"range": f"{inventory_col_letter}{row_index}", "values": [[stock_count]]})
        else:
            if variant_details["model"] in models_in_sheet:
                new_row = [''] * len(headers)
                new_row[indices["model"]] = variant_details["model"]
                new_row[indices["familia"]] = variant_details["familia"]
                new_row[indices["vp"]] = variant_details["vp"]
                new_row[indices["vs"]] = variant_details["vs"]
                new_row[indices["vt"]] = variant_details["vt"]
                new_row[indices["inventory"]] = stock_count
                new_row[indices["cert"]] = "FALSE"
                new_row[indices["pub_exitosa"]] = "FALSE"
                new_row[indices["tiene_ventas"]] = "FALSE"
                new_row[indices["principal_extra"]] = "Extra"
                rows_to_append.append(new_row)

    variants_to_zero_out = set(sheet_variants_map.keys()) - set(local_variants.keys())
    if variants_to_zero_out:
        print(f"🧹 Se encontraron {len(variants_to_zero_out)} variantes para poner en cero.")
        for key in variants_to_zero_out:
            row_index = sheet_variants_map[key]
            batch_updates.append({"range": f"{inventory_col_letter}{row_index}", "values": [[0]]})

    if batch_updates: sheet.batch_update(batch_updates)
    if rows_to_append: 
        sheet.append_rows(rows_to_append, value_input_option='USER_ENTERED')
        sheet.sort((indices["model"] + 1, 'asc'), range=f'A3:Z{sheet.row_count}')

    # --- Final Formatting ---
    final_row_count = len(sheet.get_all_values())
    checkbox_rule = {"condition": {"type": "BOOLEAN"}, "strict": True, "showCustomUi": True}
    dropdown_principal_rule = {"condition": {"type": "ONE_OF_LIST", "values": [{"userEnteredValue": v} for v in ["Principal", "Extra"]]}, "strict": False}
    dropdown_ads_rule = {"condition": {"type": "ONE_OF_LIST", "values": [{"userEnteredValue": v} for v in ["Si", "No"]]}, "strict": False}
    dropdown_vp_rule = {"condition": {"type": "ONE_OF_RANGE", "values": [{"userEnteredValue": f"={AUX_SHEET_NAME}!E2:E"}]}, "strict": False}
    dropdown_vs_rule = {"condition": {"type": "ONE_OF_RANGE", "values": [{"userEnteredValue": f"={AUX_SHEET_NAME}!F2:F"}]}, "strict": False}
    dropdown_vt_rule = {"condition": {"type": "ONE_OF_RANGE", "values": [{"userEnteredValue": f"={AUX_SHEET_NAME}!G2:G"}]}, "strict": False}
    vp_cell_format = {"horizontalAlignment": "CENTER", "textFormat": {"fontSize": 10}}

    apply_data_validation_rule(spreadsheet, sheet, indices["cert"], final_row_count, checkbox_rule, "¿Certificado?")
    apply_data_validation_rule(spreadsheet, sheet, indices["pub_exitosa"], final_row_count, checkbox_rule, "¿Publicación exitosa?")
    apply_data_validation_rule(spreadsheet, sheet, indices["tiene_ventas"], final_row_count, checkbox_rule, "Tiene ventas?")
    apply_data_validation_rule(spreadsheet, sheet, indices["principal_extra"], final_row_count, dropdown_principal_rule, "¿Principal o Extra?")
    apply_data_validation_rule(spreadsheet, sheet, indices["ads_primaria"], final_row_count, dropdown_ads_rule, "Pagamos Ads? (primaria)")
    apply_data_validation_rule(spreadsheet, sheet, indices["ads_secundaria"], final_row_count, dropdown_ads_rule, "Pagamos Ads? (secundaria)")
    apply_data_validation_rule(spreadsheet, sheet, indices["vp"], final_row_count, dropdown_vp_rule, "Variante Primaria")
    apply_data_validation_rule(spreadsheet, sheet, indices["vs"], final_row_count, dropdown_vs_rule, "Variante Secundaria")
    apply_data_validation_rule(spreadsheet, sheet, indices["vt"], final_row_count, dropdown_vt_rule, "Variante Terciaria")
    apply_cell_format(spreadsheet, sheet, indices["vp"], final_row_count, vp_cell_format, "Variante Primaria (Formato)")

    if not batch_updates and not rows_to_append: print("\n🤷 No se necesitaron cambios. La hoja ya está sincronizada.")

if __name__ == "__main__":
    main()
