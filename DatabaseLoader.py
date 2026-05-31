"""
Programa para cargar datos de CSV a la base de datos MySQL 'inversiones'
Lee el archivo CSV de resultados y lo inserta en la tabla 'inversion'
"""
import csv
import mysql.connector
from mysql.connector import Error
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import os

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseLoader:
    """Clase para cargar datos CSV a la base de datos MySQL"""
    
    def __init__(self):
        self.db_config = {
            'host': 'localhost',
            'database': 'inversion',
            'user': 'root',
            'password': '',
            'port': 3306
        }
        self.connection = None
    
    def conectar_db(self) -> bool:
        """Establece conexión con la base de datos"""
        try:
            self.connection = mysql.connector.connect(**self.db_config)
            if self.connection.is_connected():
                logger.info(f"Conectado a la base de datos MySQL: {self.db_config['database']}")
                return True
        except Error as e:
            logger.error(f"Error conectando a MySQL: {e}")
            return False
        return False
    
    def desconectar_db(self):
        """Cierra la conexión con la base de datos"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            logger.info("Conexión a MySQL cerrada")
    
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
            return None
        
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
                    return fecha_obj.strftime('%Y-%m-%d')
                except ValueError:
                    continue
            
            logger.warning(f"No se pudo parsear fecha: {fecha_str}")
            return None
        except Exception as e:
            logger.error(f"Error parseando fecha {fecha_str}: {e}")
            return None
    
    def limpiar_valor_numerico_db(self, valor: str) -> Optional[float]:
        """Convierte un valor numérico limpio a float para la base de datos"""
        if not valor or valor.strip() == '' or valor.lower() == 'null':
            return None
        
        try:
            # El valor ya viene limpio del extractor
            return float(valor.strip())
        except (ValueError, TypeError) as e:
            logger.warning(f"No se pudo convertir a número: {valor}")
            return None
    
    def preparar_registro_db(self, registro_csv: Dict[str, Any]) -> Dict[str, Any]:
        """Prepara un registro CSV para inserción en la base de datos"""
        
        # Mapeos y conversiones
        tipo_documento = registro_csv.get('tipo_documento', '')
        inv_tipo = self.mapear_tipo_documento_a_tipo_inversion(tipo_documento)
        
        # Fechas
        inv_fecha_compra = datetime.now().strftime('%Y-%m-%d')  # Fecha actual como compra
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
        id_instrumento = self.mapear_emisor_a_id_instrumento(emisor, titulo_valor)
        
        # Construir registro para BD
        registro_db = {
            'inv_tipo': inv_tipo,
            'inv_fecha_compra': inv_fecha_compra,
            'inv_propietario': registro_csv.get('propietario', 'Jhon'),  # Tomar del CSV, default Jhon
            'inv_liquidacion': registro_csv.get('operacion_no', ''),
            'inv_instrumento': id_instrumento, 
            'inv_fecha_emision': inv_fecha_emision,
            'inv_fecha_vencimiento': inv_fecha_vencimiento,
            'inv_fecha_venta': None,
            'inv_emisor': emisor if emisor else 'SRI 2034-12-31',
            'inv_calificacion_riesgo': None,
            'inv_valor_nominal': valor_nominal,
            'inv_monto_a_negociar': monto_a_negociar,
            'inv_capital_invertido': capital_invertido,
            'inv_tasa_interes': 1,  # Valor fijo según ejemplo
            'inv_rendimiento_nominal': rend_nominal if rend_nominal else 1,
            'inv_rendimiento_efectivo': rend_efectivo if rend_efectivo else 1,
            'inv_valor_efectivo': valor_efectivo,
            'inv_valor_interes': 0,  # Valor fijo según ejemplo
            'inv_comision_bolsa': comision_bolsa,
            'inv_comision_operador': comision_operador,
            'inv_retencion': 0,  # Valor fijo según ejemplo
            'inv_expirado': 0,  # Valor fijo según ejemplo
            'inv_pagada': 0,  # Valor fijo según ejemplo
            'inv_tasa_mensual_real': 1,  # Valor fijo según ejemplo
            'inv_interes_primer_mes': 0,  # Valor fijo según ejemplo
            'inv_fecha_primer_pago': None,
            'inv_precio_comprado': precio,
            'inv_precio_neto_comprado': precio_neto,
            'inv_valor_sin_comision': valor_efectivo,
            'inv_valor_con_interes': capital_invertido,
            'inv_interes_acumulado_previo': 0,  # Valor fijo según ejemplo
            'inv_total_comisiones': total_comisiones,
            'inv_codigo_SEB': None,
            'inv_codigo_BCE': None,
            'inv_fechas_pagos_capital': None,
            'id_instrumento': 91 if 'BONO' in tipo_documento else 222,  # Valor según ejemplo,
            'is_active': 1,
            'is_deleted': 0
        }
        
        return registro_db
    
    def insertar_registro(self, registro: Dict[str, Any]) -> bool:
        """Inserta un registro en la base de datos"""
        try:
            cursor = self.connection.cursor()
            
            # Query SQL
            query = """
            INSERT INTO inversion (
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
                %(inv_tipo)s, %(inv_fecha_compra)s, %(inv_propietario)s, %(inv_liquidacion)s,
                %(inv_instrumento)s, %(inv_fecha_emision)s, %(inv_fecha_vencimiento)s,
                %(inv_fecha_venta)s, %(inv_emisor)s, %(inv_calificacion_riesgo)s,
                %(inv_valor_nominal)s, %(inv_monto_a_negociar)s, %(inv_capital_invertido)s,
                %(inv_tasa_interes)s, %(inv_rendimiento_nominal)s, %(inv_rendimiento_efectivo)s,
                %(inv_valor_efectivo)s, %(inv_valor_interes)s, %(inv_comision_bolsa)s,
                %(inv_comision_operador)s, %(inv_retencion)s, %(inv_expirado)s, %(inv_pagada)s,
                %(inv_tasa_mensual_real)s, %(inv_interes_primer_mes)s, %(inv_fecha_primer_pago)s,
                %(inv_precio_comprado)s, %(inv_precio_neto_comprado)s, %(inv_valor_sin_comision)s,
                %(inv_valor_con_interes)s, %(inv_interes_acumulado_previo)s, %(inv_total_comisiones)s,
                %(inv_codigo_SEB)s, %(inv_codigo_BCE)s, %(inv_fechas_pagos_capital)s,
                %(id_instrumento)s, %(is_active)s, %(is_deleted)s, NOW(), NOW()
            )
            """
            
            cursor.execute(query, registro)
            self.connection.commit()
            
            logger.info(f"Registro insertado correctamente: {registro.get('inv_liquidacion', 'N/A')}")
            return True
            
        except Error as e:
            logger.error(f"Error insertando registro: {e}")
            if self.connection:
                self.connection.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
    
    def cargar_csv_a_db(self, ruta_csv: str) -> Dict[str, Any]:
        """Carga todos los registros del CSV a la base de datos"""
        resultados = {
            'total_registros': 0,
            'insertados': 0,
            'errores': 0,
            'detalles_errores': []
        }
        
        try:
            with open(ruta_csv, 'r', encoding='latin-1') as file:
                reader = csv.DictReader(file, delimiter=';')
                
                logger.info(f"Procesando archivo CSV: {ruta_csv}")
                logger.info(f"Columnas encontradas: {list(reader.fieldnames)}")
                
                for row_num, row in enumerate(reader, 1):
                    resultados['total_registros'] += 1
                    
                    try:
                        # Preparar registro para BD
                        registro_db = self.preparar_registro_db(row)
                        
                        # Insertar registro
                        if self.insertar_registro(registro_db):
                            resultados['insertados'] += 1
                        else:
                            resultados['errores'] += 1
                            resultados['detalles_errores'].append({
                                'fila': row_num,
                                'error': 'Error en inserción',
                                'datos': row.get('archivo', 'N/A')
                            })
                    
                    except Exception as e:
                        resultados['errores'] += 1
                        resultados['detalles_errores'].append({
                            'fila': row_num,
                            'error': str(e),
                            'datos': row.get('archivo', 'N/A')
                        })
                        logger.error(f"Error procesando fila {row_num}: {e}")
        
        except FileNotFoundError:
            logger.error(f"No se encontró el archivo CSV: {ruta_csv}")
            resultados['errores'] += 1
            resultados['detalles_errores'].append({
                'error': f'Archivo no encontrado: {ruta_csv}'
            })
        except Exception as e:
            logger.error(f"Error leyendo CSV: {e}")
            resultados['errores'] += 1
            resultados['detalles_errores'].append({
                'error': f'Error leyendo CSV: {str(e)}'
            })
        
        return resultados
    
    def encontrar_ultimo_csv(self) -> Optional[str]:
        """Encuentra el archivo CSV más reciente en la carpeta Salida"""
        carpeta_salida = "Salida"
        
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
    print("[BD]  CARGADOR DE DATOS A BASE DE DATOS")
    print("Este programa carga los datos del CSV a la base de datos MySQL")
    print("Base de datos: inversiones, Tabla: inversion")
    print()
    
    # Configuración de base de datos (permitir modificación)
    loader = DatabaseLoader()
    
    print("Configuración de base de datos:")
    print(f"  Host: {loader.db_config['host']}")
    print(f"  Database: {loader.db_config['database']}")
    print(f"  User: {loader.db_config['user']}")
    print(f"  Port: {loader.db_config['port']}")
    print()
    
    # Ejecución automática desde GUI - sin prompts interactivos
    print("[INICIO] Iniciando ejecución automática del cargador de base de datos...")
    
    # Encontrar archivo CSV más reciente
    archivo_csv = loader.encontrar_ultimo_csv()
    
    if not archivo_csv:
        print("[ERROR] No se encontraron archivos CSV para procesar")
        return
    
    print(f"\n[DIR] Archivo a procesar: {os.path.basename(archivo_csv)}")
    
    # Confirmación automática para ejecución desde GUI
    print("[OK] Continuando automáticamente con la carga a la base de datos...")
    
    # Conectar a la base de datos
    if not loader.conectar_db():
        print("[ERROR] No se pudo conectar a la base de datos")
        return
    
    # Procesar carga
    print(f"\n[PROCESANDO] Iniciando carga a base de datos...")
    resultados = loader.cargar_csv_a_db(archivo_csv)
    
    # Mostrar resultados
    print("\n" + "="*60)
    print("[INFO] RESULTADOS DE LA CARGA")
    print("="*60)
    print(f"Total de registros en CSV: {resultados['total_registros']}")
    print(f"Registros insertados: {resultados['insertados']}")
    print(f"Registros con error: {resultados['errores']}")
    
    if resultados['errores'] > 0:
        print(f"\n[ERROR] DETALLES DE ERRORES:")
        for error in resultados['detalles_errores']:
            print(f"   Fila {error.get('fila', 'N/A')}: {error.get('error', 'Error desconocido')}")
            if 'datos' in error:
                print(f"      Archivo: {error['datos']}")
    
    print("="*60)
    
    # Cerrar conexión
    loader.desconectar_db()
    
    print(f"\n[EXITO] Proceso completado.")

if __name__ == "__main__":
    main()
