import pandas as pd
import time
import logging
from src import config

class Building:
    def __init__(self, building_id, building_type_id, longitude, latitude, social_cluster_id, sector_id, biomass_pattern_id, el_area_id, lpg_area_id, 
                 region_code, region_name, region_level, parent_region):
        """
        Represents a single building and its associated data.

        :param building_id: ID of the building.
        :param building_type_id: Type of the building.
        :param long: Longitude of the building
        :param lat: Latitude of the building
        :param social_cluster_id: ID of the social cluster the building belongs to.
        :param sector_id: Sector ID of the building.
        :param biomass_pattern: Biomass pattern of the building.
        :param el_area_id: ID of the electrical area associated with the building.
        :param lpg_area_id: ID of the LPG area associated with the building.
        :param region_code: Code of the region the building belongs to.
        :param region_name: Name of the region the building belongs to.
        :param region_level: Level of the region (hierarchical level).
        :param parent_region: Parent region code.
        """

        self.building_id = building_id
        self.building_type_id = building_type_id
        self.longitude = longitude
        self.latitude = latitude
        self.social_cluster_id = social_cluster_id
        self.sector_id = sector_id
        self.biomass_pattern_id = biomass_pattern_id 
        self.el_area_id = el_area_id
        self.lpg_area_id = lpg_area_id
        self.region_code = region_code
        self.region_name = region_name
        self.region_level = region_level
        self.parent_region = parent_region
        self.parent_regions = []
        # # demands per year for this building (type)
        # self.electric_demand = 0
        # self.cooking_demand = 0
        # self.heating_demand = 0

    def assign_parent_regions(self, region_hierarchy):
        """
        Assigns all parent regions based on the region hierarchy.

        :param region_hierarchy: Dictionary mapping region codes to their parent codes.
        """
        region_code = self.region_code
        while region_code in region_hierarchy and pd.notna(region_hierarchy[region_code]):
            region_code = region_hierarchy[region_code]
            self.parent_regions.append(region_code)


   
   
    def get_data(self, key):
        """
        Returns the value of a specific attribute or additional data.
        Includes the fuel columns dynamically from config.defaults["fuel_names"].
        """
        # Lista de columnas fijas que siempre son atributos directos
        columnas_fijas = [
            "BuildingID", "BuildingType", "Long", "Lat",
            "SocClust_Id", "SectorCode_Id", "BiomasPat_Id"
        ]

        # Añadir dinámicamente los fuels definidos en el config
        #fuel_names = config.defaults.get("fuel_names", [])
        fuel_names = config["defaults"]["fuel_names"]

        columnas_fijas.extend(fuel_names)

        if key in columnas_fijas:
            return getattr(self, key.lower())

        # Resto, buscarlo en additional_data
        return self.additional_data.get(key)
    
    def get_demand(self, demands_by_building_type, demand_type):
        """
        Returns a specific demand (electricity, cooking, or heating) for this building
            using those precomputed by building type.

        :param demands_by_building_type: Dictionary with demands by building type.
        :param demand_type: Type of demand to retrieve ('electricity', 'cooking', 'heating').
        :return: Value of the specific demand for this building.
        :raises ValueError: If the building type or specific demand is not found.
        """
        try:
            building_type_id = self.data["BuildingType_Id"].astype(int)

            if building_type_id not in demands_by_building_type:
                raise ValueError(f"No precomputed demand was found for BuildingType_Id: {building_type_id}")

            demands = demands_by_building_type[building_type_id]

            if demand_type not in demands:
                raise ValueError(f"No precomputed demand was found for demand type '{demand_type}'.")

            return demands[demand_type]

        except Exception as e:
            # Registrar el error y re-lanzar
            logging.error(f"Error en Building.get_demand: {e}")
            error_message = f"Error in Building.get_demand: BuildingType_Id={self.data.get('BuildingType_Id')}, DemandType={demand_type}, Error={str(e)}"
            logging.error(error_message)
            raise RuntimeError(error_message)

