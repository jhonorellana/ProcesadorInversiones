"""
Programa para generar archivos SQL de ejecución a partir de datos CSV
Genera sentencias SQL INSERT para la base de datos MySQL 'inversiones'
"""
import csv
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import os

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SQLGenerator:
    """Clase para generar archivos SQL a partir de datos CSV"""
    
    def __init__(self):
        self.output_folder = "../Salida"
    
    def mapear_tipo_documento_a_tipo_inversion(self, tipo_documento: str) -> int:
        """Mapea el tipo de documento al código de tipo de inversión"""
        mapeo = {
            'NOTA_CREDITO': 91,
            'BONO_ESTADO': 92,
            'PAPEL_COMERCIAL': 93
        }
        return mapeo.get(tipo_documento, 91)  # Default a NOTA_CREDITO
    
    def mapear_emisor_a_id_instrumento(self, emisor: str, titulo_valor: str) -> str:
        """Mapea el emisor al ID del instrumento"""
        # Si el emisor contiene SRI, usar ese formato
        if 'SERVICIO DE RENTAS INTERNAS' in emisor or 'SRI' in emisor:
            return 'SRI 2034-12-31'
        
        # Para Bonos del Estado
        if 'BONO DEL ESTADO' in titulo_valor:
            return 'BONO_ESTADO 2034-12-31'
        
        # Default
        return 'SRI 2034-12-31'
    
    def parsear_fecha(self, fecha_str: str) -> Optional[str]:
        """Parsea diferentes formatos de fecha a YYYY-MM-DD"""
        if not fecha_str or fecha_str.strip() == '' or fecha_str.lower() == 'null':
            return 'NULL'
        
        try:
            # Intentar diferentes formatos
            formatos = [
                '%d/%m/%Y',  # 25/07/2024
                '%Y-%m-%d',  # 2024-07-25
                '%d-%m-%Y',  # 25-07-2024
                '%Y/%m/%d',  # 2024/07/25
            ]
            
            for formato in formatos:
                try:
                    fecha_obj = datetime.strptime(fecha_str.strip(), formato)
                    return f"'{fecha_obj.strftime('%Y-%m-%d')}'"
                except ValueError:
                    continue
            
            logger.warning(f"No se pudo parsear fecha: {fecha_str}")
            return 'NULL'
        except Exception as e:
            logger.error(f"Error parseando fecha {fecha_str}: {e}")
            return 'NULL'
    
    def limpiar_valor_numerico_db(self, valor: str) -> str:
        """Convierte un valor numérico limpio a string SQL"""
        if not valor or valor.strip() == '' or valor.lower() == 'null':
            return 'NULL'
        
        try:
            # El valor ya viene limpio del extractor
            valor_float = float(valor.strip())
            return str(valor_float)
        except (ValueError, TypeError) as e:
            logger.warning(f"No se pudo convertir a número: {valor}")
            return 'NULL'
    
    def escapar_string_sql(self, valor: str) -> str:
        """Escapa strings para SQL"""
        if not valor or valor.strip() == '' or valor.lower() == 'null':
            return 'NULL'
        
        # Escapar comillas simples
        valor_escaped = valor.strip().replace("'", "\\'").replace('"', '\\"')
        return f"'{valor_escaped}'"
    
    def generar_sql_registro(self, registro_csv: Dict[str, Any]) -> str:
        """Genera una sentencia SQL INSERT para un registro"""
        
        # Mapeos y conversiones
        tipo_documento = registro_csv.get('tipo_documento', '')
        inv_tipo = self.mapear_tipo_documento_a_tipo_inversion(tipo_documento)
        
        # Fechas
        inv_fecha_compra = f"'{datetime.now().strftime('%Y-%m-%d')}'"  # Fecha actual como compra
        inv_fecha_emision = self.parsear_fecha(registro_csv.get('emision_titulo', ''))
        inv_fecha_vencimiento = self.parsear_fecha(registro_csv.get('vencimiento_titulo', ''))
        
        # Valores numéricos
        valor_nominal = self.limpiar_valor_numerico_db(registro_csv.get('valor_nominal', ''))
        monto_a_negociar = self.limpiar_valor_numerico_db(registro_csv.get('monto_a_negociar', ''))
        capital_invertido = self.limpiar_valor_numerico_db(registro_csv.get('total_comprador_neto', ''))
        valor_efectivo = self.limpiar_valor_numerico_db(registro_csv.get('valor_efectivo', ''))
        comision_bolsa = self.limpiar_valor_numerico_db(registro_csv.get('comision_bolsa', ''))
        comision_operador = self.limpiar_valor_numerico_db(registro_csv.get('comision_operador', ''))
        total_comisiones = self.limpiar_valor_numerico_db(registro_csv.get('total_comisiones', ''))
        precio = self.limpiar_valor_numerico_db(registro_csv.get('precio', ''))
        precio_neto = self.limpiar_valor_numerico_db(registro_csv.get('precio_neto', ''))
        rend_nominal = self.limpiar_valor_numerico_db(registro_csv.get('rend_nominal', ''))
        rend_efectivo = self.limpiar_valor_numerico_db(registro_csv.get('rend_efectivo', ''))
        
        # Emisor e instrumento
        emisor = registro_csv.get('emisor', '')
        titulo_valor = registro_csv.get('titulo_valor', '')
        id_instrumento = self.escapar_string_sql(self.mapear_emisor_a_id_instrumento(emisor, titulo_valor))
        
        # Strings
        inv_liquidacion = self.escapar_string_sql(registro_csv.get('operacion_no', ''))
        inv_emisor = self.escapar_string_sql(emisor if emisor else 'SRI 2034-12-31')
        
        # Construir sentencia SQL
        sql = f"""INSERT INTO inversion (
    inv_tipo, inv_fecha_compra, inv_propietario, inv_liquidacion, inv_instrumento,
    inv_fecha_emision, inv_fecha_vencimiento, inv_fecha_venta, inv_emisor,
    inv_calificacion_riesgo, inv_valor_nominal, inv_monto_a_negociar,
    inv_capital_invertido, inv_tasa_interes, inv_rendimiento_nominal,
    inv_rendimiento_efectivo, inv_valor_efectivo, inv_valor_interes,
    inv_comision_bolsa, inv_comision_operador, inv_retencion, inv_expirado,
    inv_pagada, inv_tasa_mensual_real, inv_interes_primer_mes,
    inv_fecha_primer_pago, inv_precio_comprado, inv_precio_neto_comprado,
    inv_valor_sin_comision, inv_valor_con_interes, inv_interes_acumulado_previo,
    inv_total_comisiones, inv_codigo_SEB, inv_codigo_BCE, inv_fechas_pagos_capital,
    id_instrumento, is_active, is_deleted, created_at, updated_at
) VALUES (
    {inv_tipo}, {inv_fecha_compra}, 'Jhon', {inv_liquidacion}, {91 if 'BONO' in tipo_documento else 222},
    {inv_fecha_emision}, {inv_fecha_vencimiento}, NULL, {inv_emisor},
    NULL, {valor_nominal}, {monto_a_negociar},
    {capital_invertido}, 1, {rend_nominal if rend_nominal != 'NULL' else 1},
    {rend_efectivo if rend_efectivo != 'NULL' else 1}, {valor_efectivo}, 0,
    {comision_bolsa}, {comision_operador}, 0, 0,
    0, 1, 0,
    NULL, {precio}, {precio_neto},
    {valor_efectivo}, {capital_invertido}, 0,
    {total_comisiones}, NULL, NULL, NULL,
    {id_instrumento}, 1, 0, NOW(), NOW()
);"""
        
        return sql
    
    def generar_archivo_sql(self, ruta_csv: str) -> Dict[str, Any]:
        """Genera un archivo SQL con todas las sentencias INSERT"""
        resultados = {
            'total_registros': 0,
            'sql_generados': 0,
            'errores': 0,
            'detalles_errores': [],
            'archivo_sql': ''
        }
        
        try:
            with open(ruta_csv, 'r', encoding='latin-1') as file:
                reader = csv.DictReader(file, delimiter=';')
                
                logger.info(f"Procesando archivo CSV: {ruta_csv}")
                logger.info(f"Columnas encontradas: {list(reader.fieldnames)}")
                
                # Generar nombre de archivo SQL
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                nombre_archivo_sql = f"insert_inversion_{timestamp}.sql"
                ruta_archivo_sql = os.path.join(self.output_folder, nombre_archivo_sql)
                
                # Crear archivo SQL
                with open(ruta_archivo_sql, 'w', encoding='utf-8') as sql_file:
                    # Escribir encabezado
                    sql_file.write(f"-- Generated SQL INSERT statements\n")
                    sql_file.write(f"-- Source CSV: {os.path.basename(ruta_csv)}\n")
                    sql_file.write(f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    sql_file.write(f"-- Database: inversiones, Table: inversion\n\n")
                    
                    # Escribir configuración inicial
                    sql_file.write("-- Disable foreign key checks\n")
                    sql_file.write("SET FOREIGN_KEY_CHECKS = 0;\n")
                    sql_file.write("SET UNIQUE_CHECKS = 0;\n\n")
                    
                    registro_num = 0
                    for row_num, row in enumerate(reader, 1):
                        resultados['total_registros'] += 1
                        
                        try:
                            # Generar SQL para el registro
                            sql_registro = self.generar_sql_registro(row)
                            
                            # Escribir en el archivo
                            sql_file.write(f"-- Registro {row_num}: {row.get('archivo', 'N/A')}\n")
                            sql_file.write(sql_registro + "\n\n")
                            
                            resultados['sql_generados'] += 1
                            registro_num += 1
                            
                            if registro_num % 10 == 0:
                                logger.info(f"Generados {registro_num} registros SQL...")
                        
                        except Exception as e:
                            resultados['errores'] += 1
                            resultados['detalles_errores'].append({
                                'fila': row_num,
                                'error': str(e),
                                'datos': row.get('archivo', 'N/A')
                            })
                            logger.error(f"Error generando SQL para fila {row_num}: {e}")
                    
                    # Escribir pie de página
                    sql_file.write("-- Re-enable foreign key checks\n")
                    sql_file.write("SET FOREIGN_KEY_CHECKS = 1;\n")
                    sql_file.write("SET UNIQUE_CHECKS = 1;\n\n")
                    
                    sql_file.write(f"-- Total statements generated: {resultados['sql_generados']}\n")
                    sql_file.write(f"-- Total errors: {resultados['errores']}\n")
                
                resultados['archivo_sql'] = ruta_archivo_sql
                logger.info(f"Archivo SQL generado: {ruta_archivo_sql}")
        
        except FileNotFoundError:
            logger.error(f"No se encontró el archivo CSV: {ruta_csv}")
            resultados['errores'] += 1
            resultados['detalles_errores'].append({
                'error': f'Archivo no encontrado: {ruta_csv}'
            })
        except Exception as e:
            logger.error(f"Error procesando CSV: {e}")
            resultados['errores'] += 1
            resultados['detalles_errores'].append({
                'error': f'Error procesando CSV: {str(e)}'
            })
        
        return resultados
    
    def encontrar_ultimo_csv(self) -> Optional[str]:
        """Encuentra el archivo CSV más reciente en la carpeta Salida"""
        carpeta_salida = "../Salida"
        
        if not os.path.exists(carpeta_salida):
            logger.error(f"No existe la carpeta: {carpeta_salida}")
            return None
        
        archivos_csv = []
        for archivo in os.listdir(carpeta_salida):
            if archivo.startswith('resultados_pdf_') and archivo.endswith('.csv'):
                ruta_completa = os.path.join(carpeta_salida, archivo)
                archivos_csv.append((ruta_completa, os.path.getmtime(ruta_completa)))
        
        if not archivos_csv:
            logger.error("No se encontraron archivos CSV de resultados")
            return None
        
        # Ordenar por fecha de modificación (el más reciente primero)
        archivos_csv.sort(key=lambda x: x[1], reverse=True)
        
        archivo_reciente = archivos_csv[0][0]
        logger.info(f"Archivo CSV más reciente: {os.path.basename(archivo_reciente)}")
        
        return archivo_reciente

def main():
    """Función principal"""
    print("[LOG] GENERADOR DE ARCHIVOS SQL")
    print("Este programa genera sentencias SQL INSERT a partir de datos CSV")
    print("Base de datos: inversiones, Tabla: inversion")
    print()
    
    # Crear generador
    generator = SQLGenerator()
    
    # Encontrar archivo CSV más reciente
    archivo_csv = generator.encontrar_ultimo_csv()
    
    if not archivo_csv:
        print("[ERROR] No se encontraron archivos CSV para procesar")
        return
    
    print(f"[DIR] Archivo a procesar: {os.path.basename(archivo_csv)}")
    
    # Confirmar operación
    confirmacion = input("¿Desea generar el archivo SQL? (S/N): ").strip().upper()
    if confirmacion != 'S':
        print("Operación cancelada.")
        return
    
    # Generar archivo SQL
    print(f"\n[PROCESANDO] Generando archivo SQL...")
    resultados = generator.generar_archivo_sql(archivo_csv)
    
    # Mostrar resultados
    print("\n" + "="*60)
    print("[INFO] RESULTADOS DE LA GENERACIÓN")
    print("="*60)
    print(f"Total de registros en CSV: {resultados['total_registros']}")
    print(f"Sentencias SQL generadas: {resultados['sql_generados']}")
    print(f"Registros con error: {resultados['errores']}")
    
    if resultados['archivo_sql']:
        print(f"\n[DOC] Archivo SQL generado: {os.path.basename(resultados['archivo_sql'])}")
        print(f"[INFO] Ruta completa: {resultados['archivo_sql']}")
    
    if resultados['errores'] > 0:
        print(f"\n[ERROR] DETALLES DE ERRORES:")
        for error in resultados['detalles_errores']:
            print(f"   Fila {error.get('fila', 'N/A')}: {error.get('error', 'Error desconocido')}")
            if 'datos' in error:
                print(f"      Archivo: {error['datos']}")
    
    print("="*60)
    print(f"\n[EXITO] Proceso completado.")
    print(f"[TIP] Para ejecutar las sentencias SQL:")
    print(f"   mysql -u root -p inversiones < {os.path.basename(resultados['archivo_sql']) if resultados['archivo_sql'] else 'archivo.sql'}")

if __name__ == "__main__":
    main()
