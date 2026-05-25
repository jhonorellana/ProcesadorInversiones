"""
Programa para descomprimir archivos ZIP de la carpeta Entrada
Extrae todos los archivos PDF y otros documentos al mismo directorio
"""
import os
import zipfile
import logging
from datetime import datetime
from typing import List, Dict

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Unzipper:
    """Clase para descomprimir archivos ZIP"""
    
    def __init__(self, carpeta_entrada="../Entrada"):
        self.carpeta_entrada = carpeta_entrada
        self.archivos_procesados = []
        self.errores = []
    
    def listar_archivos_zip(self) -> List[str]:
        """Lista todos los archivos ZIP en la carpeta de entrada"""
        archivos_zip = []
        
        if not os.path.exists(self.carpeta_entrada):
            logger.error(f"No existe la carpeta: {self.carpeta_entrada}")
            return archivos_zip
        
        for archivo in os.listdir(self.carpeta_entrada):
            if archivo.lower().endswith('.zip'):
                archivos_zip.append(archivo)
        
        return archivos_zip
    
    def descomprimir_archivo(self, ruta_zip: str) -> Dict[str, any]:
        """Descomprime un archivo ZIP específico"""
        resultado = {
            'archivo_zip': os.path.basename(ruta_zip),
            'archivos_extraidos': [],
            'errores': [],
            'exitoso': False
        }
        
        try:
            with zipfile.ZipFile(ruta_zip, 'r') as zip_ref:
                # Obtener lista de archivos
                lista_archivos = zip_ref.namelist()
                logger.info(f"Archivos en {os.path.basename(ruta_zip)}: {len(lista_archivos)}")
                
                # Extraer cada archivo (manejar carpetas anidadas)
                for archivo_zip in lista_archivos:
                    try:
                        # Ignorar directorios (terminan con /)
                        if archivo_zip.endswith('/'):
                            logger.info(f"Omitiendo directorio: {archivo_zip}")
                            continue
                        
                        # Obtener nombre base del archivo (sin ruta de carpetas anidadas)
                        nombre_base = os.path.basename(archivo_zip)
                        
                        # Si no tiene nombre base (archivo en raíz), usar el nombre completo
                        if not nombre_base:
                            nombre_base = archivo_zip.replace('/', '_').replace('\\', '_')
                        
                        # Ruta completa del archivo extraído
                        ruta_extraida = os.path.join(self.carpeta_entrada, nombre_base)
                        
                        # Evitar sobreescribir si ya existe
                        contador = 1
                        ruta_original = ruta_extraida
                        while os.path.exists(ruta_extraida):
                            # Agregar sufijo numérico si ya existe
                            nombre_base_sin_ext, extension = os.path.splitext(nombre_base)
                            ruta_extraida = os.path.join(self.carpeta_entrada, f"{nombre_base_sin_ext}_{contador}{extension}")
                            contador += 1
                        
                        # Extraer el archivo
                        with zip_ref.open(archivo_zip) as source:
                            with open(ruta_extraida, 'wb') as target:
                                target.write(source.read())
                        
                        # Determinar si es un archivo PDF para estadísticas
                        es_pdf = nombre_base.lower().endswith('.pdf')
                        
                        resultado['archivos_extraidos'].append({
                            'nombre_original': archivo_zip,
                            'ruta_extraida': ruta_extraida,
                            'tamaño': os.path.getsize(ruta_extraida),
                            'es_pdf': es_pdf,
                            'carpeta_original': os.path.dirname(archivo_zip) if os.path.dirname(archivo_zip) else 'raíz'
                        })
                        
                        logger.info(f"Extraído: {archivo_zip} -> {os.path.basename(ruta_extraida)}")
                        
                    except Exception as e:
                        error_msg = f"Error extrayendo {archivo_zip}: {str(e)}"
                        resultado['errores'].append(error_msg)
                        logger.error(error_msg)
                
                resultado['exitoso'] = len(resultado['errores']) == 0
                
        except Exception as e:
            error_msg = f"Error procesando ZIP {os.path.basename(ruta_zip)}: {str(e)}"
            resultado['errores'].append(error_msg)
            logger.error(error_msg)
        
        return resultado
    
    def descomprimir_todos(self) -> Dict[str, any]:
        """Descomprime todos los archivos ZIP de la carpeta"""
        logger.info(f"Iniciando descompresión en: {self.carpeta_entrada}")
        
        # Listar archivos ZIP
        archivos_zip = self.listar_archivos_zip()
        
        if not archivos_zip:
            logger.info("No se encontraron archivos ZIP para procesar")
            return {
                'total_zip': 0,
                'procesados': 0,
                'archivos_extraidos': 0,
                'errores': 0,
                'detalles': []
            }
        
        logger.info(f"Se encontraron {len(archivos_zip)} archivos ZIP:")
        for archivo in archivos_zip:
            logger.info(f"  - {archivo}")
        
        # Procesar cada archivo ZIP
        resultados_totales = {
            'total_zip': len(archivos_zip),
            'procesados': 0,
            'archivos_extraidos': 0,
            'errores': 0,
            'detalles': []
        }
        
        for archivo_zip in archivos_zip:
            ruta_completa = os.path.join(self.carpeta_entrada, archivo_zip)
            logger.info(f"\nProcesando: {archivo_zip}")
            
            resultado = self.descomprimir_archivo(ruta_completa)
            resultados_totales['detalles'].append(resultado)
            
            if resultado['exitoso']:
                resultados_totales['procesados'] += 1
                resultados_totales['archivos_extraidos'] += len(resultado['archivos_extraidos'])
            else:
                resultados_totales['errores'] += 1
        
        return resultados_totales
    
    def mostrar_resumen(self, resultados: Dict[str, any]):
        """Muestra un resumen del proceso de descompresión"""
        print("\n" + "="*60)
        print("RESUMEN DEL PROCESO DE DESCOMPRESIÓN")
        print("="*60)
        print(f"Total archivos ZIP encontrados: {resultados['total_zip']}")
        print(f"Archivos ZIP procesados: {resultados['procesados']}")
        print(f"Total archivos extraídos: {resultados['archivos_extraidos']}")
        print(f"Errores: {resultados['errores']}")
        
        if resultados['detalles']:
            print(f"\n📁 DETALLES POR ARCHIVO:")
            for detalle in resultados['detalles']:
                print(f"\n📦 {detalle['archivo_zip']}")
                if detalle['exitoso']:
                    archivos_extraidos = detalle['archivos_extraidos']
                    pdfs_extraidos = [a for a in archivos_extraidos if a.get('es_pdf', False)]
                    otros_archivos = [a for a in archivos_extraidos if not a.get('es_pdf', False)]
                    
                    print(f"   ✅ Extraídos: {len(archivos_extraidos)} archivos totales")
                    print(f"      📄 PDFs: {len(pdfs_extraidos)}")
                    print(f"      📎 Otros: {len(otros_archivos)}")
                    
                    # Mostrar carpetas anidadas encontradas
                    carpetas_origen = set(a.get('carpeta_original', 'raíz') for a in archivos_extraidos)
                    if len(carpetas_origen) > 1 or 'raíz' not in carpetas_origen:
                        print(f"      📂 Carpetas anidadas: {', '.join(sorted(carpetas_origen))}")
                    
                    # Mostrar primeros archivos
                    print(f"      Archivos extraídos:")
                    for i, archivo in enumerate(archivos_extraidos[:5]):
                        carpeta_icon = "📁" if archivo.get('carpeta_original', 'raíz') != 'raíz' else "📄"
                        print(f"         {i+1}. {carpeta_icon} {archivo['nombre_original']} ({archivo['tamaño']} bytes)")
                    
                    if len(archivos_extraidos) > 5:
                        print(f"         ... y {len(archivos_extraidos) - 5} archivos más")
                else:
                    print(f"   ❌ Error en extracción")
                    for error in detalle['errores']:
                        print(f"      - {error}")
        
        print("="*60)
    
    def guardar_reporte(self, resultados: Dict[str, any], nombre_archivo: str = None):
        """Guarda un reporte del proceso de descompresión"""
        if not nombre_archivo:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            nombre_archivo = f"../Salida/reporte_descompresion_{timestamp}.json"
        
        try:
            os.makedirs("../Salida", exist_ok=True)
            import json
            with open(nombre_archivo, 'w', encoding='utf-8') as f:
                json.dump(resultados, f, indent=2, ensure_ascii=False)
            logger.info(f"Reporte guardado en: {nombre_archivo}")
        except Exception as e:
            logger.error(f"Error guardando reporte: {e}")

