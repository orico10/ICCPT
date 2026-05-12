import os

def convert_txt_to_csv(input_file_path, output_file_path):
    """
    Converts a TXT file to a CSV file with ';' as the delimiter.
    Ensures numeric values and formatting are preserved.

    :param input_file_path: Path to the input TXT file.
    :param output_file_path: Path to save the output CSV file.
    """
    print(f"Processing file: {input_file_path}")
    with open(input_file_path, 'r', encoding='utf-8') as infile:
        raw_content = infile.readlines()

    with open(output_file_path, 'w', encoding='utf-8') as outfile:
        for line in raw_content:
            # Replace tab characters (\t) with semicolons (;)
            cleaned_line = line.replace('\t', ';').strip()
            outfile.write(cleaned_line + "\n")
    print(f"File saved as: {output_file_path}")


def process_folder(input_folder, output_folder):
    """
    Processes all TXT files in a folder and converts them to CSV.

    :param input_folder: Path to the folder containing TXT files.
    :param output_folder: Path to save the converted CSV files.
    """
    # Ensure the output folder exists
    os.makedirs(output_folder, exist_ok=True)
    print(f"Output folder ensured: {output_folder}")

    # Iterate over each file in the input folder
    for filename in os.listdir(input_folder):
        if filename.endswith('.txt'):
            input_file_path = os.path.join(input_folder, filename)
            output_file_name = filename.replace('.txt', '.csv')
            output_file_path = os.path.join(output_folder, output_file_name)

            try:
                convert_txt_to_csv(input_file_path, output_file_path)
                print(f"Converted: {input_file_path} -> {output_file_path}")
            except Exception as e:
                print(f"Error processing {input_file_path}: {e}")
        else:
            print(f"Skipping non-TXT file: {filename}")


# Define your folder paths
input_folder_path = '/Users/olgaricodiez/Documents/GitHub/CleanCooking_os/data/inputs/Plan/LPG'
output_folder_path = '/Users/olgaricodiez/Documents/GitHub/CleanCooking_os/data/inputs/Plan/LPG'


if os.path.exists(input_folder_path):
    process_folder(input_folder_path, output_folder_path)
else:
    print(f"Input folder does not exist: {input_folder_path}")
