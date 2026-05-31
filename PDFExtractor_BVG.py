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
    
    def extraer_tipo_operacion(self, texto: str) -> str:
        """Extrae el tipo de operacion (Compra o Venta) del texto del PDF.
        
        Soporta dos formatos:
        - BVG: campo 'Postura:' seguido de COMPRA o VENTA en la siguiente linea.
        - BVQ: campo 'Liquidacion de contrato:' que contiene 'Compra' o 'Venta'.
        """
        lineas = texto.split('\n')
        for i, linea in enumerate(lineas):
            linea_strip = linea.strip()

            # Formato BVG: 'Postura:' en la linea, valor en la siguiente
            if 'Postura:' in linea:
                # El valor puede estar en la misma linea o en la siguiente
                # Ejemplo: "Postura:\nCOMPRA Factura No.:"
                resto = linea.split('Postura:')[1].strip()
                if resto:
                    palabra = resto.split()[0].upper()
                    if palabra in ('COMPRA', 'VENTA'):
                        return palabra
                # Buscar en la linea siguiente
                if i + 1 < len(lineas):
                    siguiente = lineas[i + 1].strip()
                    palabra = siguiente.split()[0].upper() if siguiente else ''
                    if palabra in ('COMPRA', 'VENTA'):
                        return palabra

            # Formato BVQ: 'Liquidacion de contrato:' contiene Compra o Venta
            if 'Liquidaci' in linea and 'contrato' in linea.lower():
                # Buscar en la misma linea y en la siguiente
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
            # Ejemplo: "Cliente:", "Inversionista:", "Propietario:", "Titular:"
            if any(palabra in linea_strip for palabra in ['Cliente:', 'Inversionista:', 'Propietario:', 'Titular:', 'Nombre:']):
                # Extraer el valor que sigue después del campo
                for campo in ['Cliente:', 'Inversionista:', 'Propietario:', 'Titular:', 'Nombre:']:
                    if campo in linea_strip:
                        resto = linea_strip.split(campo)[1].strip()
                        if resto:
                            return resto
                        # Si está en la siguiente línea
                        if i + 1 < len(lineas):
                            siguiente = lineas[i + 1].strip()
                            if siguiente and not any(palabra in siguiente for palabra in ['Sector', 'Dirección', 'Teléfono', 'Email']):
                                return siguiente
        
        return ''
    
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
        
        # Formatos como DD-MM-YYYY o DD-MM-YY
        match = re.match(r'^(\d{1,2})-(\d{1,2})-(\d{2,4})$', parte_fecha)
        if match:
            d, m, y = match.groups()
            if len(y) == 2:
                # Asumir siglo 20 o 21
                y = "20" + y if int(y) < 50 else "19" + y
            return f"{y}-{m.zfill(2)}-{d.zfill(2)}{parte_hora}"
            
        # Formatos como YYYY-MM-DD
        match = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})$', parte_fecha)
        if match:
            y, m, d = match.groups()
            return f"{y}-{m.zfill(2)}-{d.zfill(2)}{parte_hora}"
            
        return fecha_str
        
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
    
    def extraer_datos_bvg_comun(self, texto: str, tipo_doc: str) -> Dict[str, Any]:
        """Extrae de manera unificada todos los campos de un PDF de BVG"""
        datos = {
            'tipo_operacion': '',
            'propietario': '',
            'tipo_documento': tipo_doc,
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
            'numero_titulos': '',
            'factura_no': '',
            'mercado': '',
            'fecha_negociacion': '',
            'hora_negociacion': '',
            'casa_valores': '',
            'ruc_casa_valores': '',
            'direccion_casa_valores': '',
            'operador_valores': '',
            'saldo_por_amortizar': '',
            'sector_economico': '',
            'calificacion_riesgo': '',
            'resolucion_scvs': '',
            'catastro_mercado_valores': '',
            'codigo_isin': '',
            'tipo_mercado': '',
            'plazo_por_vencer': '',
            'plazo_venc_real': '',
            'base_dias': '',
            'precio_sucio': '',
            'cupon': '',
            'inicio_cupon': '',
            'vcto_cupon': '',
            'tasa_interes_futura': '',
            'dias_interes': '',
            'tipo_tasa': '',
            'valor_garantia': '',
            'plazo_garantia': '',
            'cump_garantia': '',
            'fecha_valor': '',
            'deposito_compensacion': '',
            'valor_efectivo_recompra': '',
            'factor_calculo': '',
            'cruzada': '',
            'retenciones_fuente_bvg': '',
            'retenciones_fuente_cv': '',
            'total_retenciones': '',
            'subtotales': '',
            'iva': '',
            'total_comprador_bruto': ''
        }

        # Extraer número de operación de la cabecera
        match_cabecera = re.search(r'BOLSA DE VALORES DE GUAYAQUIL S.A. BVG\s+(\d+)', texto)
        if match_cabecera:
            datos['operacion_no'] = match_cabecera.group(1).strip()
            
        # Aplicar expresiones regulares para cada campo
        def aplicar_regex(patron, string, flags=re.IGNORECASE):
            match = re.search(patron, string, flags)
            return match.groups() if match else None

        # Mercado y Postura
        res = aplicar_regex(r'Mercado[ \t]*:[ \t]*(.*?)[ \t]+Postura[ \t]*:[ \t]*([A-Z\s]+)', texto)
        if res:
            datos['mercado'] = res[0].strip()
            datos['tipo_operacion'] = res[1].strip()

        # Fecha y Hora de negociación
        res = aplicar_regex(r'Fecha de negociaci[óo]n[ \t]*:[ \t]*([\d/]+)[ \t]+Hora de negociaci[óo]n[ \t]*:[ \t]*([\d:]+)', texto)
        if res:
            datos['fecha_negociacion'] = res[0].strip()
            datos['hora_negociacion'] = res[1].strip()

        # Factura No.
        res = aplicar_regex(r'Factura No\.[ \t]*:[ \t]*(\d+)', texto)
        if res:
            datos['factura_no'] = res[0].strip()

        # Casa de Valores y RUC
        res = aplicar_regex(r'Casa de valores[ \t]*:[ \t]*(.*?)[ \t]+R\.?U\.?C\.?[ \t]*:?[ \t]*(\d+)', texto)
        if res:
            datos['casa_valores'] = res[0].strip()
            datos['ruc_casa_valores'] = res[1].strip()

        # Dirección de la Casa de Valores
        res = aplicar_regex(r'Direcci[óo]n[ \t]*:[ \t]*(.*?)(?=\n\s*Operador de valores:|\n\s*Emisor - T|$)', texto, re.DOTALL)
        if res:
            datos['direccion_casa_valores'] = res[0].replace('\n', ' ').strip()

        # Operador de Valores
        res = aplicar_regex(r'Operador de valores[ \t]*:[ \t]*([^\n\r]+)', texto)
        if res:
            datos['operador_valores'] = res[0].strip()

        # Título Valor
        res = aplicar_regex(r'T[íi]tulo valor[ \t]*:[ \t]*(.*?)(?=\n\s*N[úu]mero de t[íi]tulos:|\n\s*Emisor:|$)', texto, re.DOTALL)
        if res:
            datos['titulo_valor'] = res[0].replace('\n', ' ').strip()

        # Número de títulos, Valor nominal y Saldo por amortizar
        res = aplicar_regex(r'N[úu]mero de t[íi]tulos[ \t]*:[ \t]*([\d,\.]+)[ \t]+Valor nominal[ \t]*:[ \t]*\$[ \t]*([\d,\.]+)(?:[ \t]+Saldo por amortizar[ \t]*:[ \t]*([\d,\.\%]*))?', texto)
        if res:
            datos['numero_titulos'] = self.limpiar_valor_numerico(res[0])
            datos['valor_nominal'] = self.limpiar_valor_numerico(res[1])
            if len(res) > 2 and res[2]:
                datos['saldo_por_amortizar'] = self.limpiar_valor_numerico(res[2])

        # Emisor
        res = aplicar_regex(r'Emisor[ \t]*:[ \t]*(.*?)(?=\n\s*Sector econ[óo]mico:|$)', texto)
        if res:
            datos['emisor'] = res[0].strip()

        # Sector Económico
        res = aplicar_regex(r'Sector econ[óo]mico[ \t]*:[ \t]*([^\n\r]+)', texto)
        if res:
            datos['sector_economico'] = res[0].strip()

        # Emisión, Vencimiento, Desmaterializado, Derecho
        res = aplicar_regex(r'Emisi[óo]n de t[íi]tulo[ \t]*:[ \t]*([\d/]*)[ \t]*Vencimiento t[íi]tulo[ \t]*:[ \t]*([\d/]*)[ \t]*Desmaterializado[ \t]*:[ \t]*([A-Z]*)[ \t]*Derecho[ \t]*:[ \t]*([A-Za-z0-9[ \t]]*)', texto)
        if res:
            datos['emision_titulo'] = res[0].strip() if res[0] else ''
            datos['vencimiento_titulo'] = res[1].strip() if res[1] else ''
            datos['desmaterializado'] = res[2].strip() if res[2] else ''
            datos['derecho'] = res[3].strip() if res[3] else ''

        # Calificación de riesgo
        res = aplicar_regex(r'Calificaci[óo]n de riesgo[ \t]*:[ \t]*(.*?)(?=\n\s*Resoluci[óo]n SCVS[ \t]*:|\n\s*C[óo]digo vector precio[ \t]*:|$)', texto, re.DOTALL)
        if res:
            datos['calificacion_riesgo'] = res[0].replace('\n', ' ').strip()

        # Resolución SCVS y Catastro
        res = aplicar_regex(r'Resoluci[óo]n SCVS[ \t]*:[ \t]*(.*?)[ \t]+Catastro mercado de valores[ \t]*:[ \t]*([^\n\r]*)', texto)
        if res:
            datos['resolucion_scvs'] = res[0].strip()
            datos['catastro_mercado_valores'] = res[1].strip()

        # Código vector precio y Código ISIN
        res = aplicar_regex(r'C[óo]digo vector precio[ \t]*:[ \t]*(.*?)[ \t]+C[óo]digo ISIN[ \t]*:[ \t]*([^\n\r]*)', texto)
        if res:
            datos['codigo_vector_precio'] = res[0].strip()
            datos['codigo_isin'] = res[1].strip()

        # Tipo de mercado, Plazo por vencer, Plazo venc. Real, Base días
        res = aplicar_regex(r'Tipo de mercado[ \t]*:[ \t]*(.*?)[ \t]+Plazo por vencer[ \t]*:[ \t]*(.*?)[ \t]+Plazo venc\. Real[ \t]*:[ \t]*(.*?)[ \t]+Base d[íi]as[ \t]*:[ \t]*([^\n\r]*)', texto)
        if res:
            datos['tipo_mercado'] = res[0].strip()
            datos['plazo_por_vencer'] = res[1].strip()
            datos['plazo_venc_real'] = res[2].strip()
            datos['base_dias'] = res[3].strip()

        # Rendimientos y Precios
        res = aplicar_regex(r'Rend\.? Nominal[ \t]*:[ \t]*([\d,\.\%]*)[ \t]*Rend\.? Efectivo[ \t]*:[ \t]*([\d,\.\%]*)[ \t]*Precio sucio[ \t]*:[ \t]*([\d,\.\%]*)[ \t]*Precio[ \t]*:[ \t]*([\d,\.\%]+)', texto)
        if res:
            datos['rend_nominal'] = self.limpiar_valor_numerico(res[0])
            datos['rend_efectivo'] = self.limpiar_valor_numerico(res[1])
            datos['precio_sucio'] = self.limpiar_valor_numerico(res[2])
            datos['precio'] = self.limpiar_valor_numerico(res[3])

        # Cupón, Inicio de cupón, Vcto. Cupón, Monto a negociar
        res = aplicar_regex(r'Cup[óo]n[ \t]*:[ \t]*(.*?)[ \t]+Inicio de cup[óo]n[ \t]*:[ \t]*(.*?)[ \t]+Vcto\. Cup[óo]n[ \t]*:[ \t]*(.*?)[ \t]+Monto a negociar[ \t]*:[ \t]*\$[ \t]*([\d,\.\-]+)', texto)
        if res:
            datos['cupon'] = res[0].strip()
            datos['inicio_cupon'] = res[1].strip()
            datos['vcto_cupon'] = res[2].strip()
            datos['monto_a_negociar'] = self.limpiar_valor_numerico(res[3])

        # Tasas e Intereses
        res = aplicar_regex(r'Tasa inter[ée]s vigente[ \t]*:[ \t]*([\d,\.\%]*)[ \t]*Tasa inter[ée]s futura[ \t]*:[ \t]*([\d,\.\%]*)[ \t]*D[íi]as inter[ée]s[ \t]*:[ \t]*(\d*)[ \t]*Tipo tasa[ \t]*:[ \t]*([A-Za-z]*)', texto)
        if res:
            datos['tasa_interes_vigente'] = self.limpiar_valor_numerico(res[0])
            datos['tasa_interes_futura'] = self.limpiar_valor_numerico(res[1])
            datos['dias_interes'] = res[2].strip()
            datos['tipo_tasa'] = res[3].strip()

        # Valor garantía, Plazo garantía, Cump. Garantía, Fecha valor
        res = aplicar_regex(r'Valor de garant[íi]a[ \t]*:[ \t]*(.*?)[ \t]+Plazo garant[íi]a[ \t]*:[ \t]*(.*?)[ \t]+Cump\. Garant[íi]a[ \t]*:[ \t]*(.*?)[ \t]+Fecha valor[ \t]*:[ \t]*([\d/]+)', texto)
        if res:
            datos['valor_garantia'] = res[0].strip()
            datos['plazo_garantia'] = res[1].strip()
            datos['cump_garantia'] = res[2].strip()
            datos['fecha_valor'] = res[3].strip()

        # Depósito compensación y Valor efectivo recompra
        res = aplicar_regex(r'Dep[óo]sito de compensaci[óo]n[ \t]*:[ \t]*(.*?)[ \t]+Valor efectivo recompra[ \t]*:[ \t]*([^\n\r]*)', texto)
        if res:
            datos['deposito_compensacion'] = res[0].strip()
            datos['valor_efectivo_recompra'] = res[1].strip()

        # Factor cálculo y Cruzada
        res = aplicar_regex(r'Factor de c[áa]lculo[ \t]*:[ \t]*(.*?)[ \t]+Cruzada[ \t]*:[ \t]*([A-Z]+)', texto)
        if res:
            datos['factor_calculo'] = res[0].strip()
            datos['cruzada'] = res[1].strip()

        # Totales - usando regex más generales sobre el texto completo
        totales_patrones = {
            'valor_efectivo': r'\(A\)VALOR EFECTIVO\s+([\d,\.\-]+)',
            'valor_interes': r'\(B\)\s*VALOR INTER[EÉ]S\s+([\d,\.\-]+)?',
            'total_desembolso': r'TOTAL DE DESEMBOLSO\s+([\d,\.\-]+)',
            'comision_bolsa': r'\(C\) BOLSA\s+[\d\.%]+\s+([\d,\.\-]+)',
            'comision_operador': r'\(D\) OPERADOR\s+[\d\.%]+\s+([\d,\.\-]+)',
            'total_comisiones': r'TOTAL DE COMISIONES\s+([\d,\.\-]+)',
            'retenciones_fuente_bvg': r'\(E\) RETENCIONES EN LA FUENTE BVG \*\s*([\d,\.\-]+)?',
            'retenciones_fuente_cv': r'\(F\) RETENCIONES EN LA FUENTE CV\s*([\d,\.\-]+)?',
            'total_retenciones': r'TOTAL DE RETENCIONES\s+([\d,\.\-]+)?',
            'subtotales': r'SUBTOTALES:\s+([\d,\.\-]+)',
            'iva': r'IVA:\s+([\d,\.\-]+)',
            'total_comprador_bruto': r'TOTAL COMPRADOR BRUTO:\s*([\d,\.\-]+)',
            'total_comprador_neto': r'TOTAL COMPRADOR NETO[:\s]*\$?\s*([\d,\.\-]+)'
        }

        # Para vendedor netos si es el caso
        if datos['tipo_operacion'] == 'VENTA':
            totales_patrones['total_comprador_neto'] = r'TOTAL VENDEDOR NETO[:\s]*\$?\s*([\d,\.\-]+)'
            totales_patrones['total_comprador_bruto'] = r'TOTAL VENDEDOR BRUTO:\s*([\d,\.\-]+)'

        for campo, patron in totales_patrones.items():
            res = re.search(patron, texto, re.IGNORECASE)
            if res and res.group(1):
                datos[campo] = self.limpiar_valor_numerico(res.group(1).strip())

        # Precio Neto
        res_precio_neto = re.search(r'PRECIO NETO:\s*([\d,\.\-]+)', texto, re.IGNORECASE)
        if res_precio_neto:
            datos['precio_neto'] = self.limpiar_valor_numerico(res_precio_neto.group(1).strip())

        # Limpiar y formatear fechas a YYYY-MM-DD
        campos_fecha = [
            'fecha_negociacion', 'fecha_valor', 'emision_titulo', 
            'vencimiento_titulo', 'inicio_cupon', 'vcto_cupon'
        ]
        for campo in campos_fecha:
            if campo in datos and datos[campo]:
                datos[campo] = self.formatear_fecha_yyyy_mm_dd(str(datos[campo]))

        return datos

    def extraer_datos_nota_credito(self, texto: str) -> Dict[str, Any]:
        """Extrae datos específicos de una nota de crédito"""
        return self.extraer_datos_bvg_comun(texto, 'NOTA_CREDITO')

    def extraer_datos_bono_estado(self, texto: str) -> Dict[str, Any]:
        """Extrae datos específicos de Bonos del Estado de BVG"""
        return self.extraer_datos_bvg_comun(texto, 'BONO_ESTADO')
    
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
        
        # Extraer tipo de operacion del texto crudo (aplica a todos los tipos de documento)
        tipo_operacion = self.extraer_tipo_operacion(texto)
        if tipo_operacion:
            datos['tipo_operacion'] = tipo_operacion
        else:
            # Si no se encuentra el tipo de operación, dejar vacío
            datos['tipo_operacion'] = ''
        
        # Extraer propietario del documento
        propietario = self.extraer_propietario(texto)
        if propietario:
            datos['propietario'] = propietario
        else:
            # Si no se encuentra el propietario, dejar vacío
            datos['propietario'] = ''

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
            campos_principales = [
                'tipo_operacion', 'propietario', 'tipo_documento', 'operacion_no', 'titulo_valor', 'emisor', 
                'valor_nominal', 'emision_titulo', 'vencimiento_titulo',
                'codigo_vector_precio', 'rend_nominal', 'rend_efectivo',
                'precio', 'tasa_interes_vigente', 'monto_a_negociar',
                'valor_efectivo', 'valor_interes', 'total_desembolso',
                'comision_bolsa', 'comision_operador', 'total_comisiones',
                'total_comprador_neto', 'precio_neto', 'numero_titulos',
                'factura_no', 'mercado', 'fecha_negociacion', 'hora_negociacion',
                'casa_valores', 'ruc_casa_valores', 'direccion_casa_valores', 'operador_valores',
                'saldo_por_amortizar', 'sector_economico', 'calificacion_riesgo', 'resolucion_scvs',
                'catastro_mercado_valores', 'codigo_isin', 'tipo_mercado', 'plazo_por_vencer',
                'plazo_venc_real', 'base_dias', 'precio_sucio', 'cupon', 'inicio_cupon',
                'vcto_cupon', 'tasa_interes_futura', 'dias_interes', 'tipo_tasa',
                'valor_garantia', 'plazo_garantia', 'cump_garantia', 'fecha_valor',
                'deposito_compensacion', 'valor_efectivo_recompra', 'factor_calculo', 'cruzada',
                'retenciones_fuente_bvg', 'retenciones_fuente_cv', 'total_retenciones', 'subtotales',
                'iva', 'total_comprador_bruto',
                'extractor_utilizado', 'archivo'
            ]
            
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
            
            print(f"\n[HERRAMIENTA] ESTADÍSTICAS DE EXTRACTORES:")
            for extractor, cantidad in extractores_usados.items():
                print(f"   {extractor}: {cantidad} documentos")
            
            # Mostrar resultados válidos
            print(f"\n[INFO] RESULTADOS VÁLIDOS ({len(resultados_validos)} documentos):")
            for resultado in resultados_validos:
                print(f"\n--- {resultado['archivo']} ---")
                print(f"Tipo: {resultado['tipo_documento']}")
                print(f"Extractor: {resultado.get('extractor_utilizado', 'N/A')}")
                for key, value in resultado.items():
                    if key not in ['archivo', 'ruta_completa', 'fecha_procesamiento', 'texto_completo', 'extractor_utilizado']:
                        print(f"{key}: {value}")
            
            # Mostrar documentos desconocidos si los hay
            if desconocidos:
                print(f"\n[WARN]  DOCUMENTOS DESCONOCIDOS ({len(desconocidos)} archivos):")
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
