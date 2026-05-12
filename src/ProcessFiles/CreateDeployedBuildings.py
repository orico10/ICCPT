import pandas as pd
import os

def generate_buildings_full_deployment_clean(buildings_path, deploy_electric_path, deploy_lpg_path, output_path):
    """
    Generates a deployment file combining building data with electric and LPG deployment info per state.
    Keeps all original building columns and adds: State_ID, Year, Semester, Electrified_Current, LPG_Deployed_Current.
    
    Parameters:
    - buildings_path: Path to the enriched buildings TSV file.
    - deploy_electric_path: Path to the electric deployment TSV file.
    - deploy_lpg_path: Path to the LPG deployment TSV file.
    - output_path: Path to save the final output TSV.
    """
    try:
        # Load base data
        buildings = pd.read_csv(buildings_path, sep="\t")
        el_deploy = pd.read_csv(deploy_electric_path, sep="\t")
        lpg_deploy = pd.read_csv(deploy_lpg_path, sep="\t")

        # Get list of states
        states = el_deploy[["State_ID", "Year", "Semester"]].drop_duplicates()
        buildings["key"] = 1
        states["key"] = 1
        expanded = buildings.merge(states, on="key").drop(columns=["key"])

        # Merge Electrified info (ElArea_Id + State_ID)
        el_deploy_reduced = el_deploy[["State_ID", "Year", "Semester", "ElArea_Id", "Electrified_Current"]]
        expanded = expanded.merge(
            el_deploy_reduced,
            on=["State_ID", "Year", "Semester", "ElArea_Id"],
            how="left"
        )

        # Merge LPG Deployed info (LpgArea_Id + State_ID)
        lpg_deploy_reduced = lpg_deploy[["State_ID", "Year", "Semester", "LpgArea_Id", "LPG_Deployed_Current"]]
        expanded = expanded.merge(
            lpg_deploy_reduced,
            on=["State_ID", "Year", "Semester", "LpgArea_Id"],
            how="left"
        )

        # Fill missing deploy flags with False
        expanded["Electrified_Current"] = expanded["Electrified_Current"].fillna(False)
        expanded["LPG_Deployed_Current"] = expanded["LPG_Deployed_Current"].fillna(False)

        # Sort by State_ID for clarity
        expanded = expanded.sort_values(by=["State_ID", "Building_Id"])

        # Save result
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        expanded.to_csv(output_path, sep="\t", index=False)
        print(f"✅ Final deployment file with all building info saved to: {output_path}")

        return expanded.head()

    except Exception as e:
        print(f"❌ Error: {e}")

# Example usage with placeholders
buildings_path = "/Users/olgaricodiez/Desktop/Buildings_postProcss/buildings_master_enriched.tsv"#"/Users/olgaricodiez/Documents/GitHub/CleanCooking_os/buildings_master_enriched.tsv"
deploy_electric_path = "/Users/olgaricodiez/Documents/GitHub/CleanCooking_os/data/outputs/electricity_deployment_debug.tsv"
deploy_lpg_path = "/Users/olgaricodiez/Documents/GitHub/CleanCooking_os/data/outputs/lpg_deployment_debug.tsv"
output_path = "/Users/olgaricodiez/Desktop/Buildings_postProcss/buildings_master_full_deployment.tsv"#"/Users/olgaricodiez/Documents/GitHub/CleanCooking_os/buildings_master_full_deployment.tsv"

generate_buildings_full_deployment_clean(buildings_path, deploy_electric_path, deploy_lpg_path, output_path)
