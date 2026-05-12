import os
import logging
import pandas as pd
import csv 

class BaseFileLoader:
    def __init__(self, file_path):
        self.file_path = file_path
        self.data = None
    
    def validate_file(self):
        """Valida si el archivo existe y es accesible."""
        if not os.path.isfile(self.file_path):
            raise FileNotFoundError(f"El archivo '{self.file_path}' no existe.")
        logging.info(f"Archivo encontrado: {self.file_path}")

    
    def load_file(self):
        """Load a tsv text input file."""
        try:
            self.validate_file()
            
            delimiter = '\t'
            
            preprocessed_file = self.file_path

            # Cargar el archivo preprocesado
            self.data = pd.read_csv(
                preprocessed_file,
                sep = delimiter,
                #skiprows=2,  # Omitir las dos líneas iniciales de momento vamos sin ello 
                encoding="utf-8", 
                engine="python",  # Especifica explícitamente el motor 'python'
                skipinitialspace=True,  # Elimina espacios iniciales en cada columna automáticamente
                decimal="."  # Especifica el separador decimal
            )
            # Limpiar los espacios iniciales y finales de los valores y nombres de columnas
            self.data.columns = self.data.columns.str.strip()  # Limpiar espacios iniciales y finales en los nombres de las columnas
            
            self.data = self.data.map(lambda x: x.strip() if isinstance(x, str) else x)
            # self.data = self.data.applymap(
            #     lambda x: x.strip() if isinstance(x, str) else x
            # )

            logging.info(f"Archivo cargado correctamente: {self.file_path}")
        except Exception as e:
            logging.critical(f"Error loading file  {self.file_path}: {e}")
            raise

    def clean_data(self):
        """
        Cleans the DataFrame by removing NaN values, trimming whitespace, and correcting numbers.
        Also ensures that column names and data values are properly formatted.
        Additionally, removes columns with names containing 'Unnamed' and those completely empty.
        """
        try:
            if self.data is not None:
                # Paso 1: Limpiar los nombres de las columnas
                self.data.columns = (
                    self.data.columns.str.strip()  # Elimina espacios al inicio y al final
                    .str.replace(r"[\u200b-\u200d\uFEFF]", "", regex=True)  # Elimina caracteres invisibles
                )
                
                # Paso 2: Eliminar columnas cuyo nombre contenga "Unnamed"
                cols_to_drop = [col for col in self.data.columns if "Unnamed" in col]
                if cols_to_drop:
                    self.data.drop(columns=cols_to_drop, inplace=True)
                
                # Paso 3: Eliminar columnas que estén completamente vacías (solo NaN)
                self.data.dropna(axis=1, how="all", inplace=True)
                
                # Paso 4: Eliminar filas completamente vacías
                self.data.dropna(axis=0, how="all", inplace=True)
                
                # Paso 5: Limpiar los valores dentro del DataFrame (eliminar espacios en strings)
                self.data = self.data.map(lambda x: x.strip() if isinstance(x, str) else x)
                #self.data = self.data.applymap(lambda x: x.strip() if isinstance(x, str) else x)
                
                # Opcional: Resetear el índice si lo deseas
                self.data.reset_index(drop=True, inplace=True)
            else:
                logging.warning("El DataFrame está vacío o no ha sido cargado. No se realizaron operaciones.")
        except Exception as e:
            logging.error(f"Error al limpiar los datos: {e}", exc_info=True)
            raise





    def correct_numeric_format(self, decimal_format=",", decimal_replace="."):
        """Corrects numeric formats in the DataFrame, replacing specified decimal formats."""
        if self.data is not None:
            for col in self.data.columns:
                if self.data[col].dtype == "object":
                    if self.data[col].str.contains(decimal_format, na=False).any():
                        try:
                            self.data[col] = (
                                self.data[col]
                                .str.replace(decimal_format, decimal_replace)
                                .str.replace(r"[^\d\.\-]", "", regex=True)
                                .astype(float)
                            )
                            logging.info(f"Columna '{col}' corregida al formato numérico.")
                        except ValueError:
                            logging.warning(f"No se pudo convertir la columna '{col}' a numérica. Revisar valores.")
        else:
            logging.warning("The DataFrame is empty or has not been loaded. No corrections were made.")

    

