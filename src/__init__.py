"""
CleanCooking_os - Versión 1.0 - December 2024- Septermber 2025
Integrated clean cooking planning model

Developed por:
   Olga Rico Díez
   Instituto de Investigación Tecnológica (IIT)
   Escuela Técnica Superior de Ingeniería - ICAI
   Universidad Pontificia Comillas
   Alberto Aguilera 23
   28015 Madrid, Spain
   orico@comillas.edu
   https://www.iit.comillas.edu/personas/orico
"""



import yaml
import os
import sys

# Función para cargar config.yaml
def load_configuration():
    try:
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        
        
        ruta_config = os.path.abspath(os.path.join(base_dir, os.pardir, "config.yaml"))


        print(f"[INFO] Loading config from: {ruta_config}")  # debug clave

        with open(ruta_config, "r", encoding="utf-8") as archivo:
            return yaml.safe_load(archivo)

    except Exception as e:
        print(f"[ERROR] Fallo al cargar config.yaml: {e}")
        import traceback
        traceback.print_exc()
        input("Presiona Enter para cerrar...")
        sys.exit(1)



config = load_configuration()

# Exponer config como parte del paquete
__all__ = ["config"]
