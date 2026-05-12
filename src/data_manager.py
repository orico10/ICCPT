import os
import logging
import pandas as pd
from src.base_file_loader import BaseFileLoader

class DataManager:
    def __init__(self, route_configuration, config):
        self.route_configuration = route_configuration
        self.config = config  # Almacena la configuración general
        self.dataframes = {}
        self.relations = {}
        self.errors = []
        self.demand_areas = None  # Aquí se almacenarán las áreas de demanda

    def load_files(self):
        """Load all files using BaseFileLoader."""
        for name, file_path in self.route_configuration.resolved_files.items():
            try:
                loader = BaseFileLoader(file_path)
                loader.load_file()
                self.dataframes[name] = loader.data
                logging.info(f"File '{name}' loaded successfully.")
                # Limpiar datos cargados llamando a la función clean_data
                loader.clean_data()
                
            except FileNotFoundError as e:
                self.errors.append(str(e))
                logging.error(str(e))
            except Exception as e:
                error_msg = f"Error loading '{name}': {e}"
                self.errors.append(error_msg)
                logging.error(error_msg)

    def load_preprocessed_files(self, preprocess_path, available_files):
        """
        Load preprocessed files into the DataManager based on the available files.

        :param preprocess_path: Path where preprocessed files are located.
        :param available_files: List of available preprocessed files.
        """
        logging.info("Cargando archivos preprocesados en memoria...")
        

        for file_name in available_files:
            file_path = os.path.join(preprocess_path, file_name)
            file_loader = BaseFileLoader(file_path)
            try:
                # Leer el archivo usando BaseFileLoader
                file_loader.load_file()

                # Registrar el DataFrame en el DataManager
                self.dataframes[file_name.replace(".tsv", "")] = file_loader.data
                logging.info(f"File {file_name} loaded and registered in DataManager.")

                file_loader.clean_data()

                
            except Exception as e:
                logging.error(f"Error loading file {file_name}: {str(e)}")

        logging.info("All available preprocessed files have been loaded into memory.")




    def detect_relations(self):
        """Detect relationships between DataFrames based on the third header line."""
        headers = {}

        for name, df in self.dataframes.items():
            # Obtener nombres de columnas desde la tercera línea del archivo
            try:
                headers[name] = list(df.columns)
            except Exception as e:
                logging.error(f"Error al procesar cabecera de '{name}': {e}")

        # Identificar claves comunes y relaciones
        for key in set(header for cols in headers.values() for header in cols):
            involved_tables = [name for name, cols in headers.items() if key in cols]

            if len(involved_tables) > 1:
                for i, parent in enumerate(involved_tables):
                    for child in involved_tables[i + 1:]:
                        self.relations.setdefault((parent, child), []).append(key)
                        self._validate_relationship(parent, child, key)

    def _validate_relationship(self, parent_name, child_name, key):
        """Validate that ID values are present in both tables."""
        parent_ids = set(self.dataframes[parent_name][key].dropna().unique())
        child_ids = set(self.dataframes[child_name][key].dropna().unique())

        missing_in_parent = child_ids - parent_ids
        missing_in_child = parent_ids - child_ids

        
    
    def register_dataframe(self, name, dataframe):
        """
        Register a DataFrame in the DataManager with a specific name.

        :param name: The name to use for registering the DataFrame.
        :param dataframe: The DataFrame to be registered.
        """
        if not isinstance(name, str):
            raise TypeError("The name must be a string.")
        if not isinstance(dataframe, pd.DataFrame):
            raise TypeError("The dataframe must be a pandas DataFrame.")
        if name in self.dataframes:
            logging.warning(f"Overwriting existing DataFrame with name: {name}")
        self.dataframes[name] = dataframe
        logging.info(f"DataFrame '{name}' registered successfully.")

    


#--------Getters and Setters----------------    

    def get_relations(self):
        return self.relations

    

    def update_dataframe(self, name, new_dataframe):
        """Update a DataFrame in the internal storage."""
        if name in self.dataframes:
            logging.info(f"Updating DataFrame '{name}'.")
        else:
            logging.info(f"Adding new DataFrame '{name}'.")
        self.dataframes[name] = new_dataframe

    def get_config (self):
        return self.config
    
    def register_demand_areas(self, demand_areas):
        """
        Register demand areas in the DataManager.

        :param demand_areas: List of DemandArea objects.
        """
        self.demand_areas = demand_areas
        logging.info(f"{len(demand_areas)} demand areas registered in DataManager.")

    def get_dataframe(self, name):
        """
        Obtain a DataFrame from the DataManager.

        :param name: Name of the DataFrame to obtain.
        :return: Requested DataFrame.
        """
        if name not in self.dataframes:
            raise KeyError(f"DataFrame '{name}' not found in DataManager.")
        return self.dataframes[name]

    