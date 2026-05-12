from src import config
import pandas as pd
import time
import logging
import os
from src.base_file_loader import BaseFileLoader
from src.building import Building
from src.demand_area import DemandArea
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

class BuildingsManager:
    def __init__(self, territory_partition, base_path):
        """
        Manages the loading and processing of building data.

        :param territory_partition: DataFrame containing Territory_partition information.
        :param base_path: Base path where the Territory_partition file is located.
        """
        self.territory_partition = territory_partition
        self.base_path = base_path
        self.buildings = [] # List of Building objects
        self.buildings_by_id = {}  # Diccionario para búsquedas rápidas por ID
        self.demand_areas = []  # List of DemandArea objects
        self.logger = logging.getLogger("BuildingsManager")
        self.demands_by_building_type = {}

    def load_buildings(self):
        """
        Loads building files specified in Territory_partition and associates them with regions.
        """
        # Verify that `Buildings file` column exists in Territory_partition
        if "Buildings file" not in self.territory_partition.columns:
            raise ValueError("The 'Buildings file' column is missing in Territory_partition.")

        # Initialize timing
        start_time = time.time()
        processed_files = []
        failed_files = []

        for _, region in self.territory_partition.iterrows():
            building_file = region["Buildings file"]

            if pd.isna(building_file):
                continue  # Skip regions without building files

            # Resolve relative or absolute paths
            if not os.path.isabs(building_file):
                full_path = os.path.join(self.base_path, building_file)
            else:
                full_path = building_file

            try:
                # Use BaseFileLoader to process the file
                file_loader = BaseFileLoader(full_path)
                file_loader.load_file()
                building_df = file_loader.data
                fuel_names = config["defaults"]["fuel_names"]

                # Asumimos que el primer fuel es eléctrico y el segundo LPG
                elec_fuel = fuel_names[0] if len(fuel_names) > 0 else None
                lpg_fuel  = fuel_names[1] if len(fuel_names) > 1 else None
                
                for building_data in building_df.itertuples(index=False):
                    # Create a Building object with direct access to variables
                    building = Building(
                        building_id=building_data.BuildingID,
                        building_type_id=building_data.BuildingType,
                        #el_area_id=building_data.ElArea_Id,
                        #lpg_area_id=building_data.LpgArea_Id,
                        el_area_id=getattr(building_data, elec_fuel) if elec_fuel else None,
                        lpg_area_id=getattr(building_data, lpg_fuel)  if lpg_fuel  else None,
                        longitude=building_data.Long,
                        latitude=building_data.Lat,
                        social_cluster_id=building_data.SocClust_Id,
                        sector_id=building_data.SectorCode_Id,
                        biomass_pattern_id=building_data.BiomasPat_Id,
                        region_code=region["Code"],
                        region_name=region["Name"],
                        region_level=region["Level"],
                        parent_region=region["RegCode_Upstream"]
                    )
                    self.buildings.append(building)

                processed_files.append(full_path)
                self.logger.info(f"Processed building file: {full_path}")
                self.buildings_by_id = {b.building_id: b for b in self.buildings}

            except Exception as e:
                failed_files.append(full_path)
                self.logger.error(f"Error processing file {full_path}: {e}")

        end_time = time.time()
        self.logger.info(f"Total processing time for buildings: {end_time - start_time:.2f} seconds")
        self.logger.info(f"Processed files: {processed_files}")
        if failed_files:
            self.logger.warning(f"Failed files: {failed_files}")

    def assign_regions(self):
        """
        Assigns parent and intermediate regions to each building based on the hierarchy.
        """
        if not self.buildings:
            self.logger.warning("No building data loaded to assign regions.")
            return

        # Create a map of regions for hierarchy
        region_hierarchy = self.territory_partition.set_index("Code")["RegCode_Upstream"].to_dict()

        # Assign parent regions to each building
        for building in self.buildings:
            building.assign_parent_regions(region_hierarchy)

        self.logger.info("Parent region assignment completed.")


    def calculate_demands_by_building_type(self, de1_electric_df, de1_cooking_df, de1_heating_df,
                                           de2_config_df, de2_electric_df, de2_cooking_df, de2_heating_df):
        """
        Calculates demands by building type using demand profiles and building type configurations.

        :param de1_*_df: DataFrames de perfiles de demanda (electricidad, cocinado, calor).
        :param de2_*_df: DataFrames de tipos de edificios (config, electric, cooking, heating).
        :return: Diccionario con demandas por tipo de edificio.
        """
        try:
            self.logger.info("Calculando demandas por tipo de edificio...")
            #demands_by_building_type = {}

            for _, building_type in de2_config_df.iterrows():
                building_type_id = building_type["BuildingType_Id"]
                size = building_type["Size"]

                # Obtener multiplicadores para este tipo de edificio
                electric_multipliers = de2_electric_df.loc[
                    de2_electric_df["BuildingType_Id"] == building_type_id, ["Domestic", "Commercial", "Industrial"]
                ].values.flatten()
                cooking_multipliers = de2_cooking_df.loc[
                    de2_cooking_df["BuildingType_Id"] == building_type_id, ["Domestic", "Commercial", "Industrial"]
                ].values.flatten()
                heating_multipliers = de2_heating_df.loc[
                    de2_heating_df["BuildingType_Id"] == building_type_id, ["Domestic", "Commercial", "Industrial"]
                ].values.flatten()

                # Validar que los multiplicadores no estén vacíos
                if len(electric_multipliers) == 0 or len(cooking_multipliers) == 0 or len(heating_multipliers) == 0:
                    raise ValueError(f"Multipliers not found for BuildingType_Id: {building_type_id}")
                

                # Calcular demandas totales
                electric_demand = sum(
                    de1_electric_df.loc[
                        de1_electric_df["DemandProfile_name"] == col, "Total"
                    ].values[0] * multiplier
                    for col, multiplier in zip(["Domestic", "Commercial", "Industrial"], electric_multipliers)
                    if multiplier > 0
                ) * 365.25 * size

                cooking_demand = sum(
                    de1_cooking_df.loc[
                        de1_cooking_df["DemandProfile_name"] == col, "Total"
                    ].values[0] * multiplier
                    for col, multiplier in zip(["Domestic", "Commercial", "Industrial"], cooking_multipliers)
                    if multiplier > 0
                ) * 365.25 * size

                heating_demand = sum(
                    de1_heating_df.loc[
                        de1_heating_df["DemandProfile_name"] == col, "Total"
                    ].values[0] * multiplier
                    for col, multiplier in zip(["Domestic", "Commercial", "Industrial"], heating_multipliers)
                    if multiplier > 0
                ) * 365.25 * size

                # Guardar resultados en el diccionario
                self.demands_by_building_type[building_type_id] = {
                    "electric_demand": electric_demand,
                    "cooking_demand": cooking_demand,
                    "heating_demand": heating_demand,
                }

            self.logger.info("Demands calculated for all building types.")
           # return demands_by_building_type

        except Exception as e:
            error_message = f"Error in calculate_demands_by_building_type: {str(e)}"
            self.logger.error(error_message)
            raise RuntimeError(error_message)


    def construct_demand_areas(self):
        """
        Constructs and returns demand areas by grouping buildings based on their El and LPG areas.
        """
        demand_areas = []
        demand_area_id = 1

        # Filter out invalid buildings early
        valid_buildings = [
            b for b in self.buildings if b.el_area_id != 0 and b.lpg_area_id != 0
        ]
        self.logger.info(f"Filtered out {len(self.buildings) - len(valid_buildings)} buildings with invalid ElArea_Id or LpgArea_Id.")

        # Group by ElArea_Id
        grouped_by_el_area = self._parallel_group_by(valid_buildings, "el_area_id")

        # Create demand areas grouped by ElArea_Id and LpgArea_Id
        for el_area_id, buildings_by_el_area in grouped_by_el_area.items():
            grouped_by_lpg_area = self._group_by(buildings_by_el_area, "lpg_area_id")
            for lpg_area_id, buildings_group in grouped_by_lpg_area.items():
                region_name = buildings_group[0].region_name if buildings_group else "Unknown"
                demand_area = DemandArea(
                    demand_area_id=demand_area_id,
                    el_area_id=el_area_id,
                    lpg_area_id=lpg_area_id,
                    region_name=region_name
                )
                demand_area.building_ids = [b.building_id for b in buildings_group]
                demand_areas.append(demand_area)
                demand_area_id += 1

        demand_areas.sort(key=lambda x: x.id)
        self.logger.info(f"Total demand areas created: {len(demand_areas)}")

        return demand_areas

    def _parallel_group_by(self, buildings, key):
        """
        Groups buildings by a specific attribute (e.g., el_area_id) in parallel.

        :param buildings: List of Building objects.
        :param key: Attribute to group by.
        :return: Dictionary with groups.
        """
        grouped = defaultdict(list)

        def group_by_chunk(chunk):
            chunk_grouped = defaultdict(list)
            for building in chunk:
                attribute_value = getattr(building, key, None)
                if attribute_value is not None:
                    chunk_grouped[attribute_value].append(building)
                else:
                    self.logger.warning(f"Key '{key}' missing in building: {building}")
            return chunk_grouped

        # Split into chunks for parallel processing
        num_chunks = min(len(buildings), 8)
        if num_chunks == 0:
            return grouped

        chunk_size = (len(buildings) + num_chunks - 1) // num_chunks
        chunks = [buildings[i:i + chunk_size] for i in range(0, len(buildings), chunk_size)]

        with ThreadPoolExecutor(max_workers=num_chunks) as executor:
            results = executor.map(group_by_chunk, chunks)

        # Combine grouped results
        for chunk_grouped in results:
            for k, v in chunk_grouped.items():
                grouped[k].extend(v)

        return grouped

    def _group_by(self, buildings, key):
        """
        Groups buildings by a specific attribute (e.g., lpg_area_id).

        :param buildings: List of Building objects.
        :param key: Attribute to group by.
        :return: Dictionary with groups.
        """
        grouped = defaultdict(list)
        for building in buildings:
            attribute_value = getattr(building, key, None)
            if attribute_value is not None:
                grouped[attribute_value].append(building)
            else:
                self.logger.warning(f"Key '{key}' missing in building: {building}")
        return grouped

    def export_demand_areas(self, output_path):
        """
        Exports all demand areas to a CSV file.
        """
        DemandArea.export_all_to_csv(self.demand_areas, output_path)
        self.logger.info("Demand areas exported successfully.")


# GETTERS------------

    def get_demands_by_building_type(self):
        """
        Returns the precomputed demands by building type.
        """
        if not self.demands_by_building_type:
            raise RuntimeError("Demands by building type have not been computed.")
        return self.demands_by_building_type

    def get_buildings(self):
        """
        Returns the list of buildings.
        """
        return self.buildings
    
    def get_buildings_by_id(self):
        """
        Returns the map of buildings by ID.
        """
        return self.buildings_by_id