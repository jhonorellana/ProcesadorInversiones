import os
import re
import logging
from datetime import datetime
from typing import Dict, Any
from PDFExtractor_BVQ import PDFExtractor_BVQ

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RenombrarArchivosBVQ:
    """Clase para renombrar archivos PDF de liquidaciones de Bolsa de Valores de Quito"""
    
    def __init__(self):
        self.extractor = PDFExtractor_BVQ()
    
    def extraer_datos_renombrado(self, ruta_pdf: str) -> Dict[str, str]:
        """Extrae los datos necesarios para el renombrado: operacion_no y valor_nominal"""
        try:
            # Procesar el PDF para obtener todos los datos
            datos_completos = self.extractor.procesar_pdf(ruta_pdf)
            
            if not datos_completos or datos_completos.get('tipo_documento') == 'DESCONOCIDO':
                logger.warning(f"No se pudieron extraer datos del archivo: {ruta_pdf}")
                return {'operacion_no': '', 'valor_nominal': ''}
            
            # Extraer y limpiar los campos necesarios
            operacion_no = datos_completos.get('operacion_no', '').strip()
            valor_nominal = datos_completos.get('valor_nominal', '').strip()
            
            # Limpiar el valor_nominal para el nombre de archivo
            if valor_nominal:
                # Eliminar caracteres problemáticos para nombres de archivo
                valor_nominal = valor_nominal.replace('$', '').replace(',', '.')
                # Eliminar puntos adicionales (ej: 2.457.00 -> 2457.00)
                valor_nominal = re.sub(r'\.(\d{3})\.', r'\1.', valor_nominal)
            
            return {
                'operacion_no': operacion_no,
                'valor_nominal': valor_nominal
            }
            
        except Exception as e:
            logger.error(f"Error al extraer datos de {ruta_pdf}: {e}")
            return {'operacion_no': '', 'valor_nominal': ''}
    
    def generar_nuevo_nombre(self, nombre_original: str, operacion_no: str, valor_nominal: str) -> str:
        """Genera el nuevo nombre del archivo con el formato solicitado"""
        if not operacion_no or not valor_nominal:
            return nombre_original
        
        # Separar el nombre del archivo de la extensión
        nombre_base, extension = os.path.splitext(nombre_original)
        
        # Limpiar los valores para el nombre de archivo
        operacion_no_limpio = re.sub(r'[^\w\-]', '_', operacion_no)
        valor_nominal_limpio = re.sub(r'[^\w\.\-]', '_', valor_nominal)
        
        # Generar nuevo nombre: original_operacion_no_valor_nominal.pdf
        nuevo_nombre = f"{nombre_base}_{operacion_no_limpio}_{valor_nominal_limpio}{extension}"
        
        return nuevo_nombre
    
    def renombrar_archivo(self, ruta_original: str, operacion_no: str, valor_nominal: str) -> bool:
        """Renombra un archivo individual"""
        try:
            if not operacion_no or not valor_nominal:
                logger.warning(f"No se puede renombrar {ruta_original}: faltan datos de operación o valor nominal")
                return False
            
            nombre_original = os.path.basename(ruta_original)
            nuevo_nombre = self.generar_nuevo_nombre(nombre_original, operacion_no, valor_nominal)
            
            if nuevo_nombre == nombre_original:
                logger.info(f"El nombre no cambió para: {nombre_original}")
                return True
            
            ruta_nueva = os.path.join(os.path.dirname(ruta_original), nuevo_nombre)
            
            # Verificar si el nuevo archivo ya existe
            if os.path.exists(ruta_nueva):
                logger.warning(f"El archivo de destino ya existe: {nuevo_nombre}")
                return False
            
            # Renombrar el archivo
            os.rename(ruta_original, ruta_nueva)
            logger.info(f"Renombrado: {nombre_original} -> {nuevo_nombre}")
            return True
            
        except Exception as e:
            logger.error(f"Error al renombrar archivo {ruta_original}: {e}")
            return False
    
    def procesar_carpeta(self, ruta_carpeta: str) -> Dict[str, Any]:
        """Procesa todos los archivos PDF en la carpeta especificada"""
        resultados = {
            'total_archivos': 0,
            'renombrados': 0,
            'errores': 0,
            'detalles': []
        }
        
        if not os.path.exists(ruta_carpeta):
            logger.error(f"La carpeta no existe: {ruta_carpeta}")
            return resultados
        
        logger.info(f"Procesando archivos en la carpeta: {ruta_carpeta}")
        
        # Obtener lista de archivos PDF
        archivos_pdf = [f for f in os.listdir(ruta_carpeta) if f.lower().endswith('.pdf')]
        resultados['total_archivos'] = len(archivos_pdf)
        
        for archivo in archivos_pdf:
            ruta_completa = os.path.join(ruta_carpeta, archivo)
            
            # Extraer datos para el renombrado
            datos = self.extraer_datos_renombrado(ruta_completa)
            operacion_no = datos['operacion_no']
            valor_nominal = datos['valor_nominal']
            
            # Intentar renombrar
            exito = self.renombrar_archivo(ruta_completa, operacion_no, valor_nominal)
            
            # Registrar resultado
            resultado_detalle = {
                'archivo_original': archivo,
                'operacion_no': operacion_no,
                'valor_nominal': valor_nominal,
                'renombrado': exito
            }
            
            if exito:
                resultados['renombrados'] += 1
            else:
                resultados['errores'] += 1
            
            resultados['detalles'].append(resultado_detalle)
        
        return resultados
    
    def guardar_reporte(self, resultados: Dict[str, Any], archivo_reporte: str):
        """Guarda un reporte del proceso de renombrado en formato JSON"""
        try:
            import json
            with open(archivo_reporte, 'w', encoding='utf-8') as f:
                json.dump(resultados, f, indent=2, ensure_ascii=False)
            logger.info(f"Reporte guardado en: {archivo_reporte}")
        except Exception as e:
            logger.error(f"Error al guardar reporte: {e}")

