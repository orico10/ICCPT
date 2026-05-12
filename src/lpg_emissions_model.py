import logging
import os
import csv
from src.lpg_emissions_params import LPGEmissionsParameters

class EmissionsLPG:
    def __init__(self, state, data_manager, lpg_area, area_type, lpg_model):
        """
        Constructor for EmissionsLPG.
        
        :param final_costs: Dictionary containing final LPG technology costs.
        :param adjustment_factor: Adjustment factor for emissions calculation.
        """
        self.state = state
        self.data_manager = data_manager
        self.lpg_area = int(lpg_area)
        self.area_type = area_type
        # self.adoption_model = adoption_model
        # self.income_model = income_model
        self.lpg_model = lpg_model
        self.technologies = data_manager.get_dataframe("Cooking_technologies")

        # Reutilizamos los mapeos ya obtenidos.
        # self.fuel_id_to_name = adoption_model.fuel_id_to_names
        # self.appl_id_to_name = adoption_model.appl_id_to_name
        #self.technologies = adoption_model.technologies

        self.fueld_id = lpg_model.fuel_id
        lpg_df = self.technologies[self.technologies["Fuel_id"] == self.fueld_id]
        self.appliance_id = int(lpg_df.iloc[0]["Appliance_id"])

        # Necesito Extraer datos: 
        self.cooking_appliances = data_manager.get_dataframe("Cooking_appliances")
        self.supply_chain = data_manager.get_dataframe("Cooking_supplyChains")
        self.rawMaterial = data_manager.get_dataframe("Cooking_rawMaterials")
        self.cooking_fuels = data_manager.get_dataframe("Cooking_fuels")
        self.raw_mat_id = self.supply_chain["RawMat_id"].loc[self.supply_chain["Fuel_id"] == self.fueld_id].values[0] 
        self.fuelRawEfficiency = self.supply_chain["Efficiency"].loc[self.supply_chain["Fuel_id"] == self.fueld_id].values[0]
        
        #Usage - Emissions Usage Appliances columna "Emissions" fila Appliance_id correspondiente al LPG app 
        self.usage_emissions = self.cooking_appliances["Emissions"].loc[self.cooking_appliances["Appliance_id"] == self.appliance_id].values[0]
        #Efficiency - Emissions Efficiency Appliances columna "Efficiency" fila Appliance_id correspondiente al LPG app
        self.efficiency = self.cooking_appliances["Efficiency"].loc[self.cooking_appliances["Appliance_id"] == self.appliance_id].values[0]
        #Emissions Transportation - Supply Chain columna "Emissions_transportation" fila Fuel_id correspondiente al LPG
        self.emissions_transportation = self.supply_chain["Emissions_transportation"].loc[self.supply_chain["Fuel_id"] == self.fueld_id].values[0]
        #Local Transportation
        self.local_transportation = 2*(self.emissions_transportation)/self.efficiency
        #Upstream transportation
        self.upstream_transportation = (self.emissions_transportation)/(self.efficiency*self.fuelRawEfficiency)
        #Process
        self.emission_process = self.supply_chain["Emissions_processing"].loc[self.supply_chain["Fuel_id"] == self.fueld_id].values[0]
        self.process = self.emission_process/(self.efficiency * self.fuelRawEfficiency)
        #Raw emissions =  Raw pu Emiss/ Fuel/Raw / Efficiency
        self.raw_pu_emissions = self.rawMaterial["Emissions"].loc[self.rawMaterial["RawMat_id"] == self.raw_mat_id].values[0]
        self.cal_val = self.cooking_fuels["Calorific_value"].loc[self.cooking_fuels["Fuel_id"] == self.fueld_id].values[0]
        self.raw_emissions = self.raw_pu_emissions / self.fuelRawEfficiency /(self.efficiency*self.cal_val)

        #Upstream distance del plan LPG Suma de LocalDist_upstream+ DistTo_bottling + DistTo_warehouse
        self.lpg_plan = data_manager.get_dataframe("LPG_areas")
        self.lpg_plan_row = self.lpg_plan.loc[self.lpg_plan["LpgArea_Id"] == self.lpg_area]
        self.local_distance_upstream = self.lpg_plan_row["LocalDist_upstream"].values[0]
        self.dist_to_bottling = self.lpg_plan_row["DistTo_bottling"].values[0]
        self.dist_to_warehouse = self.lpg_plan_row["DistTo_warehouse"].values[0]
        self.upstream_distance = self.local_distance_upstream + self.dist_to_bottling + self.dist_to_warehouse

        

        

        # Y de la clase LPG_CostModel
        # Adoption MCooks/year 
        cp_lpg = lpg_model.lpg_cost_parameters
        self.adoption = cp_lpg.general.consumption.Adjusted_Adoption
        # Demand Rural & Urban MCooks/year
        self.Rur_Demand = lpg_model.current_ch_demand.get("rural", 0.0)
        self.Urb_Demand = lpg_model.current_ch_demand.get("urban", 0.0)
        #Local Distance 
        self.local_distance = cp_lpg.general.costs.Local_Distance

        # Initialize the results structure 
        # Initialize LPG emissions parameters structure
        self.emissions_parameters = LPGEmissionsParameters()

        


    

    def calculate_emissions(self):
        """
        Calculates the emissions for LPG using the formula:
            emission_value = sum(final_costs) * adjustment_factor * base_factor
        where base_factor for LPG is 0.05.
        """
        try:
            # Calculate base emission components
            A = self.adoption * (self.usage_emissions + self.process + self.raw_emissions) / 1000.0
            B = self.adoption * self.local_transportation * self.local_distance / 1000.0
            C = self.adoption * self.upstream_transportation * self.upstream_distance / 1000.0

            # Store general emissions values
            gen = self.emissions_parameters.general
            gen.no_trans = A
            gen.local = B
            gen.upstream = C

            total_emissions = A + B + C

            # Calculate total emissions by area
            Dem_rur = self.Rur_Demand
            Dem_urb = self.Urb_Demand
            total_demand = Dem_rur + Dem_urb

            if total_demand > 0:
                total_emissions_rural = total_emissions * Dem_rur / total_demand
            else:
                total_emissions_rural = 0.0
            total_emissions_urban = total_emissions - total_emissions_rural

            # Upstream emissions breakdown
            if self.adoption > 0:
                upstream_rural = C * Dem_rur / self.adoption
            else:
                upstream_rural = 0.0
            upstream_urban = C - upstream_rural

            # Local emissions breakdown
            if self.adoption > 0:
                local_rural = B * Dem_rur / self.adoption
            else:
                local_rural = 0.0
            local_urban = B - local_rural

            # Usage + Import emissions breakdown
            if self.adoption > 0:
                usage_import_rural = A * Dem_rur / self.adoption
            else:
                usage_import_rural = 0.0
            usage_import_urban = A - usage_import_rural

            # Assign area-specific emissions
            self.emissions_parameters.rural.total = total_emissions_rural
            self.emissions_parameters.urban.total = total_emissions_urban

            self.emissions_parameters.rural.upstream = upstream_rural
            self.emissions_parameters.urban.upstream = upstream_urban

            self.emissions_parameters.rural.local = local_rural
            self.emissions_parameters.urban.local = local_urban

            self.emissions_parameters.rural.usage_import = usage_import_rural
            self.emissions_parameters.urban.usage_import = usage_import_urban

            logging.info("LPG emissions calculated successfully: %s", self.emissions_parameters)
            
        except Exception as e:
            logging.error("Error calculating LPG emissions: %s", e, exc_info=True)
            raise


    def export_lpg_emissions_debug_info(self, output_path, state_id):
        """
        Exporta todos los parámetros de emisiones del modelo LPG a un archivo TSV.
        Imprime los valores por tipo de área: general, rural y urbana, como filas separadas.
        """
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            with open(output_path, "a", newline='') as tsvfile:
                writer = csv.writer(tsvfile, delimiter="\t")

                if os.stat(output_path).st_size == 0:
                    writer.writerow([
                        "State_ID", "LPGArea_ID", "AreaType", "No_transport_Emissions", "Local_Emissions",
                        "Upstream_Emissions",   
                        "Total_Emissions", "Upstream_Emissions", "Local_Emissions",# solo aplica para rural/urban
                        "Usage_Import_Emissions",  # solo aplica para rural/urban
                    ])

                lpg_area_id = self.lpg_area
                e = self.emissions_parameters

                # General
                writer.writerow([
                    state_id,
                    lpg_area_id,
                    "general",
                    round(e.general.no_trans, 4),
                    round(e.general.local, 4),
                    round(e.general.upstream, 4),
                    "",  # no total emissions en general
                    "",  # no usage+import
                    "",  # no usage+import
                    ""  # no usage+import
                ])

                # Rural y urban como filas separadas
                #for area_type in ["rural", "urban"]:
                area_em = e.rural if self.area_type == "rural" else e.urban
                writer.writerow([
                    state_id,
                    lpg_area_id,
                    self.area_type,
                    "",  # no usage+import
                    "",  # no usage+import
                    "",  # no usage+import
                    round(area_em.total, 4),
                    round(area_em.upstream, 4),
                    round(area_em.local, 4),
                    round(area_em.usage_import, 4)
                ])
            logging.info("LPG emissions debug info exported to %s", output_path)
        except Exception as e:
            logging.error("Error exporting LPG emissions debug info: %s", str(e), exc_info=True)
