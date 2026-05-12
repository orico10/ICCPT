import os
import pandas as pd

class AreaAssigner:
    def __init__(self, reg_folder, csv_folder, output_folder):
        """
        Initializes the class with folder paths.

        :param reg_folder: Path to the folder containing RegFiles.
        :param csv_folder: Path to the folder containing CSV files.
        :param output_folder: Path to save updated CSV files.
        """
        self.reg_folder = reg_folder
        self.csv_folder = csv_folder
        self.output_folder = output_folder

        # Ensure the output folder exists
        os.makedirs(self.output_folder, exist_ok=True)

        # Dictionaries to store mappings from RegFiles
        self.el_area_map = {}
        self.lpg_area_map = {}

    def load_reg_files(self):
        """
        Loads RegFiles and creates mappings for ElArea_Id and LpgArea_Id.
        Normalizes Building_Id to ensure consistent formatting.
        """
        for filename in os.listdir(self.reg_folder):
            if filename.startswith("RegE") and filename.endswith(".txt"):
                area_id = filename.replace("RegE", "").replace(".txt", "")  # Extract area ID
                with open(os.path.join(self.reg_folder, filename), 'r', encoding='utf-8') as file:
                    for line in file:
                        building_id = line.strip().zfill(10)  # Normalizar a 10 caracteres
                        self.el_area_map[building_id] = area_id
            elif filename.startswith("RegL") and filename.endswith(".txt"):
                area_id = filename.replace("RegL", "").replace(".txt", "")  # Extract area ID
                with open(os.path.join(self.reg_folder, filename), 'r', encoding='utf-8') as file:
                    for line in file:
                        building_id = line.strip().zfill(10)  # Normalizar a 10 caracteres
                        self.lpg_area_map[building_id] = area_id

        # Depuración: Mostrar los mapas cargados
        print("Loaded ElArea_Id mappings:", self.el_area_map)
        print("Loaded LpgArea_Id mappings:", self.lpg_area_map)

    def process_csv_files(self):
        """
        Processes all CSV files, assigns area IDs, and saves updated files.
        Assumes the first column always contains the Building_Id.
        """
        for filename in os.listdir(self.csv_folder):
            if filename.endswith(".csv"):
                input_file_path = os.path.join(self.csv_folder, filename)
                output_file_path = os.path.join(self.output_folder, filename)

                try:
                    # Leer las primeras tres líneas para preservarlas
                    with open(input_file_path, 'r', encoding='utf-8') as infile:
                        headers = [next(infile) for _ in range(3)]

                    # Leer datos desde la cuarta línea
                    df = pd.read_csv(input_file_path, sep=';', encoding='utf-8', skiprows=3, header=None)

                    # Asignar nombres manualmente, usando la primera columna como Building_Id
                    df.rename(columns={0: "Building_Id"}, inplace=True)

                    # Normalizar Building_Id en el CSV para que coincida con los mapas
                    df["Building_Id"] = df["Building_Id"].astype(str).str.strip().str.zfill(10)

                    # Asignar identificadores de áreas
                    df["ElArea_Id"] = df["Building_Id"].map(self.el_area_map).fillna("0")  # Si no está, asignar 0
                    df["LpgArea_Id"] = df["Building_Id"].map(self.lpg_area_map).fillna("0")  # Si no está, asignar 0

                    # Depuración: Mostrar las primeras filas del DataFrame
                    print(f"Processed file: {filename}")
                    print(df[["Building_Id", "ElArea_Id", "LpgArea_Id"]].head())

                    # Escribir archivo actualizado con las cabeceras originales y sin filas en blanco
                    with open(output_file_path, 'w', encoding='utf-8', newline='') as outfile:
                        outfile.writelines(headers)  # Escribir cabeceras preservadas
                        df.to_csv(outfile, sep=';', index=False, header=False)  # Escribir datos actualizados

                    print(f"Processed and updated file saved as: {output_file_path}")

                except Exception as e:
                    print(f"Error processing {input_file_path}: {e}")

    def run(self):
        """
        Executes the full process: load RegFiles and process CSV files.
        """
        print("Loading RegFiles...")
        self.load_reg_files()

        print("Processing CSV files...")
        self.process_csv_files()




# Example usage
if __name__ == "__main__":
    # Paths to folders
    reg_folder_path = 'C:/projectTesting/Plan/RegFiles'
    csv_folder_path = 'C:/GIT/CleanCooking_os/data/inputs/Country/demand'
    output_folder_path = 'C:/GIT/CleanCooking_os/data/inputs/Country/demand_o'

    # Initialize and run the process
    assigner = AreaAssigner(reg_folder_path, csv_folder_path, output_folder_path)
    assigner.run()
