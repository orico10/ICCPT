from collections import defaultdict
import logging
from src.buildings_manager import BuildingsManager
import os 
import copy
import pandas as pd
from src import config
from src.demand_area import DemandArea

class DemandAreaManager:
    def __init__(self, data_manager, base_path, demandAreas_path):
        """
        Initialize the demand area manager.

        :param data_manager: Instance of DataManager to access loaded data.
        :param base_path: Base path for relative file paths.
        """
        self.data_manager = data_manager
        self.base_path = base_path
        self.buildings_manager = None
        self.demand_areas = []  # Lista de objetos DemandArea
        self.demandAreas_path = demandAreas_path
        self.logger = logging.getLogger("DemandAreaManager")
        #Almacén de ratios cose-beneficio por demand area y deployable fuel 
        self.benefit_cost_ratios = {}
        self.grouped_areas_by_lpg = {}
        self.lookup = {}

    def process_demand_areas(self):
        """
        Load building data, construct demand areas, and register them in the DataManager.
        """
        try:
            # Check that required data is present in the DataManager
            required_dataframes = [
                "Territory_partition", "Electric_load", "E-Cooking_load", "E-Heating_load",
                "BuildTypes_config", "BuildTypes_electric", "BuildTypes_cooking",
                "BuildTypes_heating", "Social_clusters", "LocBio_priceMult", "LocBio_timeGenMult"
            ]

            for dataframe_name in required_dataframes:
                if dataframe_name not in self.data_manager.dataframes:
                    raise ValueError(f"{dataframe_name} data is missing in the DataManager.")

            # Cargar el DataFrame Territory_partition
            territory_partition_df = self.data_manager.get_dataframe("Territory_partition")

            # Inicializar BuildingManager
            #from BuildingManager import BuildingsManager  # Importación dinámica
            self.buildings_manager = BuildingsManager(territory_partition_df, self.base_path)
            self.buildings_manager.load_buildings()
            self.buildings_manager.assign_regions()

            # Cargar otros DataFrames necesarios para cálculos
            de1_electric_df = self.data_manager.get_dataframe("Electric_load")
            de1_cooking_df = self.data_manager.get_dataframe("E-Cooking_load")
            de1_heating_df = self.data_manager.get_dataframe("E-Heating_load")
            de2_config_df = self.data_manager.get_dataframe("BuildTypes_config")
            de2_electric_df = self.data_manager.get_dataframe("BuildTypes_electric")
            de2_cooking_df = self.data_manager.get_dataframe("BuildTypes_cooking")
            de2_heating_df = self.data_manager.get_dataframe("BuildTypes_heating")

            # Calcular demandas por tipo de edificio
            self.buildings_manager.calculate_demands_by_building_type(
                de1_electric_df, de1_cooking_df, de1_heating_df,
                de2_config_df, de2_electric_df, de2_cooking_df, de2_heating_df
            )

            # Crear áreas de demanda
            self.demand_areas = self.buildings_manager.construct_demand_areas()

            # Cargar DataFrames para DemandArea
            social_clusters_df = self.data_manager.get_dataframe("Social_clusters")
            #buildings = self.buildings_manager.get_buildings()
            buildings_by_id = self.buildings_manager.get_buildings_by_id()  # Mapa {building_id: Building}
            loc_price_mult_df = self.data_manager.get_dataframe("LocBio_priceMult")
            loc_time_gen_mult_df = self.data_manager.get_dataframe("LocBio_timeGenMult")
            adoption_patterns_df = self.data_manager.get_dataframe("Initial_adoption_mix")
            technology_catalog_df = self.data_manager.get_dataframe("Cooking_technologies")
            fuels_df = self.data_manager.get_dataframe("Cooking_fuels")
            # Verificar que demands_by_building_type está calculado
            if not self.buildings_manager.demands_by_building_type:
                raise RuntimeError("demands_by_building_type not precomputed in BuildingsManager.")

            demands_by_building_type = self.buildings_manager.get_demands_by_building_type()

            # Procesar datos en cada área de demanda
            for demand_area in self.demand_areas:
                demand_area.process_all_data(
                    buildings_by_id,
                    social_clusters_df,
                    demands_by_building_type,
                    adoption_patterns_df,
                    loc_price_mult_df,
                    loc_time_gen_mult_df,
                    territory_partition_df,
                    technology_catalog_df,
                    fuels_df,
                )

            # Registrar las áreas de demanda en el DataManager
            #self.data_manager.register_demand_areas(self.demand_areas)

            #Exporta los resultados a TSv
            self.export_to_tsv()

            # Crear y registrar el DataFrame de áreas de demanda
            #demand_areas_df = self._create_demand_areas_dataframe()
            #self.data_manager.register_demand_areas_dataframe(demand_areas_df)

        except Exception as e:
            logging.critical(f"Error in process_demand_areas: {e}", exc_info=True)
            raise

    

   
        
    def export_all_to_csv(self, output_path):
        """
        Exports all demand areas to a CSV file.

        :param output_path: Path to save the CSV file.
        """
        try:
            output_file = os.path.join(output_path, "DemandAreas.csv")

            # Prepare data for export
            demand_area_data = []
            for demand_area in self.demand_areas:
                demand_area_data.append({
                    "DemandArea_Id": demand_area.id,
                    "Region": demand_area.region_name,
                    "ElArea_Id": demand_area.el_area,
                    "LpgArea_Id": demand_area.lpg_area,
                    "Num_Buildings": demand_area.num_buildings(),
                })

            # Export to CSV
            pd.DataFrame(demand_area_data).to_csv(output_file, index=False, sep=";")
            logging.info(f"Demand areas exported to {output_file}")

        except Exception as e:
            logging.critical(f"Error in export_all_to_csv: {e}", exc_info=True)
            raise

 

    def export_to_tsv(self):
        """
        Exports all demand areas to multiple TSV files nd creates corresponding DataFrames..

        :param output_path: Path to save the TSV files.
        """
        logging.info("Exporting demand areas to multiple TSV files...")
        try:
            # Create output directory if it doesn't exist
            output_dir = config["path"]["offline_data_files"]
            #os.makedirs(output_path, exist_ok=True)

            #self.export_all_to_csv(output_dir)

            # Export general configuration and demand census
            das_config_df = self._export_config_and_demand_census(output_dir)
            self.data_manager.register_dataframe("das_config", das_config_df)

            # Export and create DataFrame for demand census by social cluster
            das_demand_census_soc_cluster_df = self._export_demand_census_soc_cluster(output_dir)
            self.data_manager.register_dataframe("das_demand_census_soc_cluster", das_demand_census_soc_cluster_df)

            # Export and create DataFrame for biomass patterns
            das_biomass_patterns_df = self._export_biomass_patterns(output_dir)
            self.data_manager.register_dataframe("das_biomass_patterns", das_biomass_patterns_df)

            # Export and create DataFrame for biomass multipliers (loc_price and time_gen)
            das_biomass_multipliers_loc_price_df = self._export_biomass_multipliers_loc_price(output_dir)
            self.data_manager.register_dataframe("das_biomass_multipliers_loc_price", das_biomass_multipliers_loc_price_df)

            das_biomass_multipliers_time_gen_df = self._export_biomass_multipliers_time_gen(output_dir)
            self.data_manager.register_dataframe("das_biomass_multipliers_time_gen", das_biomass_multipliers_time_gen_df)

            # Export and create DataFrame for time_gen modified
            das_time_gen_modified_df = self._export_time_gen_modified(output_dir)
            self.data_manager.register_dataframe("das_time_gen_modified", das_time_gen_modified_df)

            # Export and create DataFrame for initial adoptions
            das_initial_adoptions_df = self._export_initial_adoptions(output_dir)
            self.data_manager.register_dataframe("das_initial_adoptions", das_initial_adoptions_df)

            # Export and create DataFrame for aggregated clusters
            das_aggregated_clusters_df = self._export_aggregated_clusters(output_dir)
            self.data_manager.register_dataframe("das_aggregated_clusters", das_aggregated_clusters_df)

            self.logger.info("Demand areas exported to multiple TSV files and DataFrames created and registered")

        except KeyError as e:
            self.logger.error(f"The key 'path.demand_areas' is not defined in the configuration file: {e}")
        except Exception as e:
            self.logger.error(f"Error exporting demand areas to TSV files and creating DataFrames: {e}")
            raise
            

    def _export_config_and_demand_census(self, output_path):
        """
        Exports general configuration and demand census to a TSV file.
        """
        try: 
            rows = []
            for demand_area in self.demand_areas:
                for area_type in ["rural", "urban"]:
                    row = {
                        "DemandArea_Id": demand_area.id,
                        "Region": demand_area.region_name,
                        "ElArea_Id": demand_area.el_area,
                        "LpgArea_Id": demand_area.lpg_area,
                        "Area_Type": area_type,
                        "Aggregated_Point_Lat": demand_area.data["aggregated_points"][area_type]["Lat"] if demand_area.data["aggregated_points"][area_type] else None,
                        "Aggregated_Point_Long": demand_area.data["aggregated_points"][area_type]["Long"] if demand_area.data["aggregated_points"][area_type] else None,
                        "Census_Electricity_Demand": demand_area.data["demand_census_rur_urb"][area_type]["electricity"],
                        "Census_CookingHeating_Demand": demand_area.data["demand_census_rur_urb"][area_type]["cooking_heating"],
                        "Census_Cooking_Demand": demand_area.data["demand_census_rur_urb"][area_type]["cooking"],
                        "Census_Heating_Demand": demand_area.data["demand_census_rur_urb"][area_type]["heating"],
                    }
                    rows.append(row)

            
            df = pd.DataFrame(rows)
            output_file = os.path.join(output_path, "das_config.tsv")
            df.to_csv(output_file, sep="\t", decimal=".",index=False)
            return df
        except Exception as e:
            logging.error(f"Error exporting general configuration and demand census: {e}", exc_info=True)
            raise
       

    def _export_aggregated_clusters(self, output_path):
        """
        Exports all parameters of the aggregated clusters to a TSV file, with all parameters in columns.
        """
        try: 
            rows = []
            for demand_area in self.demand_areas:
                for area_type in ["rural", "urban"]:
                    row = {
                        "DemandArea_Id": demand_area.id,
                        "Region": demand_area.region_name,
                        "ElArea_Id": demand_area.el_area,
                        "LpgArea_Id": demand_area.lpg_area,
                        "Area_Type": area_type,
                        
                        "E_Elast_Demand": demand_area.data["aggregated_clusters"][area_type]["params"]["e_elast_demand"],
                        "Invest_Cap": demand_area.data["aggregated_clusters"][area_type]["params"]["invest_cap"],
                        "Will_Pay": demand_area.data["aggregated_clusters"][area_type]["params"]["will_pay"],
                        "Change_Fact": demand_area.data["aggregated_clusters"][area_type]["params"]["change_fact"],
                        "Better_Fact": demand_area.data["aggregated_clusters"][area_type]["params"]["better_fact"],
                        "Worse_Fact": demand_area.data["aggregated_clusters"][area_type]["params"]["worse_fact"],
                        "Social_Weight": demand_area.data["aggregated_clusters"][area_type]["params"]["social_weight"],
                        "Health": demand_area.data["aggregated_clusters"][area_type]["params"]["social_balance"]["health"],
                        "Time_Gender": demand_area.data["aggregated_clusters"][area_type]["params"]["social_balance"]["time_gender"],
                        "Emissions": demand_area.data["aggregated_clusters"][area_type]["params"]["social_balance"]["emissions"],
                        "Deforestation": demand_area.data["aggregated_clusters"][area_type]["params"]["social_balance"]["deforestation"],
                    }

                    # Add data from the 'clusters' section
                    for cluster_id, cluster_data in demand_area.data["aggregated_clusters"][area_type]["clusters"].items():
                        row[f"SocClust_{cluster_id}_Electricity_Weight"] = cluster_data["e_weight"]
                        row[f"SocClust_{cluster_id}_CookingHeating_Weight"] = cluster_data["ch_weight"]
                        for key, value in cluster_data["scp"].items():
                            row[f"SocClust_{cluster_id}_SCP_{key}"] = value

                    rows.append(row)
            df = pd.DataFrame(rows)
            output_file = os.path.join(output_path, "das_aggregated_clusters.tsv")
            df.to_csv(output_file, sep="\t", decimal=".", index=False)
            return df
        except Exception as e:
            logging.error(f"Error exporting aggregated clusters: {e}", exc_info=True)
            raise
    
    def _export_demand_census_soc_cluster(self, output_path):
        """
        Exports demand census by social cluster to a TSV file.
        """
        try: 
            rows = []
            for demand_area in self.demand_areas:
                for social_cluster_id, demands in demand_area.data["demand_census_socCluster"].items():
                    is_urban_value = self.data_manager.social_clusters_df.loc[
                        self.data_manager.social_clusters_df["SocClust_Id"] == social_cluster_id, "Is_Urban"
                    ]
                    if len(is_urban_value) == 0:
                        raise ValueError(f"Social cluster ID {social_cluster_id} not found in the social clusters dataframe.")

                    is_urban = is_urban_value.values[0]
                    area_type = "urban" if is_urban == 1 else "rural"

                    row = {
                        "DemandArea_Id": demand_area.id,
                        "Region": demand_area.region_name,
                        "ElArea_Id": demand_area.el_area,
                        "LpgArea_Id": demand_area.lpg_area,
                        "SocClust_Id": social_cluster_id,
                        "Area_Type": area_type,
                        "Electricity_Demand": demands["electricity"],
                        "CookingHeating_Demand": demands["cooking_heating"],
                    }
                    rows.append(row)

            output_file = os.path.join(output_path, "das_demand_census_soc_cluster.tsv")
            pd.DataFrame(rows).to_csv(output_file, sep="\t", index=False)
            return pd.DataFrame(rows)
        except Exception as e:
            logging.error(f"Error exporting demand census by social cluster: {e}", exc_info=True)
            raise
    


    def _export_biomass_patterns(self, output_path):
        """
        Exports biomass patterns to a TSV file, including only alphanumeric pattern names as headers.
        """
        # Filter to include only alphanumeric pattern names
        try: 
            pattern_names = [
                name for name in
                sorted(set(str(pattern) for demand_area in self.demand_areas for pattern in demand_area.data["biomass_patterns"].keys()))
                if not name.isdigit()
            ]
            columns = ["DemandArea_Id", "Region", "ElArea_Id", "LpgArea_Id", "Area_Type"] + pattern_names

            rows = []
            for demand_area in self.demand_areas:
                for area_type in ["rural", "urban"]:
                    row = {
                        "DemandArea_Id": demand_area.id,
                        "Region": demand_area.region_name,
                        "ElArea_Id": demand_area.el_area,
                        "LpgArea_Id": demand_area.lpg_area,
                        "Area_Type": area_type,
                    }
                    for pattern in pattern_names:
                        # Convert pattern to int if it's numeric for dictionary key access
                        key = int(pattern) if pattern.isdigit() else pattern
                        row[pattern] = demand_area.data["biomass_patterns"].get(key, {}).get(area_type, 0.0)
                    rows.append(row)
            df = pd.DataFrame(rows)
            output_file = os.path.join(output_path, "das_biomass_patterns.tsv")
            df.to_csv(output_file, sep="\t", decimal=".", index=False)
            return df
        except Exception as e:
            logging.error(f"Error exporting biomass patterns: {e}", exc_info=True)

    

    def _export_biomass_multipliers_loc_price(self, output_path):
        """
        Exports biomass multipliers (location price) to a TSV file.
        """
        try:
            # Create a new DataFrame for biomass multipliers (loc_price)
            rows = []
            fuel_names = sorted(set(str(fuel) for demand_area in self.demand_areas for fuel in demand_area.data["biomass_multipliers"]["loc_price"].keys()))

            for demand_area in self.demand_areas:
                for area_type in ["rural", "urban"]:
                    row = {
                        "DemandArea_Id": demand_area.id,
                        "Region": demand_area.region_name,
                        "ElArea_Id": demand_area.el_area,
                        "LpgArea_Id": demand_area.lpg_area,
                        "Area_Type": area_type
                    }
                    for fuel in fuel_names:
                        row[fuel] = demand_area.data["biomass_multipliers"]["loc_price"].get(fuel, {}).get(area_type, 0.0)
                    rows.append(row)

            df = pd.DataFrame(rows)
            df = df[["DemandArea_Id", "Region", "ElArea_Id", "LpgArea_Id", "Area_Type"] + fuel_names]

            # Ensure the output path exists
            os.makedirs(output_path, exist_ok=True)

            # Define the output file path
            output_file = os.path.join(output_path, "das_biomass_multipliers_loc_price.tsv")

            # Export the DataFrame to a TSV file
            df.to_csv(output_file, sep='\t', decimal='.', index=False)

            # Log the successful export
            logging.info(f"Successfully exported biomass multipliers (loc_price) to {output_file}")

            return df

        except Exception as e:
            logging.error(f"Error exporting biomass multipliers (loc_price): {e}", exc_info=True)
            raise


    def _export_biomass_multipliers_time_gen(self, output_path):
        """
        Exports biomass multipliers (time generation) to a TSV file.
        """
        try:
            # Create a new DataFrame for biomass multipliers (time_gen)
            rows = []
            fuel_names = sorted(set(str(fuel) for demand_area in self.demand_areas for fuel in demand_area.data["biomass_multipliers"]["time_gen"].keys()))

            for demand_area in self.demand_areas:
                for area_type in ["rural", "urban"]:
                    row = {
                        "DemandArea_Id": demand_area.id,
                        "Region": demand_area.region_name,
                        "ElArea_Id": demand_area.el_area,
                        "LpgArea_Id": demand_area.lpg_area,
                        "Area_Type": area_type
                    }
                    for fuel in fuel_names:
                        row[fuel] = demand_area.data["biomass_multipliers"]["time_gen"].get(fuel, {}).get(area_type, 0.0)
                    rows.append(row)

            df = pd.DataFrame(rows)
            df = df[["DemandArea_Id", "Region", "ElArea_Id", "LpgArea_Id", "Area_Type"] + fuel_names]

            # Ensure the output path exists
            os.makedirs(output_path, exist_ok=True)

            # Define the output file path
            output_file = os.path.join(output_path, "das_biomass_multipliers_time_gen.tsv")

            # Export the DataFrame to a TSV file
            df.to_csv(output_file, sep='\t', decimal='.', index=False)

            # Log the successful export
            logging.info(f"Successfully exported biomass multipliers (time_gen) to {output_file}")

            return df

        except Exception as e:
            logging.error(f"Error exporting biomass multipliers (time_gen): {e}", exc_info=True)
            raise

        

    def _export_time_gen_modified(self, output_path):
        """
        Exports modified time generation data to a TSV file and registers the DataFrame in the DataManager.

        Parameters:
            output_path (str): Path where the TSV file will be saved.

        Returns:
            pd.DataFrame: The DataFrame containing the modified time generation data.
        """
        try:
            # Retrieve technology names from time_gen_modified data
            tech_names = sorted(set(tech for demand_area in self.demand_areas for tech in demand_area.data["time_gen_modified"].keys()))

            # Prepare data for DataFrame creation
            rows = []
            for demand_area in self.demand_areas:
                for area_type in ["rural", "urban"]:
                    row = {
                        'DemandArea_Id': demand_area.id,
                        'Region': demand_area.region_name,
                        'ElArea_Id': demand_area.el_area,
                        'LpgArea_Id': demand_area.lpg_area,
                        'Area_Type': area_type
                    }

                    # Add Time_Gen_Modified values for each technology
                    for tech in tech_names:
                        row[tech] = demand_area.data["time_gen_modified"].get(tech, {}).get(area_type, 0.0)

                    rows.append(row)

            # Create DataFrame
            output_df = pd.DataFrame(rows)

            # Ensure the output path exists
            os.makedirs(output_path, exist_ok=True)

            # Define the output file path
            output_file = os.path.join(output_path, "das_time_gen_modified.tsv")

            # Export the DataFrame to a TSV file
            output_df.to_csv(output_file, sep='\t', decimal='.', index=False)

            # Log the successful export
            logging.info(f"Successfully exported modified time generation data to {output_file}")

            return output_df

        except Exception as e:
            logging.error(f"Error exporting modified time generation data: {e}", exc_info=True)
            raise

 

    def _export_initial_adoptions(self, output_path):
        """
        Exports initial adoptions to a TSV file.
        """
        try: 
            tech_names = sorted(set(str(tech) for demand_area in self.demand_areas for tech in demand_area.data["initial_adoptions"]["rural"].keys()))
            columns = ["DemandArea_Id", "Region", "ElArea_Id", "LpgArea_Id", "Area_Type"] + tech_names

            rows = []
            for demand_area in self.demand_areas:
                for area_type in ["rural", "urban"]:
                    row = {
                        "DemandArea_Id": demand_area.id,
                        "Region": demand_area.region_name,
                        "ElArea_Id": demand_area.el_area,
                        "LpgArea_Id": demand_area.lpg_area,
                        "Area_Type": area_type,
                    }
                    for tech in tech_names:
                        row[tech] = demand_area.data["initial_adoptions"][area_type].get(tech, 0.0)
                    rows.append(row)
            df = pd.DataFrame(rows)
            output_file = os.path.join(output_path, "das_initial_adoptions.tsv")
            df.to_csv(output_file, sep="\t", decimal=".", index=False)
            return df
        except Exception as e:
            logging.error(f"Error exporting initial adoptions: {e}", exc_info=True)
            raise

    def _export_demand_census_soc_cluster(self, output_path):
        """
        Exports demand census by social cluster to a TSV file.
        """
        try: 
            rows = []
            social_clusters_df = self.data_manager.get_dataframe("Social_clusters")  # Obtener el DataFrame de social clusters

            for demand_area in self.demand_areas:
                for social_cluster_id, demands in demand_area.data["demand_census_socCluster"].items():
                    is_urban_value = social_clusters_df.loc[
                        social_clusters_df["SocClust_Id"] == social_cluster_id, "Is_Urban"
                    ]
                    if len(is_urban_value) == 0:
                        raise ValueError(f"Social cluster ID {social_cluster_id} not found in the social clusters dataframe.")

                    is_urban = is_urban_value.values[0]
                    area_type = "urban" if is_urban == 1 else "rural"

                    row = {
                        "DemandArea_Id": demand_area.id,
                        "Region": demand_area.region_name,
                        "ElArea_Id": demand_area.el_area,
                        "LpgArea_Id": demand_area.lpg_area,
                        "SocClust_Id": social_cluster_id,
                        "Area_Type": area_type,
                        "Electricity_Demand": demands["electricity"],
                        "CookingHeating_Demand": demands["cooking_heating"],
                    }
                    rows.append(row)
            df = pd.DataFrame(rows)
            output_file = os.path.join(output_path, "das_demand_census_soc_cluster.tsv")
            df.to_csv(output_file, sep="\t", decimal=".", index=False)
            return df
        except Exception as e:
            logging.error(f"Error exporting demand census by social cluster: {e}", exc_info=True)
            raise
    
    def load_demand_areas_from_config(self):
        """
        Obtains the demand areas configuration from the DataManager using the key 'das_config'
        and creates DemandArea objects.
        
        The DataFrame 'das_config' se espera tenga las siguientes columnas:
            DemandArea_Id, Region, ElArea_Id, LpgArea_Id, Area_Type,
            Aggregated_Point_Lat, Aggregated_Point_Long,
            Census_Electricity_Demand, Census_CookingHeating_Demand.
            Census_Cooking_Demand, Census_Heating_Demand
        
        Since there can be more than one row per DemandArea_Id (one for each Area_Type),
        this method groups the rows by DemandArea_Id and assigns the configuration for each area type.
        
        :return: List of DemandArea objects.
        """
        try:
            if "das_config" not in self.data_manager.dataframes:
                raise ValueError("DataManager does not contain the 'das_config' DataFrame.")
            df = self.data_manager.dataframes["das_config"]
            self.logger.info("Demand areas configuration obtained from DataManager 'das_config'.")
            grouped = df.groupby("DemandArea_Id")
            for demand_area_id, group in grouped:
                try:
                    first_row = group.iloc[0]
                    demand_area = DemandArea(
                        demand_area_id=int(first_row["DemandArea_Id"]),
                        el_area_id=str(first_row["ElArea_Id"]),
                        lpg_area_id=str(first_row["LpgArea_Id"]),
                        region_name=first_row["Region"]
                    )
                    for _, row in group.iterrows():
                        demand_area.assign_config_data(row)
                    self.demand_areas.append(demand_area)
                    self.logger.info("DemandArea %s created with %d area types.", demand_area.id, len(group))
                except Exception as e:
                    self.logger.error("Error creating DemandArea %s: %s", demand_area_id, e, exc_info=True)
                    raise
            return self.demand_areas
        except Exception as e:
            self.logger.error("Error in load_demand_areas_from_config: %s", e, exc_info=True)
            raise

    def assign_preprocessed_data(self):
        """
        Assigns preprocessed data from DataFrames registered in the DataManager
        to the data structure of the DemandArea objects.
        """
        try:
            # Obtener los DataFrames necesarios del DataManager
            dataframes = {
                'config': self.data_manager.get_dataframe('das_config'),
                'demand_census_soc_cluster': self.data_manager.get_dataframe('das_demand_census_soc_cluster'),
                'biomass_patterns': self.data_manager.get_dataframe('das_biomass_patterns'),
                'biomass_multipliers_loc_price': self.data_manager.get_dataframe('das_biomass_multipliers_loc_price'),
                'biomass_multipliers_time_gen': self.data_manager.get_dataframe('das_biomass_multipliers_time_gen'),
                'time_gen_modified': self.data_manager.get_dataframe('das_time_gen_modified'),
                'initial_adoptions': self.data_manager.get_dataframe('das_initial_adoptions'),
                'aggregated_clusters': self.data_manager.get_dataframe('das_aggregated_clusters')
            }

            
            # Asignar datos a cada DemandArea
            for demand_area in self.demand_areas:
                # Limpiar los datos previos
                demand_area.data = demand_area._get_data_structure()

                # Asignar demand_census_soc_cluster
                soc_cluster_rows = dataframes['demand_census_soc_cluster'][
                    dataframes['demand_census_soc_cluster']['DemandArea_Id'] == demand_area.id
                ]
                for _, row in soc_cluster_rows.iterrows():
                    demand_area.data["demand_census_socCluster"][row['SocClust_Id']] = {
                        "electricity": float(row['Electricity_Demand']),
                        "cooking_heating": float(row['CookingHeating_Demand']),
                        
                    }

                # Asignar demand_census_rur_urb
                config_rows = dataframes['config'][
                    dataframes['config']['DemandArea_Id'] == demand_area.id
                ]
                for _, row in config_rows.iterrows():
                    area_type = row['Area_Type'].lower()
                    demand_area.data["demand_census_rur_urb"][area_type] = {
                        "electricity": float(row['Census_Electricity_Demand']),
                        "cooking_heating": float(row['Census_CookingHeating_Demand']), 
                        "cooking": float(row['Census_Cooking_Demand']),
                        "heating": float(row['Census_Heating_Demand'])
                    }

                # Asignar biomass_patterns
                biomass_rows = dataframes['biomass_patterns'][
                    dataframes['biomass_patterns']['DemandArea_Id'] == demand_area.id
                ]
                for _, row in biomass_rows.iterrows():
                    for pattern in row.index:
                        if pattern not in ['DemandArea_Id', 'Region', 'ElArea_Id', 'LpgArea_Id', 'Area_Type']:
                            pattern_key = str(pattern)
                            area_type = row['Area_Type'].lower()
                            demand_area.data["biomass_patterns"][pattern_key][area_type] = float(row[pattern])

                # Asignar biomass_multipliers (loc_price y time_gen)
                for multiplier_type in ['loc_price', 'time_gen']:
                    multiplier_rows = dataframes[f'biomass_multipliers_{multiplier_type}'][
                        dataframes[f'biomass_multipliers_{multiplier_type}']['DemandArea_Id'] == demand_area.id
                    ]
                    for _, row in multiplier_rows.iterrows():
                        for fuel in row.index:
                            if fuel not in ['DemandArea_Id', 'Region', 'ElArea_Id', 'LpgArea_Id', 'Area_Type']:
                                fuel_key = str(fuel)
                                area_type = row['Area_Type'].lower()
                                demand_area.data["biomass_multipliers"][multiplier_type][fuel_key][area_type] = float(row[fuel])

                # Asignar time_gen_modified
                time_gen_rows = dataframes['time_gen_modified'][
                    dataframes['time_gen_modified']['DemandArea_Id'] == demand_area.id
                ]
                for _, row in time_gen_rows.iterrows():
                    for tech in row.index:
                        if tech not in ['DemandArea_Id', 'Region', 'ElArea_Id', 'LpgArea_Id', 'Area_Type']:
                            tech_key = str(tech)
                            area_type = row['Area_Type'].lower()
                            demand_area.data["time_gen_modified"][tech_key][area_type] = float(row[tech])

                # Asignar initial_adoptions
                initial_adoption_rows = dataframes['initial_adoptions'][
                    dataframes['initial_adoptions']['DemandArea_Id'] == demand_area.id
                ]
                for _, row in initial_adoption_rows.iterrows():
                    for tech in row.index:
                        if tech not in ['DemandArea_Id', 'Region', 'ElArea_Id', 'LpgArea_Id', 'Area_Type']:
                            tech_key = str(tech)
                            area_type = row['Area_Type'].lower()
                            demand_area.data["initial_adoptions"][area_type][tech_key] = float(row[tech])

                
                # Asignar aggregated_clusters
                cluster_rows = dataframes['aggregated_clusters'][
                    dataframes['aggregated_clusters']['DemandArea_Id'] == demand_area.id
                ]

                for _, row in cluster_rows.iterrows():
                    area_type = row['Area_Type'].lower()
                    # Estructura base de parámetros (misma para rural, urbano y clusters)
                    base_params = {
                        #"urban": row['Urban'],
                        "e_elast_demand": row['E_Elast_Demand'],
                        "invest_cap": row['Invest_Cap'],
                        "will_pay": row['Will_Pay'],
                        "change_fact": row['Change_Fact'],
                        "better_fact": row['Better_Fact'],
                        "worse_fact": row['Worse_Fact'],
                        "social_weight": row['Social_Weight'],
                        "social_balance": {
                            "health": row['Health'],
                            "time_gender": row['Time_Gender'],
                            "emissions": row['Emissions'],
                            "deforestation": row['Deforestation']
                        }
                    }
                    demand_area.data["aggregated_clusters"][area_type]["params"] = base_params

                    # Identificar dinámicamente los clusters y asignar parámetros
                    cluster_data = {}
                    for col in row.index:
                        if col.startswith("SocClust_"):
                            #  Extraer ID y nombre del parámetro
                            _, cluster_id, *param_parts = col.split('_')
                            param_name = '_'.join(param_parts)

                            # Inicializar el cluster si no existe
                            if cluster_id not in cluster_data:
                                cluster_data[cluster_id] = {
                                    "electricity_weight": 0.0,
                                    "cooking_heating_weight": 0.0,
                                    "params": {
                                        #"urban": None,
                                        "e_elast_demand": None,
                                        "invest_cap": None,
                                        "will_pay": None,
                                        "change_fact": None,
                                        "better_fact": None,
                                        "worse_fact": None,
                                        "social_weight": None,
                                        "social_balance": {
                                            "health": None,
                                            "time_gender": None,
                                            "emissions": None,
                                            "deforestation": None
                                        }
                                    }
                                }

                            # ⚡ Asignar valores según el parámetro
                            if param_name == "Electricity_Weight":
                                cluster_data[cluster_id]["electricity_weight"] = float(row[col])
                            elif param_name == "CookingHeating_Weight":
                                cluster_data[cluster_id]["cooking_heating_weight"] = float(row[col])
                            else:
                                # Asignar valores a la estructura params
                                if param_name in base_params:
                                    cluster_data[cluster_id]["params"][param_name] = row[col]
                                elif param_name in base_params["social_balance"]:
                                    cluster_data[cluster_id]["params"]["social_balance"][param_name] = row[col]

                    # Asignar los clusters al área correspondiente
                    for cluster_id, cluster_info in cluster_data.items():
                        demand_area.data["aggregated_clusters"][area_type]["clusters"][cluster_id] = cluster_info

            logging.info("Preprocessed data assigned to demand areas")
            return self.demand_areas

        except Exception as e:
            logging.error(f"Error assigning preprocessed data: {e}", exc_info=True)
            raise

    def get_demand_area_by_id(self, demand_area_id):
        """
        Returns a DemandArea object from the list of demand areas by its ID.
        """
        try:
            for demand_area in self.demand_areas:
                if demand_area.id == demand_area_id:
                    return demand_area
            raise ValueError(f"DemandArea with ID {demand_area_id} not found.")
        except Exception as e:
            logging.error(f"Error getting DemandArea by ID: {e}", exc_info=True)
            raise

    def get_demand_area_by_id_and_type(self, demand_area_id, area_type):
        """
        Returns a shallow copy of the DemandArea object with only the specified area type (rural
        or urban).
        """
        for da in self.demand_areas:
            if da.id == demand_area_id:
                return da._shallow_clone_with_type(area_type)
        raise ValueError(f"DemandArea with ID {demand_area_id} not found.")

    # def get_demand_area_by_id_and_type(self, demand_area_id, area_type):
    #     """
    #     Returns a DemandArea object filtered only for the area type (rural or urban).
    #     """
    #     try:
    #         for demand_area in self.demand_areas:
    #             if demand_area.id == demand_area_id:
    #                 # Hacer una copia profunda para no modificar el objeto original
    #                 filtered_area = copy.deepcopy(demand_area)

    #                 if area_type == "rural":
    #                     filtered_area.filter_to_rural()
    #                 elif area_type == "urban":
    #                     filtered_area.filter_to_urban()
    #                 else:
    #                     raise ValueError(f"Tipo de área no válido: {area_type}. Debe ser 'rural' o 'urban'.")
                    
    #                 return filtered_area
    #         raise ValueError(f"DemandArea with ID {demand_area_id} not found.")
    #     except Exception as e:
    #         logging.error(f"Error getting DemandArea by ID and type: {e}", exc_info=True)
    #         raise

    

    def group_areas_by_lpg_area(self, demand_areas):
        """
        Group demand areas by LPG and type (rural/urban).
        Stores the result in self.grouped_areas_by_lpg.

        :param demand_areas: List of DemandArea objects.
        """
        try:
            self.grouped_areas_by_lpg = {}

            for area in demand_areas:
                lpg_id = int(area.lpg_area)

                area_type = area.area_type  # Debe ser 'rural' o 'urban'

                if lpg_id not in self.grouped_areas_by_lpg:
                    self.grouped_areas_by_lpg[lpg_id] = {"rural": [], "urban": []}

                if area_type not in ["rural", "urban"]:
                    raise ValueError(f"Área {area.id} has invalid area_type: {area_type}")

                self.grouped_areas_by_lpg[lpg_id][area_type].append(area)
            return self.grouped_areas_by_lpg

        except Exception as e:
            logging.error(f"Error grouping areas by LPG and type: {e}", exc_info=True)
            raise


    def ungroup_areas_by_lpg_area(self, lpg_area_entries):
        """
        Given a dict with keys (lpg_area_id, area_type), returns the corresponding DemandArea
        if they exist in self.grouped_areas_by_lpg.

        :param lpg_area_entries: Dict {(lpg_area_id, area_type): {...}} (el valor no importa)
        :return: Lista de DemandArea
        """
        try:
            ungrouped = []

            for (lpg_id, area_type) in lpg_area_entries.keys():
                if area_type not in ["rural", "urban"]:
                    continue

                if lpg_id in self.grouped_areas_by_lpg:
                    demand_areas = self.grouped_areas_by_lpg[lpg_id].get(area_type, [])
                    ungrouped.extend(demand_areas)

            return ungrouped

        except Exception as e:
            logging.error(f"Error desagrupando áreas de demanda desde non_lpg_areas: {e}", exc_info=True)
            raise




    def group_areas_by_demand_area(demand_areas1, demand_areas2):
        """
        GROUP AREAS BY DEMAND AREA
        :param demand_areas: Object list of DemandArea.
        :return: Dictionary where the key is the demand_area and the value is a list of DemandArea.
        """
        try:
            demand_areas = {}
            for demand_area in demand_areas1:
                key = demand_area.id  # Se asume que cada demand_area tiene un atributo id
                if key not in demand_areas:
                    demand_areas[key] = []
                demand_areas[key].append(demand_area)
            for demand_area in demand_areas2:
                key = demand_area.id  # Se asume que cada demand_area tiene un atributo id
                if key not in demand_areas:
                    demand_areas[key] = []
                demand_areas[key].append(demand_area)
            return demand_areas
        except Exception as e:
            logging.error(f"Error grouping demand areas by DemandArea: {e}", exc_info=True)
            raise

    # Paso 1: construir índice a partir del contenedor agrupado
    @staticmethod
    def build_demand_area_lookup(grouped_areas):
        lookup = {}
        for lpg_areas in grouped_areas.values():
            for area_type in ["rural", "urban"]:
                for area in lpg_areas.get(area_type, []):
                    lookup[(area.id, area_type)] = area
        return lookup
    @staticmethod
    def set_id_non_lpg_areas_ungrupuped(non_lpg_areas_ungrouped, lookup, electrified_areas):
        """
        Returns the corresponding DemandArea objects for the electrified areas,
        checking that they do not overlap with those not connected to LPG.
        """
        try:
            existing_ids = set((area.id, area.area_type) for area in non_lpg_areas_ungrouped)

            electrified_objects = []
            for area_id, area_type in electrified_areas:
                key = (area_id, area_type)
                
                if key in existing_ids:
                    raise ValueError(f"Area {key} not found in non_lpg_areas_ungrouped. Duplication not allowed.")
                
                if key not in lookup:
                    raise ValueError(f"Electrified area {key} not found in the container.")

                electrified_objects.append(lookup[key])

            return electrified_objects  # ← ¡ESTO FALTABA!

        except Exception as e:
            logging.error(f"Error setting ID for ungrouped non-LPG areas: {e}", exc_info=True)
            raise