def main():
    """Función principal"""
    import os
    
    renombrador = RenombrarArchivosBVQ()
    
    # Carpeta de entrada
    carpeta_entrada = "Entrada_BVQ"
    
    if not os.path.exists(carpeta_entrada):
        logger.error(f"No existe la carpeta: {carpeta_entrada}")
        return
    
    print("=" * 60)
    print("RENOMBRADO DE ARCHIVOS PDF - BOLSA DE VALORES DE QUITO")
    print("=" * 60)
    print(f"Carpeta de origen: {carpeta_entrada}")
    print(f"Formato de renombrado: nombre_original_[operacion_no]_[valor_nominal].pdf")
    print()
    
    # Mostrar archivos antes del renombrado
    print("ARCHIVOS ANTES DEL RENOMBRADO:")
    archivos = [f for f in os.listdir(carpeta_entrada) if f.lower().endswith('.pdf')]
    for i, archivo in enumerate(sorted(archivos), 1):
        print(f"  {i}. {archivo}")
    
    print()
    print("¿Desea continuar con el renombrado? (S/N): ", end="")
    
    # Leer respuesta del usuario
    try:
        respuesta = input().strip().upper()
        if respuesta != 'S':
            print("Operación cancelada por el usuario.")
            return
    except KeyboardInterrupt:
        print("\nOperación cancelada por el usuario.")
        return
    
    print("\nIniciando proceso de renombrado...")
    print("-" * 60)
    
    # Procesar la carpeta
    resultados = renombrador.procesar_carpeta(carpeta_entrada)
    
    # Mostrar resultados
    print("\n" + "=" * 60)
    print("RESUMEN DEL PROCESO DE RENOMBRADO")
    print("=" * 60)
    print(f"Total archivos encontrados: {resultados['total_archivos']}")
    print(f"Archivos renombrados: {resultados['renombrados']}")
    print(f"Errores: {resultados['errores']}")
    
    if resultados['renombrados'] > 0:
        print("\n✅ ARCHIVOS RENOMBRADOS EXITOSAMENTE:")
        for detalle in resultados['detalles']:
            if detalle['renombrado']:
                nombre_original = detalle['archivo_original']
                operacion_no = detalle['operacion_no']
                valor_nominal = detalle['valor_nominal']
                
                # Generar el nuevo nombre para mostrar
                renombrador = RenombrarArchivosBVQ()
                nuevo_nombre = renombrador.generar_nuevo_nombre(nombre_original, operacion_no, valor_nominal)
                
                print(f"   {nombre_original} -> {nuevo_nombre}")
    
    if resultados['errores'] > 0:
        print("\n❌ ERRORES:")
        for detalle in resultados['detalles']:
            if not detalle['renombrado']:
                print(f"   {detalle['archivo_original']} (Operación: {detalle['operacion_no']}, Valor: {detalle['valor_nominal']})")
    
    # Guardar reporte
    os.makedirs("Salida_BVQ", exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    archivo_reporte = f"Salida_BVQ/reporte_renombrado_bvq_{timestamp}.json"
    renombrador.guardar_reporte(resultados, archivo_reporte)
    
    print(f"\n🎉 Proceso completado. Revise la carpeta {carpeta_entrada} y el reporte en Salida_BVQ.")

if __name__ == "__main__":
    main()
