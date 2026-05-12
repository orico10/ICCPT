import os
import pandas as pd
import logging
import csv

def configure_logging():
    """
    Configura el sistema de logs para registrar los procesos de conversión.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("conversion_log.log", mode="w"),
            logging.StreamHandler()
        ]
    )

def detect_delimiter(file_path):
    """
    Detecta el delimitador de un archivo CSV. Si no se puede detectar, se usa ';' por defecto.

    :param file_path: Ruta al archivo.
    :return: Delimitador detectado o ';' por defecto.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        sniffer = csv.Sniffer()
        sample = f.read(1024)
        try:
            detected_delimiter = sniffer.sniff(sample).delimiter
            logging.info(f"Delimitador detectado: '{detected_delimiter}' para el archivo: {file_path}")
            return detected_delimiter
        except csv.Error:
            logging.warning(f"No se pudo detectar el delimitador en el archivo {file_path}. Usando ';' por defecto.")
            return ';'

def preprocess_file(file_path, delimiter):
    """
    Preprocesa el archivo para reemplazar separadores decimales y otros ajustes si es necesario.

    :param file_path: Ruta al archivo original.
    :param delimiter: Delimitador detectado del archivo.
    :return: Ruta al archivo temporal preprocesado.
    """
    temp_file = file_path + ".tmp"
    with open(file_path, "r", encoding="utf-8") as f, open(temp_file, "w", encoding="utf-8") as tmp:
        for line in f:
            processed_line = line.replace(",", ".")
            tmp.write(processed_line)
    return temp_file

def convert_csv_to_tsv(input_file_path, output_file_path):
    """
    Convierte un archivo CSV a TSV con tabulador como delimitador y '.' como separador decimal.

    :param input_file_path: Ruta al archivo CSV de entrada.
    :param output_file_path: Ruta para guardar el archivo TSV de salida.
    """
    try:
        logging.info(f"Procesando archivo: {input_file_path}")

        # Detectar el delimitador
        delimiter = detect_delimiter(input_file_path)

        # Preprocesar el archivo
        preprocessed_file = preprocess_file(input_file_path, delimiter)

        # Leer el archivo preprocesado ignorando las dos primeras líneas
        df = pd.read_csv(preprocessed_file, delimiter=delimiter, encoding="utf-8", skiprows=2)

        # Asegurar que todos los floats usen '.' como separador decimal
        for col in df.select_dtypes(include=["float"]):
            df[col] = df[col].apply(lambda x: f"{x:.6f}".replace(",", "."))

        # Guardar como archivo TSV con delimitador tabulador
        df.to_csv(output_file_path, sep='\t', index=False, encoding="utf-8", float_format="%.6g")
        logging.info(f"Archivo guardado como: {output_file_path}")
    except Exception as e:
        logging.error(f"Error procesando el archivo {input_file_path}: {e}")

def process_folder(input_folder, output_folder):
    """
    Convierte todos los archivos CSV en una carpeta a archivos TSV.

    :param input_folder: Ruta a la carpeta que contiene archivos CSV.
    :param output_folder: Ruta para guardar los archivos TSV convertidos.
    """
    os.makedirs(output_folder, exist_ok=True)
    logging.info(f"Carpeta de salida asegurada: {output_folder}")

    input_folder = os.path.abspath(input_folder)
    output_folder = os.path.abspath(output_folder)

    for filename in os.listdir(input_folder):
        if filename.endswith('.csv'):
            input_file_path = os.path.join(input_folder, filename)
            output_file_name = filename.replace('.csv', '.tsv')
            output_file_path = os.path.join(output_folder, output_file_name)

            try:
                convert_csv_to_tsv(input_file_path, output_file_path)
                logging.info(f"Convertido: {input_file_path} -> {output_file_path}")
            except Exception as e:
                logging.error(f"Error procesando {input_file_path}: {e}")
        else:
            logging.info(f"Archivo no CSV omitido: {filename}")

def main():
    """
    Función principal para procesar archivos o carpetas.
    """
    configure_logging()

    input_path = os.path.abspath("./data/inputs/Plan/LPG")
    output_path = os.path.abspath("./data/inputs/Plan/LPG")

    logging.info(f"Ruta de entrada: {input_path}")
    logging.info(f"Ruta de salida: {output_path}")

    if os.path.isfile(input_path):
        if input_path.endswith('.csv'):
            output_file_path = input_path.replace('.csv', '.tsv')
            convert_csv_to_tsv(input_path, output_file_path)
        else:
            logging.error(f"El archivo proporcionado no es un archivo CSV: {input_path}")

    elif os.path.isdir(input_path):
        process_folder(input_path, output_path)

    else:
        logging.error(f"La ruta proporcionada no existe: {input_path}")

if __name__ == "__main__":
    main()
