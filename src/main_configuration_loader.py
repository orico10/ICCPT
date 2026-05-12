from src.base_file_loader import BaseFileLoader
from src.utils import Utils  # Clase que contiene métodos de validación
import logging
import os
from src import config
import pandas as pd

from src.utils import Utils

class MainConfigurationLoader(BaseFileLoader):
    def __init__(self, file_path):
        super().__init__(file_path)
        self.general_data = {}

    def process_file(self):
        """
        Validates and processes the general configuration file.
        """
        try:

            # Limpiar los datos
            self.clean_data()
            # Leer el archivo como texto
            with open(self.file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Verificar que hay suficientes líneas en el archivo
            if len(lines) < 3:
                raise ValueError("El archivo no contiene suficientes líneas para procesar.")

            # Dividir manualmente la cabecera en la (ahora la primera linea)tercera línea
            header = lines[0].strip().split('\t')

            # Verificar que las columnas requeridas están presentes
            required_columns = ["Name", "Value", "Units"]
            if not all(col in header for col in required_columns):
                raise ValueError(f"Faltan columnas requeridas en la cabecera: {header}")

            # Cargar las filas reales a partir de la cuarta línea
            data_rows = lines[3:]
            self.data = pd.DataFrame([row.strip().split('\t') for row in data_rows], columns=header)

            

            # Procesar los datos en un diccionario
            processed_data = {}
            for _, row in self.data.iterrows():
                name = row["Name"]
                value = row["Value"]

                # Validar el valor antes de añadirlo al diccionario
                if name in ["Exchange_rate", "Labor_cost", "Diesel_cost", "Generation_CAPEX", "Generation_OPEX", 
                            "Transmission_TOTEX", "Distribution_TOTEX", "Emissions_rate", "Electric_demand", "Distributed_factor"]:
                    value = Utils.validate_float(value)
                #elif name in ["DemMult_E", "DemMult_C", "DemMult_H", "Frecuency", "WoodRawMaterial_Id", "Average_grid_lifetime"]:
                elif name in ["Frecuency", "WoodRawMaterial_Id", "Average_grid_lifetime", "Last_mile_distance"]:
                    try:
                        value = Utils.validate_integer(value)
                    except ValueError:
                        logging.warning(f"The value of {name} is not a valid integer: {value}. It will be assigned as is.")
                elif name in ["Electricity_adoption", "LPG_adoption", "Very_high_voltage",
                            "High_voltage", "Medium_voltage", "Low_voltage", "Power_losses_factor", "System_peak_load",
                            "Main_grid_reliability", "Diesel_emissions"]:
                    try:
                        value = Utils.validate_float(value)
                    except ValueError:
                        logging.warning(f"The value of {name} is not a valid float: {value}. It will be assigned as is.")

                # Manejar claves repetidas convirtiéndolas en listas
                if name in processed_data:
                    if not isinstance(processed_data[name], list):
                        processed_data[name] = [processed_data[name]]
                    processed_data[name].append(value)
                else:
                    processed_data[name] = value

                # Log de depuración para cada fila procesada
                logging.debug(f"Process: {name} = {processed_data[name]}")

            # Asignar los datos procesados al atributo general_data
            self.general_data = processed_data

            logging.info(f"General data processed successfully: {self.general_data}")

        except Exception as e:
            logging.error(f"Error processing general configuration file: {e}")
            raise



    def get_general_data(self):
        """Returns the processed general data as a dictionary."""
        if not self.general_data:
            raise ValueError("General data has not been processed. Call 'process_file' before accessing it.")
        return self.general_data
    
    #Devuelve algún valor según el nombre de data 
    def get(self, name):
        return self.general_data[name]


