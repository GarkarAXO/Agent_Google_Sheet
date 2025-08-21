import gspread
import json
import re
from collections import defaultdict
from oauth2client.service_account import ServiceAccountCredentials

# === CONFIGURATION ===
SPREADSHEET_ID = '1aX1yUvj2kJFv331P9P2xgzdVwD2Miadb47wEJVMI4TQ'
SHEET_NAME = 'Articulos publicados Reventa'
AUX_SHEET_NAME = 'Auxiliar'
VARIANT_SUMMARY_JSON_PATH = 'stock_summary.json'

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

def load_local_variant_summary(json_path):
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Falló la carga del archivo de resumen de variantes JSON: {e}")
        exit()

# === DATA PROCESSING HELPERS ===
def find_column_index(headers, column_title):
    normalized_column_title = re.sub(r'[^a-z0-9]', '', column_title.lower())
    for i, header in enumerate(headers):
        normalized_header = re.sub(r'[^a-z0-9]', '', header.lower())
        if normalized_column_title == normalized_header:
            return i
    raise ValueError(f"No se pudo encontrar la columna: {column_title}")

def col_to_letter(col_idx):
    letter = ''
    temp_idx = col_idx
    while temp_idx >= 0:
        temp_idx, remainder = divmod(temp_idx, 26)
        letter = chr(65 + remainder) + letter
        temp_idx -= 1
    return letter

# === CLEANUP, AUX & FORMATTING FUNCTIONS ===
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

def update_aux_sheet(spreadsheet, aux_sheet_name, local_variant_summary):
    print(f"📋 Actualizando la hoja '{aux_sheet_name}' con opciones de variantes...")
    vp_options, vs_options, vt_options = set(), set(), set()
    for variant in local_variant_summary:
        familia = variant.get("familia", "").upper()
        if "CELULARES" in familia:
            vp_options.add(variant.get("storage", ""))
            vs_options.add(variant.get("color", "").strip())
            vt_options.add(variant.get("compania", "").strip())
        elif "CONSOLAS" in familia:
            vp_options.add(variant.get("storage", ""))
            vs_options.add(variant.get("caja", ""))
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

def apply_data_validation_rule(spreadsheet, sheet, column_index, end_row, rule_dict, column_name):
    print(f"🎨 Aplicando regla de validación a la columna '{column_name}'...")
    try:
        request = {"setDataValidation": {"range": {"sheetId": sheet.id, "startRowIndex": 2, "endRowIndex": end_row, "startColumnIndex": column_index, "endColumnIndex": column_index + 1}, "rule": rule_dict}}
        spreadsheet.batch_update({"requests": [request]})
        print(f"✅ Regla de validación aplicada a '{column_name}'.")
    except Exception as e:
        print(f"⚠️ No se pudo aplicar la regla de validación a '{column_name}'. Error: {e}")

