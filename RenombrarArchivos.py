"""
Programa para renombrar archivos PDF de la carpeta Entrada
Agrega el número de operación al final del nombre del archivo
"""
import os
import json
from PDFExtractor_BVG import PDFExtractor
import logging

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RenombradorArchivos:
    """Clase para renombrar archivos PDF basados en el número de operación"""
    
    def __init__(self, carpeta_entrada="../Entrada"):
        self.extractor = PDFExtractor()
        self.carpeta_entrada = carpeta_entrada
        self.archivos_procesados = []
        self.errores = []
    
    def extraer_numero_operacion(self, ruta_pdf: str) -> str:
        """Extrae el número de operación de un archivo PDF"""
        try:
            resultado = self.extractor.procesar_pdf(ruta_pdf)
            operacion_no = resultado.get('operacion_no', '')
            
            # Para Bonos del Estado, si no hay operación, generar un ID basado en el título
            if not operacion_no and resultado.get('tipo_documento') == 'BONO_ESTADO':
                titulo = resultado.get('titulo_valor', '')
                if 'BONO DEL ESTADO' in titulo:
                    # Extraer código del título si existe
                    import re
                    match = re.search(r'CDF-RES-(\d+)', titulo)
                    if match:
                        operacion_no = f"BONO-{match.group(1)}"
                    else:
                        operacion_no = "BONO-ESTADO"
            
            if operacion_no and operacion_no.strip():
                return operacion_no.strip()
            else:
                logger.warning(f"No se encontró número de operación en: {os.path.basename(ruta_pdf)}")
                return ""
                
        except Exception as e:
            logger.error(f"Error extrayendo operación de {os.path.basename(ruta_pdf)}: {e}")
            return ""
    
    def extraer_valor_nominal(self, ruta_pdf: str) -> str:
        """Extrae el valor nominal de un archivo PDF"""
        try:
            resultado = self.extractor.procesar_pdf(ruta_pdf)
            valor_nominal = resultado.get('valor_nominal', '')
            
            # Para Bonos del Estado, usar valor efectivo si no hay valor nominal
            if not valor_nominal and resultado.get('tipo_documento') == 'BONO_ESTADO':
                valor_efectivo = resultado.get('valor_efectivo', '')
                if valor_efectivo:
                    valor_nominal = valor_efectivo
                    logger.info(f"Bono del Estado: usando valor efectivo como valor nominal: {valor_efectivo}")
            
            if valor_nominal and valor_nominal.strip():
                return valor_nominal.strip()
            else:
                logger.warning(f"No se encontró valor nominal en: {os.path.basename(ruta_pdf)}")
                return ""
                
        except Exception as e:
            logger.error(f"Error extrayendo valor nominal de {os.path.basename(ruta_pdf)}: {e}")
            return ""
    
    def renombrar_archivo(self, ruta_original: str, operacion_no: str, valor_nominal: str) -> bool:
        """Renombra un archivo PDF agregando número de operación y valor nominal"""
        try:
            # Obtener información del archivo original
            directorio = os.path.dirname(ruta_original)
            nombre_base, extension = os.path.splitext(os.path.basename(ruta_original))
            
            # Limpiar el valor nominal (quitar $ y espacios)
            valor_nominal_limpio = valor_nominal.replace('$', '').replace(',', '').strip()
            
            # Limpiar el número de operación (reemplazar caracteres problemáticos)
            operacion_no_limpio = operacion_no.replace('/', '-').replace('\\', '-').replace(':', '-')
            
            # Crear nuevo nombre: nombre_original_operacion_no_valor_nominal.pdf
            nuevo_nombre = f"{nombre_base}_{operacion_no_limpio}_{valor_nominal_limpio}{extension}"
            ruta_nueva = os.path.join(directorio, nuevo_nombre)
            
            # Verificar si el nuevo nombre ya existe
            if os.path.exists(ruta_nueva):
                logger.warning(f"El archivo ya existe: {nuevo_nombre}")
                return False
            
            # Renombrar el archivo
            os.rename(ruta_original, ruta_nueva)
            
            # Guardar información del cambio
            self.archivos_procesados.append({
                'nombre_original': os.path.basename(ruta_original),
                'nombre_nuevo': nuevo_nombre,
                'operacion_no': operacion_no,
                'valor_nominal': valor_nominal,
                'ruta_original': ruta_original,
                'ruta_nueva': ruta_nueva
            })
            
            logger.info(f"Renombrado: {os.path.basename(ruta_original)} -> {nuevo_nombre}")
            return True
            
        except Exception as e:
            logger.error(f"Error renombrando {os.path.basename(ruta_original)}: {e}")
            self.errores.append({
                'archivo': os.path.basename(ruta_original),
                'error': str(e)
            })
            return False
    
    def procesar_carpeta(self) -> dict:
        """Procesa todos los archivos PDF de la carpeta de entrada"""
        archivos_pdf = []
        
        for archivo in os.listdir(self.carpeta_entrada):
            if archivo.lower().endswith('.pdf'):
                archivos_pdf.append(archivo)
        
        logger.info(f"Se encontraron {len(archivos_pdf)} archivos PDF")
        
        return self.procesar_lista_archivos(archivos_pdf)
    
    def procesar_lista_archivos(self, archivos_pdf: list) -> dict:
        """Procesa una lista específica de archivos PDF"""
        logger.info(f"Procesando {len(archivos_pdf)} archivos PDF")
        
        # Procesar cada archivo
        for archivo in archivos_pdf:
            ruta_completa = os.path.join(self.carpeta_entrada, archivo)
            
            # Extraer número de operación y valor nominal
            operacion_no = self.extraer_numero_operacion(ruta_completa)
            valor_nominal = self.extraer_valor_nominal(ruta_completa)
            
            if operacion_no and valor_nominal:
                # Renombrar el archivo
                self.renombrar_archivo(ruta_completa, operacion_no, valor_nominal)
            else:
                error_msg = []
                if not operacion_no:
                    error_msg.append('No se encontró número de operación')
                if not valor_nominal:
                    error_msg.append('No se encontró valor nominal')
                
                logger.warning(f"No se pudo renombrar {archivo} - {'; '.join(error_msg)}")
                self.errores.append({
                    'archivo': archivo,
                    'error': '; '.join(error_msg)
                })
        
        return self.generar_resumen()
    
    def generar_resumen(self) -> dict:
        """Genera un resumen del proceso"""
        resumen = {
            'total_archivos': len(self.archivos_procesados) + len(self.errores),
            'archivos_renombrados': len(self.archivos_procesados),
            'errores': len(self.errores),
            'archivos_procesados': self.archivos_procesados,
            'errores_detalle': self.errores
        }
        
        return resumen
    
    def guardar_reporte(self, resumen: dict, nombre_archivo: str = None):
        """Guarda un reporte del proceso de renombrado"""
        if not nombre_archivo:
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            nombre_archivo = f"../Salida/reporte_renombrado_{timestamp}.json"
        
        try:
            os.makedirs("../Salida", exist_ok=True)
            with open(nombre_archivo, 'w', encoding='utf-8') as f:
                json.dump(resumen, f, indent=2, ensure_ascii=False)
            logger.info(f"Reporte guardado en: {nombre_archivo}")
        except Exception as e:
            logger.error(f"Error guardando reporte: {e}")
    
    def mostrar_resumen(self, resumen: dict):
        """Muestra un resumen del proceso"""
        print("\n" + "="*60)
        print("RESUMEN DEL PROCESO DE RENOMBRADO")
        print("="*60)
        print(f"Total archivos encontrados: {resumen['total_archivos']}")
        print(f"Archivos renombrados: {resumen['archivos_renombrados']}")
        print(f"Errores: {resumen['errores']}")
        
        if resumen['archivos_renombrados'] > 0:
            print(f"\n✅ ARCHIVOS RENOMBRADOS EXITOSAMENTE:")
            for archivo in resumen['archivos_procesados']:
                print(f"   {archivo['nombre_original']} -> {archivo['nombre_nuevo']}")
        
        if resumen['errores'] > 0:
            print(f"\n❌ ERRORES:")
            for error in resumen['errores_detalle']:
                print(f"   {error['archivo']}: {error['error']}")
        
        print("="*60)

