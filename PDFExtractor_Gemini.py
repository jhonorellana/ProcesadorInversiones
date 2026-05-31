import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
import google.generativeai as genai
import PIL.Image
import json
import csv
import logging
import os
import re
from datetime import datetime
from typing import Dict, List, Any, Optional

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from config_utils import config_manager

# 1. Configura tu API Key
api_key = os.environ.get("GEMINI_API_KEY") or config_manager.get_gemini_api_key()
genai.configure(api_key=api_key)

# 2. Configuración del modelo
model = genai.GenerativeModel('models/gemini-flash-latest') # Flash es más rápido y económico para OCR

class PDFExtractor:
    """Clase para extraer datos de PDFs usando Gemini API"""
    
    def __init__(self):
        self.model = genai.GenerativeModel('models/gemini-flash-latest')
    
    def extraer_tipo_operacion(self, texto: str) -> str:
        """Extrae el tipo de operacion (Compra o Venta) del texto."""
        lineas = texto.split('\n')
        for i, linea in enumerate(lineas):
            linea_strip = linea.strip()

            # Formato BVG: 'Postura:' en la linea, valor en la siguiente
            if 'Postura:' in linea:
                resto = linea.split('Postura:')[1].strip()
                if resto:
                    palabra = resto.split()[0].upper()
                    if palabra in ('COMPRA', 'VENTA'):
                        return palabra
                if i + 1 < len(lineas):
                    siguiente = lineas[i + 1].strip()
                    palabra = siguiente.split()[0].upper() if siguiente else ''
                    if palabra in ('COMPRA', 'VENTA'):
                        return palabra

            # Formato BVQ: 'Liquidacion de contrato:' contiene Compra o Venta
            if 'Liquidaci' in linea and 'contrato' in linea.lower():
                texto_buscar = linea
                if i + 1 < len(lineas):
                    texto_buscar += ' ' + lineas[i + 1]
                match = re.search(r'(Compra|Venta)', texto_buscar, re.IGNORECASE)
                if match:
                    return match.group(1).upper()

        return ''
    
    def extraer_propietario(self, texto: str) -> str:
        """Extrae el nombre del propietario del texto del PDF."""
        lineas = texto.split('\n')
        for i, linea in enumerate(lineas):
            linea_strip = linea.strip()
            
            # Buscar patrones comunes para nombres de propietarios
            if any(palabra in linea_strip for palabra in ['Cliente:', 'Inversionista:', 'Propietario:', 'Titular:', 'Nombre:']):
                for campo in ['Cliente:', 'Inversionista:', 'Propietario:', 'Titular:', 'Nombre:']:
                    if campo in linea_strip:
                        resto = linea_strip.split(campo)[1].strip()
                        if resto:
                            return resto
                        if i + 1 < len(lineas):
                            siguiente = lineas[i + 1].strip()
                            if siguiente and not any(palabra in siguiente for palabra in ['Sector', 'Dirección', 'Teléfono', 'Email']):
                                return siguiente
        
        return ''
    
    def identificar_tipo_documento(self, texto: str) -> str:
        """Identifica el tipo de documento basado en el contenido"""
        texto_upper = texto.upper()
        
        # Priorizar identificación de Bonos del Estado
        if 'BONO DEL ESTADO' in texto_upper:
            return 'BONO_ESTADO'
        elif 'NOTA DE CREDITO' in texto_upper or 'NOTA DE CRÉDITO' in texto_upper:
            return 'NOTA_CREDITO'
        elif 'PAPEL COMERCIAL' in texto_upper:
            return 'NOTA_CREDITO'  # Tratar papel comercial como nota de crédito
        else:
            return 'DESCONOCIDO'
    
    def limpiar_valor_numerico(self, valor: str) -> str:
        """Limpia valores numéricos eliminando comas y espacios"""
        if not valor:
            return valor
        
        # Eliminar comas, espacios en blanco y el signo de porcentaje
        valor_limpio = valor.replace(',', '').replace(' ', '').replace('%', '').strip()
        
        # Manejar el caso de múltiples puntos (ej. 15.890.21)
        # Si hay más de un punto, asumimos que todos menos el último son separadores de miles
        if valor_limpio.count('.') > 1:
            partes = valor_limpio.split('.')
            entero = ''.join(partes[:-1])
            decimal = partes[-1]
            valor_limpio = f"{entero}.{decimal}"
        
        # Mantener el punto decimal si existe
        return valor_limpio

    def formatear_fecha_yyyy_mm_dd(self, fecha_str: str) -> str:
        """Convierte cualquier formato de fecha común a YYYY-MM-DD (con o sin hora)"""
        if not fecha_str:
            return ""
        fecha_str = fecha_str.strip()
        
        # Intentar separar fecha de hora
        partes = fecha_str.split()
        parte_fecha = partes[0]
        parte_hora = " " + partes[1] if len(partes) > 1 else ""
        
        # Reemplazar diagonales por guiones
        parte_fecha = parte_fecha.replace('/', '-')
        
        # Formatos como DD-MM-YYYY
        match = re.match(r'^(\d{1,2})-(\d{1,2})-(\d{4})$', parte_fecha)
        if match:
            d, m, y = match.groups()
            return f"{y}-{m.zfill(2)}-{d.zfill(2)}{parte_hora}"
            
        # Formatos como YYYY-MM-DD
        match = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})$', parte_fecha)
        if match:
            y, m, d = match.groups()
            return f"{y}-{m.zfill(2)}-{d.zfill(2)}{parte_hora}"
            
        return fecha_str
    
    def extraer_datos_liquidacion(self, ruta_archivo: str) -> Optional[Dict[str, Any]]:
        """Extrae datos de liquidación usando Gemini API"""
        try:
            # Subir documento
            documento = genai.upload_file(ruta_archivo, mime_type="application/pdf")
            
            prompt = """
            Analiza este documento de liquidación de la Bolsa de Valores de Quito (BVQ).
            Extrae todos los campos disponibles y devuélvelos exclusivamente en formato JSON puro.
            IMPORTANTE: No uses markdown code blocks (```json```), responde directamente con el JSON.
            IMPORTANTE: Las fechas deben tener el formato AAAA-MM-DD (por ejemplo, 2026-05-31). Si una fecha incluye hora, mantenla con formato AAAA-MM-DD HH:MM:SS.
            
            Busca y extrae la siguiente información estructurada en estas claves:
            - propietario: Nombre del cliente / propietario
            - tipo_operacion: COMPRA o VENTA
            - tipo_documento: Tipo de documento (ej. LIQUIDACION, NOTA_CREDITO, etc.)
            - fecha_consulta: Fecha y hora de consulta de la liquidación
            - fecha_cierre: Fecha y hora de cierre de la transacción
            - operacion_no: Número de operación o liquidación de contrato
            - casa_valores: Casa de valores intermediaria
            - direccion_casa_valores: Dirección de la casa de valores
            - ruc_casa_valores: RUC de la casa de valores
            - operador_valores: Operador de valores
            - titulo_valor: Nombre o descripción del título valor / valor
            - emisor: Emisor del título
            - valor_nominal_actual: Valor nominal actual (Val. Nom. actual)
            - valor_nominal_original: Valor nominal original (Val. Nom. original)
            - valor_efectivo: Valor efectivo (A)
            - cupon_actual: Cupón actual
            - cupon_anterior: Cupón anterior
            - fecha_valor: Fecha valor
            - fecha_emision: Fecha de emisión
            - fecha_vencimiento: Fecha de vencimiento
            - rendimiento_nominal: Rendimiento nominal (%) / RDTO. Nominal (%)
            - precio: Precio (%)
            - interes_nominal: Interés nominal (%)
            - tir_tea: TIR / TEA (%)
            - precio_neto: Precio neto (%)
            - dias_interes: Días de interés
            - base_dias: Base días
            - plazo_por_vencer: Plazo por vencer
            - desmaterializado: SI o NO (Desmaterializado)
            - camara_compensacion: Cámara de compensación (Cam.compensación)
            - moneda: Moneda utilizada
            - mercado: Mercado (e.g. SECUNDARIO, PRIMARIO)
            - postura: Postura (e.g. REGULAR)
            - valor_minimo_cupon: Valor mínimo Cupón
            - tipo_operacion_detalle: Tipo de operación (e.g. CONTADO, PLAZO)
            - saldo_por_amortizar: Saldo por amortizar
            - precio_sucio: Precio sucio (%)
            - calificadora_riesgos: Calificadora de riesgos
            - calificacion: Calificación de riesgos
            - ultima_calificacion: Última calificación de riesgos
            - codigo_vector: Código vector
            - registro_rmv: Registro RMV
            - plazo_reporto: Plazo reporto
            - vencimiento_reporto: Vencimiento reporto (VCTO. Reporto)
            - recurso: Recurso
            - titulo_por_dividir: Título por dividir
            - sector_economico: Sector económico (e.g. GOBIERNO CENTRAL)
            
            Sección de Comisiones:
            - comision_bolsa: Bolsa(C)
            - comision_operador: Operador(D)
            - total_comisiones: Total comisiones (C + D o Total de comisiones)
            - costo_general: Costo general
            - subtotal_comision_operador: Subtotal comisión operador
            - monto_retencion_operador: Monto retención operador
            - iva_tarifa_0_operador: IVA Tarifa 0% operador
            - total_operador: Total operador
            - subtotal_comision_bvq: Subtotal comisión BVQ o Bolsa
            - monto_retencion_bvq: Monto de retención BVQ o Bolsa
            - iva_tarifa_0_bvq: IVA Tarifa 0% BVQ o Bolsa
            - total_bvq: Total BVQ o Bolsa
            
            Sección de Intereses e Impuestos:
            - valor_interes: Monto interés (B)
            - impuestos: Impuestos
            - iva_tarifa_0: IVA Tarifa 0% (de la sección intereses/impuestos)
            - total_intereses_impuestos: Total intereses e impuestos
            
            Sección Totales Generales:
            - total_comprador: Total comprador (o Total vendedor si es venta)
            - observaciones: Observaciones
            - factura_asociada_no: Liquidación asociada a factura No. / N0.

            No agregues explicaciones adicionales, solo el JSON. 
            La parte entera de los números debe estar separada de la parte decimal con un punto (.).
            Responde ÚNICAMENTE con el objeto JSON, sin texto adicional.
            """

            # Generar respuesta
            response = self.model.generate_content([prompt, documento])
            
            logger.info(f"Respuesta cruda de Gemini: {response.text[:200]}...")
            
            try:
                # Limpiar respuesta de Gemini para eliminar markdown code blocks
                texto_limpio = response.text.strip()
                
                # Eliminar markdown code blocks si existen
                if texto_limpio.startswith('```json'):
                    texto_limpio = texto_limpio[7:]  # Eliminar ```json
                if texto_limpio.startswith('```'):
                    texto_limpio = texto_limpio[3:]   # Eliminar ```
                if texto_limpio.endswith('```'):
                    texto_limpio = texto_limpio[:-3]  # Eliminar ```
                
                texto_limpio = texto_limpio.strip()
                
                logger.info(f"Texto limpio para JSON: {texto_limpio[:200]}...")
                
                # Parsear JSON response
                datos = json.loads(texto_limpio)
                
                # Agregar campos de operacion y propietario al inicio
                datos_con_campos = {'tipo_operacion': '', 'propietario': ''}
                datos_con_campos.update(datos)
                datos = datos_con_campos
                
                # Extraer tipo de operacion y propietario del texto de la respuesta
                tipo_operacion = self.extraer_tipo_operacion(response.text)
                if tipo_operacion:
                    datos['tipo_operacion'] = tipo_operacion
                
                propietario = self.extraer_propietario(response.text)
                if propietario:
                    datos['propietario'] = propietario
                
                # Agregar información del archivo
                datos['archivo'] = os.path.basename(ruta_archivo)
                
                # Limpiar valores numéricos
                campos_numericos = [
                    'valor_nominal_actual', 'valor_nominal_original', 'valor_efectivo', 'rendimiento_nominal', 
                    'precio', 'interes_nominal', 'tir_tea', 'precio_neto', 'dias_interes', 'plazo_por_vencer',
                    'valor_minimo_cupon', 'saldo_por_amortizar', 'precio_sucio', 'plazo_reporto',
                    'comision_bolsa', 'comision_operador', 'total_comisiones', 'costo_general',
                    'subtotal_comision_operador', 'monto_retencion_operador', 'iva_tarifa_0_operador',
                    'total_operador', 'subtotal_comision_bvq', 'monto_retencion_bvq', 'iva_tarifa_0_bvq',
                    'total_bvq', 'valor_interes', 'impuestos', 'iva_tarifa_0', 'total_intereses_impuestos',
                    'total_comprador', 'total_vendedor'
                ]
                
                for campo in campos_numericos:
                    if campo in datos and datos[campo]:
                        datos[campo] = self.limpiar_valor_numerico(str(datos[campo]))
                
                # Limpiar y formatear fechas a YYYY-MM-DD
                campos_fecha = [
                    'fecha_consulta', 'fecha_cierre', 'fecha_valor', 
                    'fecha_emision', 'fecha_vencimiento', 'vencimiento_reporto'
                ]
                for campo in campos_fecha:
                    if campo in datos and datos[campo]:
                        datos[campo] = self.formatear_fecha_yyyy_mm_dd(str(datos[campo]))
                
                # Asegurar campo valor_nominal para compatibilidad con renombrado
                if 'valor_nominal' not in datos or not datos['valor_nominal']:
                    datos['valor_nominal'] = datos.get('valor_nominal_actual') or datos.get('valor_nominal_original') or ''
                
                # Identificar tipo de documento si no viene en la respuesta
                if 'tipo_documento' not in datos:
                    datos['tipo_documento'] = self.identificar_tipo_documento(response.text)
                
                logger.info(f"Datos extraídos de {os.path.basename(ruta_archivo)}: {datos.get('operacion_no', 'N/A')}")
                return datos
                
            except json.JSONDecodeError as e:
                logger.error(f"Error parseando JSON de Gemini: {e}")
                logger.error(f"Respuesta cruda: {response.text}")
                return None
            
        except Exception as e:
            logger.error(f"Error extrayendo datos con Gemini: {e}")
            return None
    
    def procesar_carpeta(self, carpeta_entrada: str) -> List[Dict[str, Any]]:
        """Procesa todos los PDFs de una carpeta usando Gemini API"""
        resultados = []
        
        if not os.path.exists(carpeta_entrada):
            logger.error(f"No existe la carpeta: {carpeta_entrada}")
            return resultados
        
        archivos_pdf = [f for f in os.listdir(carpeta_entrada) if f.lower().endswith('.pdf')]
        
        logger.info(f"Procesando {len(archivos_pdf)} archivos PDF con Gemini API...")
        
        for archivo in archivos_pdf:
            ruta_completa = os.path.join(carpeta_entrada, archivo)
            datos = self.extraer_datos_liquidacion(ruta_completa)
            
            if datos:
                resultados.append(datos)
            else:
                logger.warning(f"No se pudieron extraer datos del archivo: {archivo}")
        
        logger.info(f"Se extrajeron datos de {len(resultados)} archivos con Gemini API")
        return resultados
    
    def procesar_lista_archivos(self, carpeta_entrada: str, archivos_pdf: list) -> List[Dict[str, Any]]:
        """Procesa una lista específica de PDFs usando Gemini API"""
        resultados = []
        
        if not os.path.exists(carpeta_entrada):
            logger.error(f"No existe la carpeta: {carpeta_entrada}")
            return resultados
        
        logger.info(f"Procesando {len(archivos_pdf)} archivos PDF con Gemini API...")
        
        for archivo in archivos_pdf:
            ruta_completa = os.path.join(carpeta_entrada, archivo)
            datos = self.extraer_datos_liquidacion(ruta_completa)
            
            if datos:
                resultados.append(datos)
            else:
                logger.warning(f"No se pudieron extraer datos del archivo: {archivo}")
        
        logger.info(f"Se extrajeron datos de {len(resultados)} archivos con Gemini API")
        return resultados
    
    def guardar_resultados_csv(self, resultados: List[Dict[str, Any]], archivo_salida: str):
        """Guarda los resultados en un archivo CSV"""
        try:
            if not resultados:
                logger.warning("No hay resultados para guardar")
                return
            
            # Filtrar documentos DESCONOCIDO
            resultados_filtrados = [r for r in resultados if r.get('tipo_documento') != 'DESCONOCIDO']
            
            if not resultados_filtrados:
                logger.warning("No hay resultados válidos para guardar (todos son DESCONOCIDO)")
                return
            
            # Obtener todos los campos posibles
            todos_los_campos = set()
            for resultado in resultados_filtrados:
                todos_los_campos.update(resultado.keys())
            
            # Ordenar campos para consistencia
            campos_principales = [
                'tipo_operacion', 'propietario', 'tipo_documento', 'fecha_consulta', 'fecha_cierre', 'operacion_no',
                'casa_valores', 'direccion_casa_valores', 'ruc_casa_valores', 'operador_valores',
                'titulo_valor', 'emisor', 'valor_nominal_actual', 'valor_nominal_original', 'valor_efectivo',
                'cupon_actual', 'cupon_anterior', 'fecha_valor', 'fecha_emision', 'fecha_vencimiento',
                'rendimiento_nominal', 'precio', 'interes_nominal', 'tir_tea', 'precio_neto',
                'dias_interes', 'base_dias', 'plazo_por_vencer', 'desmaterializado', 'camara_compensacion',
                'moneda', 'mercado', 'postura', 'valor_minimo_cupon', 'tipo_operacion_detalle',
                'saldo_por_amortizar', 'precio_sucio', 'calificadora_riesgos', 'calificacion',
                'ultima_calificacion', 'codigo_vector', 'registro_rmv', 'plazo_reporto',
                'vencimiento_reporto', 'recurso', 'titulo_por_dividir', 'sector_economico',
                'comision_bolsa', 'comision_operador', 'total_comisiones', 'costo_general',
                'subtotal_comision_operador', 'monto_retencion_operador', 'iva_tarifa_0_operador',
                'total_operador', 'subtotal_comision_bvq', 'monto_retencion_bvq', 'iva_tarifa_0_bvq',
                'total_bvq', 'valor_interes', 'impuestos', 'iva_tarifa_0', 'total_intereses_impuestos',
                'total_comprador', 'observaciones', 'factura_asociada_no',
                'extractor_utilizado', 'archivo'
            ]
            
            campos_adicionales = sorted([campo for campo in todos_los_campos if campo not in campos_principales])
            encabezados = campos_principales + campos_adicionales
            
            # Escribir archivo CSV
            with open(archivo_salida, 'w', newline='', encoding='latin-1') as f:
                writer = csv.DictWriter(f, fieldnames=encabezados, delimiter=';')
                writer.writeheader()
                
                for resultado in resultados_filtrados:
                    fila = {campo: resultado.get(campo, '') for campo in encabezados}
                    writer.writerow(fila)
            
            logger.info(f"Resultados guardados en CSV: {archivo_salida}")
            logger.info(f"Total registros: {len(resultados_filtrados)}")
            
        except Exception as e:
            logger.error(f"Error guardando resultados CSV: {e}")

