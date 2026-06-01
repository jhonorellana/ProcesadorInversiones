"""
Programa principal para ejecutar la secuencia completa de procesamiento:
1. Descomprimir archivos ZIP
2. Renombrar archivos PDF
3. Extraer datos de los PDF
"""
import os
import re
import logging
from datetime import datetime
from typing import Dict, Any

# Importar los módulos locales
from UnzipArchivos import Unzipper
from RenombrarArchivos import RenombradorArchivos
from PDFExtractor_BVG import PDFExtractor as PDFExtractorBVG
from PDFExtractor_BVQ import PDFExtractor as PDFExtractorBVQ
from PDFExtractor_Gemini import PDFExtractor as PDFExtractorGemini

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MainProcesador:
    """Clase principal que orquesta todo el proceso"""
    
    def __init__(self):
        self.carpeta_entrada = "Entrada"
        self.carpeta_salida = "Salida"
        self.carpeta_programas = "."
        self.resultados_globales = {
            'fecha_inicio': datetime.now().isoformat(),
            'descompresion': {},
            'renombrado': {},
            'extraccion': {},
            'errores': []
        }
    
    def verificar_estructura_carpetas(self) -> bool:
        """Verifica que la estructura de carpetas sea correcta"""
        carpetas_necesarias = [self.carpeta_entrada, self.carpeta_salida]
        
        for carpeta in carpetas_necesarias:
            if not os.path.exists(carpeta):
                try:
                    os.makedirs(carpeta, exist_ok=True)
                    logger.info(f"Creada carpeta: {carpeta}")
                except Exception as e:
                    logger.error(f"No se pudo crear carpeta {carpeta}: {e}")
                    return False
        
        return True
    
    def filtrar_archivos_pdf(self, archivos_pdf: list) -> tuple:
        """Filtra archivos PDF excluyendo los de factura de bolsa"""
        # Excluir archivos que empiezan con "4. FACTURA DE BOLSA"
        archivos_filtrados = [f for f in archivos_pdf if not f.startswith("4. FACTURA DE BOLSA")]
        
        archivos_excluidos = len(archivos_pdf) - len(archivos_filtrados)
        
        if archivos_excluidos > 0:
            print(f"   Se excluyeron {archivos_excluidos} archivos de factura de bolsa")
            logger.info(f"Se excluyeron {archivos_excluidos} archivos de factura de bolsa")
        
        return archivos_filtrados, archivos_excluidos

    def detectar_bolsa_origen(self, ruta_pdf: str) -> str:
        """Determina si un PDF viene de BVG (Guayaquil) o BVQ (Quito) analizando su texto"""
        texto = ""
        try:
            import pdfplumber
            with pdfplumber.open(ruta_pdf) as pdf:
                for pagina in pdf.pages[:1]:
                    texto = pagina.extract_text() or ""
        except Exception as e:
            logger.warning(f"No se pudo usar pdfplumber para detectar bolsa en {ruta_pdf}: {e}")
            try:
                import PyPDF2
                with open(ruta_pdf, 'rb') as f:
                    lector = PyPDF2.PdfReader(f)
                    if lector.pages:
                        texto = lector.pages[0].extract_text() or ""
            except Exception as e2:
                logger.error(f"No se pudo extraer texto con PyPDF2 para detectar bolsa en {ruta_pdf}: {e2}")
                
        texto_upper = texto.upper()
        if 'QUITO' in texto_upper or 'BVQ' in texto_upper:
            return 'BVQ'
        return 'BVG' # Por defecto asumimos BVG
    
    def renombrar_usando_datos_existentes(self, archivos_filtrados: list, datos_extraidos: list) -> Dict[str, Any]:
        """Renombra archivos usando datos ya extraídos para evitar llamadas adicionales a la API"""
        archivos_renombrados = []
        errores = []
        
        # Crear un diccionario de datos extraídos por nombre de archivo
        datos_por_archivo = {}
        for dato in datos_extraidos:
            nombre_archivo = dato.get('archivo', '')
            if nombre_archivo:
                datos_por_archivo[nombre_archivo] = dato
        
        print(f"[INFO] Usando datos extraídos de {len(datos_extraidos)} archivos para renombrar")
        
        for archivo in archivos_filtrados:
            ruta_completa = os.path.join(self.carpeta_entrada, archivo)
            
            # Obtener datos extraídos para este archivo
            datos_archivo = datos_por_archivo.get(archivo, {})
            
            if datos_archivo:
                operacion_no = datos_archivo.get('operacion_no', '')
                valor_nominal = datos_archivo.get('valor_nominal', '')
                
                # Para Bonos del Estado, usar valor efectivo si no hay valor nominal
                if not valor_nominal and datos_archivo.get('tipo_documento') == 'BONO_ESTADO':
                    valor_efectivo = datos_archivo.get('valor_efectivo', '')
                    if valor_efectivo:
                        valor_nominal = valor_efectivo
                        logger.info(f"Bono del Estado: usando valor efectivo como valor nominal: {valor_efectivo}")
                
                if operacion_no and valor_nominal:
                    # Renombrar el archivo
                    exito = self._renombrar_archivo_interno(ruta_completa, operacion_no, valor_nominal)
                    if exito:
                        archivos_renombrados.append({
                            'nombre_original': archivo,
                            'nombre_nuevo': exito['nombre_nuevo'],
                            'operacion_no': operacion_no,
                            'valor_nominal': valor_nominal
                        })
                        logger.info(f"[OK] Renombrado: {archivo} -> {exito['nombre_nuevo']}")
                    else:
                        errores.append({
                            'archivo': archivo,
                            'error': 'Error al renombrar archivo'
                        })
                else:
                    error_msg = []
                    if not operacion_no:
                        error_msg.append('No se encontró número de operación')
                    if not valor_nominal:
                        error_msg.append('No se encontró valor nominal')
                    
                    logger.warning(f"No se pudo renombrar {archivo} - {'; '.join(error_msg)}")
                    errores.append({
                        'archivo': archivo,
                        'error': '; '.join(error_msg)
                    })
            else:
                logger.warning(f"No se encontraron datos extraídos para: {archivo}")
                errores.append({
                    'archivo': archivo,
                    'error': 'No se encontraron datos extraídos'
                })
        
        # Mostrar resumen
        print("\n" + "="*60)
        print("RESUMEN DEL PROCESO DE RENOMBRADO (CON DATOS EXISTENTES)")
        print("="*60)
        print(f"Total archivos encontrados: {len(archivos_filtrados)}")
        print(f"Archivos renombrados: {len(archivos_renombrados)}")
        print(f"Errores: {len(errores)}")
        
        if archivos_renombrados:
            print(f"\n[OK] ARCHIVOS RENOMBRADOS EXITOSAMENTE:")
            for archivo in archivos_renombrados:
                print(f"   {archivo['nombre_original']} -> {archivo['nombre_nuevo']}")
        
        if errores:
            print(f"\n[ERROR] ERRORES:")
            for error in errores:
                print(f"   {error['archivo']}: {error['error']}")
        
        print("="*60)
        
        return {
            'total_archivos': len(archivos_filtrados),
            'archivos_renombrados': len(archivos_renombrados),
            'errores': len(errores),
            'archivos_procesados': archivos_renombrados,
            'errores_detalle': errores
        }
    
    def _renombrar_archivo_interno(self, ruta_original: str, operacion_no: str, valor_nominal: str) -> Dict[str, Any]:
        """Método interno para renombrar un archivo PDF"""
        try:
            # Obtener información del archivo original
            directorio = os.path.dirname(ruta_original)
            nombre_base, extension = os.path.splitext(os.path.basename(ruta_original))
            
            # Limpiar y formatear los valores
            operacion_no_limpio = re.sub(r'[^\w\-]', '_', str(operacion_no))
            valor_nominal_limpio = re.sub(r'[^\w\-\.]', '_', str(valor_nominal))
            
            # Crear nuevo nombre
            nuevo_nombre = f"{nombre_base}_{operacion_no_limpio}_{valor_nominal_limpio}{extension}"
            ruta_nueva = os.path.join(directorio, nuevo_nombre)
            
            # Verificar si el archivo ya existe
            if os.path.exists(ruta_nueva):
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                nuevo_nombre = f"{nombre_base}_{operacion_no_limpio}_{valor_nominal_limpio}_{timestamp}{extension}"
                ruta_nueva = os.path.join(directorio, nuevo_nombre)
            
            # Renombrar el archivo
            os.rename(ruta_original, ruta_nueva)
            
            return {
                'nombre_original': os.path.basename(ruta_original),
                'nombre_nuevo': nuevo_nombre,
                'ruta_original': ruta_original,
                'ruta_nueva': ruta_nueva
            }
            
        except Exception as e:
            logger.error(f"Error renombrando {os.path.basename(ruta_original)}: {e}")
            return None
    
    def paso_1_descomprimir(self) -> Dict[str, Any]:
        """Paso 1: Descomprimir archivos ZIP"""
        print("\n" + "="*60)
        print("PASO 1: DESCOMPRIMIENDO ARCHIVOS ZIP")
        print("="*60)
        
        try:
            unzipper = Unzipper(self.carpeta_entrada)
            
            # Verificar si hay archivos ZIP
            archivos_zip = unzipper.listar_archivos_zip()
            
            if not archivos_zip:
                print("   No se encontraron archivos ZIP para descomprimir")
                return {
                    'exitoso': True,
                    'mensaje': 'No hay archivos ZIP para procesar',
                    'archivos_zip': [],
                    'archivos_extraidos': 0
                }
            
            print(f"Se encontraron {len(archivos_zip)} archivos ZIP:")
            for archivo in archivos_zip:
                ruta_completa = os.path.join(self.carpeta_entrada, archivo)
                tamaño = os.path.getsize(ruta_completa)
                print(f"  [ZIP] {archivo} ({tamaño:,} bytes)")
            
            # Descomprimir
            resultados = unzipper.descomprimir_todos()
            resultados['exitoso'] = (resultados.get('errores', 0) == 0)
            unzipper.mostrar_resumen(resultados)
            
            # Guardar reporte de descompresión
            unzipper.guardar_reporte(resultados)
            
            return resultados
            
        except Exception as e:
            error_msg = f"Error en descompresión: {str(e)}"
            logger.error(error_msg)
            self.resultados_globales['errores'].append(error_msg)
            return {'exitoso': False, 'error': error_msg}
    
    def paso_2_renombrar(self, datos_extraidos: Dict[str, Any] = None) -> Dict[str, Any]:
        """Paso 2: Renombrar archivos PDF usando datos ya extraídos"""
        print("\n" + "="*60)
        print("PASO 2: RENOMBRANDO ARCHIVOS PDF")
        print("="*60)
        
        try:
            # Verificar si hay archivos PDF
            if not os.path.exists(self.carpeta_entrada):
                error_msg = f"No existe la carpeta: {self.carpeta_entrada}"
                logger.error(error_msg)
                return {'exitoso': False, 'error': error_msg}
            
            archivos_pdf = []
            for archivo in os.listdir(self.carpeta_entrada):
                if archivo.lower().endswith('.pdf'):
                    archivos_pdf.append(archivo)
            
            if not archivos_pdf:
                print("   No se encontraron archivos PDF para renombrar")
                return {
                    'exitoso': True,
                    'mensaje': 'No hay archivos PDF para procesar',
                    'total_archivos': 0,
                    'archivos_renombrados': 0
                }
            
            # Aplicar filtrado centralizado
            archivos_filtrados, archivos_excluidos = self.filtrar_archivos_pdf(archivos_pdf)
            
            if not archivos_filtrados:
                print("   No se encontraron archivos PDF válidos para renombrar")
                return {
                    'exitoso': True,
                    'mensaje': 'No hay archivos PDF válidos para procesar',
                    'total_archivos': 0,
                    'archivos_renombrados': 0,
                    'archivos_excluidos': archivos_excluidos
                }
            
            print(f"Se encontraron {len(archivos_pdf)} archivos PDF ({len(archivos_filtrados)} válidos):")
            for i, archivo in enumerate(sorted(archivos_filtrados)[:5], 1):
                print(f"  {i}. {archivo}")
            if len(archivos_filtrados) > 5:
                print(f"  ... y {len(archivos_filtrados) - 5} archivos más")
            
            # Renombrar usando datos ya extraídos si están disponibles
            if datos_extraidos and 'resultados' in datos_extraidos:
                print("[PROCESANDO] Usando datos ya extraídos para renombrar (evitando llamadas adicionales a la API)")
                resultados = self.renombrar_usando_datos_existentes(archivos_filtrados, datos_extraidos['resultados'])
            else:
                # Fallback: método tradicional (solo si no hay datos extraídos)
                print("[WARN]  No se encontraron datos extraídos, usando método tradicional")
                renombrador = RenombradorArchivos(self.carpeta_entrada)
                resultados = renombrador.procesar_lista_archivos(archivos_filtrados)
                renombrador.mostrar_resumen(resultados)
                renombrador.guardar_reporte(resultados)
            
            # Agregar información de archivos excluidos al resultado
            resultados['archivos_excluidos'] = archivos_excluidos
            
            return resultados
            
        except Exception as e:
            error_msg = f"Error en renombrado: {str(e)}"
            logger.error(error_msg)
            self.resultados_globales['errores'].append(error_msg)
            return {'exitoso': False, 'error': error_msg}
    
    def extraer_datos_factura(self, ruta_pdf: str) -> Dict[str, Any]:
        """Extrae el propietario y el número de operación de una factura de bolsa"""
        try:
            import pdfplumber
            with pdfplumber.open(ruta_pdf) as pdf:
                texto = pdf.pages[0].extract_text() or ""
        except Exception as e:
            logger.warning(f"No se pudo leer factura {ruta_pdf}: {e}")
            return {}

        # Propietario: "Razón Social / Nombres y Apellidos: [OWNER] RUC/CI:" (BVG)
        #              "Razon Social: [OWNER] CI/RUC/PAS:" (BVQ)
        owner_match = re.search(
            r'Raz(?:ó|o)n\s+Social\s*(?:/\s*Nombres\s*y\s*Apellidos)?\s*:\s*(.*?)\s*(?:RUC/CI|CI/RUC/PAS):',
            texto, re.IGNORECASE
        )
        propietario = owner_match.group(1).strip() if owner_match else ''

        # Número de operación: BVG "OPE:368081", BVQ "BOLSA NO. 00012089" o "LIQ BVQ: ... 12089"
        ope_match = re.search(r'OPE\s*:\s*(\d+)', texto, re.IGNORECASE)
        if not ope_match:
            ope_match = re.search(r'BOLSA\s+N[Oº°]\s*\.?\s*(\d+)', texto, re.IGNORECASE)
        if not ope_match:
            ope_match = re.search(r'LIQ\s+BVQ\s*:[^\d]*(\d{5,})', texto, re.IGNORECASE)

        operacion_no = ''
        if ope_match:
            operacion_no = str(int(ope_match.group(1).strip()))  # normalizar quitando ceros

        return {'propietario': propietario, 'operacion_no': operacion_no}

    def paso_3_extraer_datos(self) -> Dict[str, Any]:
        """Paso 3: Extraer datos de los PDF"""
        print("\n" + "="*60)
        print("PASO 3: EXTRAYENDO DATOS DE PDF")
        print("="*60)
        
        try:
            extractor_bvg = PDFExtractorBVG()
            extractor_bvq = PDFExtractorBVQ()
            extractor_gemini = PDFExtractorGemini()
            
            # Verificar si hay archivos PDF
            if not os.path.exists(self.carpeta_entrada):
                error_msg = f"No existe la carpeta: {self.carpeta_entrada}"
                logger.error(error_msg)
                return {'exitoso': False, 'error': error_msg}
            
            archivos_pdf = []
            for archivo in os.listdir(self.carpeta_entrada):
                if archivo.lower().endswith('.pdf'):
                    archivos_pdf.append(archivo)
            
            if not archivos_pdf:
                print("   No se encontraron archivos PDF para extraer datos")
                return {
                    'exitoso': True,
                    'mensaje': 'No hay archivos PDF para procesar',
                    'total_registros': 0,
                    'archivo_salida': ''
                }
            
            # Separar facturas de liquidaciones
            archivos_facturas = [f for f in archivos_pdf if f.startswith('4. FACTURA DE BOLSA')]
            archivos_liquidaciones = [f for f in archivos_pdf if not f.startswith('4. FACTURA DE BOLSA')]

            # Aplicar filtrado centralizado solo a liquidaciones
            archivos_filtrados, archivos_excluidos = self.filtrar_archivos_pdf(archivos_liquidaciones)
            
            # ── Paso A: leer todas las facturas para construir el mapa propietario ──
            print(f"\nLeyendo {len(archivos_facturas)} facturas para extraer propietarios...")
            propietarios_por_operacion = {}   # operacion_no -> propietario
            facturas_por_operacion = {}       # operacion_no -> [{archivo, ruta}]
            for factura in archivos_facturas:
                ruta_factura = os.path.join(self.carpeta_entrada, factura)
                datos_factura = self.extraer_datos_factura(ruta_factura)
                ope_no = datos_factura.get('operacion_no', '')
                propietario = datos_factura.get('propietario', '')
                if ope_no:
                    propietarios_por_operacion[ope_no] = propietario
                    facturas_por_operacion.setdefault(ope_no, []).append({
                        'archivo': factura, 'ruta': ruta_factura
                    })
                    print(f"   Factura {factura} -> Ope: {ope_no}, Propietario: {propietario}")
                else:
                    logger.warning(f"No se pudo identificar operación en factura: {factura}")

            # ── Paso B: renombrar facturas con el número de operación ──
            self._renombrar_facturas(facturas_por_operacion)

            if not archivos_filtrados:
                print("   No se encontraron archivos PDF válidos para extraer datos")
                return {
                    'exitoso': True,
                    'mensaje': 'No hay archivos PDF válidos para procesar',
                    'total_registros': 0,
                    'archivo_salida': '',
                    'archivos_excluidos': archivos_excluidos
                }
            
            print(f"\nDetectando origen y procesando {len(archivos_filtrados)} archivos PDF válidos...")
            
            resultados_bvg = []
            resultados_quito = []
            
            for archivo in archivos_filtrados:
                ruta_completa = os.path.join(self.carpeta_entrada, archivo)
                origen = self.detectar_bolsa_origen(ruta_completa)
                
                if origen == 'BVG':
                    print(f"   Procesando con BVG (Guayaquil): {archivo}")
                    datos = None
                    try:
                        datos = extractor_bvg.procesar_pdf(ruta_completa)
                    except Exception as e:
                        logger.error(f"Error en extractor local BVG para {archivo}: {e}")
                    
                    # Fallback a Gemini si falla o no se reconoce el documento
                    if not datos or datos.get('tipo_documento') == 'DESCONOCIDO':
                        print(f"   [FALLBACK] Extractor local BVG falló o no identificó el tipo de documento. Invocando Gemini...")
                        try:
                            datos = extractor_gemini.extraer_datos_liquidacion(ruta_completa, tipo_bolsa='BVG')
                            if datos:
                                datos['extractor_utilizado'] = 'Gemini (Guayaquil) [Fallback]'
                        except Exception as e:
                            logger.error(f"Error en fallback Gemini para {archivo}: {e}")
                    
                    if datos:
                        # Inyectar propietario desde el mapa de facturas
                        ope_raw = datos.get('operacion_no', '') or ''
                        try:
                            ope_no_norm = str(int(ope_raw)) if ope_raw else ''
                        except ValueError:
                            ope_no_norm = ope_raw
                        datos['propietario'] = propietarios_por_operacion.get(ope_no_norm, '')
                        # Asegurar metadatos del archivo
                        if 'archivo' not in datos or not datos['archivo']:
                            datos['archivo'] = archivo
                            datos['ruta_completa'] = ruta_completa
                            datos['fecha_procesamiento'] = datetime.now().isoformat()
                            datos['tamaño_archivo'] = os.path.getsize(ruta_completa)
                        resultados_bvg.append(datos)
                else:
                    print(f"   Procesando con BVQ (Quito): {archivo}")
                    datos = None
                    try:
                        datos = extractor_bvq.extraer_datos_liquidacion(ruta_completa)
                    except Exception as e:
                        logger.error(f"Error en extractor local BVQ para {archivo}: {e}")
                    
                    # Fallback a Gemini si falla o no se reconoce el documento
                    if not datos or datos.get('tipo_documento') == 'DESCONOCIDO':
                        print(f"   [FALLBACK] Extractor local BVQ falló o no identificó el tipo de documento. Invocando Gemini...")
                        try:
                            datos = extractor_gemini.extraer_datos_liquidacion(ruta_completa, tipo_bolsa='BVQ')
                            if datos:
                                datos['extractor_utilizado'] = 'Gemini (Quito) [Fallback]'
                        except Exception as e:
                            logger.error(f"Error en fallback Gemini para {archivo}: {e}")
                    
                    if datos:
                        # Asegurar metadatos consistentes
                        if 'archivo' not in datos or not datos['archivo']:
                            datos['archivo'] = archivo
                            datos['ruta_completa'] = ruta_completa
                            datos['fecha_procesamiento'] = datetime.now().isoformat()
                            datos['tamaño_archivo'] = os.path.getsize(ruta_completa)
                        if 'extractor_utilizado' not in datos or not datos['extractor_utilizado']:
                            datos['extractor_utilizado'] = 'PDFExtractor_BVQ (Quito)'
                        # Inyectar propietario: la clave puede ser "12089" (sin guión VRF)
                        ope_quito = str(datos.get('operacion_no', '') or '').split('-')[0].strip()
                        datos['propietario'] = propietarios_por_operacion.get(ope_quito, '')
                        resultados_quito.append(datos)
            
            total_extraidos = len(resultados_bvg) + len(resultados_quito)
            
            if total_extraidos > 0:
                print(f"\n[INFO] RESUMEN DE EXTRACCIÓN:")
                print(f"Total de registros extraídos: {total_extraidos} (BVG: {len(resultados_bvg)}, Quito: {len(resultados_quito)})")
                
                # Contar por tipo de documento
                tipos = {}
                for resultado in resultados_bvg + resultados_quito:
                    tipo = resultado.get('tipo_documento', 'DESCONOCIDO')
                    tipos[tipo] = tipos.get(tipo, 0) + 1
                
                print("Distribución por tipo:")
                for tipo, cantidad in tipos.items():
                    print(f"  - {tipo}: {cantidad}")
                
                # Guardar resultados en CSV distintos
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                archivo_salida_bvg = os.path.join(self.carpeta_salida, f"resultados_pdf_bvg_{timestamp}.csv")
                archivo_salida_quito = os.path.join(self.carpeta_salida, f"resultados_pdf_quito_{timestamp}.csv")
                
                archivos_salida = []
                if resultados_bvg:
                    extractor_bvg.guardar_resultados_csv(resultados_bvg, archivo_salida_bvg)
                    archivos_salida.append(archivo_salida_bvg)
                else:
                    archivo_salida_bvg = ""
                    
                if resultados_quito:
                    extractor_bvq.guardar_resultados_csv(resultados_quito, archivo_salida_quito)
                    archivos_salida.append(archivo_salida_quito)
                else:
                    archivo_salida_quito = ""
                
                # Guardar archivo recopilatorio con los campos originales
                archivo_salida_recopilatorio = os.path.join(self.carpeta_salida, f"resultados_pdf_{timestamp}.csv")
                self.guardar_resultados_recopilatorio(resultados_bvg, resultados_quito, archivo_salida_recopilatorio)
                archivos_salida.append(archivo_salida_recopilatorio)
                
                return {
                    'exitoso': True,
                    'total_registros': total_extraidos,
                    'archivo_salida_bvg': archivo_salida_bvg,
                    'archivo_salida_quito': archivo_salida_quito,
                    'archivo_salida_recopilatorio': archivo_salida_recopilatorio,
                    'archivo_salida': " y ".join(archivos_salida),
                    'tipos_documento': tipos,
                    'archivos_excluidos': archivos_excluidos,
                    'resultados': resultados_bvg + resultados_quito
                }
            else:
                print("[WARN]  No se extrajeron datos de los archivos PDF")
                return {
                    'exitoso': False,
                    'mensaje': 'No se pudieron extraer datos',
                    'total_registros': 0
                }
                
        except Exception as e:
            error_msg = f"Error en extracción de datos: {str(e)}"
            logger.error(error_msg)
            self.resultados_globales['errores'].append(error_msg)
            return {'exitoso': False, 'error': error_msg}

    def _renombrar_facturas(self, facturas_por_operacion: dict):
        """Renombra las facturas extraídas con el número de operación correspondiente"""
        for ope_no, facturas in facturas_por_operacion.items():
            for idx, info in enumerate(facturas):
                ruta_original = info['ruta']
                archivo_original = info['archivo']
                directorio = os.path.dirname(ruta_original)

                # Construir nuevo nombre: "4. FACTURA DE BOLSA[_N]_[operacion_no].pdf"
                sufijo = f"_{idx}" if idx > 0 else ""
                nuevo_nombre = f"4. FACTURA DE BOLSA{sufijo}_{ope_no}.pdf"
                ruta_nueva = os.path.join(directorio, nuevo_nombre)

                if ruta_original == ruta_nueva:
                    continue
                # Evitar colisiones
                contador = 1
                while os.path.exists(ruta_nueva):
                    nuevo_nombre = f"4. FACTURA DE BOLSA{sufijo}_{ope_no}_{contador}.pdf"
                    ruta_nueva = os.path.join(directorio, nuevo_nombre)
                    contador += 1
                try:
                    os.rename(ruta_original, ruta_nueva)
                    logger.info(f"Factura renombrada: {archivo_original} -> {nuevo_nombre}")
                    print(f"   [OK] Factura renombrada: {archivo_original} -> {nuevo_nombre}")
                    # Actualizar ruta para consistencia interna
                    info['ruta'] = ruta_nueva
                    info['archivo'] = nuevo_nombre
                except Exception as e:
                    logger.error(f"Error renombrando factura {archivo_original}: {e}")
            
    def guardar_resultados_recopilatorio(self, resultados_bvg: list, resultados_quito: list, archivo_salida: str):
        """Genera un archivo CSV consolidado con los 22 campos del extractor original para ambas bolsas"""
        import csv
        try:
            registros_normalizados = []
            
            # 1. Procesar registros de BVG (ya tienen los campos originales)
            for r in resultados_bvg:
                if r.get('tipo_documento') == 'DESCONOCIDO':
                    continue
                registros_normalizados.append(r)
                
            # 2. Procesar y mapear registros de Quito (Gemini)
            for r in resultados_quito:
                if r.get('tipo_documento') == 'DESCONOCIDO':
                    continue
                # Mapear campos del extractor de Quito a los del extractor original
                r_mapped = {
                    'tipo_operacion': r.get('tipo_operacion', ''),
                    'propietario': r.get('propietario', ''),
                    'tipo_documento': r.get('tipo_documento', ''),
                    'operacion_no': r.get('operacion_no', ''),
                    'titulo_valor': r.get('titulo_valor', ''),
                    'emisor': r.get('emisor', ''),
                    'valor_nominal': r.get('valor_nominal', ''),
                    'emision_titulo': r.get('fecha_emision', ''),
                    'vencimiento_titulo': r.get('fecha_vencimiento', ''),
                    'codigo_vector_precio': r.get('codigo_vector', ''),
                    'rend_nominal': r.get('rendimiento_nominal', ''),
                    'rend_efectivo': r.get('cupon_actual', ''),
                    'precio': r.get('precio', ''),
                    'tasa_interes_vigente': r.get('interes_nominal', ''),
                    'monto_a_negociar': r.get('valor_nominal', ''),
                    'valor_efectivo': r.get('valor_efectivo', ''),
                    'valor_interes': r.get('valor_interes', ''),
                    'total_desembolso': r.get('valor_efectivo', ''),
                    'comision_bolsa': r.get('comision_bolsa', ''),
                    'comision_operador': r.get('comision_operador', ''),
                    'total_comisiones': r.get('total_comisiones', ''),
                    'total_comprador_neto': r.get('total_comprador', ''),
                    'precio_neto': r.get('precio_neto', ''),
                    'numero_titulos': r.get('numero_titulos', '1'),
                    'archivo': r.get('archivo', '')
                }
                registros_normalizados.append(r_mapped)
                
            if not registros_normalizados:
                logger.warning("No hay registros válidos para guardar en el recopilatorio")
                return
                
            # Cabeceras: tipo_operacion y propietario primero, luego los 22 campos originales + archivo
            encabezados = [
                'tipo_operacion', 'propietario',
                'tipo_documento', 'operacion_no', 'titulo_valor', 'emisor', 
                'valor_nominal', 'emision_titulo', 'vencimiento_titulo',
                'codigo_vector_precio', 'rend_nominal', 'rend_efectivo',
                'precio', 'tasa_interes_vigente', 'monto_a_negociar',
                'valor_efectivo', 'valor_interes', 'total_desembolso',
                'comision_bolsa', 'comision_operador', 'total_comisiones',
                'total_comprador_neto', 'precio_neto', 'numero_titulos',
                'archivo'
            ]
            
            with open(archivo_salida, 'w', newline='', encoding='latin-1') as f:
                writer = csv.DictWriter(f, fieldnames=encabezados, delimiter=';')
                writer.writeheader()
                for reg in registros_normalizados:
                    fila = {campo: reg.get(campo, '') for campo in encabezados}
                    writer.writerow(fila)
                    
            logger.info(f"Archivo recopilatorio guardado en CSV: {archivo_salida}")
            print(f"   Archivo recopilatorio guardado en CSV: {archivo_salida}")
            
        except Exception as e:
            logger.error(f"Error generando archivo recopilatorio: {e}")
    
    def ejecutar_proceso_completo(self) -> Dict[str, Any]:
        """Ejecuta la secuencia completa de procesamiento"""
        print("[INICIO] INICIANDO PROCESO COMPLETO DE PROCESAMIENTO DE DOCUMENTOS")
        print(f"Fecha y hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Carpeta de entrada: {os.path.abspath(self.carpeta_entrada)}")
        print(f"Carpeta de salida: {os.path.abspath(self.carpeta_salida)}")
        
        # Verificar estructura de carpetas
        if not self.verificar_estructura_carpetas():
            print("[ERROR] Error en la verificación de carpetas. Proceso cancelado.")
            return {'exitoso': False, 'error': 'Error en estructura de carpetas'}
        
        # Ejecutar cada paso
        print("\n[PROCESANDO] Iniciando secuencia de procesamiento optimizada...")
        
        # Paso 1: Descomprimir
        self.resultados_globales['descompresion'] = self.paso_1_descomprimir()
        
        # Paso 2: Extraer datos (ahora antes de renombrar para eficiencia)
        print("\n[META] EXTRAYENDO DATOS PRIMERO (para usar en renombrado)")
        self.resultados_globales['extraccion'] = self.paso_3_extraer_datos()
        
        # Paso 3: Renombrar usando datos ya extraídos
        if self.resultados_globales['extraccion'].get('exitoso'):
            print("\n[PROCESANDO] RENOMBRANDO USANDO DATOS YA EXTRAÍDOS")
            self.resultados_globales['renombrado'] = self.paso_2_renombrar(self.resultados_globales['extraccion'])
        else:
            print("\n[WARN]  No se pudieron extraer datos, intentando renombrado tradicional")
            self.resultados_globales['renombrado'] = self.paso_2_renombrar()
        
        # Resumen final
        self.mostrar_resumen_final()
        
        # Guardar reporte global
        self.guardar_reporte_global()
        
        return self.resultados_globales
    
    def mostrar_resumen_final(self):
        """Muestra un resumen final de todo el proceso"""
        print("\n" + "="*80)
        print("[INFO] RESUMEN FINAL DEL PROCESO COMPLETO")
        print("="*80)
        
        # Descompresión
        descomp = self.resultados_globales['descompresion']
        if descomp.get('exitoso'):
            print(f"[OK] Descompresión: {descomp.get('archivos_extraidos', 0)} archivos extraídos")
        else:
            print(f"[ERROR] Descompresión: {descomp.get('error', 'Error desconocido')}")
        
        # Renombrado
        renomb = self.resultados_globales['renombrado']
        if renomb.get('archivos_renombrados', 0) > 0:
            print(f"[OK] Renombrado: {renomb.get('archivos_renombrados', 0)} archivos renombrados")
        else:
            print(f"   Renombrado: {renomb.get('mensaje', 'No se procesaron archivos')}")
        
        # Extracción
        extra = self.resultados_globales['extraccion']
        if extra.get('exitoso'):
            print(f"[OK] Extracción: {extra.get('total_registros', 0)} registros extraídos")
            if extra.get('archivo_salida'):
                print(f"[DIR] Archivo de salida: {extra['archivo_salida']}")
        else:
            print(f"[ERROR] Extracción: {extra.get('error', extra.get('mensaje', 'Error desconocido'))}")
        
        # Errores globales
        if self.resultados_globales['errores']:
            print(f"\n[WARN]  Errores encontrados: {len(self.resultados_globales['errores'])}")
            for error in self.resultados_globales['errores']:
                print(f"   - {error}")
        
        print("="*80)
        print(f"[EXITO] Proceso completado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    def guardar_reporte_global(self):
        """Guarda un reporte global de todo el proceso"""
        try:
            self.resultados_globales['fecha_fin'] = datetime.now().isoformat()
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            archivo_reporte = f"{self.carpeta_salida}/reporte_proceso_completo_{timestamp}.json"
            
            os.makedirs(self.carpeta_salida, exist_ok=True)
            
            import json
            with open(archivo_reporte, 'w', encoding='utf-8') as f:
                json.dump(self.resultados_globales, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Reporte global guardado en: {archivo_reporte}")
            print(f"\n[INFO] Reporte global guardado en: {archivo_reporte}")
            
        except Exception as e:
            logger.error(f"Error guardando reporte global: {e}")

def main():
    """Función principal"""
    print("[META] PROCESADOR PRINCIPAL DE DOCUMENTOS FINANCIEROS (OPTIMIZADO)")
    print("Este programa ejecuta la secuencia completa de procesamiento:")
    print("  1. Descomprimir archivos ZIP")
    print("  2. Extraer datos de los PDF (con Gemini fallback si es necesario)")
    print("  3. Renombrar archivos PDF usando datos ya extraídos")
    print("\n[OK] Optimización: Los datos se extraen solo UNA VEZ y se reutilizan")
    print()
    
    # Confirmar ejecución - automático para ejecución desde GUI
    print("[INICIO] Iniciando ejecución automática del proceso completo...")
    
    # Crear y ejecutar procesador
    procesador = MainProcesador()
    resultados = procesador.ejecutar_proceso_completo()
    
    print("\n[FIN] Programa finalizado. Revise los reportes en la carpeta Salida.")

if __name__ == "__main__":
    main()
