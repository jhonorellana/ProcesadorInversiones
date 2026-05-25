import PyPDF2
import pdfplumber
import re
import json
import csv
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging
from PDFExtractor_Gemini import PDFExtractor as PDFExtractorGemini

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PDFExtractor:
    """Clase para extraer datos de archivos PDF de liquidaciones y notas de crédito"""
    
    def __init__(self):
        self.datos_extraidos = {}
        self.gemini_extractor = PDFExtractorGemini()  # Instancia del extractor Gemini como fallback
    
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
        
    def extraer_texto_pdf(self, ruta_pdf: str) -> str:
        """Extrae todo el texto de un archivo PDF"""
        texto = ""
        try:
            # Intentar primero con pdfplumber (mejor para tablas)
            with pdfplumber.open(ruta_pdf) as pdf:
                for pagina in pdf.pages:
                    texto += pagina.extract_text() + "\n"
        except Exception as e:
            logger.warning(f"No se pudo usar pdfplumber: {e}")
            try:
                # Alternativa con PyPDF2
                with open(ruta_pdf, 'rb') as archivo:
                    lector = PyPDF2.PdfReader(archivo)
                    for pagina in lector.pages:
                        texto += pagina.extract_text() + "\n"
            except Exception as e2:
                logger.error(f"No se pudo extraer texto con PyPDF2: {e2}")
                return ""
        
        return texto
    
    def extraer_datos_nota_credito(self, texto: str) -> Dict[str, Any]:
        """Extrae datos específicos de una nota de crédito"""
        datos = {
            'tipo_documento': 'NOTA_CREDITO',
            'operacion_no': '',
            'titulo_valor': '',
            'emisor': '',
            'valor_nominal': '',
            'emision_titulo': '',
            'vencimiento_titulo': '',
            'codigo_vector_precio': '',
            'rend_nominal': '',
            'rend_efectivo': '',
            'precio': '',
            'tasa_interes_vigente': '',
            'monto_a_negociar': '',
            'valor_efectivo': '',
            'valor_interes': '',
            'total_desembolso': '',
            'comision_bolsa': '',
            'comision_operador': '',
            'total_comisiones': '',
            'total_comprador_neto': '',
            'precio_neto': ''
        }
        
        # Patrones de búsqueda actualizados según los campos solicitados
        patrones = {
            'operacion_no': r'BVG\s+(\d+)',
            'titulo_valor': r'Título valor[:\s]*([A-Za-z0-9\s\(\)\-\.]+)',
            'emisor': '',
            'valor_nominal': r'Valor nominal[:\s]*\$\s*([\d,\.]+)',
            'emision_titulo': r'Emisión de título[:\s]*([A-Za-z0-9\s\-\./]+)',
            'vencimiento_titulo': r'Vencimiento título[:\s]*([A-Za-z0-9\s\-\./]+)',
            'codigo_vector_precio': r'Código vector precio[:\s]*([A-Z\s]+)',
            'rend_nominal': r'Rend\.? Nominal[:\s]*([\d,\.%]+)',
            'rend_efectivo': r'Rend\.? Efectivo[:\s]*([\d,\.%]+)',
            'precio': r'Precio[:\s]*([\d,\.]+)',
            'tasa_interes_vigente': r'Tasa interés vigente[:\s]*([\d,\.%]+)',
            'monto_a_negociar': r'Monto a negociar[:\s]*\$\s*([\d,\.]+)',
            'valor_efectivo': r'\(A\)VALOR EFECTIVO\s+([\d,\.]+)',
            'valor_interes': r'\(B\) VALOR INTERÉS\s+([\d,\.]*)',
            'total_desembolso': r'TOTAL DE DESEMBOLSO\s+([\d,\.]+)',
            'comision_bolsa': r'\(C\) BOLSA\s+[\d\.%]+\s+([\d,\.]+)',
            'comision_operador': r'\(D\) OPERADOR\s+[\d\.%]+\s+([\d,\.]+)',
            'total_comisiones': r'TOTAL DE COMISIONES\s+([\d,\.]+)',
            'total_comprador_neto': r'TOTAL COMPRADOR NETO[:\s]*\$?\s*([\d,\.]+)',
            'precio_neto': r'PRECIO NETO[:\s]*([\d,\.]+)'
        }
        
        for campo, patron in patrones.items():
            coincidencia = re.search(patron, texto, re.IGNORECASE)
            if coincidencia and coincidencia.lastindex is not None and coincidencia.lastindex >= 1:
                valor = coincidencia.group(1).strip()
                
                # Limpiar saltos de línea específicamente para titulo_valor
                if campo == 'titulo_valor':
                    valor = valor.replace('\n', ' ').replace('\r', '').strip()
                # Limpiar valores numéricos
                elif campo in ['valor_nominal', 'rend_nominal', 'rend_efectivo', 'precio', 
                             'tasa_interes_vigente', 'monto_a_negociar', 'valor_efectivo', 
                             'valor_interes', 'total_desembolso', 'comision_bolsa', 
                             'comision_operador', 'total_comisiones', 'total_comprador_neto', 
                             'precio_neto', 'numero_titulos']:
                    valor = self.limpiar_valor_numerico(valor)
                
                datos[campo] = valor
        
        # Extraer información adicional usando análisis por líneas
        lineas = texto.split('\n')
        
        for i, linea in enumerate(lineas):
            linea_limpia = linea.strip()
            
            # Emisor (línea siguiente a "Emisor:")
            if 'Emisor:' in linea and i + 1 < len(lineas):
                siguiente_linea = lineas[i + 1].strip()
                if siguiente_linea and 'SERVICIO DE RENTAS INTERNAS' in siguiente_linea:
                    datos['emisor'] = 'SERVICIO DE RENTAS INTERNAS'
                elif siguiente_linea and 'Sector económico:' not in siguiente_linea and siguiente_linea:
                    datos['emisor'] = siguiente_linea
            
            # Extraer campos que están en la misma línea
            if 'Emisión de título:' in linea:
                partes = linea.split('Emisión de título:')
                if len(partes) > 1:
                    valor = partes[1].strip()
                    # Limpiar el valor para que no incluya Vencimiento título
                    if 'Vencimiento título:' in valor:
                        valor = valor.split('Vencimiento título:')[0].strip()
                    if valor and valor != 'Desmaterializado: SI Derecho:':
                        datos['emision_titulo'] = valor
                    else:
                        datos['emision_titulo'] = ''
            
            if 'Vencimiento título:' in linea:
                partes = linea.split('Vencimiento título:')
                if len(partes) > 1:
                    valor = partes[1].strip()
                    # Limpiar para obtener solo el vencimiento
                    if ':' in valor and not valor.startswith('Desmaterializado'):
                        datos['vencimiento_titulo'] = valor
                    elif valor.startswith('Desmaterializado'):
                        datos['vencimiento_titulo'] = ''
                    else:
                        datos['vencimiento_titulo'] = valor
            
            # Rendimientos - buscar valores numéricos específicos
            if 'Rend. Nominal:' in linea:
                # Buscar en la misma línea o siguientes
                match = re.search(r'Rend\.? Nominal[:\s]*([\d,\.%]+)', linea)
                if match:
                    datos['rend_nominal'] = match.group(1).strip()
                else:
                    # Buscar en líneas siguientes
                    for j in range(i + 1, min(i + 3, len(lineas))):
                        if re.search(r'^[\d,\.%]+$', lineas[j].strip()):
                            datos['rend_nominal'] = lineas[j].strip()
                            break
            
            if 'Rend. Efectivo:' in linea:
                # Buscar en la misma línea o siguientes
                match = re.search(r'Rend\.? Efectivo[:\s]*([\d,\.%]+)', linea)
                if match:
                    datos['rend_efectivo'] = match.group(1).strip()
                else:
                    # Buscar en líneas siguientes
                    for j in range(i + 1, min(i + 3, len(lineas))):
                        if re.search(r'^[\d,\.%]+$', lineas[j].strip()):
                            datos['rend_efectivo'] = lineas[j].strip()
                            break
            
            # Tasa interés vigente
            if 'Tasa interés vigente:' in linea:
                match = re.search(r'Tasa interés vigente[:\s]*([\d,\.%]+)', linea)
                if match:
                    datos['tasa_interes_vigente'] = match.group(1).strip()
        
        # Extraer número de títulos adicional
        num_titulos_match = re.search(r'Número de títulos[:\s]*(\d+)', texto)
        if num_titulos_match:
            datos['numero_titulos'] = num_titulos_match.group(1).strip()
        
        return datos
    
    def extraer_datos_bono_estado(self, texto: str) -> Dict[str, Any]:
        """Extrae datos específicos de Bonos del Estado de BVG"""
        datos = {
            'tipo_documento': 'BONO_ESTADO',
            'operacion_no': '',
            'titulo_valor': '',
            'emisor': '',
            'valor_nominal': '',
            'emision_titulo': '',
            'vencimiento_titulo': '',
            'codigo_vector_precio': '',
            'rend_nominal': '',
            'rend_efectivo': '',
            'precio': '',
            'tasa_interes_vigente': '',
            'monto_a_negociar': '',
            'valor_efectivo': '',
            'valor_interes': '',
            'total_desembolso': '',
            'comision_bolsa': '',
            'comision_operador': '',
            'total_comisiones': '',
            'total_comprador_neto': '',
            'precio_neto': '',
            'numero_titulos': ''
        }
        
        # Extraer información usando análisis por líneas
        lineas = texto.split('\n')
        
        for i, linea in enumerate(lineas):
            linea_limpia = linea.strip()
            
            # Operación No - buscar en la primera línea con BVG
            if 'BOLSA DE VALORES DE GUAYAQUIL S.A. BVG' in linea:
                # Extraer el número que sigue a BVG
                match = re.search(r'BVG (\d+)', linea)
                if match:
                    datos['operacion_no'] = match.group(1).strip()
            
            # Título valor
            if 'Título valor:' in linea:
                # Formato: Título valor: BONO DEL ESTADO CDF-RES-2024-0004 JUBILA (2)- Clase:SC- Serie:UNICA
                match = re.search(r'Título valor: (BONO DEL ESTADO[^-]+)', linea)
                if match:
                    datos['titulo_valor'] = match.group(1).strip()
                else:
                    # Alternativa: extraer después de "Título valor:"
                    partes = linea.split('Título valor:')
                    if len(partes) > 1:
                        titulo = partes[1].strip()
                        if 'Clase:' in titulo:
                            titulo = titulo.split('Clase:')[0].strip()
                        datos['titulo_valor'] = titulo
            
            # Emisor
            if 'Emisor:' in linea:
                # Buscar en la siguiente línea
                if i + 1 < len(lineas):
                    siguiente = lineas[i + 1].strip()
                    if siguiente and 'Sector económico:' not in siguiente:
                        datos['emisor'] = siguiente
            
            # Número de títulos y Valor nominal
            if 'Número de títulos:' in linea:
                # Formato: Número de títulos: 3,610,000 Valor nominal: $ 36,100.00 Saldo por amortizar: 100.00 %
                match = re.search(r'Número de títulos: ([\d,\.]+) Valor nominal: \$ ([\d,\.]+)', linea)
                if match:
                    datos['numero_titulos'] = self.limpiar_valor_numerico(match.group(1).strip())
                    datos['valor_nominal'] = self.limpiar_valor_numerico(match.group(2).strip())
            
            # Valor efectivo (en sección Totales)
            if '(A)VALOR EFECTIVO' in linea:
                # Formato: (A)VALOR EFECTIVO 31,780.52
                match = re.search(r'\(A\)VALOR EFECTIVO ([\d,\.]+)', linea)
                if match:
                    datos['valor_efectivo'] = self.limpiar_valor_numerico(match.group(1).strip())
            
            # Valor interés
            if '(B) VALOR INTERÉS' in linea:
                # Formato: (B) VALOR INTERÉS 24.91
                match = re.search(r'\(B\) VALOR INTERÉS ([\d,\.]+)', linea)
                if match:
                    datos['valor_interes'] = self.limpiar_valor_numerico(match.group(1).strip())
            
            # Total desembolso
            if 'TOTAL DE DESEMBOLSO' in linea:
                # Formato: TOTAL DE DESEMBOLSO 31,805.43
                match = re.search(r'TOTAL DE DESEMBOLSO ([\d,\.]+)', linea)
                if match:
                    datos['total_desembolso'] = self.limpiar_valor_numerico(match.group(1).strip())
            
            # Comisiones
            if '(C) BOLSA' in linea:
                # Formato: (C) BOLSA 0.05000 15.890.21
                match = re.search(r'\(C\) BOLSA [\d,\.]+ ([\d,\.]+)', linea)
                if match:
                    datos['comision_bolsa'] = self.limpiar_valor_numerico(match.group(1).strip())
            
            if '(D) OPERADOR' in linea:
                # Formato: (D) OPERADOR 0.10000 31.78
                match = re.search(r'\(D\) OPERADOR [\d,\.]+ ([\d,\.]+)', linea)
                if match:
                    datos['comision_operador'] = self.limpiar_valor_numerico(match.group(1).strip())
            
            # Total comisiones
            if 'TOTAL DE COMISIONES' in linea:
                # Formato: TOTAL DE COMISIONES 47.67
                match = re.search(r'TOTAL DE COMISIONES ([\d,\.]+)', linea)
                if match:
                    datos['total_comisiones'] = self.limpiar_valor_numerico(match.group(1).strip())
            
            # Total comprador neto
            if 'TOTAL COMPRADOR NETO:' in linea:
                # Formato: TOTAL COMPRADOR NETO: 31,853.10 (A+B+C+D-E-F)
                match = re.search(r'TOTAL COMPRADOR NETO: ([\d,\.]+)', linea)
                if match:
                    datos['total_comprador_neto'] = self.limpiar_valor_numerico(match.group(1).strip())
            
            # Datos adicionales del bono
            if 'Emisión de título:' in linea:
                # Formato: Emisión de título: 25/07/2024 Vencimiento título: 25/07/2033 Desmaterializado: SI Derecho:
                match = re.search(r'Emisión de título: ([\d/]+)', linea)
                if match:
                    datos['emision_titulo'] = match.group(1).strip()
            
            if 'Vencimiento título:' in linea:
                # Formato: Vencimiento título: 25/07/2033 Desmaterializado: SI Derecho:
                match = re.search(r'Vencimiento título: ([\d/]+)', linea)
                if match:
                    datos['vencimiento_titulo'] = match.group(1).strip()
            
            # Código vector precio
            if 'Código vector precio :' in linea:
                # Formato: Código vector precio : 045040100401330725
                match = re.search(r'Código vector precio : ([A-Z0-9]+)', linea)
                if match:
                    datos['codigo_vector_precio'] = match.group(1).strip()
            
            # Rendimientos
            if 'Rend. Nominal:' in linea:
                # Formato: Rend. Nominal: 8.90000000
                match = re.search(r'Rend\.? Nominal: ([\d,\.%]+)', linea)
                if match:
                    datos['rend_nominal'] = self.limpiar_valor_numerico(match.group(1).strip())
            
            if 'Rend. Efectivo:' in linea:
                # Formato: Rend. Efectivo: 9.27217270
                match = re.search(r'Rend\.? Efectivo: ([\d,\.%]+)', linea)
                if match:
                    datos['rend_efectivo'] = self.limpiar_valor_numerico(match.group(1).strip())
            
            # Precio
            if 'Precio:' in linea and 'Precio sucio' not in linea:
                # Buscar en la siguiente línea
                if i + 1 < len(lineas):
                    siguiente = lineas[i + 1].strip()
                    # Formato: 88.03468709%
                    match = re.search(r'([\d,\.%]+)%', siguiente)
                    if match:
                        datos['precio'] = self.limpiar_valor_numerico(match.group(1).strip())
            
            # Tasa interés vigente
            if 'Tasa interés vigente:' in linea:
                # Formato: Tasa interés vigente: 6.210000
                match = re.search(r'Tasa interés vigente: ([\d,\.%]+)', linea)
                if match:
                    datos['tasa_interes_vigente'] = self.limpiar_valor_numerico(match.group(1).strip())
            
            # Monto a negociar
            if 'Monto a negociar:' in linea:
                # Formato: Monto a negociar: $ 36,100.00
                match = re.search(r'Monto a negociar: \$ ([\d,\.%]+)', linea)
                if match:
                    datos['monto_a_negociar'] = self.limpiar_valor_numerico(match.group(1).strip())
            
            # Precio neto
            if 'PRECIO NETO:' in linea:
                # Formato: PRECIO NETO: 88.2357
                match = re.search(r'PRECIO NETO: ([\d,\.%]+)', linea)
                if match:
                    datos['precio_neto'] = self.limpiar_valor_numerico(match.group(1).strip())
        
        return datos
    
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
    
    def procesar_pdf(self, ruta_pdf: str, debug: bool = False) -> Dict[str, Any]:
        """Procesa un archivo PDF y extrae sus datos"""
        logger.info(f"Procesando archivo: {ruta_pdf}")
        
        if not os.path.exists(ruta_pdf):
            logger.error(f"El archivo no existe: {ruta_pdf}")
            return {}
        
        # Extraer texto del PDF
        texto = self.extraer_texto_pdf(ruta_pdf)
        if not texto:
            logger.error("No se pudo extraer texto del PDF")
            return {}
        
        # Debug: mostrar texto extraído
        if debug:
            print(f"\n=== TEXTO EXTRAÍDO DE {os.path.basename(ruta_pdf)} ===")
            print(texto[:2000])  # Primeros 2000 caracteres
            print("=" * 50)
        
        # Identificar tipo de documento
        tipo = self.identificar_tipo_documento(texto)
        
        # Debug: mostrar tipo identificado
        if debug:
            print(f"Tipo de documento identificado: {tipo}")
        
        # Extraer datos según el tipo
        if tipo == 'BONO_ESTADO':
            datos = self.extraer_datos_bono_estado(texto)
        elif tipo == 'NOTA_CREDITO':
            datos = self.extraer_datos_nota_credito(texto)
        else:
            # Usar Gemini como fallback para documentos DESCONOCIDO
            logger.info(f"Documento no reconocido por extractor BVG, usando Gemini fallback: {os.path.basename(ruta_pdf)}")
            datos_gemini = self.gemini_extractor.extraer_datos_liquidacion(ruta_pdf)
            
            if datos_gemini:
                datos = datos_gemini
                logger.info(f"Gemini extrajo datos exitosamente: {datos.get('operacion_no', 'N/A')}")
            else:
                # Si Gemini tampoco puede extraer, marcar como DESCONOCIDO
                datos = {
                    'tipo_documento': 'DESCONOCIDO',
                    'archivo': os.path.basename(ruta_pdf),
                    'error': 'No se pudo identificar el documento con ningún extractor'
                }
                logger.warning(f"Ningún extractor pudo procesar el archivo: {os.path.basename(ruta_pdf)}")
        
        # Agregar metadatos
        datos['archivo'] = os.path.basename(ruta_pdf)
        datos['ruta_completa'] = ruta_pdf
        datos['fecha_procesamiento'] = datetime.now().isoformat()
        datos['tamaño_archivo'] = os.path.getsize(ruta_pdf)
        
        # Agregar información del extractor usado
        if tipo == 'DESCONOCIDO' and datos.get('tipo_documento') != 'DESCONOCIDO':
            datos['extractor_utilizado'] = 'Gemini (Fallback)'
        else:
            datos['extractor_utilizado'] = 'BVG'
        
        return datos
    
    def procesar_carpeta(self, ruta_carpeta: str) -> List[Dict[str, Any]]:
        """Procesa todos los archivos PDF de una carpeta"""
        resultados = []
        
        if not os.path.exists(ruta_carpeta):
            logger.error(f"La carpeta no existe: {ruta_carpeta}")
            return resultados
        
        archivos_pdf = [f for f in os.listdir(ruta_carpeta) if f.lower().endswith('.pdf')]
        
        logger.info(f"Procesando {len(archivos_pdf)} archivos PDF...")
        
        for archivo in archivos_pdf:
            ruta_completa = os.path.join(ruta_carpeta, archivo)
            datos = self.procesar_pdf(ruta_completa)
            if datos:
                resultados.append(datos)
        
        return resultados
    
    def procesar_lista_archivos(self, ruta_carpeta: str, archivos_pdf: list) -> List[Dict[str, Any]]:
        """Procesa una lista específica de archivos PDF"""
        resultados = []
        
        if not os.path.exists(ruta_carpeta):
            logger.error(f"La carpeta no existe: {ruta_carpeta}")
            return resultados
        
        logger.info(f"Procesando {len(archivos_pdf)} archivos PDF...")
        
        for archivo in archivos_pdf:
            ruta_completa = os.path.join(ruta_carpeta, archivo)
            datos = self.procesar_pdf(ruta_completa)
            if datos:
                resultados.append(datos)
        
        return resultados
    
    def guardar_resultados_csv(self, resultados: List[Dict[str, Any]], archivo_salida: str):
        """Guarda los resultados en un archivo CSV"""
        try:
            if not resultados:
                logger.warning("No hay resultados para guardar")
                return
            
            # Filtrar documentos de tipo DESCONOCIDO
            resultados_filtrados = [r for r in resultados if r.get('tipo_documento') != 'DESCONOCIDO']
            
            if not resultados_filtrados:
                logger.warning("No hay resultados válidos para guardar (todos son DESCONOCIDO)")
                return
            
            # Registrar cuántos documentos fueron filtrados
            cantidad_filtrados = len(resultados) - len(resultados_filtrados)
            if cantidad_filtrados > 0:
                logger.info(f"Se excluyeron {cantidad_filtrados} documentos de tipo DESCONOCIDO")
            
            # Usar resultados filtrados para el resto del proceso
            resultados = resultados_filtrados
            
            # Obtener todos los campos posibles (encabezados)
            todos_los_campos = set()
            for resultado in resultados:
                todos_los_campos.update(resultado.keys())
            
            # Ordenar campos para consistencia (campos principales primero)
            campos_principales = ['tipo_documento', 'operacion_no', 'titulo_valor', 'emisor', 
                               'valor_nominal', 'emision_titulo', 'vencimiento_titulo',
                               'codigo_vector_precio', 'rend_nominal', 'rend_efectivo',
                               'precio', 'tasa_interes_vigente', 'monto_a_negociar',
                               'valor_efectivo', 'valor_interes', 'total_desembolso',
                               'comision_bolsa', 'comision_operador', 'total_comisiones',
                               'total_comprador_neto', 'precio_neto', 'numero_titulos',
                               'extractor_utilizado', 'archivo']
            
            # Agregar campos adicionales que no estén en los principales
            campos_adicionales = sorted([campo for campo in todos_los_campos if campo not in campos_principales])
            encabezados = campos_principales + campos_adicionales
            
            # Escribir archivo CSV
            with open(archivo_salida, 'w', newline='', encoding='latin-1') as f:
                writer = csv.DictWriter(f, fieldnames=encabezados, delimiter=';')
                writer.writeheader()
                
                for resultado in resultados:
                    # Asegurar que todos los campos estén presentes (rellenar con vacíos si es necesario)
                    fila = {campo: resultado.get(campo, '') for campo in encabezados}
                    writer.writerow(fila)
            
            logger.info(f"Resultados guardados en CSV: {archivo_salida}")
            logger.info(f"Total registros: {len(resultados)}")
            logger.info(f"Total campos: {len(encabezados)}")
            
        except Exception as e:
            logger.error(f"Error al guardar resultados CSV: {e}")

