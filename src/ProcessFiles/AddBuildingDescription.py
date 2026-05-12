import os

def create_txt_with_descriptions(input_file_path, output_file_path, descriptions):
    """
    Creates a new TXT file based on the input CSV file.
    Adds column descriptions as the third line, ignoring the first two lines of the original file.

    :param input_file_path: Path to the input CSV file.
    :param output_file_path: Path to save the new TXT file.
    :param descriptions: List of column descriptions to add.
    """
    print(f"Processing file: {input_file_path}")
    
    with open(input_file_path, 'r', encoding='utf-8') as infile:
        lines = infile.readlines()

    # Skip the first two lines of the input file
    content_to_write = lines[2:]  # Everything after the second line
    
    with open(output_file_path, 'w', encoding='utf-8') as outfile:
        # Write the first two lines from the original file
        outfile.write(lines[0])
        outfile.write(lines[1])
        
        # Add the column descriptions as the third line
        description_line = ";".join(descriptions) + "\n"
        outfile.write(description_line)
        
        # Append the remaining content
        outfile.writelines(content_to_write)

    print(f"File with descriptions saved as: {output_file_path}")


def process_files_to_txt(input_folder, output_folder, descriptions):
    """
    Processes all CSV files in a folder, creates a new TXT file for each,
    and adds column descriptions as the third line.

    :param input_folder: Path to the folder containing CSV files.
    :param output_folder: Path to save the new TXT files.
    :param descriptions: List of column descriptions to add.
    """
    # Ensure the output folder exists
    os.makedirs(output_folder, exist_ok=True)
    print(f"Output folder ensured: {output_folder}")

    # Iterate over each file in the input folder
    for filename in os.listdir(input_folder):
        if filename.endswith('.csv'):  # Process only CSV files
            input_file_path = os.path.join(input_folder, filename)
            output_file_name = filename.replace('.csv', '.txt')
            output_file_path = os.path.join(output_folder, output_file_name)

            try:
                create_txt_with_descriptions(input_file_path, output_file_path, descriptions)
                print(f"Processed: {input_file_path} -> {output_file_path}")
            except Exception as e:
                print(f"Error processing {input_file_path}: {e}")
        else:
            print(f"Skipping non-CSV file: {filename}")


# Example usage
input_folder_path = '/path/to/your/input/folder'
output_folder_path = '/path/to/your/output/folder'

# Descriptions to add as the third line
column_descriptions = [
    "Building_Id", "BuildingType_Id", "Long", "Lat", 
    "SocClust_Id", "SectorCode_Id", "BiomasPat_Id", 
    "ElArea_Id", "LpgArea_Id"
]

# Process the files
process_files_to_txt(input_folder_path, output_folder_path, column_descriptions)
