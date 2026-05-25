import os
import glob
import pymysql
import pandas as pd
from datetime import datetime

# ==============================================================================
# Configuration Constants
# ==============================================================================
ID_GRUPO_FAMILIAR = 1
ID_INSTRUMENTO = 222
ID_PROPIETARIO = 3
ID_APORTANTE = 1
ID_ESTADO_INVERSION = 128

# ==============================================================================
# Helper Functions
# ==============================================================================
def map_propietario_to_id(propietario_name, default_id=3):
    """
    Maps the owner name from the CSV to the corresponding persona ID in sipro_desa.
    """
    if pd.isna(propietario_name) or not isinstance(propietario_name, str):
        return default_id
    
    name_clean = propietario_name.lower().strip()
    if 'jhon' in name_clean:
        return 1
    elif 'cristian' in name_clean:
        return 2
    elif 'isabel' in name_clean:
        return 3
    elif 'jaime' in name_clean:
        return 4
    elif 'argentina' in name_clean:
        return 5
        
    return default_id


def read_csv_data(csv_file):
    """
    Reads the CSV file with semicolon delimiter trying different encodings.
    """
    encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    for encoding in encodings:
        try:
            return pd.read_csv(csv_file, delimiter=';', encoding=encoding)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(csv_file, delimiter=';', encoding='utf-8', errors='ignore')


def filter_records(df):
    """
    Filters records based on the conditions:
    - tipo_operacion = COMPRA (if exists)
    - tipo_documento = NOTA_CREDITO or similar
    """
    df_filtered = df.copy()
    # Filter for COMPRA operations if column exists
    if 'tipo_operacion' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['tipo_operacion'] == 'COMPRA'].copy()
    # Filter for NOTA_CREDITO or similar documents if column exists
    if 'tipo_documento' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['tipo_documento'].str.contains('NOTA_CREDITO', case=False, na=False)]
    return df_filtered


def load_db_config():
    """
    Loads database configuration from the backend .env file if available,
    otherwise falls back to default localhost settings.
    """
    db_config = {
        'host': '127.0.0.1',
        'port': 3306,
        'user': 'root',
        'password': '',
        'database': 'sipro_desa'
    }
    
    # Check common relative locations for the backend .env file
    # Path relative to script location: '../../../Angular/SGII/backend/.env' (from Bolsa/Programas)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    env_locations = [
        os.path.abspath(os.path.join(script_dir, '../../../Angular/SGII/backend/.env')),
        os.path.abspath(os.path.join(script_dir, '../../Angular/SGII/backend/.env')),
        os.path.abspath(os.path.join(script_dir, '../Angular/SGII/backend/.env')),
        os.path.abspath(os.path.join(script_dir, '.env'))
    ]
    
    env_path = None
    for loc in env_locations:
        if os.path.exists(loc):
            env_path = loc
            break
            
    if env_path:
        print(f"Loading database configuration from env: {env_path}")
        try:
            with open(env_path, 'r') as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, val = line.strip().split('=', 1)
                        val = val.strip().strip('"').strip("'")
                        if key == 'DB_HOST': db_config['host'] = val
                        elif key == 'DB_PORT': db_config['port'] = int(val)
                        elif key == 'DB_DATABASE': db_config['database'] = val
                        elif key == 'DB_USERNAME': db_config['user'] = val
                        elif key == 'DB_PASSWORD': db_config['password'] = val
        except Exception as e:
            print(f"Warning: Failed to parse .env file: {e}. Using defaults.")
    else:
        print("Using default local database configuration (no .env found).")
        
    return db_config


def to_float(val, default=0.0):
    """
    Safely converts a value to float, returning default if conversion fails or if it is NaN.
    """
    try:
        if pd.isna(val):
            return default
        return float(val)
    except (ValueError, TypeError):
        return default