def main():
    """Función principal para pruebas"""
    import os
    extractor = PDFExtractor()
    
    # Procesar la carpeta Entrada
    carpeta_docs = "../Entrada"
    if os.path.exists(carpeta_docs):
        logger.info(f"Procesando archivos PDF en la carpeta: {carpeta_docs}")
        logger.info("Se excluirán archivos que empiecen con '4. FACTURA DE BOLSA'")
        resultados = extractor.procesar_carpeta(carpeta_docs)
        
        if resultados:
            # Filtrar documentos de tipo DESCONOCIDO para mostrar
            resultados_validos = [r for r in resultados if r.get('tipo_documento') != 'DESCONOCIDO']
            desconocidos = [r for r in resultados if r.get('tipo_documento') == 'DESCONOCIDO']
            
            # Mostrar estadísticas de extractores usados
            extractores_usados = {}
            for resultado in resultados_validos:
                extractor = resultado.get('extractor_utilizado', 'Desconocido')
                extractores_usados[extractor] = extractores_usados.get(extractor, 0) + 1
            
            print(f"\n🔧 ESTADÍSTICAS DE EXTRACTORES:")
            for extractor, cantidad in extractores_usados.items():
                print(f"   {extractor}: {cantidad} documentos")
            
            # Mostrar resultados válidos
            print(f"\n📊 RESULTADOS VÁLIDOS ({len(resultados_validos)} documentos):")
            for resultado in resultados_validos:
                print(f"\n--- {resultado['archivo']} ---")
                print(f"Tipo: {resultado['tipo_documento']}")
                print(f"Extractor: {resultado.get('extractor_utilizado', 'N/A')}")
                for key, value in resultado.items():
                    if key not in ['archivo', 'ruta_completa', 'fecha_procesamiento', 'texto_completo', 'extractor_utilizado']:
                        print(f"{key}: {value}")
            
            # Mostrar documentos desconocidos si los hay
            if desconocidos:
                print(f"\n⚠️  DOCUMENTOS DESCONOCIDOS ({len(desconocidos)} archivos):")
                for resultado in desconocidos:
                    print(f"   - {resultado['archivo']}")
                print(f"   Estos archivos no serán incluidos en el CSV de salida.")
            
            # Guardar resultados en carpeta Salida
            os.makedirs("../Salida", exist_ok=True)
            archivo_salida = f"../Salida/resultados_pdf_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            extractor.guardar_resultados_csv(resultados, archivo_salida)
        else:
            logger.info("No se encontraron archivos PDF para procesar")
    else:
        logger.error(f"No existe la carpeta: {carpeta_docs}")

if __name__ == "__main__":
    main()
