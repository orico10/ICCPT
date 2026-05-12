from src.utils import Utils
from src.base_file_loader import BaseFileLoader
from src.log_handler import logging
import os
import pandas as pd


class RouteConfigurationLoader(BaseFileLoader):
    def __init__(self, csv_file_path):
        super().__init__(csv_file_path)
        self.resolved_files = {}

    def process_file(self):
        """
        Process and resolve the complete paths of the files.
        """
        try:
            base_path = Utils.get_base_path()

            # Clean the data
            self.clean_data()
            
            # Leer el archivo como texto
            with open(self.file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Verificar que hay suficientes líneas en el archivo
            if len(lines) < 2:
                raise ValueError("El archivo no contiene suficientes líneas para procesar.")

            # Dividir manualmente la cabecera (ahora en la primera línea) -- no hace falta 
            header = lines[0].strip().split('\t')

            # Verificar que las columnas requeridas están presentes
            required_columns = ["Description", "Folder", "File"]
            if not all(col in header for col in required_columns):
                raise ValueError(f"Missing required columns in header: {header}")

            # Cargar las filas reales a partir de la segunda línea
            data_rows = lines[1:]
            self.data = pd.DataFrame([row.strip().split('\t') for row in data_rows], columns=header)

            

            # Procesar las rutas
            for _, row in self.data.iterrows():
                name = row["Description"]
                folder = row["Folder"]
                file_name = row["File"]

                # Validar contenido de las columnas
                if not folder or not isinstance(folder, str):
                    logging.warning(f"Carpeta no válida para '{name}': {folder}")
                    continue

                if not file_name or not isinstance(file_name, str):
                    logging.warning(f"Archivo no válido para '{name}': {file_name}")
                    continue

                # Construir ruta completa usando la base y la carpeta del CSV
                full_path = os.path.join(base_path, folder)

                try:
                    # Validar que el folder existe
                    Utils.validate_path(full_path)

                    # Construir ruta completa del archivo
                    file_path = os.path.join(full_path, file_name).replace('\\', '/')

                    # Guardar ruta resuelta
                    self.resolved_files[name] = file_path
                    logging.info(f"Resolved path for '{name}': {file_path}")

                except ValueError as e:
                    logging.warning(f"Error processing '{name}': {e}")
                except Exception as e:
                    logging.error(f"Unexpected error processing '{name}': {e}")

        except Exception as e:
            logging.critical(f"Critical error processing routes: {e}")
            raise
