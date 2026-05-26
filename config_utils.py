import json
import os
from typing import Dict, Any

class ConfigManager:
    _instance = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            config_path = os.path.join(os.path.dirname(__file__), 'config.json')
            with open(config_path, 'r') as config_file:
                cls._config = json.load(config_file)
        return cls._instance
    
    def get_database_config(self) -> Dict[str, Any]:
        """Obtiene la configuración de la base de datos."""
        return self._config['database']
    
    def get_paths(self) -> Dict[str, str]:
        """Obtiene las rutas base de los archivos."""
        return self._config['paths']
    
    def get_file_config(self, file_type: str) -> Dict[str, str]:
        """Obtiene la configuración para un tipo de archivo específico."""
        return self._config['archivos'].get(file_type, {})
    
    def get_gemini_api_key(self) -> str:
        """Obtiene la API Key de Gemini."""
        return self._config.get('gemini', {}).get('api_key', '')
    
    def get_file_path(self, file_type: str) -> str:
        """Genera la ruta completa para un archivo basado en su tipo y la fecha actual."""
        import time
        from datetime import datetime
        
        # Obtener la fecha actual
        now = datetime.now()
        aaaa = now.strftime("%Y")
        mm = now.strftime("%m")
        dd = now.strftime("%d")
        
        # Obtener configuraciones
        paths = self.get_paths()
        file_config = self.get_file_config(file_type)
        
        # Construir la ruta del archivo
        file_name = f"{file_config['nombre']}_{aaaa}_{mm}_{dd}{file_config['extension']}"
        full_path = os.path.join(
            paths['directorioBase'],
            f"{aaaa}_{mm}",
            f"{aaaa}_{mm}_{dd}",
            paths['carpeta'],
            file_name
        )
        
        return full_path

# Instancia global para facilitar el acceso
config_manager = ConfigManager()
