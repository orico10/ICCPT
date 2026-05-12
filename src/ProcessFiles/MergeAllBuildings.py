import pandas as pd
import os
from glob import glob

def merge_all_building_tsvs(input_folder, output_path):
    """
    Merges all TSV files in a folder containing building data into one master file.

    Parameters:
    - input_folder: Folder path where all the TSV files are located.
    - output_path: Path where the merged TSV file will be saved.
    """
    try:
        all_files = glob(os.path.join(input_folder, "*.tsv"))
        if not all_files:
            raise FileNotFoundError("No TSV files found in the specified folder.")

        # Read and concatenate all files
        df_list = [pd.read_csv(file, sep="\t") for file in all_files]
        merged_df = pd.concat(df_list, ignore_index=True)

        # Save to output
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        merged_df.to_csv(output_path, sep="\t", index=False)
        print(f"✅ Merged {len(all_files)} files into {output_path}")
        return merged_df.head()
    
    except Exception as e:
        print(f"❌ Error during merge: {e}")

# Example usage (fill in your paths)
input_folder = "/Users/olgaricodiez/Documents/GitHub/CleanCooking_os/data/inputs/Country/demand"
output_path = "/Users/olgaricodiez/Desktop/Buildings_postProcss/master_file_buildings.tsv"#"/Users/olgaricodiez/Documents/GitHub/CleanCooking_os/master_file_buildings.tsv"

merge_all_building_tsvs(input_folder, output_path)