def main():
    """Función principal para pruebas"""
    print("[ROBOT] EXTRACTOR GEMINI API - Bolsa de Valores")
    print("Este programa extrae datos de PDFs usando Gemini API")
    print()
    
    extractor = PDFExtractor()
    
    # Procesar carpeta de entrada
    carpeta_entrada = "../Entrada"
    carpeta_salida = "../Salida"
    
    if not os.path.exists(carpeta_entrada):
        print(f"[ERROR] No existe la carpeta de entrada: {carpeta_entrada}")
        return
    
    # Extraer datos
    print(f"[PROCESANDO] Procesando archivos PDF en: {carpeta_entrada}")
    print("   Se excluirán archivos que empiecen con '4. FACTURA DE BOLSA'")
    resultados = extractor.procesar_carpeta(carpeta_entrada)
    
    if not resultados:
        print("[ERROR] No se extrajeron datos")
        return
    
    # Generar archivo de salida
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    archivo_salida = os.path.join(carpeta_salida, f"resultados_gemini_{timestamp}.csv")
    
    # Guardar resultados
    extractor.guardar_resultados_csv(resultados, archivo_salida)
    
    # Mostrar resumen
    print("\n" + "="*60)
    print("[INFO] RESUMEN DE EXTRACCIÓN GEMINI")
    print("="*60)
    
    tipos = {}
    for resultado in resultados:
        tipo = resultado.get('tipo_documento', 'DESCONOCIDO')
        tipos[tipo] = tipos.get(tipo, 0) + 1
    
    for tipo, cantidad in tipos.items():
        print(f"{tipo}: {cantidad}")
    
    print(f"\n[DOC] Archivo de salida: {os.path.basename(archivo_salida)}")
    print("="*60)

if __name__ == "__main__":
    main()