def main():
    """Función principal"""
    print("🔄 RENOMBRADOR DE ARCHIVOS PDF MEJORADO")
    print("Este programa renombra los archivos PDF agregando número de operación y valor nominal")
    print("Soporta: Liquidaciones BVQ, Notas de Crédito, y Bonos del Estado")
    print("Formato: nombre_original_[operacion_no]_[valor_nominal].pdf")
    print("Ejemplo: 12.3. LIQUIDACION DE BOLSA_BONO-2024_3178052.pdf")
    print()
    
    # Seleccionar carpeta de entrada
    print("Carpetas disponibles:")
    print("1. Entrada (carpeta general)")
    print("2. Entrada_BVQ (Bolsa de Valores de Quito)")
    
    opcion = input("Seleccione la carpeta a procesar (1/2): ").strip()
    
    if opcion == "1":
        carpeta_entrada = "../Entrada"
    elif opcion == "2":
        carpeta_entrada = "../Entrada_BVQ"
    else:
        print("Opción no válida. Usando carpeta Entrada por defecto.")
        carpeta_entrada = "../Entrada"
    
    print(f"\nProcesando carpeta: {carpeta_entrada}")
    
    # Mostrar archivos que se procesarán
    if os.path.exists(carpeta_entrada):
        archivos_pdf = [f for f in os.listdir(carpeta_entrada) if f.lower().endswith('.pdf')]
        print(f"Se encontraron {len(archivos_pdf)} archivos PDF:")
        for i, archivo in enumerate(sorted(archivos_pdf)[:5], 1):
            print(f"  {i}. {archivo}")
        if len(archivos_pdf) > 5:
            print(f"  ... y {len(archivos_pdf) - 5} archivos más")
    else:
        print(f"❌ La carpeta {carpeta_entrada} no existe.")
        return
    
    print()
    
    # Confirmar operación
    confirmacion = input("¿Desea continuar con el renombrado? (S/N): ").strip().upper()
    if confirmacion != 'S':
        print("Operación cancelada.")
        return
    
    # Crear renombrador y procesar
    renombrador = RenombradorArchivos(carpeta_entrada)
    resumen = renombrador.procesar_carpeta()
    
    # Mostrar resumen y guardar reporte
    renombrador.mostrar_resumen(resumen)
    renombrador.guardar_reporte(resumen)
    
    print(f"\n🎉 Proceso completado. Revise la carpeta {carpeta_entrada} y el reporte en Salida.")

if __name__ == "__main__":
    main()
