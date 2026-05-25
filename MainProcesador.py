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
from PDFExtractor_BVG import PDFExtractor

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
            print(f"ℹ️  Se excluyeron {archivos_excluidos} archivos de factura de bolsa")
            logger.info(f"Se excluyeron {archivos_excluidos} archivos de factura de bolsa")
        
        return archivos_filtrados, archivos_excluidos
    
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
        
        print(f"📊 Usando datos extraídos de {len(datos_extraidos)} archivos para renombrar")
        
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
                        logger.info(f"✅ Renombrado: {archivo} -> {exito['nombre_nuevo']}")
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
            print(f"\n✅ ARCHIVOS RENOMBRADOS EXITOSAMENTE:")
            for archivo in archivos_renombrados:
                print(f"   {archivo['nombre_original']} -> {archivo['nombre_nuevo']}")
        
        if errores:
            print(f"\n❌ ERRORES:")
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
                print("ℹ️  No se encontraron archivos ZIP para descomprimir")
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
                print(f"  📦 {archivo} ({tamaño:,} bytes)")
            
            # Descomprimir
            resultados = unzipper.descomprimir_todos()
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
                print("ℹ️  No se encontraron archivos PDF para renombrar")
                return {
                    'exitoso': True,
                    'mensaje': 'No hay archivos PDF para procesar',
                    'total_archivos': 0,
                    'archivos_renombrados': 0
                }
            
            # Aplicar filtrado centralizado
            archivos_filtrados, archivos_excluidos = self.filtrar_archivos_pdf(archivos_pdf)
            
            if not archivos_filtrados:
                print("ℹ️  No se encontraron archivos PDF válidos para renombrar")
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
                print("🔄 Usando datos ya extraídos para renombrar (evitando llamadas adicionales a la API)")
                resultados = self.renombrar_usando_datos_existentes(archivos_filtrados, datos_extraidos['resultados'])
            else:
                # Fallback: método tradicional (solo si no hay datos extraídos)
                print("⚠️  No se encontraron datos extraídos, usando método tradicional")
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
    
    def paso_3_extraer_datos(self) -> Dict[str, Any]:
        """Paso 3: Extraer datos de los PDF"""
        print("\n" + "="*60)
        print("PASO 3: EXTRAYENDO DATOS DE PDF")
        print("="*60)
        
        try:
            extractor = PDFExtractor()
            
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
                print("ℹ️  No se encontraron archivos PDF para extraer datos")
                return {
                    'exitoso': True,
                    'mensaje': 'No hay archivos PDF para procesar',
                    'total_registros': 0,
                    'archivo_salida': ''
                }
            
            # Aplicar filtrado centralizado
            archivos_filtrados, archivos_excluidos = self.filtrar_archivos_pdf(archivos_pdf)
            
            if not archivos_filtrados:
                print("ℹ️  No se encontraron archivos PDF válidos para extraer datos")
                return {
                    'exitoso': True,
                    'mensaje': 'No hay archivos PDF válidos para procesar',
                    'total_registros': 0,
                    'archivo_salida': '',
                    'archivos_excluidos': archivos_excluidos
                }
            
            print(f"Procesando {len(archivos_filtrados)} archivos PDF válidos...")
            
            # Extraer datos usando archivos filtrados
            if hasattr(extractor, 'procesar_lista_archivos'):
                resultados = extractor.procesar_lista_archivos(self.carpeta_entrada, archivos_filtrados)
            else:
                # Fallback para extractores que no tienen el método
                resultados = extractor.procesar_carpeta(self.carpeta_entrada)
            
            if resultados:
                print(f"\n📊 RESUMEN DE EXTRACCIÓN:")
                print(f"Total de registros extraídos: {len(resultados)}")
                
                # Contar por tipo de documento
                tipos = {}
                for resultado in resultados:
                    tipo = resultado.get('tipo_documento', 'DESCONOCIDO')
                    tipos[tipo] = tipos.get(tipo, 0) + 1
                
                print("Distribución por tipo:")
                for tipo, cantidad in tipos.items():
                    print(f"  - {tipo}: {cantidad}")
                
                # Guardar resultados en CSV
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                archivo_salida = os.path.join(self.carpeta_salida, f"resultados_pdf_{timestamp}.csv")
                extractor.guardar_resultados_csv(resultados, archivo_salida)
                
                return {
                    'exitoso': True,
                    'total_registros': len(resultados),
                    'archivo_salida': archivo_salida,
                    'tipos_documento': tipos,
                    'archivos_excluidos': archivos_excluidos,
                    'resultados': resultados  # Agregar resultados brutos para reutilizar en renombrado
                }
            else:
                print("⚠️  No se extrajeron datos de los archivos PDF")
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
    
    def ejecutar_proceso_completo(self) -> Dict[str, Any]:
        """Ejecuta la secuencia completa de procesamiento"""
        print("🚀 INICIANDO PROCESO COMPLETO DE PROCESAMIENTO DE DOCUMENTOS")
        print(f"Fecha y hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Carpeta de entrada: {os.path.abspath(self.carpeta_entrada)}")
        print(f"Carpeta de salida: {os.path.abspath(self.carpeta_salida)}")
        
        # Verificar estructura de carpetas
        if not self.verificar_estructura_carpetas():
            print("❌ Error en la verificación de carpetas. Proceso cancelado.")
            return {'exitoso': False, 'error': 'Error en estructura de carpetas'}
        
        # Ejecutar cada paso
        print("\n🔄 Iniciando secuencia de procesamiento optimizada...")
        
        # Paso 1: Descomprimir
        self.resultados_globales['descompresion'] = self.paso_1_descomprimir()
        
        # Paso 2: Extraer datos (ahora antes de renombrar para eficiencia)
        print("\n🎯 EXTRAYENDO DATOS PRIMERO (para usar en renombrado)")
        self.resultados_globales['extraccion'] = self.paso_3_extraer_datos()
        
        # Paso 3: Renombrar usando datos ya extraídos
        if self.resultados_globales['extraccion'].get('exitoso'):
            print("\n🔄 RENOMBRANDO USANDO DATOS YA EXTRAÍDOS")
            self.resultados_globales['renombrado'] = self.paso_2_renombrar(self.resultados_globales['extraccion'])
        else:
            print("\n⚠️  No se pudieron extraer datos, intentando renombrado tradicional")
            self.resultados_globales['renombrado'] = self.paso_2_renombrar()
        
        # Resumen final
        self.mostrar_resumen_final()
        
        # Guardar reporte global
        self.guardar_reporte_global()
        
        return self.resultados_globales
    
    def mostrar_resumen_final(self):
        """Muestra un resumen final de todo el proceso"""
        print("\n" + "="*80)
        print("📋 RESUMEN FINAL DEL PROCESO COMPLETO")
        print("="*80)
        
        # Descompresión
        descomp = self.resultados_globales['descompresion']
        if descomp.get('exitoso'):
            print(f"✅ Descompresión: {descomp.get('archivos_extraidos', 0)} archivos extraídos")
        else:
            print(f"❌ Descompresión: {descomp.get('error', 'Error desconocido')}")
        
        # Renombrado
        renomb = self.resultados_globales['renombrado']
        if renomb.get('archivos_renombrados', 0) > 0:
            print(f"✅ Renombrado: {renomb.get('archivos_renombrados', 0)} archivos renombrados")
        else:
            print(f"ℹ️  Renombrado: {renomb.get('mensaje', 'No se procesaron archivos')}")
        
        # Extracción
        extra = self.resultados_globales['extraccion']
        if extra.get('exitoso'):
            print(f"✅ Extracción: {extra.get('total_registros', 0)} registros extraídos")
            if extra.get('archivo_salida'):
                print(f"📁 Archivo de salida: {extra['archivo_salida']}")
        else:
            print(f"❌ Extracción: {extra.get('error', extra.get('mensaje', 'Error desconocido'))}")
        
        # Errores globales
        if self.resultados_globales['errores']:
            print(f"\n⚠️  Errores encontrados: {len(self.resultados_globales['errores'])}")
            for error in self.resultados_globales['errores']:
                print(f"   - {error}")
        
        print("="*80)
        print(f"🎉 Proceso completado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
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
            print(f"\n📊 Reporte global guardado en: {archivo_reporte}")
            
        except Exception as e:
            logger.error(f"Error guardando reporte global: {e}")

def main():
    """Función principal"""
    print("🎯 PROCESADOR PRINCIPAL DE DOCUMENTOS FINANCIEROS (OPTIMIZADO)")
    print("Este programa ejecuta la secuencia completa de procesamiento:")
    print("  1. Descomprimir archivos ZIP")
    print("  2. Extraer datos de los PDF (con Gemini fallback si es necesario)")
    print("  3. Renombrar archivos PDF usando datos ya extraídos")
    print("\n✨ Optimización: Los datos se extraen solo UNA VEZ y se reutilizan")
    print()
    
    # Confirmar ejecución - automático para ejecución desde GUI
    print("🚀 Iniciando ejecución automática del proceso completo...")
    
    # Crear y ejecutar procesador
    procesador = MainProcesador()
    resultados = procesador.ejecutar_proceso_completo()
    
    print("\n🏁 Programa finalizado. Revise los reportes en la carpeta Salida.")

if __name__ == "__main__":
    main()
