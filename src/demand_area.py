from collections import defaultdict
import os
import logging
import pandas as pd
from math import sqrt, atan2, cos, sin
import copy
from types import MappingProxyType

class DemandArea:
    def __init__(self, demand_area_id, el_area_id, lpg_area_id, region_name):
        """
        Represents a single demand area.

        :param demand_area_id: Unique ID for the demand area.
        :param el_area_id: Electric area ID.
        :param lpg_area_id: LPG area ID.
        :param region_name: Name of the region the area belongs to.
        """
        
        self.id = demand_area_id
        self.el_area = el_area_id
        self.lpg_area = lpg_area_id
        self.region_name = region_name
        self.building_ids = []  # List of building IDs in this area
        self.data = self._get_data_structure()
        

        #self.income_model = None
        self.area_type = None

        self.logger = logging.getLogger("DemandArea")

        self._original_area_type = None

    def _get_data_structure(self):
        """
        Returns the data structure for the DemandArea.data.
        """
        return self.data if hasattr(self, 'data') else  {
            "demand_census_socCluster": defaultdict(lambda: {"electricity": 0.0, "cooking_heating": 0.0}),
            "demand_census_rur_urb": {
                "rural": {"electricity": 0.0, "cooking_heating": 0.0, "cooking": 0.0, "heating": 0.0}, #Solo modifico esto 
                "urban": {"electricity": 0.0, "cooking_heating": 0.0, "cooking": 0.0, "heating": 0.0}, #Solo modifico esto 
            },
            "aggregated_points": {"rural": None, "urban": None},
            "biomass_patterns": defaultdict(lambda: {"rural": 0.0, "urban": 0.0}),
            "biomass_multipliers": {
                "loc_price": defaultdict(lambda: {"rural": 0.0, "urban": 0.0}),
                "time_gen": defaultdict(lambda: {"rural": 0.0, "urban": 0.0}),
            },
            "time_gen_modified": defaultdict(lambda: {"rural": 0.0, "urban": 0.0}),
            "initial_adoptions": {
                "rural": defaultdict(float),
                "urban": defaultdict(float),
            },
            "aggregated_clusters": {
                "rural": {
                    "clusters": {},
                    "params": {
                        "population": 1.0,
                        "e_elast_demand": 1.0,
                        "will_pay": 1.0,
                        "invest_cap": 1.0,
                        "change_fact": 1.0,
                        "better_fact": 1.0,
                        "worse_fact": 1.0,
                        "social_weight": 1.0,
                        "social_balance": {
                            "health": 0.0,
                            "time_gender": 0.0,
                            "emissions": 0.0,
                            "deforestation": 0.0
                        }
                    }
                },
                "urban": {
                    "clusters": {},
                    "params": {
                        "population": 1.0,
                        "e_elast_demand": 1.0,
                        "will_pay": 1.0,
                        "invest_cap": 1.0,
                        "change_fact": 1.0,
                        "better_fact": 1.0,
                        "worse_fact": 1.0,
                        "social_weight": 1.0,
                        "social_balance": {
                            "health": 0.0,
                            "time_gender": 0.0,
                            "emissions": 0.0,
                            "deforestation": 0.0
                        }
                    }
                }
            }
        }

    def add_building(self, building_id):
        """Adds a building ID to the demand area."""
        self.building_ids.append(building_id)

    def num_buildings(self):
        """Returns the number of buildings in the demand area."""
        return len(self.building_ids)
    

    def _process_building_data(
        self,
        buildings_map,
        social_clusters_df,
        demands_by_building_type,
        loc_price_mult_df,
        loc_time_gen_mult_df,
        territory_partition_df
    ):
        """
        Core method to process building data once, classifying them into rural/urban
        and calculating necessary variables, including biomass multipliers.
        """
        self.logger.info("Procesando datos de edificios")
        try: 
            aggregated_coords = {
                "rural": {"Lat": [], "Long": []},
                "urban": {"Lat": [], "Long": []},
            }
            total_buildings = {"rural": 0, "urban": 0}
            

            # Extraer dinámicamente los nombres de los patrones de biomasa desde los archivos de biomasa
            # Extraer los nombres de los patrones de biomasa desde la columna BiomassPat_Name para evitar repeticiones
            biomass_pattern_columns = loc_price_mult_df["BiomassPat_Name"].unique().tolist()
            biomass_pattern_ids = loc_price_mult_df["BiomassPat_Id"].unique().tolist()


            # Procesar cada edificio en el área de demanda
            for building_id in self.building_ids:
                if building_id not in buildings_map:
                    continue

                building = buildings_map[building_id]
                social_cluster_id = int(building.social_cluster_id)
                building_type_id = int(building.building_type_id)
                biomass_pattern = int(building.biomass_pattern_id)

                if building_type_id not in demands_by_building_type:
                    self.logger.warning(f"BuildingType_Id {building_type_id} not found in precomputed demands.")
                    continue

                building_demands = demands_by_building_type[building_type_id]

                # Determinar si el edificio es rural o urbano
                is_urban_value = social_clusters_df.loc[
                    social_clusters_df["SocClust_Id"] == social_cluster_id, "Is_Urban"
                ]
                if len(is_urban_value) == 0:
                    raise ValueError(f"Social cluster ID {social_cluster_id} not found in the social clusters dataframe.")

                is_urban = is_urban_value.values[0]
                if is_urban == 1:
                    area_type = "urban"
                elif is_urban == 0:
                    area_type = "rural"
                else:
                    raise ValueError(f"Invalid Is_Urban value for social cluster ID {social_cluster_id}. Expected 0 (rural) or 1 (urban).")

                # Censo de demandas por social cluster y rural/urbano
                self.data["demand_census_socCluster"][social_cluster_id]["electricity"] += building_demands["electric_demand"]
                self.data["demand_census_socCluster"][social_cluster_id]["cooking_heating"] += (
                    building_demands["cooking_demand"] + building_demands["heating_demand"]
                )
                self.data["demand_census_rur_urb"][area_type]["electricity"] += building_demands["electric_demand"]
                self.data["demand_census_rur_urb"][area_type]["cooking_heating"] += (
                    building_demands["cooking_demand"] + building_demands["heating_demand"]
                )
                self.data["demand_census_rur_urb"][area_type]["cooking"] += building_demands["cooking_demand"]
                self.data["demand_census_rur_urb"][area_type]["heating"] += building_demands["heating_demand"]
                
                

                # Aggregated points
                aggregated_coords[area_type]["Lat"].append(building.latitude)
                aggregated_coords[area_type]["Long"].append(building.longitude)
                #aggregated_coords[area_type]["count"] += 1
                
                # Biomass Patterns (locales)
                self.data["biomass_patterns"][biomass_pattern][area_type] += 1
                total_buildings[area_type] += 1

                # Agregación de consumidores
                if social_cluster_id not in self.data["aggregated_clusters"][area_type]["clusters"]:
                    self.data["aggregated_clusters"][area_type]["clusters"][social_cluster_id] = {
                        "scp": social_clusters_df.loc[social_clusters_df["SocClust_Id"] == social_cluster_id].iloc[0].to_dict(),
                        "e_weight": 0.0,
                        "ch_weight": 0.0
                    }

                self.data["aggregated_clusters"][area_type]["clusters"][social_cluster_id]["e_weight"] += building_demands["electric_demand"]
                self.data["aggregated_clusters"][area_type]["clusters"][social_cluster_id]["ch_weight"] += (
                    building_demands["cooking_demand"] + building_demands["heating_demand"]
                )
            # Calcular puntos agregados
            self._calculate_aggregated_points(aggregated_coords)

            # Normalizar patrones de biomasa locales
            self._normalize_local_biomass_patterns()

            # Obtener las proporciones regionales y promediar con las locales
            self._average_biomass_patterns_with_regional(biomass_pattern_ids, biomass_pattern_columns, territory_partition_df)

            # Normalizar patrones de biomasa finales
            self._normalize_final_biomass_patterns()

            # Calcular multiplicadores de loc_price y time_gen
            self._calculate_biomass_multipliers(loc_price_mult_df, loc_time_gen_mult_df)

         
        except Exception as e:
            self.logger.critical(f"Error in _process_building_data: {e}", exc_info=True)
            raise
    

    def _calculate_aggregated_points(self, aggregated_coords):
        """
        Calculate the aggregated points for rural and urban areas, ensuring a minimum distance between them.
        """
        MIN_DISTANCE = 0.01  # 1 km en grados decimales (aproximadamente)
        for area_type in ["rural", "urban"]:
            if aggregated_coords[area_type]["Lat"]:
                lat_mean = sum(aggregated_coords[area_type]["Lat"]) / len(aggregated_coords[area_type]["Lat"])
                long_mean = sum(aggregated_coords[area_type]["Long"]) / len(aggregated_coords[area_type]["Long"])

                # Ajustar la posición para asegurar una distancia mínima
                if area_type == "urban" and self.data["aggregated_points"]["rural"] is not None:
                    rural_lat, rural_long = self.data["aggregated_points"]["rural"]["Lat"], self.data["aggregated_points"]["rural"]["Long"]
                    distance = sqrt((lat_mean - rural_lat)**2 + (long_mean - rural_long)**2)
                    if distance < MIN_DISTANCE:
                        # Ajustar la posición del punto urbano
                        angle = atan2(long_mean - rural_long, lat_mean - rural_lat)
                        lat_mean = rural_lat + MIN_DISTANCE * cos(angle)
                        long_mean = rural_long + MIN_DISTANCE * sin(angle)

                self.data["aggregated_points"][area_type] = {
                    "Lat": lat_mean,
                    "Long": long_mean
                }
            else:
                self.data["aggregated_points"][area_type] = None

    def _normalize_local_biomass_patterns(self):
        """
        Normalize local biomass patterns.
        """
        for area_type in ["rural", "urban"]:
            total_proportion = sum(self.data["biomass_patterns"][p][area_type] for p in self.data["biomass_patterns"])
            if total_proportion > 0:
                for pattern in self.data["biomass_patterns"]:
                    self.data["biomass_patterns"][pattern][area_type] /= total_proportion

    def _average_biomass_patterns_with_regional(self, biomass_pattern_ids, biomass_pattern_columns, territory_partition_df):
        """
        Average local biomass patterns with regional proportions.
        """
        regional_proportions = territory_partition_df.loc[
            territory_partition_df["Name"] == self.region_name, biomass_pattern_columns
        ]
        regional_proportions_dict = (
            regional_proportions.iloc[0].to_dict() if not regional_proportions.empty else {col: 0.0 for col in biomass_pattern_columns}
        )
        
        id_to_name = dict(zip(biomass_pattern_ids, biomass_pattern_columns))
        

        # Y luego itera así:
        # Promediar local y regional
        # Convertir todos los IDs previos en nombres
        biomass_patterns_by_name = defaultdict(lambda: {"rural": 0.0, "urban": 0.0})
        for pattern_id in list(self.data["biomass_patterns"].keys()):
            if isinstance(pattern_id, int):
                name = id_to_name.get(pattern_id)
                if name:
                    for area_type in ["rural", "urban"]:
                        biomass_patterns_by_name[name][area_type] += self.data["biomass_patterns"][pattern_id][area_type]
                del self.data["biomass_patterns"][pattern_id]

        for name, value in biomass_patterns_by_name.items():
            self.data["biomass_patterns"][name] = value

        for pattern_name in biomass_pattern_columns:
            for area_type in ["rural", "urban"]:
                local_value = self.data["biomass_patterns"][pattern_name][area_type]
                regional_value = regional_proportions_dict.get(pattern_name, 0.0)
                self.data["biomass_patterns"][pattern_name][area_type] = (local_value + regional_value) / 2


        # for pattern in biomass_pattern_columns:
        #     for area_type in ["rural", "urban"]:
        #         local_value = self.data["biomass_patterns"][pattern][area_type]
        #         regional_value = regional_proportions_dict.get(pattern, 0.0)
        #         self.data["biomass_patterns"][pattern][area_type] = (local_value + regional_value) / 2

    def _normalize_final_biomass_patterns(self):
        """
        Normalize final biomass patterns.
        """
        for area_type in ["rural", "urban"]:
            total_proportion = sum(self.data["biomass_patterns"][p][area_type] for p in self.data["biomass_patterns"])
            if total_proportion > 0:
                for pattern in self.data["biomass_patterns"]:
                    self.data["biomass_patterns"][pattern][area_type] /= total_proportion

    def _calculate_biomass_multipliers(self, loc_price_mult_df, loc_time_gen_mult_df):
        """
        Calculate biomass multipliers for loc_price and time_gen.
        """
        fuel_columns = [col for col in loc_price_mult_df.columns if col not in ["BiomassPat_Id", "BiomassPat_Name", "Is_Urban"]]
        total_weight = {"rural": defaultdict(float), "urban": defaultdict(float)}
        weighted_sums = {
            "loc_price": {"rural": defaultdict(float), "urban": defaultdict(float)},
            "time_gen": {"rural": defaultdict(float), "urban": defaultdict(float)}
        }

        for fuel in fuel_columns:
            for area_type in ["rural", "urban"]:
                for pattern in self.data["biomass_patterns"].keys():
                    proportion = self.data["biomass_patterns"][pattern][area_type]

                    loc_price_mult = loc_price_mult_df[
                        (loc_price_mult_df["BiomassPat_Name"] == pattern)
                        & (loc_price_mult_df["Is_Urban"] == (1 if area_type == "urban" else 0))
                    ][fuel].sum()

                    time_gen_mult = loc_time_gen_mult_df[
                        (loc_time_gen_mult_df["BiomassPat_Name"] == pattern)
                        & (loc_time_gen_mult_df["Is_Urban"] == (1 if area_type == "urban" else 0))
                    ][fuel].sum()

                    weighted_sums["loc_price"][area_type][fuel] += loc_price_mult * proportion
                    weighted_sums["time_gen"][area_type][fuel] += time_gen_mult * proportion
                    total_weight[area_type][fuel] += proportion

        for fuel in fuel_columns:
            for area_type in ["rural", "urban"]:
                if total_weight[area_type][fuel] > 0:
                    self.data["biomass_multipliers"]["loc_price"][fuel][area_type] = (
                        weighted_sums["loc_price"][area_type][fuel] / total_weight[area_type][fuel]
                    )
                    self.data["biomass_multipliers"]["time_gen"][fuel][area_type] = (
                        weighted_sums["time_gen"][area_type][fuel] / total_weight[area_type][fuel]
                    )
                else:
                    self.data["biomass_multipliers"]["loc_price"][fuel][area_type] = 0.0
                    self.data["biomass_multipliers"]["time_gen"][fuel][area_type] = 0.0

            
    

    def calculate_aggregated_adoptions(
            self,
            adoption_patterns_df,
            social_clusters_df
        ):
        """
        Calculates initial aggregated adoptions for rural and urban areas.
        """
        self.logger.info("Calculando adopciones iniciales agregadas")
        try: 
            rural_adoption_sums = defaultdict(float)
            urban_adoption_sums = defaultdict(float)
            rural_total_weight = 0.0
            urban_total_weight = 0.0

            # Extraer nombres de tecnologías dinámicamente
            technology_columns = [
                col for col in adoption_patterns_df.columns if col not in ["SocClust_Id", "SocClust_Name", "Is_Urban"]
            ]

            # 🔹 Asegurar que todas las tecnologías tienen valores iniciales (equivalente a C++)
            for tech_name in technology_columns:
                rural_adoption_sums[tech_name] = 0.0
                urban_adoption_sums[tech_name] = 0.0

            for social_cluster_id, demands in self.data["demand_census_socCluster"].items():
                is_urban_value = social_clusters_df.loc[
                    social_clusters_df["SocClust_Id"] == social_cluster_id, "Is_Urban"
                ]

                if len(is_urban_value) == 0:
                    raise ValueError(f"Social cluster ID {social_cluster_id} not found in the social clusters dataframe.")

                is_urban = is_urban_value.values[0]
                area_type = "urban" if is_urban == 1 else "rural"

                # Obtener adopciones del cluster
                adoption_data = adoption_patterns_df.loc[
                    adoption_patterns_df["SocClust_Id"] == social_cluster_id, technology_columns
                ]

                if adoption_data.empty or adoption_data.isnull().all().all():
                    self.logger.warning(f"No adoption data found for social cluster {social_cluster_id}.")
                    continue

                ch_weight = demands.get("cooking_heating", 0.0)
                if not isinstance(ch_weight, (int, float)) or ch_weight < 0:
                    ch_weight = 0.0  

                # Sumar el peso una vez por cluster
                if area_type == "rural":
                    rural_total_weight += ch_weight
                else:
                    urban_total_weight += ch_weight

                for tech_name in technology_columns:
                    adoption_value = adoption_data[tech_name].values[0]
                    if area_type == "rural":
                        rural_adoption_sums[tech_name] += adoption_value * ch_weight
                    else:
                        urban_adoption_sums[tech_name] += adoption_value * ch_weight

            # ✅ Ajuste en la normalización (ahora igual que en C++)
            def normalize_adoptions(adoption_sums):
                sum_adoption = sum(adoption_sums.values())
                if sum_adoption > 0:
                    for tech_name in adoption_sums:
                        adoption_sums[tech_name] /= sum_adoption

            normalize_adoptions(rural_adoption_sums)
            normalize_adoptions(urban_adoption_sums)

            self.data["initial_adoptions"]["rural"] = rural_adoption_sums
            self.data["initial_adoptions"]["urban"] = urban_adoption_sums

        except Exception as e:
            self.logger.critical(f"Error in calculate_aggregated_adoptions: {e}", exc_info=True)
            raise



    def calculate_time_gen_modified(self, technology_catalog_df, fuels_df):
        """
        Calculates the TimeGen Modified value for each technology based on time generation multipliers
        and assigns the results to the time_gen_modified data structure.

        :param technology_catalog_df: DataFrame containing the technology catalog with TechID, TechName, FuelID, FuelTimeGen, and ApplianceTimeGen.
        :param fuels_df: DataFrame containing the mapping of FuelID to FuelName.
        """
        self.logger.info("Calculando TimeGen modificado")
        try:
            for _, row in technology_catalog_df.iterrows():
                tech_id = int(row["Technologies_id"])
                tech_name = row["Tech_name"]
                fuel_id = int(row["Fuel_id"])

                # Obtener el nombre del fuel desde fuels_df
                fuel_name_values = fuels_df.loc[fuels_df["Fuel_id"] == fuel_id, "Fuel_name"].values
                if len(fuel_name_values) == 0:
                    self.logger.warning(f"FuelID {fuel_id} no tiene un nombre asociado en fuels_df. Saltando TechID {tech_id}.")
                    continue
                fuel_name = fuel_name_values[0]  # Extraer el único valor

                time_f_gen = float(row.get("FuelTimeGen", 0.0))  # Valor predeterminado si no existe
                time_a_gen = float(row.get("ApplianceTimeGen", 0.0)) # Valor predeterminado si no existe

                if pd.isna(time_f_gen) or pd.isna(time_a_gen):
                    self.logger.warning(f"Skipping TechID {tech_id} ({tech_name}) debido a valores de tiempo de generación faltantes.")
                    continue

                # Verificar si existen multiplicadores para el FuelName
                if fuel_name not in self.data["biomass_multipliers"]["time_gen"]:
                    self.logger.warning(f"No hay multiplicadores de generación de tiempo para '{fuel_name}' (TechID {tech_id}).")
                    continue

                for area_type, time_gen_mult in self.data["biomass_multipliers"]["time_gen"][fuel_name].items():
                    time_gen_modified = 0.0

                    # Calcular el valor modificado según las reglas
                    if time_f_gen == 0 or time_a_gen == 0 or time_gen_mult == 0:
                        time_gen_modified = time_f_gen + time_a_gen
                    else:
                        time_gen_modified = time_gen_mult * time_f_gen + time_a_gen

                    # Guardar el valor calculado por nombre de tecnología
                    self.data["time_gen_modified"][tech_name][area_type] = time_gen_modified

        except Exception as e:
            self.logger.critical(f"Error en calculate_time_gen_modified: {e}", exc_info=True)
            raise


    def calculate_final_params(self):
        """
        Calculates final parameters for all clusters and stores them in aggregated_clusters.
        """
        self.logger.info("Calculating final parameters for all clusters")

        try:
            for area_type in ["rural", "urban"]:
                area_electric_demand = self.data["demand_census_rur_urb"][area_type]["electricity"]
                area_ch_demand = self.data["demand_census_rur_urb"][area_type]["cooking_heating"]

                if area_electric_demand > 0 and area_ch_demand > 0:
                    total_elasticity = 0.0
                    total_invest_cap = 0.0
                    total_will_pay = 0.0
                    total_change_fact = 0.0
                    total_better_fact = 0.0
                    total_worse_fact = 0.0
                    total_social_weight = 0.0
                    total_health = 0.0
                    total_time_gender = 0.0
                    total_emissions = 0.0
                    total_deforestation = 0.0

                    for cluster_id, cluster_data in self.data["aggregated_clusters"][area_type]["clusters"].items():
                        scp = cluster_data["scp"]
                        e_weight = cluster_data["e_weight"]
                        ch_weight = cluster_data["ch_weight"]

                        total_elasticity += scp["Elasticity"] * e_weight
                        total_invest_cap += scp["Budget"] * ch_weight
                        total_will_pay += scp["WTP"] * ch_weight
                        total_change_fact += scp["Penalty"] * ch_weight
                        total_better_fact += scp["Better"] * ch_weight
                        total_worse_fact += scp["Worse"] * ch_weight
                        total_social_weight += scp["Social_weight"] * ch_weight

                        total_health += scp["Health"] * ch_weight
                        total_time_gender += scp["Time_gender"] * ch_weight
                        total_emissions += scp["Emissions"] * ch_weight
                        total_deforestation += scp["Deforestation"] * ch_weight

                    self.data["aggregated_clusters"][area_type]["params"]["e_elast_demand"] = total_elasticity / area_electric_demand
                    self.data["aggregated_clusters"][area_type]["params"]["invest_cap"] = total_invest_cap / area_ch_demand
                    self.data["aggregated_clusters"][area_type]["params"]["will_pay"] = total_will_pay / area_ch_demand
                    self.data["aggregated_clusters"][area_type]["params"]["change_fact"] = total_change_fact / area_ch_demand
                    self.data["aggregated_clusters"][area_type]["params"]["better_fact"] = total_better_fact / area_ch_demand
                    self.data["aggregated_clusters"][area_type]["params"]["worse_fact"] = total_worse_fact / area_ch_demand
                    self.data["aggregated_clusters"][area_type]["params"]["social_weight"] = total_social_weight / area_ch_demand

                    self.data["aggregated_clusters"][area_type]["params"]["social_balance"]["health"] = total_health / area_ch_demand
                    self.data["aggregated_clusters"][area_type]["params"]["social_balance"]["time_gender"] = total_time_gender / area_ch_demand
                    self.data["aggregated_clusters"][area_type]["params"]["social_balance"]["emissions"] = total_emissions / area_ch_demand
                    self.data["aggregated_clusters"][area_type]["params"]["social_balance"]["deforestation"] = total_deforestation / area_ch_demand

                # else:
                #     #self.logger.error(f"{area_type.capitalize()} electric or cooking+heating demand is zero, cannot calculate final parameters")
                    
        except Exception as e:
            self.logger.critical(f"Error in calculate_final_params: {e}", exc_info=True)
            raise


    def process_all_data(
        self,
        buildings_by_id,
        social_clusters_df,
        demands_by_building_type,
        adoption_patterns_df,
        loc_price_mult_df,
        loc_time_gen_mult_df,
        territory_partition_df,
        technology_catalog_df,
        fuels_df,
    ):
        """
        Processes all data for the demand area, including demands, points, biomass patterns, and multipliers.
        """
        try:
            # Obtener edificios del área de demanda utilizando el mapa
            buildings_in_area_map = {
                building_id: buildings_by_id[building_id]
                for building_id in self.building_ids
                if building_id in buildings_by_id
            }

            if not buildings_in_area_map:
                self.logger.warning(f"No buildings match the provided building IDs for DemandArea {self.id}.")

            # Process building data once
            self._process_building_data(
                buildings_in_area_map,
                social_clusters_df,
                demands_by_building_type,
                loc_price_mult_df,
                loc_time_gen_mult_df,
                territory_partition_df,
            )

            # Calculate aggregated adoptions
            self.calculate_aggregated_adoptions(adoption_patterns_df, social_clusters_df)
            # Calculate TimeGen Modified
            self.calculate_time_gen_modified(technology_catalog_df, fuels_df)
            # Calculate final parameters
            self.calculate_final_params()

        except Exception as e:
            self.logger.critical(f"Error in process_all_data: {e}", exc_info=True)
            raise

    def assign_config_data(self, config_row):
        """
        Assigns the configuration data from a single row to the DemandArea.
        Since the configuration file has one row per area type, this method assigns the data
        to the appropriate subkeys (e.g. for 'aggregated_points' and 'demand_census_rur_urb').

        :param config_row: A pandas Series representing one row from the configuration file.
        """
        try:
            area_type = config_row["Area_Type"].strip().lower()
            # Set aggregated points for this area type
            self.data["aggregated_points"][area_type] = {
                "Lat": config_row["Aggregated_Point_Lat"],
                "Long": config_row["Aggregated_Point_Long"]
            }
            # Set census demand for this area type
            # self.data["demand_census_rur_urb"][area_type] = {
            #     "electricity": config_row["Census_Electricity_Demand"],
            #     "cooking_heating": config_row["Census_CookingHeating_Demand"],
            #     "cooking": config_row["Census_Cooking_Demand"],
            #     "heating": config_row["Census_Heating_Demand"]
            # }
            # Almacenar la demanda base, incluyendo las nuevas columnas separadas:
            self.data.setdefault("demand_census_rur_urb", {})
            self.data["demand_census_rur_urb"].setdefault(config_row["Area_Type"].lower(), {})
            self.data["demand_census_rur_urb"][config_row["Area_Type"].lower()]["electricity"] = config_row["Census_Electricity_Demand"]
            self.data["demand_census_rur_urb"][config_row["Area_Type"].lower()]["cooking_heating"] = config_row["Census_CookingHeating_Demand"]
            self.data["demand_census_rur_urb"][config_row["Area_Type"].lower()]["cooking"] = config_row["Census_Cooking_Demand"]
            self.data["demand_census_rur_urb"][config_row["Area_Type"].lower()]["heating"] = config_row["Census_Heating_Demand"]
            logging.info("Config data assigned for DemandArea %s (%s)", self.id, area_type)
        except Exception as e:
            logging.error("Error assigning config data for DemandArea %s: %s", self.id, e, exc_info=True)
            raise

    def assign_preprocessed_data(self, preprocessed_data):
        """
        Assigns the input data (preprocessed DataFrames) to the DemandArea's internal data structure.
        Here we fill the fields with the values loaded from input files.
        For example, if the preprocessed data contains the demand census per social cluster,
        biomass patterns, multipliers, etc., they are assigned to the corresponding keys.

        :param preprocessed_data: Dictionary with keys corresponding to the required file names 
                                  (e.g., "das_config", "das_demand_census_soc_cluster", etc.) and values as the
                                  filtered DataFrames for this demand area.
        """
        try:
            # Store the entire dictionary of input data (if needed later)
            self.data["preprocessed"] = preprocessed_data

            # For each expected key, assign the corresponding DataFrame to the appropriate field.
            if "das_demand_census_soc_cluster" in preprocessed_data:
                self.data["demand_census_socCluster"] = preprocessed_data["das_demand_census_soc_cluster"]

            if "das_biomass_patterns" in preprocessed_data:
                self.data["biomass_patterns"] = preprocessed_data["das_biomass_patterns"]

            if "das_biomass_multipliers_loc_price" in preprocessed_data:
                self.data["biomass_multipliers"]["loc_price"] = preprocessed_data["das_biomass_multipliers_loc_price"]

            if "das_biomass_multipliers_time_gen" in preprocessed_data:
                self.data["biomass_multipliers"]["time_gen"] = preprocessed_data["das_biomass_multipliers_time_gen"]

            if "das_time_gen_modified" in preprocessed_data:
                self.data["time_gen_modified"] = preprocessed_data["das_time_gen_modified"]

            if "das_initial_adoptions" in preprocessed_data:
                self.data["initial_adoptions"] = preprocessed_data["das_initial_adoptions"]

            if "das_aggregated_clusters" in preprocessed_data:
                self.data["aggregated_clusters"] = preprocessed_data["das_aggregated_clusters"]

            # if "das_config" in preprocessed_data:
            #     self.data["config"] = preprocessed_data["das_config"]

            # if "enriched_technologies" in preprocessed_data:
            #     self.data["enriched_technologies"] = preprocessed_data["enriched_technologies"]

            logging.info("Preprocessed data assigned for DemandArea %s", self.id)
        except Exception as e:
            logging.error("Error assigning preprocessed data in DemandArea %s: %s", self.id, e, exc_info=True)
            raise


    def filter_to_rural(self):
        """
        Mantiene solo los datos rurales. Limpia los datos urbanos.
        """
        self.area_type = "rural"
        

    def filter_to_urban(self):
        """
        Mantiene solo los datos urbanos. Limpia los datos rurales.
        """
        self.area_type = "urban"

    def _shallow_clone_with_type(self, area_type: str):
        """
        Create a shallow clone of the current DemandArea with the specified area_type.
        This method is used to create separate instances for rural and urban areas
        without duplicating all the data.
        :param area_type: A string, either "rural" or "urban".
        """
        if area_type not in ("rural", "urban"):
            raise ValueError("area_type must be 'rural' or 'urban'")
        new = object.__new__(self.__class__)
        new.__dict__ = self.__dict__.copy()   # copia 1er nivel del objeto
        new.area_type = area_type             # único cambio
        return new
        

    def enter_dual_mode(self):
        self._original_area_type = self.area_type
        self.area_type = None

    def restore_area_type(self):
        self.area_type = getattr(self, "_original_area_type", None)
        if hasattr(self, "_original_area_type"):
            del self._original_area_type
    
    def clone_or_merge_with(self, area_rural, area_urban):
        """
        Fusiona los datos de un área rural y urbana en un nuevo objeto DemandArea combinado.
        """
        if area_rural.area_type == area_urban.area_type:
            raise ValueError("Both areas must be of different types (rural vs urban)")

        # Crear nuevo objeto combinado (metadatos)
        merged_area = DemandArea(
            demand_area_id=self.id,
            el_area_id=self.el_area,
            lpg_area_id=self.lpg_area,
            region_name=self.region_name
        )
        merged_area.building_ids = self.building_ids.copy()  # 1º nivel
        merged_area.area_type = None

        # === 1) socCluster ===
        # Si es de solo lectura, NO copies; si puede mutarse, copia 1º nivel.
        # Antes: deepcopy(self.data["demand_census_socCluster"])
        base_soc = self.data["demand_census_socCluster"]
        merged_area.data["demand_census_socCluster"] = dict(base_soc)

        # === 2) aggregated_points (solo lectura, referencias baratas) ===
        merged_area.data["aggregated_points"]["rural"] = area_rural.data["aggregated_points"]["rural"]
        merged_area.data["aggregated_points"]["urban"] = area_urban.data["aggregated_points"]["urban"]

        # === 3) demand_census_rur_urb (1º nivel) ===
        # Antes: deepcopy(...)
        merged_area.data["demand_census_rur_urb"]["rural"] = dict(
            area_rural.data["demand_census_rur_urb"]["rural"]
        )
        merged_area.data["demand_census_rur_urb"]["urban"] = dict(
            area_urban.data["demand_census_rur_urb"]["urban"]
        )

        # === 4) biomass_patterns (construcción nueva ya evita compartir referencias peligrosas) ===
        merged_bp = merged_area.data["biomass_patterns"]
        rur_bp = area_rural.data["biomass_patterns"]
        urb_bp = area_urban.data["biomass_patterns"]
        for pattern, rur_dict in rur_bp.items():
            merged_bp[pattern] = {
                "rural": rur_dict.get("rural", 0.0),
                "urban": urb_bp.get(pattern, {}).get("urban", 0.0),
            }

        # === 5) biomass_multipliers (1º nivel por clave/fuel) ===
        merged_bm = merged_area.data["biomass_multipliers"]
        for key in ["loc_price", "time_gen"]:
            merged_bm_key = merged_bm[key]
            rur_bm_key = area_rural.data["biomass_multipliers"][key]
            urb_bm_key = area_urban.data["biomass_multipliers"][key]
            for fuel, rur_vals in rur_bm_key.items():
                dst = merged_bm_key.setdefault(fuel, {})
                # asignación escalar por rama (no se mutan estructuras compartidas)
                dst["rural"] = rur_vals["rural"]
                dst["urban"] = urb_bm_key[fuel]["urban"]

        # === 6) time_gen_modified (construcción nueva) ===
        merged_tgm = merged_area.data["time_gen_modified"]
        rur_tgm = area_rural.data["time_gen_modified"]
        urb_tgm = area_urban.data["time_gen_modified"]
        for tech, rur_vals in rur_tgm.items():
            merged_tgm[tech] = {
                "rural": rur_vals.get("rural", 0.0),
                "urban": urb_tgm.get(tech, {}).get("urban", 0.0),
            }

        # === 7) initial_adoptions (1º nivel) ===
        # Antes: deepcopy(...)
        merged_area.data["initial_adoptions"]["rural"] = dict(
            area_rural.data["initial_adoptions"]["rural"]
        )
        merged_area.data["initial_adoptions"]["urban"] = dict(
            area_urban.data["initial_adoptions"]["urban"]
        )

        # === 8) aggregated_clusters ===
        # Clave: NO deepcopy. Copia 1º nivel de 'params' (luego los reescribes)
        # y convierte 'clusters' a tupla para blindar contra mutaciones in-place.
        for area_type, src in (("rural", area_rural), ("urban", area_urban)):
            src_branch = src.data["aggregated_clusters"][area_type]
            dst_branch = merged_area.data["aggregated_clusters"][area_type]

            # params: 1º nivel (lo demás en params son escalares o dicts que ya reconstruyes luego)
            dst_branch["params"] = dict(src_branch.get("params", {}))

            # clusters: suelen ser listas grandes que solo se LEEN -> hacerlas inmutables
            clusters = src_branch.get("clusters")
            if isinstance(clusters, list):
                dst_branch["clusters"] = tuple(clusters)
            else:
                # si ya es tupla/estructura inmutable, asigna tal cual
                dst_branch["clusters"] = clusters

        return merged_area


    # def clone_or_merge_with(self, area_rural, area_urban):
    #     """
    #     Fusiona los datos de un área rural y urbana en un nuevo objeto DemandArea combinado.
    #     """
    #     if area_rural.area_type == area_urban.area_type:
    #         raise ValueError("Both areas must be of different types (rural vs urban)")

    #     # Crear nuevo objeto combinado
    #     merged_area = DemandArea(
    #         demand_area_id=self.id,
    #         el_area_id=self.el_area,
    #         lpg_area_id=self.lpg_area,
    #         region_name=self.region_name
    #     )
    #     merged_area.building_ids = self.building_ids.copy()
    #     merged_area.area_type = None

    #     # Copia directa del socCluster desde el área base (puede ser cualquiera, se asume igual)
    #     merged_area.data["demand_census_socCluster"] = copy.deepcopy(self.data["demand_census_socCluster"])

    #     # Campos combinados
    #     merged_area.data["aggregated_points"]["rural"] = area_rural.data["aggregated_points"]["rural"]
    #     merged_area.data["aggregated_points"]["urban"] = area_urban.data["aggregated_points"]["urban"]

    #     merged_area.data["demand_census_rur_urb"]["rural"] = copy.deepcopy(area_rural.data["demand_census_rur_urb"]["rural"])
    #     merged_area.data["demand_census_rur_urb"]["urban"] = copy.deepcopy(area_urban.data["demand_census_rur_urb"]["urban"])

    #     for pattern in area_rural.data["biomass_patterns"]:
    #         merged_area.data["biomass_patterns"][pattern] = {
    #             "rural": area_rural.data["biomass_patterns"][pattern]["rural"],
    #             "urban": area_urban.data["biomass_patterns"].get(pattern, {}).get("urban", 0.0)
    #         }

    #     for key in ["loc_price", "time_gen"]:
    #         for fuel in area_rural.data["biomass_multipliers"][key]:
    #             if fuel not in merged_area.data["biomass_multipliers"][key]:
    #                 merged_area.data["biomass_multipliers"][key][fuel] = {}
    #             merged_area.data["biomass_multipliers"][key][fuel]["rural"] = area_rural.data["biomass_multipliers"][key][fuel]["rural"]
    #             merged_area.data["biomass_multipliers"][key][fuel]["urban"] = area_urban.data["biomass_multipliers"][key][fuel]["urban"]

    #     for tech in area_rural.data["time_gen_modified"]:
    #         merged_area.data["time_gen_modified"][tech] = {
    #             "rural": area_rural.data["time_gen_modified"][tech]["rural"],
    #             "urban": area_urban.data["time_gen_modified"].get(tech, {}).get("urban", 0.0)
    #         }

    #     merged_area.data["initial_adoptions"]["rural"] = copy.deepcopy(area_rural.data["initial_adoptions"]["rural"])
    #     merged_area.data["initial_adoptions"]["urban"] = copy.deepcopy(area_urban.data["initial_adoptions"]["urban"])

    #     for area_type in ["rural", "urban"]:
    #         merged_area.data["aggregated_clusters"][area_type]["params"] = copy.deepcopy(
    #             area_rural.data["aggregated_clusters"][area_type]["params"]
    #             if area_type == "rural" else
    #             area_urban.data["aggregated_clusters"][area_type]["params"]
    #         )
    #         merged_area.data["aggregated_clusters"][area_type]["clusters"] = copy.deepcopy(
    #             area_rural.data["aggregated_clusters"][area_type]["clusters"]
    #             if area_type == "rural" else
    #             area_urban.data["aggregated_clusters"][area_type]["clusters"]
    #         )

    #     return merged_area





    def store_electricity_costs(self, cost_parameters):
        """
        Save the electricity cost parameters for the demand area.
        This allows having the data available also in the separate instances (rural/urban).
        """
        
        #self.electricity_cost_parameters = copy.deepcopy(cost_parameters)
        
        self.electricity_cost_parameters = dict(cost_parameters)