def main():
    """Función principal"""
    print("🗂️  DESCOMPRESOR DE ARCHIVOS ZIP")
    print("Este programa descomprime todos los archivos ZIP de la carpeta Entrada")
    print("Los archivos extraídos se guardan en la misma carpeta Entrada")
    print()
    
    # Crear descompresor
    unzipper = Unzipper()
    
    # Mostrar archivos ZIP que se procesarán
    archivos_zip = unzipper.listar_archivos_zip()
    
    if not archivos_zip:
        print("❌ No se encontraron archivos ZIP en la carpeta Entrada")
        return
    
    print(f"Se encontraron {len(archivos_zip)} archivos ZIP:")
    for i, archivo in enumerate(sorted(archivos_zip), 1):
        ruta_completa = os.path.join(unzipper.carpeta_entrada, archivo)
        tamaño = os.path.getsize(ruta_completa)
        print(f"  {i}. {archivo} ({tamaño:,} bytes)")
    
    print()
    
    # Confirmar operación
    confirmacion = input("¿Desea continuar con la descompresión? (S/N): ").strip().upper()
    if confirmacion != 'S':
        print("Operación cancelada.")
        return
    
    # Procesar descompresión
    print(f"\n🔄 Iniciando descompresión...")
    resultados = unzipper.descomprimir_todos()
    
    # Mostrar resumen y guardar reporte
    unzipper.mostrar_resumen(resultados)
    unzipper.guardar_reporte(resultados)
    
    print(f"\n🎉 Proceso completado. Revise la carpeta Entrada y el reporte en Salida.")

if __name__ == "__main__":
    main()
