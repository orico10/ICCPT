import os
import platform
from src import config

class Utils:
    @staticmethod
    def get_base_path():
        """Obtain the base path according to the operating system."""

        # Forzar el uso de la carpeta inputs
        base_path = os.path.join(config["path"]["inputs"])

        
        
        if not os.path.isdir(base_path):
            raise ValueError(f"La ruta base '{base_path}' no es válida o no existe.")
        return base_path
    


    @staticmethod
    def validate_float(value):
        """Validate if a value is a valid float."""
        try:
            return float(value)
        except ValueError:
            raise ValueError(f"The value '{value}' is not a valid float.")

    @staticmethod
    def validate_integer(value):
        """Validate if a value is a valid integer."""
        try:
            return int(value)
        except ValueError:
            raise ValueError(f"The value '{value}' is not a valid integer.")

    @staticmethod
    def validate_path(root_path):
        """Validate if a path is valid and exists."""
        if not os.path.isdir(root_path):
            raise ValueError(f"The root path '{root_path}' is not valid or does not exist.")
        return root_path



    @staticmethod
    def validate_file_path(root_path, file_name):
        """Validate if a file exists in the provided path."""
        full_path = os.path.join(root_path, file_name)
        if not os.path.isfile(full_path):
            raise ValueError(f"The file '{full_path}' does not exist.")
        return full_path