def main():
    # Find the CSV file in Salida directory relative to script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    carpeta_salida = os.path.join(script_dir, "Salida")
    
    if not os.path.exists(carpeta_salida):
        # Fallback to parent Salida
        carpeta_salida = os.path.join(script_dir, "..", "Salida")
        
    if not os.path.exists(carpeta_salida):
        print(f"Error: No existe la carpeta Salida en {os.path.dirname(carpeta_salida)}")
        return
        
    archivos_csv = []
    for archivo in os.listdir(carpeta_salida):
        if archivo.startswith('resultados_pdf_') and archivo.endswith('.csv'):
            ruta_completa = os.path.join(carpeta_salida, archivo)
            archivos_csv.append((ruta_completa, os.path.getmtime(ruta_completa)))
            
    if not archivos_csv:
        print(f"Error: No se encontraron archivos CSV de resultados en {carpeta_salida}")
        return
        
    # Sort by modification time (most recent first)
    archivos_csv.sort(key=lambda x: x[1], reverse=True)
    csv_file = archivos_csv[0][0]
    print(f"Using CSV file: {csv_file}")
    
    # Read CSV data
    try:
        df = read_csv_data(csv_file)
        print(f"CSV loaded successfully. Shape: {df.shape}")
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return
        
    # Filter records based on conditions
    filtered_df = filter_records(df)
    print(f"Found {len(filtered_df)} records matching the criteria (COMPRA + NOTA_CREDITO)")
    
    if len(filtered_df) == 0:
        print("No records to process. Exiting.")
        return
        
    # Get database connection config
    db_config = load_db_config()
    
    # Establish connection
    try:
        conn = pymysql.connect(**db_config)
        print("Connected to database successfully.")
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return
        
    try:
        today_date = datetime.now().strftime("%Y-%m-%d")
        now_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        records_inserted = 0
        records_skipped = 0
        
        with conn.cursor() as cursor:
            for index, row in filtered_df.iterrows():
                liquidacion = str(row['operacion_no']).strip()
                csv_propietario = row.get('propietario', '')
                id_propietario = map_propietario_to_id(csv_propietario, default_id=ID_PROPIETARIO)
                print(f"\nProcessing record {index + 1}:")
                print(f"  Propietario: {csv_propietario} (ID: {id_propietario})")
                print(f"  Liquidación (Operación No): {liquidacion}")
                print(f"  Valor Nominal: {row['valor_nominal']}")
                
                # Check for duplicates using liquidacion
                check_sql = "SELECT id_inversion FROM inversion WHERE liquidacion = %s AND eliminado = 0"
                cursor.execute(check_sql, (liquidacion,))
                if cursor.fetchone():
                    print(f"  [SKIP] Record with liquidacion '{liquidacion}' already exists in database.")
                    records_skipped += 1
                    continue
                
                # Extract and parse numeric fields safely
                valor_nominal = to_float(row['valor_nominal'])
                precio_compra = to_float(row['precio'])
                precio_neto = to_float(row['precio_neto'])
                total_comisiones = to_float(row['total_comisiones'])
                comision_bolsa = to_float(row['comision_bolsa'])
                comision_casa_valores = to_float(row['comision_operador'])
                capital_invertido = to_float(row['total_comprador_neto'])
                
                # Calculate derived values (valor comprado sin comision)
                valor_comprado_sin_comision = valor_nominal * (precio_neto / 100.0)
                
                # Prepare insert statement fields
                insert_sql = """
                INSERT INTO inversion (
                    id_grupo_familiar,
                    id_instrumento,
                    id_propietario,
                    id_aportante,
                    liquidacion,
                    id_estado_inversion,
                    fecha_compra,
                    fecha_venta,
                    valor_nominal,
                    monto_a_negociar,
                    capital_invertido,
                    tasa_interes,
                    rendimiento_nominal,
                    rendimiento_efectivo,
                    valor_efectivo,
                    valor_sin_comision,
                    valor_con_interes,
                    interes_acumulado_previo,
                    interes_mensual,
                    interes_primer_mes,
                    total_comisiones,
                    tasa_mensual_real,
                    fecha_primer_pago,
                    precio_compra,
                    precio_neto_compra,
                    comision_bolsa,
                    comision_casa_valores,
                    retencion_fuente,
                    observacion,
                    expirado,
                    activo,
                    eliminado,
                    fecha_creacion,
                    fecha_actualizacion
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s
                )
                """
                
                # Construct query parameters tuple
                params = (
                    ID_GRUPO_FAMILIAR,
                    ID_INSTRUMENTO,
                    id_propietario,
                    ID_APORTANTE,
                    liquidacion,
                    ID_ESTADO_INVERSION,
                    today_date,                # fecha_compra
                    None,                      # fecha_venta
                    valor_nominal,             # valor_nominal
                    valor_nominal,             # monto_a_negociar
                    capital_invertido,         # capital_invertido (valor comprado con comision)
                    1.0,                       # tasa_interes
                    1.0,                       # rendimiento_nominal
                    None,                      # rendimiento_efectivo
                    valor_comprado_sin_comision, # valor_efectivo (valor comprado sin comision)
                    valor_comprado_sin_comision, # valor_sin_comision
                    valor_comprado_sin_comision, # valor_con_interes
                    0.0,                       # interes_acumulado_previo
                    0.0,                       # interes_mensual
                    0.0,                       # interes_primer_mes
                    total_comisiones,          # total_comisiones
                    0.0,                       # tasa_mensual_real
                    None,                      # fecha_primer_pago
                    precio_compra,             # precio_compra (precio_comprado)
                    precio_neto,               # precio_neto_compra (precio_neto)
                    total_comisiones - comision_casa_valores, # comision_bolsa
                    comision_casa_valores,     # comision_casa_valores
                    0.0,                       # retencion_fuente
                    f"Migrado de archivo: {row['archivo']}", # observacion
                    0,                         # expirado
                    1,                         # activo
                    0,                         # eliminado
                    now_datetime,              # fecha_creacion
                    now_datetime               # fecha_actualizacion
                )
                
                cursor.execute(insert_sql, params)
                # Retrieve generated id_inversion
                id_inversion = cursor.lastrowid

                # Insert amortization record
                amort_sql = """
                INSERT INTO amortizacion (
                    id_amortizacion,
                    id_inversion,
                    numero_cuota,
                    fecha_pago,
                    interes,
                    capital,
                    descuento,
                    total,
                    int_parcial,
                    retencion,
                    id_estado_amortizacion,
                    pagada,
                    activo,
                    eliminado,
                    fecha_creacion,
                    fecha_actualizacion
                ) VALUES (
                    NULL,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    CURRENT_TIMESTAMP(),
                    CURRENT_TIMESTAMP()
                )
                """
                amort_params = (
                    id_inversion,
                    1,                     # numero_cuota
                    '2034-12-31',          # fecha_pago placeholder
                    0,                     # interes
                    capital_invertido,     # capital
                    0,                     # descuento
                    capital_invertido,     # total
                    0,                     # int_parcial
                    0,                     # retencion
                    134,                   # id_estado_amortizacion
                    0,                     # pagada
                    1,                     # activo
                    0                      # eliminado
                )
                cursor.execute(amort_sql, amort_params)

                # Insert capital movement record
                mov_sql = """
                INSERT INTO movimiento_capital (
                    id_tipo_movimiento,
                    id_persona,
                    id_inversion,
                    id_venta_inversion,
                    id_cuenta_bancaria,
                    id_signo,
                    monto,
                    fecha_movimiento,
                    descripcion,
                    conciliado,
                    fecha_conciliacion,
                    activo,
                    eliminado,
                    fecha_creacion,
                    fecha_actualizacion
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()
                )
                """
                mov_params = (
                    181,                   # id_tipo_movimiento
                    id_propietario,        # id_persona
                    id_inversion,          # id_inversion
                    None,                  # id_venta_inversion
                    None,                  # id_cuenta_bancaria
                    191,                   # id_signo
                    capital_invertido,     # monto
                    today_date,            # fecha_movimiento
                    "Compra Nota de Crédito", # descripcion
                    0,                     # conciliado
                    None,                  # fecha_conciliacion
                    1,                     # activo
                    0                      # eliminado
                )
                cursor.execute(mov_sql, mov_params)

                print(f"  [OK] Successfully inserted records into inversion, amortizacion, and movimiento_capital tables.")
                records_inserted += 1
                
        # Commit the transaction
        conn.commit()
        print(f"\n[OK] Database operation finished.")
        print(f"     Records inserted: {records_inserted}")
        print(f"     Records skipped (duplicates): {records_skipped}")
        
    except Exception as e:
        # Rollback in case of errors
        conn.rollback()
        print(f"\nError: Database operation failed, transaction rolled back. Detail: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