#-----GETTERS AND SETTERS-----#

    def get_aggregated_clusters(self):
        """
        Returns the aggregated clusters for use by the data manager.
        """
        return self.data["aggregated_clusters"]
    
    def get_local_fuel_multiplier(self, fuel_name, area_type):
        """
        Returns the local fuel price multiplier for the given fuel name and area type.
        
        It retrieves the value from the 'biomass_multipliers' section of the demand area's data.
        If the fuel or area type is not found, it returns a default multiplier of 1.0.
        
        :param fuel_name: The name (or identifier) of the fuel.
        :param area_type: A string, either "rural" or "urban".
        :return: The local fuel price multiplier (float).
        """
        try:
            # Retrieve the biomass multipliers dictionary from the data structure.
            biomass_multipliers = self.data.get("biomass_multipliers", {})
            # Get the dictionary corresponding to local price multipliers.
            loc_price_dict = biomass_multipliers.get("loc_price", {})
            # Get the multiplier for the specified fuel; default to 1.0 for both area types if not found.
            fuel_multiplier = loc_price_dict.get(fuel_name, {"rural": 1.0, "urban": 1.0})
            # Return the value for the requested area type.
            return fuel_multiplier.get(area_type)
        except Exception as e:
            self.logger.error("Error in get_local_fuel_multiplier for fuel '%s' and area '%s': %s", 
                            fuel_name, area_type, e, exc_info=True)
            return 0.0

    