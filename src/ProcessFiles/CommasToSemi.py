import pandas as pd

def convert_csv_delimiter(input_file_path, output_file_path):
    """
    Converts a CSV file with ',' delimiter to ';' delimiter.

    :param input_file_path: Path to the input CSV file.
    :param output_file_path: Path to save the output CSV file with ';' delimiter.
    """
    try:
        # Leer el archivo CSV original con ',' como delimitador
        df = pd.read_csv(input_file_path, sep=',')

        # Guardar el archivo CSV con ';' como delimitador
        df.to_csv(output_file_path, sep=';', index=False)

        print(f"File converted successfully: {output_file_path}")

    except Exception as e:
        print(f"Error converting file {input_file_path}: {e}")

# Ejemplo de uso
if __name__ == "__main__":
    # Rutas de los archivos
    input_csv = "C:\GIT\CleanCooking_os\data/Co0_routes_config.csv"
    output_csv = "C:\GIT\CleanCooking_os\data/Co0_routes_config_o.csv"

    # Llamar a la función
    convert_csv_delimiter(input_csv, output_csv)