def apply_chip_style_from_template(spreadsheet, sheet, column_index, end_row, template_cell_a1, column_name):
    """Copies the data validation from a template cell to a whole column."""
    print(f"🎨 Aplicando estilo de validación 'chip' a la columna '{column_name}' desde la plantilla '{template_cell_a1}'...")
    try:
        match = re.match(r"([A-Z]+)([0-9]+)", template_cell_a1.upper())
        if not match:
            raise ValueError(f"Formato de celda de plantilla no válido: {template_cell_a1}")
        
        col_str, row_str = match.groups()
        
        col_idx = 0
        for char in col_str:
            col_idx = col_idx * 26 + (ord(char) - ord('A') + 1)
        col_idx = col_idx - 1

        row_idx = int(row_str) - 1

        source_range = {
            "sheetId": sheet.id,
            "startRowIndex": row_idx,
            "endRowIndex": row_idx + 1,
            "startColumnIndex": col_idx,
            "endColumnIndex": col_idx + 1,
        }
        
        destination_range = {
            "sheetId": sheet.id,
            "startRowIndex": 2,
            "endRowIndex": end_row,
            "startColumnIndex": column_index,
            "endColumnIndex": column_index + 1,
        }

        request = {
            "copyPaste": {
                "source": source_range,
                "destination": destination_range,
                "pasteType": "PASTE_DATA_VALIDATION",
                "pasteOrientation": "NORMAL"
            }
        }
        
        spreadsheet.batch_update({"requests": [request]})
        print(f"✅ Estilo de validación 'chip' aplicado a '{column_name}'.")

    except Exception as e:
        print(f"⚠️ No se pudo aplicar el estilo de validación 'chip' a '{column_name}'. Error: {e}")


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
def map_sheet_variants(rows, headers, indices):
    print("📊 Mapeando variantes existentes en la hoja de Google...")
    sheet_variants = {}
    for i, row in enumerate(rows, start=3):
        try:
            model = row[indices["model"]].strip()
            familia = row[indices["familia"]].strip().upper()
            vp = row[indices["vp"]].strip()
            vs = row[indices["vs"]].strip()
            vt = row[indices["vt"]].strip()
            if not model: continue
            
            variant_key = None
            if "CELULARES" in familia:
                variant_key = f"{model.lower()}::{vp.lower()}::{vs.lower()}::{vt.lower()}"
            elif "CONSOLAS" in familia:
                color_from_sheet = row[indices["color_col"]].strip()
                variant_key = f"{model.lower()}::{vp.lower()}::{vs.lower()}::{color_from_sheet.lower()}"

            if variant_key: sheet_variants[variant_key] = i
        except IndexError: 
            continue
    print(f"-> Se mapearon {len(sheet_variants)} variantes de la hoja de Google.")
    return sheet_variants

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
            "ads_primaria": find_column_index(headers, "Pagamos Ads? (primaria)"), "ads_secundaria": find_column_index(headers, "Pagamos Ads? (secundaria)"),
            "color_col": find_column_index(headers, "Color")
        }
        try:
            indices["caja"] = find_column_index(headers, "¿Caja?")
        except ValueError:
            print("⚠️ No se encontró la columna '¿Caja?'. Se omitirá.")
        try:
            indices["clase"] = find_column_index(headers, "Clase")
        except ValueError:
            print("⚠️ No se encontró la columna 'Clase'. Se omitirá.")
        try:
            indices["quien_publica"] = find_column_index(headers, "Quien publica?")
        except ValueError:
            print("⚠️ No se encontró la columna 'Quien publica?'. Se omitirá.")

        inventory_col_letter = col_to_letter(indices["inventory"])
    except ValueError as e:
        print(f"❌ Error crítico: {e}. Revisa los nombres de las columnas en tu hoja."); exit()

    clean_column_brackets(sheet, indices["vp"])
    rows = sheet.get_all_values()[2:] if len(sheet.get_all_values()) > 2 else []

    # --- NEW: Pre-process to find models marked as 'Principal' ---
    principal_models = set()
    print("🔍 Identificando modelos 'Principales' en la hoja...")
    for row in rows:
        try:
            if row[indices["principal_extra"]].strip().lower() == 'principal':
                principal_models.add(row[indices["model"]].strip())
        except IndexError:
            continue
    print(f"-> {len(principal_models)} modelos marcados como 'Principal' encontrados.")
    # ---------------------------------------------------------

    local_variant_summary = load_local_variant_summary(VARIANT_SUMMARY_JSON_PATH)
    update_aux_sheet(spreadsheet, AUX_SHEET_NAME, local_variant_summary)

    sheet_variants_map = map_sheet_variants(rows, headers, indices)
    local_variants_map = {}

    batch_updates, rows_to_append = [], []
    print("\n🔄 Sincronizando el resumen de stock local con la hoja de Google...")

    for variant in local_variant_summary:
        model_original = variant.get("model_original", "")

        # --- NEW: 'Principal' Filter Logic ---
        if model_original not in principal_models:
            continue
        # ------------------------------------

        familia = variant.get("familia", "").upper()
        storage = variant.get("storage", "")
        color = variant.get("color", "")
        compania = variant.get("compania", "")
        caja = variant.get("caja", "")

        key = None
        variant_details_for_new_row = {}
        if "CELULARES" in familia:
            key = f"{model_original.lower()}::{storage.lower()}::{color.lower()}::{compania.lower()}"
            variant_details_for_new_row = {"model": model_original, "familia": familia, "vp": storage, "vs": color, "vt": compania}
        elif "CONSOLAS" in familia:
            # Key for consoles includes model, storage (vp), caja (vs), and color (from the 'color' field in the variant)
            key = f"{model_original.lower()}::{storage.lower()}::{caja.lower()}::{color.lower()}"
            # For new rows, vp is storage, vs is caja, vt is empty, and 'Color' column is populated with variant['color']
            variant_details_for_new_row = {"model": model_original, "familia": familia, "vp": storage, "vs": caja, "vt": "", "color_col": color}
        
        if not key: continue
        
        local_variants_map[key] = variant["stock"]

        if key in sheet_variants_map:
            row_index = sheet_variants_map[key]
            batch_updates.append({'range': f'{inventory_col_letter}{row_index}', 'values': [[variant["stock"]]]})
        else:
            new_row = [''] * len(headers)
            for col_name, index in indices.items():
                if col_name in variant_details_for_new_row:
                    new_row[index] = variant_details_for_new_row[col_name]
                elif col_name == "inventory":
                    new_row[index] = variant["stock"]
                elif col_name == "color_col" and "color_col" in variant_details_for_new_row: # Handle color_col specifically
                    new_row[index] = variant_details_for_new_row["color_col"]
            # Set default values for boolean-like columns for new rows
            new_row[indices["cert"]] = "FALSE"
            new_row[indices["pub_exitosa"]] = "FALSE"
            new_row[indices["tiene_ventas"]] = "FALSE"
            new_row[indices["principal_extra"]] = "Extra"
            rows_to_append.append(new_row)

    variants_to_zero_out = set(sheet_variants_map.keys()) - set(local_variants_map.keys())
    if variants_to_zero_out:
        print(f"🧹 Se encontraron {len(variants_to_zero_out)} variantes en la hoja que no existen localmente. Poniendo su stock a 0...")
        for key in variants_to_zero_out:
            row_index = sheet_variants_map[key]
            batch_updates.append({'range': f'{inventory_col_letter}{row_index}', 'values': [[0]]})

    if batch_updates:
        print(f"-> Actualizando {len(batch_updates)} filas existentes...")
        sheet.batch_update(batch_updates)
    
    if rows_to_append:
        print(f"-> Añadiendo {len(rows_to_append)} nuevas filas...")
        sheet.append_rows(rows_to_append, value_input_option='USER_ENTERED')
        # FIX: Use the actual column count for the sort range to avoid issues with columns beyond Z
        last_col_letter = col_to_letter(sheet.col_count - 1)
        print(f"-> Ordenando hasta la columna {last_col_letter}...")
        sheet.sort((indices["model"] + 1, 'asc'), range=f'A3:{last_col_letter}{sheet.row_count}')

    # --- Final Formatting Calls ---
    final_row_count = len(sheet.get_all_values())
    checkbox_rule = {"condition": {"type": "BOOLEAN"}, "strict": True, "showCustomUi": True}
    
    apply_data_validation_rule(spreadsheet, sheet, indices["cert"], final_row_count, checkbox_rule, "¿Certificado?")
    apply_data_validation_rule(spreadsheet, sheet, indices["pub_exitosa"], final_row_count, checkbox_rule, "¿Publicación exitosa?")
    apply_data_validation_rule(spreadsheet, sheet, indices["tiene_ventas"], final_row_count, checkbox_rule, "Tiene ventas?")

    apply_chip_style_from_template(spreadsheet, sheet, indices["principal_extra"], final_row_count, 'L3', "¿Principal o Extra?")
    apply_chip_style_from_template(spreadsheet, sheet, indices["ads_primaria"], final_row_count, 'Q3', "Pagamos Ads? (primaria)")
    apply_chip_style_from_template(spreadsheet, sheet, indices["ads_secundaria"], final_row_count, 'R3', "Pagamos Ads? (secundaria)")
    if "caja" in indices:
        apply_chip_style_from_template(spreadsheet, sheet, indices["caja"], final_row_count, 'S3', "¿Caja?")
    if "clase" in indices:
        apply_chip_style_from_template(spreadsheet, sheet, indices["clase"], final_row_count, 'W3', "Clase")
    if "quien_publica" in indices:
        apply_chip_style_from_template(spreadsheet, sheet, indices["quien_publica"], final_row_count, 'X3', "Quien publica?")
    if "familia" in indices:
        apply_chip_style_from_template(spreadsheet, sheet, indices["familia"], final_row_count, 'AA3', "Familia")

    dropdown_vp_rule = {"condition": {"type": "ONE_OF_RANGE", "values": [{"userEnteredValue": f"={AUX_SHEET_NAME}!E2:E"}]}, "strict": False}
    dropdown_vs_rule = {"condition": {"type": "ONE_OF_RANGE", "values": [{"userEnteredValue": f"={AUX_SHEET_NAME}!F2:F"}]}, "strict": False}
    dropdown_vt_rule = {"condition": {"type": "ONE_OF_RANGE", "values": [{"userEnteredValue": f"={AUX_SHEET_NAME}!G2:G"}]}, "strict": False}
    vp_cell_format = {"horizontalAlignment": "CENTER", "textFormat": {"fontSize": 10}}

    apply_data_validation_rule(spreadsheet, sheet, indices["vp"], final_row_count, dropdown_vp_rule, "Variante Primaria")
    apply_data_validation_rule(spreadsheet, sheet, indices["vs"], final_row_count, dropdown_vs_rule, "Variante Secundaria")
    apply_data_validation_rule(spreadsheet, sheet, indices["vt"], final_row_count, dropdown_vt_rule, "Variante Terciaria")
    apply_cell_format(spreadsheet, sheet, indices["vp"], final_row_count, vp_cell_format, "Variante Primaria (Formato)")

    if not batch_updates and not rows_to_append and not variants_to_zero_out:
        print("\n🤷 No se necesitaron cambios. La hoja ya está sincronizada.")
    else:
        print("\n✅ Sincronización completada.")


if __name__ == "__main__":
    main()