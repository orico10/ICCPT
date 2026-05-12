import pandas as pd
import os

def enrich_buildings_with_area_type(buildings_path, clusters_path, output_path):
    """
    Enriches the building master file with area type ("urban" or "rural") based on social cluster data.
    
    Parameters:
    - buildings_path: Path to the TSV file with building information.
    - clusters_path: Path to the TSV file with social cluster definitions (must include Is_Urban and SocClust_Id).
    - output_path: Path to save the enriched TSV file.
    """
    try:
        # Load input data
        buildings = pd.read_csv(buildings_path, sep="\t")
        clusters = pd.read_csv(clusters_path, sep="\t")

        # Convert Is_Urban to boolean and map to AreaType
        clusters["Is_Urban"] = clusters["Is_Urban"].astype(bool)
        clusters["AreaType"] = clusters["Is_Urban"].apply(lambda x: "urban" if x else "rural")

        # Merge AreaType into buildings
        enriched = buildings.merge(clusters[["SocClust_Id", "AreaType"]], on="SocClust_Id", how="left")

        # Check for missing AreaType
        if enriched["AreaType"].isnull().any():
            missing_count = enriched["AreaType"].isnull().sum()
            print(f"⚠️ Warning: {missing_count} buildings could not be matched to a cluster.")

        # Save result
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        enriched.to_csv(output_path, sep="\t", index=False)
        print(f"✅ Enriched building file saved to: {output_path}")
        
        return enriched.head()  # Display preview
    except Exception as e:
        print(f"❌ Error during processing: {e}")

# Example paths (you can replace these with actual file paths)
#/Users/olgaricodiez/Documents/GitHub/CleanCooking_os/data/inputs/Catalogs
#./data/inputs
buildings_path = "/Users/olgaricodiez/Desktop/Buildings_postProcss/master_file_buildings.tsv"#"/Users/olgaricodiez/Documents/GitHub/CleanCooking_os/master_file_buildings.tsv"#"/Users/olgaricodiez/Documents/GitHub/CleanCooking_os/master_file_buildings.tsv"
clusters_path = "/Users/olgaricodiez/Documents/GitHub/CleanCooking_os/data/inputs/Country/De4.tsv"
output_path = "/Users/olgaricodiez/Desktop/Buildings_postProcss/buildings_master_enriched.tsv"#"/Users/olgaricodiez/Documents/GitHub/CleanCooking_os/buildings_master_enriched.tsv"

enrich_buildings_with_area_type(buildings_path, clusters_path, output_path)
