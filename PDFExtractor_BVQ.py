"""
Extractor de datos de PDF para documentos de Bolsa de Valores de Guayaquil (BVG)
Procesa PDFs con estructura diferente al formato BVG estándar
"""
import PyPDF2
import pdfplumber
import re
import os
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PDFExtractor_BVQ:
    """Clase para extraer datos de PDFs con estructura BVQ alternativa"""
    
    def __init__(self):
        self.tipos_documento = {
            'NOTA_CREDITO': 'NOTA_CREDITO',
            'BONO_ESTADO': 'BONO_ESTADO',
            'PAPEL_COMERCIAL': 'PAPEL_COMERCIAL',
            'DESCONOCIDO': 'DESCONOCIDO'
        }
    
    def limpiar_valor_numerico(self, valor: str) -> str:
        """Limpia valores numéricos eliminando comas, espacios y signos"""
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
    
    def extraer_texto_pdf(self, ruta_pdf: str) -> Optional[str]:
        """Extrae todo el texto de un archivo PDF usando pdfplumber"""
        try:
            texto_completo = ""
            with pdfplumber.open(ruta_pdf) as pdf:
                for pagina in pdf.pages:
                    texto = pagina.extract_text()
                    if texto:
                        texto_completo += texto + "\n"
            
            return texto_completo
        except Exception as e:
            logger.error(f"Error extrayendo texto del PDF {ruta_pdf}: {e}")
            return None
    
    def identificar_tipo_documento_bvq(self, texto: str) -> str:
        """Identifica el tipo de documento basado en el texto extraído (formato BVQ)"""
        texto_upper = texto.upper()
        
        # Buscar patrones específicos del formato BVQ
        if 'BOLSA DE VALORES QUITO' in texto_upper and 'NOTAS DE CREDITO' in texto_upper:
            return self.tipos_documento['NOTA_CREDITO']
        elif 'BONO DEL ESTADO' in texto_upper:
            return self.tipos_documento['BONO_ESTADO']
        elif 'PAPEL COMERCIAL' in texto_upper:
            return self.tipos_documento['PAPEL_COMERCIAL']
        else:
            return self.tipos_documento['DESCONOCIDO']
    
    def extraer_datos_nota_credito_bvq(self, texto: str) -> Dict[str, Any]:
        """Extrae datos específicos de nota de crédito en formato BVQ"""
        datos = {
            'tipo_documento': 'NOTA_CREDITO',
            'archivo': '',
            'pagina': 1
        }
        
        # Para formato BVQ donde los valores están debajo de los nombres de campo
        # Dividimos el texto en líneas y buscamos patrones de campo seguidos de valor en la siguiente línea
        lineas = texto.split('\n')
        datos_extraidos = {}
        
        # Mapeo de campos a patrones de búsqueda
        mapeo_campos = {
            'operacion_no': ['Operaci[óo]n\s*No[.\s]*', 'Operaci[óo]n\s*No'],
            'mercado': ['Mercado', 'Mercado\s*[:\s]*'],
            'fecha_negociacion': ['Fecha\s*de\s*negociaci[óo]n', 'Fecha\s*de\s*negociaci[óo]n\s*[:\s]*'],
            'hora_negociacion': ['Hora\s*de\s*negociaci[óo]n', 'Hora\s*de\s*negociaci[óo]n\s*[:\s]*'],
            'postura': ['Postura', 'Postura\s*[:\s]*'],
            'factura_no': ['Factura\s*No', 'Factura\s*No[.\s]*'],
            'casa_valores': ['Casa\s*de\s*valores', 'Casa\s*de\s*valores\s*[:\s]*'],
            'direccion': ['Direcci[óo]n', 'Direcci[óo]n\s*[:\s]*'],
            'operador': ['Operador\s*de\s*valores', 'Operador\s*de\s*valores\s*[:\s]*'],
            'ruc': ['R\.?U\.?C\.?', 'R\.?U\.?C\.?\s*[:\s]*'],
            'titulo_valor': ['T[íi]tulo\s*valor', 'T[íi]tulo\s*valor\s*[:\s]*'],
            'numero_titulos': ['N[úu]mero\s*de\s*t[íi]tulos', 'N[úu]mero\s*de\s*t[íi]tulos\s*[:\s]*'],
            'valor_nominal': ['Valor\s*nominal', 'Valor\s*nominal\s*[:\s]*'],
            'emisor': ['Emisor', 'Emisor\s*[:\s]*'],
            'sector_economico': ['Sector\s*econ[óo]mico', 'Sector\s*econ[óo]mico\s*[:\s]*'],
            'resolucion_scvs': ['Resoluci[óo]n\s*SCVS', 'Resoluci[óo]n\s*SCVS\s*[:\s]*'],
            'codigo_vector_precio': ['C[óo]digo\s*vector\s*precio', 'C[óo]digo\s*vector\s*precio\s*[:\s]*'],
            'desmaterializado': ['Desmaterializado', 'Desmaterializado\s*[:\s]*'],
            'tipo_mercado': ['Tipo\s*de\s*mercado', 'Tipo\s*de\s*mercado\s*[:\s]*'],
            'base_dias': ['Base\s*d[íi]as', 'Base\s*d[íi]as\s*[:\s]*'],
            'precio': ['Precio', 'Precio\s*[:\s]*'],
            'monto_a_negociar': ['Monto\s*a\s*negociar', 'Monto\s*a\s*negociar\s*[:\s]*'],
            'tipo_tasa': ['Tipo\s*tasa', 'Tipo\s*tasa\s*[:\s]*'],
            'fecha_valor': ['Fecha\s*valor', 'Fecha\s*valor\s*[:\s]*'],
            'deposito_compensacion': ['Dep[óo]sito\s*de\s*compensaci[óo]n', 'Dep[óo]sito\s*de\s*compensaci[óo]n\s*[:\s]*'],
            'cruzada': ['Cruzada', 'Cruzada\s*[:\s]*']
        }
        
        # Buscar valores debajo de los campos
        for i, linea in enumerate(lineas):
            linea_limpia = linea.strip()
            if not linea_limpia:
                continue
                
            # Para cada campo, buscar si coincide con la línea actual
            for campo, patrones_campo in mapeo_campos.items():
                for patron in patrones_campo:
                    if re.search(patron, linea, re.IGNORECASE):
                        # Buscar valor en las siguientes líneas
                        for j in range(i + 1, min(i + 4, len(lineas))):  # Revisar hasta 3 líneas adelante
                            siguiente_linea = lineas[j].strip()
                            if siguiente_linea and not re.search(r'^[a-zA-Z\s]+:$', siguiente_linea):
                                # Si la siguiente línea no es otro campo, es el valor
                                if campo not in datos_extraidos:
                                    datos_extraidos[campo] = siguiente_linea
                                break
        
        # Patrones especiales para valores numéricos que están en líneas específicas
        patrones_especiales = {
            'valor_efectivo': r'VALOR\s*EFECTIVO\s*\$?\s*([\d.,]+)',
            'total_desembolso': r'TOTAL\s*DE\s*DESEMBOLSO\s*\$?\s*([\d.,]+)',
            'comision_bolsa': r'BOLSA\s*[\d.]+\s*%?\s*\(?[\d.]*\)?\s*\$?\s*([\d.,]+)',
            'comision_operador': r'OPERADOR\s*[\d.]+\s*%?\s*\(?[\d.]*\)?\s*\$?\s*([\d.,]+)',
            'total_comisiones': r'TOTAL\s*DE\s*COMISIONES\s*\$?\s*([\d.,]+)',
            'total_comprador_neto': r'TOTAL\s*COMPRADOR\s*NETO\s*\$?\s*([\d.,]+)',
            'precio_neto': r'PRECIO\s*NETO\s*([\d.]+)',
            'iva': r'IVA\s*\$?\s*([\d.,]+)',
            'total_comprador_bruto': r'TOTAL\s*COMPRADOR\s*BRUTO\s*\$?\s*([\d.,]+)'
        }
        
        # Extraer valores numéricos con patrones especiales
        for campo, patron in patrones_especiales.items():
            coincidencia = re.search(patron, texto, re.IGNORECASE)
            if coincidencia and coincidencia.lastindex is not None and coincidencia.lastindex >= 1:
                datos_extraidos[campo] = coincidencia.group(1).strip()
        
        # Limpiar valores numéricos en todos los datos extraídos
        campos_numericos = ['valor_nominal', 'numero_titulos', 'precio', 'monto_a_negociar', 
                           'valor_efectivo', 'total_desembolso', 'comision_bolsa', 
                           'comision_operador', 'total_comisiones', 'total_comprador_neto',
                           'precio_neto', 'iva', 'total_comprador_bruto']
        
        for campo in campos_numericos:
            if campo in datos_extraidos:
                datos_extraidos[campo] = self.limpiar_valor_numerico(datos_extraidos[campo])
        
        # Usar los datos extraídos con el nuevo método vertical
        datos = datos_extraidos
        
        # Calcular campos adicionales
        if 'valor_efectivo' in datos and 'total_comisiones' in datos:
            try:
                valor_efectivo = float(datos['valor_efectivo']) if datos['valor_efectivo'] else 0
                total_comisiones = float(datos['total_comisiones']) if datos['total_comisiones'] else 0
                datos['valor_interes'] = '0'  # En nota de crédito no hay interés
                datos['capital_invertido'] = str(valor_efectivo + total_comisiones)
            except (ValueError, TypeError):
                datos['valor_interes'] = '0'
                datos['capital_invertido'] = datos.get('total_comprador_neto', '0')
        
        # Campos adicionales con valores por defecto
        campos_defecto = {
            'rend_nominal': '0',
            'rend_efectivo': '0',
            'tasa_interes_vigente': '0',
            'emision_titulo': None,
            'vencimiento_titulo': None
        }
        
        for campo, valor_defecto in campos_defecto.items():
            if campo not in datos:
                datos[campo] = valor_defecto
        
        return datos
    
    def extraer_datos_bono_estado_bvq(self, texto: str) -> Dict[str, Any]:
        """Extrae datos específicos de bono del estado en formato BVQ"""
        datos = {
            'tipo_documento': 'BONO_ESTADO',
            'archivo': '',
            'pagina': 1
        }
        
        # Similar a nota de crédito pero con campos específicos de bonos
        patrones = {
            'operacion_no': r'Operaci[óo]n\s*No[.\s]*:?\s*([\d]+)',
            'titulo_valor': r'T[íi]tulo\s*valor\s*[:\s]*([^\n]+)',
            'emisor': r'Emisor\s*[:\s]*([^\n]+)',
            'numero_titulos': r'N[úu]mero\s*de\s*t[íi]tulos\s*[:\s]*([\d]+)',
            'valor_nominal': r'Valor\s*nominal\s*[:\s]*\$?\s*([\d.,]+)',
            'valor_efectivo': r'VALOR\s*EFECTIVO\s*[:\s]*\$?\s*([\d.,]+)',
            'total_desembolso': r'TOTAL\s*DE\s*DESEMBOLSO\s*[:\s]*\$?\s*([\d.,]+)',
            'comision_bolsa': r'BOLSA\s*[:\s]*[\d.]+\s*%?\s*\(?[\d.]*\)?\s*[:\s]*\$?\s*([\d.,]+)',
            'comision_operador': r'OPERADOR\s*[:\s]*[\d.]+\s*%?\s*\(?[\d.]*\)?\s*[:\s]*\$?\s*([\d.,]+)',
            'total_comisiones': r'TOTAL\s*DE\s*COMISIONES\s*[:\s]*\$?\s*([\d.,]+)',
            'total_comprador_neto': r'TOTAL\s*COMPRADOR\s*NETO\s*[:\s]*\$?\s*([\d.,]+)',
            'rend_nominal': r'Rend\.?\s*Nominal\s*[:\s]*([\d.]+)',
            'rend_efectivo': r'Rend\.?\s*Efectivo\s*[:\s]*([\d.]+)',
            'precio': r'Precio\s*[:\s]*([\d.]+)',
            'tasa_interes_vigente': r'Tasa\s*inter[ée]s\s*vigente\s*[:\s]*([\d.]+)',
            'monto_a_negociar': r'Monto\s*a\s*negociar\s*[:\s]*\$?\s*([\d.,]+)',
            'precio_neto': r'PRECIO\s*NETO\s*[:\s]*([\d.]+)'
        }
        
        # Extraer datos
        for campo, patron in patrones.items():
            coincidencia = re.search(patron, texto, re.IGNORECASE)
            if coincidencia and coincidencia.lastindex is not None and coincidencia.lastindex >= 1:
                valor = coincidencia.group(1).strip()
                
                # Limpiar valores numéricos
                if campo in ['numero_titulos', 'valor_nominal', 'valor_efectivo', 'total_desembolso',
                             'comision_bolsa', 'comision_operador', 'total_comisiones', 
                             'total_comprador_neto', 'rend_nominal', 'rend_efectivo', 'precio',
                             'tasa_interes_vigente', 'monto_a_negociar', 'precio_neto']:
                    valor = self.limpiar_valor_numerico(valor)
                
                datos[campo] = valor
        
        # Campos adicionales
        campos_defecto = {
            'valor_interes': '0',
            'capital_invertido': datos.get('total_comprador_neto', '0'),
            'emision_titulo': None,
            'vencimiento_titulo': None
        }
        
        for campo, valor_defecto in campos_defecto.items():
            if campo not in datos:
                datos[campo] = valor_defecto
        
        return datos
    
    def extraer_datos_pdf_bvq(self, ruta_pdf: str) -> Optional[Dict[str, Any]]:
        """Extrae todos los datos de un archivo PDF en formato BVQ"""
        try:
            # Extraer texto del PDF
            texto = self.extraer_texto_pdf(ruta_pdf)
            if not texto:
                logger.error(f"No se pudo extraer texto del PDF: {ruta_pdf}")
                return None
            
            # Identificar tipo de documento
            tipo_doc = self.identificar_tipo_documento_bvq(texto)
            
            # Extraer datos según tipo
            if tipo_doc == 'NOTA_CREDITO':
                datos = self.extraer_datos_nota_credito_bvq(texto)
            elif tipo_doc == 'BONO_ESTADO':
                datos = self.extraer_datos_bono_estado_bvq(texto)
            elif tipo_doc == 'PAPEL_COMERCIAL':
                datos = self.extraer_datos_nota_credito_bvq(texto)  # Similar a nota de crédito
            else:
                datos = {
                    'tipo_documento': 'DESCONOCIDO',
                    'archivo': os.path.basename(ruta_pdf),
                    'error': 'No se pudo identificar el tipo de documento'
                }
            
            # Agregar información del archivo
            datos['archivo'] = os.path.basename(ruta_pdf)
            
            logger.info(f"Datos extraídos de {os.path.basename(ruta_pdf)}: {datos.get('operacion_no', 'N/A')}")
            return datos
            
        except Exception as e:
            logger.error(f"Error extrayendo datos del PDF {ruta_pdf}: {e}")
            return None
    
    def procesar_carpeta_bvq(self, carpeta_entrada: str) -> List[Dict[str, Any]]:
        """Procesa todos los PDFs de una carpeta usando el extractor BVQ"""
        resultados = []
        
        if not os.path.exists(carpeta_entrada):
            logger.error(f"No existe la carpeta: {carpeta_entrada}")
            return resultados
        
        archivos_pdf = [f for f in os.listdir(carpeta_entrada) if f.lower().endswith('.pdf')]
        
        if not archivos_pdf:
            logger.warning(f"No se encontraron archivos PDF en: {carpeta_entrada}")
            return resultados
        
        logger.info(f"Procesando {len(archivos_pdf)} archivos PDF con extractor BVQ...")
        
        for archivo in archivos_pdf:
            ruta_completa = os.path.join(carpeta_entrada, archivo)
            datos = self.extraer_datos_pdf_bvq(ruta_completa)
            
            if datos:
                resultados.append(datos)
            else:
                logger.warning(f"No se pudieron extraer datos del archivo: {archivo}")
        
        logger.info(f"Se extrajeron datos de {len(resultados)} archivos con extractor BVQ")
        return resultados
    
    def guardar_resultados_csv_bvq(self, resultados: List[Dict[str, Any]], archivo_salida: str):
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
            campos_principales = ['tipo_documento', 'operacion_no', 'titulo_valor', 'emisor', 
                               'valor_nominal', 'emision_titulo', 'vencimiento_titulo',
                               'codigo_vector_precio', 'rend_nominal', 'rend_efectivo',
                               'precio', 'tasa_interes_vigente', 'monto_a_negociar',
                               'valor_efectivo', 'valor_interes', 'total_desembolso',
                               'comision_bolsa', 'comision_operador', 'total_comisiones',
                               'total_comprador_neto', 'precio_neto', 'numero_titulos',
                               'mercado', 'fecha_negociacion', 'hora_negociacion', 'postura',
                               'factura_no', 'casa_valores', 'direccion', 'operador', 'ruc']
            
            campos_adicionales = sorted([campo for campo in todos_los_campos if campo not in campos_principales])
            encabezados = campos_principales + campos_adicionales
            
            # Escribir archivo CSV
            with open(archivo_salida, 'w', newline='', encoding='latin-1') as f:
                writer = csv.DictWriter(f, fieldnames=encabezados, delimiter=';')
                writer.writeheader()
                
                for resultado in resultados_filtrados:
                    fila = {campo: resultado.get(campo, '') for campo in encabezados}
                    writer.writerow(fila)
            
            logger.info(f"Resultados BVQ guardados en CSV: {archivo_salida}")
            logger.info(f"Total registros: {len(resultados_filtrados)}")
            
        except Exception as e:
            logger.error(f"Error guardando resultados CSV BVQ: {e}")

def main():
    """Función principal para pruebas"""
    print("[BUSCAR] EXTRACTOR BVQ - Bolsa de Valores de Quito")
    print("Este programa extrae datos de PDFs con estructura BVQ diferente")
    print()
    
    extractor = PDFExtractor_BVQ()
    
    # Procesar carpeta de entrada
    carpeta_entrada = "../Entrada"
    carpeta_salida = "../Salida"
    
    if not os.path.exists(carpeta_entrada):
        print(f"[ERROR] No existe la carpeta de entrada: {carpeta_entrada}")
        return
    
    # Extraer datos
    print(f"[PROCESANDO] Procesando archivos PDF en: {carpeta_entrada}")
    resultados = extractor.procesar_carpeta_bvq(carpeta_entrada)
    
    if not resultados:
        print("[ERROR] No se extrajeron datos")
        return
    
    # Generar archivo de salida
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    archivo_salida = os.path.join(carpeta_salida, f"resultados_bvq_{timestamp}.csv")
    
    # Guardar resultados
    extractor.guardar_resultados_csv_bvq(resultados, archivo_salida)
    
    # Mostrar resumen
    print("\n" + "="*60)
    print("[INFO] RESUMEN DE EXTRACCIÓN BVQ")
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
    import csv
    main()
