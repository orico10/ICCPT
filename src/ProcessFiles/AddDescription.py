import os

class CSVDescriptionAdder:
    def __init__(self, input_folder, output_folder, descriptions):
        """
        Initializes the class with the folder paths and column descriptions.

        :param input_folder: Path to the folder containing CSV files.
        :param output_folder: Path to save the updated CSV files.
        :param descriptions: List of column descriptions to add.
        """
        self.input_folder = input_folder
        self.output_folder = output_folder
        self.descriptions = ";".join(descriptions) + "\n"

        # Ensure the output folder exists
        os.makedirs(self.output_folder, exist_ok=True)

    def add_description_to_csv(self, input_file_path, output_file_path):
        """
        Adds column descriptions as the third line in a CSV file.

        :param input_file_path: Path to the input CSV file.
        :param output_file_path: Path to save the updated CSV file.
        """
        print(f"Processing file: {input_file_path}")

        with open(input_file_path, 'r', encoding='utf-8') as infile:
            lines = infile.readlines()

        # Insert descriptions after the second line
        if len(lines) >= 2:
            updated_lines = lines[:2] + [self.descriptions] + lines[2:]
        else:
            print(f"File {input_file_path} has fewer than 2 lines. Skipping.")
            return

        # Write the updated content to the output file
        with open(output_file_path, 'w', encoding='utf-8') as outfile:
            outfile.writelines(updated_lines)

        print(f"Updated file saved as: {output_file_path}")

    def process_all_files(self):
        """
        Processes all CSV files in the input folder and adds column descriptions.
        """
        for filename in os.listdir(self.input_folder):
            if filename.endswith('.csv'):
                input_file_path = os.path.join(self.input_folder, filename)
                output_file_path = os.path.join(self.output_folder, filename)

                try:
                    self.add_description_to_csv(input_file_path, output_file_path)
                except Exception as e:
                    print(f"Error processing {input_file_path}: {e}")
            else:
                print(f"Skipping non-CSV file: {filename}")


# Example usage
if __name__ == "__main__":
    # Paths to input and output folders
    input_folder_path = 'C:/GIT/CleanCooking_os/data/inputs/Country/demand_csv'
    output_folder_path = 'C:/GIT/CleanCooking_os/data/inputs/Country/demand'

    # Column descriptions
    column_descriptions = [
        "Building_Id", "BuildingType_Id", "Long", "Lat",
        "SocClust_Id", "SectorCode_Id", "BiomasPat_Id",
        "ElArea_Id", "LpgArea_Id"
    ]

    # Initialize the class and process files
    adder = CSVDescriptionAdder(input_folder_path, output_folder_path, column_descriptions)
    adder.process_all_files()
