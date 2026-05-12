import logging
import os 
import csv 
import pandas as pd
from src.lpg_cost_params import LPGCostParameters



class LPGCostModel ():
    def __init__(self, state, prev_state,  mixed_states,  data_manager,lpg_area, areas, simulation_growth_scenario):
        self.state = state
        self.prev_state = prev_state
        self.mixed_states = mixed_states
        self.data_manager = data_manager
        self.lpg_area = int(lpg_area)
        self.demand_areas = areas
        self.growth_scenario = simulation_growth_scenario
        #self.demand_area = demand_area
        #self.adoption_model = adoption_model
        #self.income_model = income_model
       


        # self.fuel_info = self.data_manager.get_fuel_deployments(state.stage_id)
        # self.lpg_fuel = next((f for f in self.fuel_info if f["Fuel_type"] == "LPG"), None)
        #self.demand_areas = []

        #Obtenemos el plan LPG correspondiente al área LPG 
        # Usamos el DataFrame Electricity_areas para obtener los datos de la demanda de electricidad
        self.lpg_plan = data_manager.get_dataframe("LPG_areas")
        self.lpg_plan_row = self.lpg_plan.loc[self.lpg_plan["LpgArea_Id"] == self.lpg_area]

        self.lpg_cost_breakdown = data_manager.get_dataframe("LPG_costBreakdown")



        # Reutilizamos los mapeos ya obtenidos.
        self.fuel_id_to_name = dict(zip(
            data_manager.get_dataframe("Cooking_fuels")["Fuel_id"],
            data_manager.get_dataframe("Cooking_fuels")["Fuel_name"]
        ))
        self.appl_id_to_name = dict(zip(
            data_manager.get_dataframe("Cooking_appliances")["Appliance_id"],
            data_manager.get_dataframe("Cooking_appliances")["Appl_name"]
        ))
        #Extraer growth scenario del adopcion model 
        


        # Inicialio la información relevante para el fuel de LPG
        self.fuel_id = 2

        #Extraer el nombre del fuel de electricidad
        self.fuel_name = self.fuel_id_to_name.get(self.fuel_id, "Unknown_Fuel")
        self.df = data_manager.get_dataframe("enriched_technologies")
        self.tech_id = self.get_fuel_id_to_tech_id(self.fuel_id) #0 es el valor por defecto si no se encuentra el fuel_id

        deployment_plan_details = state.deployment_plan.details 
        self.deployment_plan_fuels_data = deployment_plan_details.get("fuel_reference", [])
        #Extraer el Ref_capacity y Margin del fuel de electricidad (suponiendo que Fuel_id == 2 corresponde a LPG)
        self.lpg_fuel_data = next((fuel for fuel in self.deployment_plan_fuels_data if fuel["Fuel_id"] == self.fuel_id), None)
        if self.lpg_fuel_data is None:
            raise ValueError("No se encontró el fuel de LPG con Fuel_id==2")

        self.lpg_fuel_ref_capacity = self.lpg_fuel_data["Ref_capacity"]
        self.lpg_fuel_margin = self.lpg_fuel_data["Margin"]

        self.raw_mat = data_manager.get_dataframe("Cooking_rawMaterials")
        self.supply_chains = data_manager.get_dataframe("Cooking_supplyChains")

        # Construimos un mapeo Fuel_id → RawMat_id
        self.fuel_to_raw = dict(zip(
            self.supply_chains["Fuel_id"],
            self.supply_chains["RawMat_id"]
        ))
        # Y otro mapa RawMat_id → Cost
        self.raw_to_cost = dict(zip(
            self.raw_mat["RawMat_id"],
            self.raw_mat["Cost"]
        ))
        # Ahora tenemos Fuel_id → Cost
        self.fuel_to_cost = {
            fuel: self.raw_to_cost[raw]
            for fuel, raw in self.fuel_to_raw.items()
        }
        

        # Extraer el target de electricidad a través del fuel_name (por ejemplo, "Electricity") salvo si es el estado base 
        self.base_year = self.growth_scenario.base_year 
        #self.base_year_state = state.get_state(self.base_year)
        self.base_year_state = self.find_state(self.mixed_states, self.base_year, "first")
       
        if self.state.year == self.base_year and self.state.semester == "first":
            self.lpg_target = None
        else:
            #Extraer los detalles del plan de despliegue desde el state
            
            self.deployment_plan_fuels_target = deployment_plan_details.get("fuels_target", [])
            # Obtener el dep_plan_id actual desde el state
            
            
            # Extraer el target de electricidad de la fila encontrada
            self.lpg_target = self.deployment_plan_fuels_target[0].get(self.fuel_name)

    #Parámetros de clase a calcular 
     #Extraer datos necesatios para el modelo de coste -- carga los datos de modelo income YA HACIENDO LA CONVERSIÓN A GWh Y MCOOK 
    #Año 0 - Demanda C+H total = 100% de adopción de tecnologías de calefacción y cocinado eléctricas 
        self.base_ch_demand = {"rural": 0.0, "urban": 0.0} #Demanda base de calefacción y cocinado eléctrica (MCooks/year) para cada segmento (rural y urbano)
        #Para el modelo de costes eléctrico y de C+H
        #Demanda del estado actual de calefacción y cocinado eléctrica
        self.current_ch_demand = {"rural": 0.0, "urban": 0.0} #Demanda de calefacción y cocinado eléctrica (MCooks/year) para cada segmento (rural y urbano)
        #Demanda total CH + Margin 
        self.total_current_ch_demand_capacity = {"rural": 0.0, "urban": 0.0} #Demanda total de calefacción y cocinado eléctrica (MCooks/year) para cada segmento (rural y urbano)
        #Adopción proyectada de demanda de calefacción y cocinado
        self.current_projected_adoption_chdemand = {"rural": 0.0, "urban": 0.0} #Adopción proyectada de calefacción y cocinado eléctrica (MCooks/year) para cada segmento (rural y urbano)
         #Pesos de adopción proyectada 
        self.projection__multilinear_weights_demand = None
        self.projection__multilinear_weights_capacity = None

        self.consumption_without_adjustment = {"rural": 0.0, "urban": 0.0}

        self.lpg_cost_parameters = LPGCostParameters()

        self.total_country_demand = 0.0
        self.area_ratios = []

         #Consumo total de fuel debido a calefacción y cocinado (MTons/year) para el área de LPG
        self.total_fuel_consumption_due_toCH = {"rural": 0.0, "urban": 0.0}#0.0 #Consumo total de fuel debido a calefacción y cocinado (MTons/year) para el área de LPG

    @staticmethod
    def find_state(states_list, year, semester):
        return next((s for s in states_list if s.year == year and s.semester == semester), None)

        
    def get_fuel_id_to_tech_id(self, fuel_id):
        # Filtrar el DataFrame para obtener la fila correspondiente al fuel_id
        row = self.df[self.df["Fuel_id"] == fuel_id]
        if not row.empty:
            return int(row.iloc[0]["Technologies_id"])
        logging.error("No se encontró el fuel_id %s en el DataFrame de eriched_technologies", fuel_id)
        return None

    

    def run_simulation(self):

        try: 
            logging.info("Iniciando la simulación para el área de LPG: %s", self.lpg_area)

            # Calcular demanda de electricidad y calefacción/cocinado + proyección de la adopción 
            self.calculate_initial_params()
            # Calcular consumos generales
            self.calculate_general_consumptions()
            # Calcular las proyecciones de pesos de adopción
            self.calculate_projection_weights()
            #get State values for El Area 
            base_values = self.get_stage_values()
            # Calcular costes generales 
            self.calculate_general_cost(base_values)
            # Calcular factores de sobrecoste
            self.calculate_overcost_factors(base_values)
            # Calcular costes unitarios por rural y urbano
            self.calculate_upu_rpu_costs()
            #Calcular costos finales split rural y urbano
            self.calculate_lpg_cost_splits()
            # Calcular los ratios de área
            self.calculate_ratios()
            # Guardar los resultados en el DataFrame de costos
            self.state.store_lpg_cost_parameters(
                self.lpg_area,
                self.lpg_cost_parameters,
                self.area_ratios
            )
            
            
        except Exception as e:
            logging.error(f"Error al buscar información para el fuel de LPG: {e}")
            return   

    def calculate_initial_params(self):
            "Initialize the initial parameters for the lpg cost model."
        
            try:
                sum_weighted_current = {"rural": 0.0, "urban": 0.0}
                sum_current_adoption = {"rural": 0.0, "urban": 0.0}
                
                #Recorrer las áreas de demanda y suma los valores de todas las áreas por un lado rural y otro urbano 
                for demand_area in self.demand_areas:
                    #for area_type in ["rural", "urban"]:
                    area_type = demand_area.area_type
                    #En el excel obtiene directamente la adopción relativa, yo lo voy a hacer como en electricidad a través la potential adoption  
                    demand_area_id = demand_area.id
                    current_value = self.state.get_CH_consumption(demand_area_id, area_type).get(area_type)
                    if current_value == 0:
                        #AQUÍ ES DONDE TENEMOS QUE PONER K=1 
                        continue #Pasamos de área de demanda 
                    
                    
                    potential_adoption_dis_lpg = self.state.get_potential_adoption_for_tech(demand_area_id, area_type, self.tech_id)
                    #base_value = self.base_year_state.get_CH_consumption(demand_area_id, area_type)
                    base_value = self.base_year_state.get_CH_consumption(demand_area_id, area_type).get(area_type)
                    
                    fuel_consumption = self.state.get_total_fuel_consumption(demand_area_id, area_type).get(self.fuel_id, 0.0)

                    self.base_ch_demand[area_type] += base_value #Nota la demanda base no se ajusta con las adopciones porque damos por hecho que corresponde al 100% de adopción 
                    #self.current_ch_demand[area_type] += current_value

                    sum_weighted_current[area_type] += current_value * potential_adoption_dis_lpg
                    sum_current_adoption[area_type] += potential_adoption_dis_lpg
                    self.consumption_without_adjustment[area_type] += current_value
                    self.total_fuel_consumption_due_toCH[area_type] += fuel_consumption

                # Una vez agregados los valores, calcular la capacidad (demanda total con margen)
                for area_type in ["rural", "urban"]:
                    if sum_current_adoption[area_type] <= 0:
                        logging.warning(f"No hay adopciones acumuladas para {area_type}. Se omite cálculo.")
                        self.current_ch_demand[area_type] = 0.0
                        self.total_current_ch_demand_capacity[area_type] = 0.0
                        self.current_projected_adoption_chdemand[area_type] = 0.0
                        continue


                    self.current_ch_demand[area_type] = sum_weighted_current[area_type]/sum_current_adoption[area_type]
                    self.total_current_ch_demand_capacity[area_type] = self.current_ch_demand[area_type] * (self.lpg_fuel_margin + 1)
                   
                    # Calcular la adopción proyectada: relación entre la demanda actual y la demanda base
                    # Se previene la división por cero asignando 1.0 (o 0) en caso de que la demanda base sea 0.
                    if self.base_ch_demand[area_type] > 0:
                        self.current_projected_adoption_chdemand[area_type] = self.current_ch_demand[area_type] / self.base_ch_demand[area_type]
                    else:
                        #Warning si la demanda base es 0
                        logging.warning("The base demand for %s is 0. Assigning 0.0 as projected adoption.", area_type)
                        self.current_projected_adoption_chdemand[area_type] = 0.0

                    #Saving consumption due to Ch in state 
                    self.state.set_total_lpg_consumption_due_toCH(self.lpg_area, area_type, self.total_fuel_consumption_due_toCH[area_type])

            except Exception as e:
                logging.error("Error calculating initial parameters for lpg: %s", str(e))
                raise
    
    
    def calculate_general_consumptions(self):
        """
        Calculates the general LPG consumptions.

        It uses:
        - self.current_ch_demand: a dictionary with keys "rural" and "urban" containing the current CH consumption (MCooks/year) for each segment.
        - self.lpg_fuel_ref_capacity: the reference capacity (Ref) for LPG.
        - self.lpg_fuel_margin: the LPG margin (in decimal, e.g., 0.1 for 10%).

        It calculates:
        - Demand: the sum of the current rural and urban consumption (without adoption adjustment).
        - Reference_Demand: Demand * Ref.
        - Adjusted_Capacity: Demand * (1 + Margin).
        - Adjusted_Adoption: Assumed equal to Demand.

        These values are stored in an instance of LPGGeneralConsumption within self.lpg_cost_parameters.
        """
        try:
            cp = self.lpg_cost_parameters 
            # Sumar los consumos actuales de CH para áreas rurales y urbanas.
            rural = self.consumption_without_adjustment.get("rural", 0.0)
            urban = self.consumption_without_adjustment.get("urban", 0.0)

            # Forzamos a escalar si vienen como Series
            if isinstance(rural, pd.Series):
                rural = rural.item()
            if isinstance(urban, pd.Series):
                urban = urban.item()

            consumption_without_adjustment = rural + urban
            #reference_demand = consumption_without_adjustment * self.lpg_fuel_ref_capacity

            
            # Demanda absoluta (sin ajuste de adopción)
            demand = consumption_without_adjustment
            
            # La Demanda de Referencia se calcula multiplicando por la capacidad de referencia
            Ref = self.lpg_fuel_ref_capacity  # Por ejemplo, puede estar definido en la configuración.
            reference_demand = demand * Ref
            
            # La capacidad ajustada se obtiene aplicando el margen
            margin = self.lpg_fuel_margin   # Ejemplo: 0.1 para 10%
            adjusted_capacity = (self.current_ch_demand.get("rural", 0.0) + self.current_ch_demand.get("urban", 0.0)) + (demand + margin)
            
            # La adopción ajustada, en este caso, se asume igual a la demanda actual (puede ajustarse según el modelo)
            adjusted_adoption = (self.current_ch_demand.get("rural", 0.0) + self.current_ch_demand.get("urban", 0.0))
            
            # Crear la instancia de LPGGeneralConsumption con los valores calculados
            cp.general.consumption.Demand = demand
            cp.general.consumption.Reference_Demand = reference_demand
            cp.general.consumption.Adjusted_Capacity= adjusted_capacity
            cp.general.consumption.Adjusted_Adoption = adjusted_adoption
            
            
            logging.info("General LPG consumptions calculated: %s", cp.general.consumption)
        except Exception as e:
            logging.error("Error calculating general LPG consumptions: %s", str(e))
            raise


    def _compute_lpg_adoption_weights(self, adopt_rur: float, adopt_urb: float, Ref: float) -> dict:
        """
        Calculate the weights for LPG adoption using the formula:
            W1 = (Ref - AdoptInter(Rur)) * (Ref - AdoptInter(Urb)) / (Ref*Ref)
            W2 = (AdoptInter(Urb) * (Ref - AdoptInter(Rur))) / (Ref*Ref)
            W3 = (AdoptInter(Rur) * (Ref - AdoptInter(Urb))) / (Ref*Ref)
            W4 = (AdoptInter(Rur) * AdoptInter(Urb)) / (Ref*Ref)
    
        :return: Dic with keys "W1", "W2", "W3" y "W4".
        """
        W1 = (Ref - adopt_rur) * (Ref - adopt_urb) / (Ref * Ref)
        W2 = (adopt_urb * (Ref - adopt_rur)) / (Ref * Ref)
        W3 = (adopt_rur * (Ref - adopt_urb)) / (Ref * Ref)
        W4 = (adopt_rur * adopt_urb) / (Ref * Ref)
        return {"W1": W1, "W2": W2, "W3": W3, "W4": W4}

    def _compute_lpg_capacity_weights(self, adopt_rur: float, adopt_urb: float, Ref: float, Margin: float) -> dict:
        """
        Calculate the weights for LPG capacity using the formula:
        
            W1 = (Ref - adopt_rur - Margin) * (Ref - adopt_urb - Margin) / (Ref*Ref)
            W2 = (Ref - adopt_rur - Margin) * (adopt_urb + Margin) / (Ref*Ref)
            W3 = (adopt_rur + Margin) * (Ref - adopt_urb - Margin) / (Ref*Ref)
            W4 = (adopt_rur + Margin) * (adopt_urb + Margin) / (Ref*Ref)
       
        :return: Dictionary weights "W1", "W2", "W3" y "W4".
        """
        W1 = (Ref - adopt_rur - Margin) * (Ref - adopt_urb - Margin) / (Ref * Ref)
        W2 = (Ref - adopt_rur - Margin) * (adopt_urb + Margin) / (Ref * Ref)
        W3 = (adopt_rur + Margin) * (Ref - adopt_urb - Margin) / (Ref * Ref)
        W4 = (adopt_rur + Margin) * (adopt_urb + Margin) / (Ref * Ref)
        return {"W1": W1, "W2": W2, "W3": W3, "W4": W4}

    def calculate_projection_weights(self):
        """
        Calculate the projection weights for LPG adoption and capacity.
        Save the results in the corresponding lpg_capacity or lpg_adoption attributes.
        """
        try:
            Ref = self.lpg_fuel_ref_capacity
            Margin = self.lpg_fuel_margin
            # Valores proyectados para adopción en LPG (por ejemplo, para el grupo LPG)
            adopt_rur = self.current_projected_adoption_chdemand["rural"]
            adopt_urb = self.current_projected_adoption_chdemand["urban"]

            weights_adoption = self._compute_lpg_adoption_weights(adopt_rur, adopt_urb, Ref)
            weights_capacity = self._compute_lpg_capacity_weights(adopt_rur, adopt_urb, Ref, Margin)

            self.projection_multilinear_weights_lpg_adoption = weights_adoption
            self.projection_multilinear_weights_lpg_capacity = weights_capacity

            logging.info("LPG Projection weights (adoption) calculated: %s", weights_adoption)
            logging.info("LPG Projection weights (capacity) calculated: %s", weights_capacity)
        except Exception as e:
            logging.error("Error calculating LPG projection weights: %s", str(e))
            raise

    def weighted_sum(self, values: list, weights: dict) -> float:
        """
        Calculate the weighted sum of a list of values using the given weights.
      
        :return: Weighted sum of the values. 
        """
        return (weights["W1"] * values[0] + 
                weights["W2"] * values[1] +
                weights["W3"] * values[2] +
                weights["W4"] * values[3])
    
   
    def get_stage_values(self):
        """
        Obtain the values for the current stage.
        Ensures all values are extracted as scalars using .iloc[0] if needed.
        """
        try:
            row = self.lpg_plan_row

            def scalar(val):
                return val.iloc[0] if isinstance(val, pd.Series) else val

            return {
                "lpg_area_id": scalar(row["LpgArea_Id"]),
                "sup_area_name": scalar(row["SupArea_Name"]),
                "st2_capex": scalar(row["St2_CAPEX"]),
                "st2_opex_og": scalar(row["St2_OPEX_OG"]),
                "st2_localdist": scalar(row["St2_LocalDist"]),
                "st3_capex": scalar(row["St3_CAPEX"]),
                "st3_opex_og": scalar(row["St3_OPEX_OG"]),
                "st3_localdist": scalar(row["St3_LocalDist"]),
                "st4_capex": scalar(row["St4_CAPEX"]),
                "st4_opex_og": scalar(row["St4_OPEX_OG"]),
                "st4_localdist": scalar(row["St4_LocalDist"]),
                "capex_upstream": scalar(row["CAPEX_upstream"]),
                "opex_upstream": scalar(row["OPEX_upstream"]),
                "localdist_upstream": scalar(row["LocalDist_upstream"]),
                "dist_to_bottling": scalar(row["DistTo_bottling"]),
                "dist_to_warehouse": scalar(row["DistTo_warehouse"]),
                "dist_to_retailer": scalar(row["DistTo_retailer"])
            }

        except Exception as e:
            logging.error("Error al obtener los valores del estado base: %s", str(e), exc_info=True)
            raise


    def calculate_general_cost(self, base_values):
        """
        Calculates the general LPG cost parameters using the projection weights and stage values.

        The formulas used are:
        - FIX_Cost = max( W2Cap * FixCost(st2) + W3Cap * FixCost(st3) + W4Cap * FixCost(st4), 0 )
        - VAR_Cost = max( W2Adopt * VarCost(st2) + W3Adopt * VarCost(st3) + W4Adopt * VarCost(st4), 0 )
        - Local_Distance = max( W2Cap * LocalDist(st2) + W3Cap * LocalDist(st3) + W4Cap * LocalDist(st4), 0 )
        
        Additionally, upstream costs are adjusted as:
            Ups_FIX = capex_upstream * (Adjusted_Capacity / Reference_Demand)
            Ups_VAR = opex_upstream * (Adjusted_Adoption / Reference_Demand)

        The capacity-related weights are taken from self.projection_multilinear_weights_lpg_capacity,
        and the adoption-related weights from self.projection_multilinear_weights_lpg_adoption.
        
        The stage values are obtained by get_stage_values(), which returns a dictionary with keys:
        - "st2_capex", "st3_capex", "st4_capex"
        - "st2_opex_og", "st3_opex_og", "st4_opex_og"
        - "st2_localdist", "st3_localdist", "st4_localdist"
        - "capex_upstream", "opex_upstream", etc.
        
        The calculated values are stored in self.lpg_cost_parameters.general.costs.
        """
        try:
            
            # For FIX_Cost, use capacity weights and CAPEX values from st2, st3, st4.
            # Prepend 0.0 for st1 (not available).
            fix_cost_values = [0.0, base_values["st2_capex"], base_values["st3_capex"], base_values["st4_capex"]]
            cap_weights = self.projection_multilinear_weights_lpg_capacity
            weighted_fix_cost = self.weighted_sum(fix_cost_values, cap_weights)
            fix_cost = max(weighted_fix_cost, 0.0)

            # For VAR_Cost, use adoption weights and OPEX_OG values from st2, st3, st4.
            var_cost_values = [0.0, base_values["st2_opex_og"], base_values["st3_opex_og"], base_values["st4_opex_og"]]
            adopt_weights = self.projection_multilinear_weights_lpg_adoption
            weighted_var_cost = self.weighted_sum(var_cost_values, adopt_weights)
            var_cost = max(weighted_var_cost, 0.0)

            # For Local_Distance, use capacity weights and LocalDist values from st2, st3, st4.
            local_dist_values = [0.0, base_values["st2_localdist"], base_values["st3_localdist"], base_values["st4_localdist"]]
            weighted_local_distance = self.weighted_sum(local_dist_values, cap_weights)
            local_distance = max(weighted_local_distance, 0.0)

            # Retrieve general consumption values already calculated:
            # These should have been computed in calculate_general_consumptions:
            #   - Adjusted_Capacity and Adjusted_Adoption are stored in self.lpg_cost_parameters.general.consumption.
            gc = self.lpg_cost_parameters.general.consumption
            adjusted_capacity = gc.Adjusted_Capacity
            adjusted_adoption = gc.Adjusted_Adoption
            reference_demand = gc.Reference_Demand

            # Compute upstream costs using the formulas:
            # Ups_FIX = capex_upstream * (Adjusted_Capacity / Reference_Demand)
            # Ups_VAR = opex_upstream * (Adjusted_Adoption / Reference_Demand)
            if reference_demand > 0:
                ups_fix = base_values["capex_upstream"] * (adjusted_capacity / reference_demand)
                ups_var = base_values["opex_upstream"] * (adjusted_adoption / reference_demand)
            else:
                ups_fix = ups_var = 0.0

            # Store the calculated general cost parameters in LPGCostParameters.
            cp = self.lpg_cost_parameters
            cp.general.costs.FIX_Cost = fix_cost
            cp.general.costs.VAR_Cost = var_cost
            cp.general.costs.Local_Distance = local_distance

            # Store the computed upstream costs.
            cp.general.costs.Ups_FIX_Cost = ups_fix
            cp.general.costs.Ups_VAR_Cost = ups_var

            logging.info("General LPG costs calculated: FIX_Cost=%.4f, VAR_Cost=%.4f, Local_Distance=%.4f, Ups_FIX=%.4f, Ups_VAR=%.4f",
                        fix_cost, var_cost, local_distance, ups_fix, ups_var)
        except Exception as e:
            logging.error("Error calculating general LPG costs: %s", str(e))
            raise

    def calculate_overcost_factors(self, base_values):
        """
        Calculates the overcost factors for LPG supply areas, separately for rural and urban segments.
        
        Uses the aggregated capacities and demands along with stage cost values.
        
        If both rural and urban segments exist (nonzero capacity and demand), then:
        overcost_factor_fix = (total_capacity_urban * fixCost_st3) / (total_capacity_rural * fixCost_st2)
        overcost_factor_var = (total_demand_urban * varCost_st3) / (total_demand_rural * varCost_st2)
        Otherwise, assigns 1.0 for the corresponding factor.
        """
        try:
            # Retrieve aggregated capacities and demands
            total_capacity_rural = self.total_current_ch_demand_capacity["rural"]
            total_capacity_urban = self.total_current_ch_demand_capacity["urban"]
            total_demand_rural = self.consumption_without_adjustment["rural"]
            total_demand_urban = self.consumption_without_adjustment["urban"]
            
            # Retrieve stage cost values for fix and variable from the plan data
            ld = base_values  # Expected keys: 'fixCost_st2', 'fixCost_st3', 'varCost_st2', 'varCost_st3'
            cp = self.lpg_cost_parameters
            if (total_capacity_rural * ld['st2_capex'] > 0.0 and 
                    total_demand_rural * ld['st2_opex_og'] > 0.0):

                cp.general.costs.FIX_local_overcost_factor = (
                    total_capacity_urban * ld['st3_capex']
                ) / (
                    total_capacity_rural * ld['st2_capex']
                )

                cp.general.costs.VAR_local_overcost_factor = (
                    total_demand_urban * ld['st3_opex_og']
                ) / (
                    total_demand_rural * ld['st2_opex_og']
                )
            else:
                cp.general.costs.FIX_local_overcost_factor = 1.0
                cp.general.costs.VAR_local_overcost_factor = 1.0

            
            logging.info("LPG OverCost Factors calculated: FIX = %.4f, VAR = %.4f", 
                        cp.general.costs.FIX_local_overcost_factor, cp.general.costs.VAR_local_overcost_factor)
        except Exception as e:
            logging.error("Error calculating LPG overcost factors: %s", str(e))
            raise

    def calculate_upu_rpu_costs(self):
        """
        Calculates the unit costs (Upu) and the adjusted unit costs (Rpu) for LPG supply areas,
        separately for rural and urban segments.
        
        The formulas are:
        For FIX costs:
            denominator_fix = (overcost_factor_fix * total_capacity_rural) + total_capacity_urban
            upu_fix = fix_cost_LPG / denominator_fix      ;   rpu_fix = overcost_factor_fix * upu_fix
        For VAR costs:
            denominator_var = (overcost_factor_var * total_demand_rural) + total_demand_urban
            upu_var = var_cost_LPG / denominator_var      ;   rpu_var = overcost_factor_var * upu_var
        """
        try:
            # Retrieve aggregated capacities/demands and already computed overcost factors.
            total_capacity_rural = self.total_current_ch_demand_capacity["rural"]
            total_capacity_urban = self.total_current_ch_demand_capacity["urban"]
            total_demand_rural = self.consumption_without_adjustment["rural"]
            total_demand_urban = self.consumption_without_adjustment["urban"]
            
            # fix_cost_LPG and var_cost_LPG should have been computed previously.
            cp = self.lpg_cost_parameters
            overcost_factor_fix = cp.general.costs.FIX_local_overcost_factor
            overcost_factor_var = cp.general.costs.VAR_local_overcost_factor
            # Retrieve the fix and var costs from the general costs.
            fix_cost_LPG = cp.general.costs.FIX_Cost
            var_cost_LPG = cp.general.costs.VAR_Cost
            
            # Calculate denominators for FIX and VAR costs.
            den_fix = (overcost_factor_fix * total_capacity_rural) + total_capacity_urban
            den_var = (overcost_factor_var * total_demand_rural) + total_demand_urban
            
            # Calculate Upu and Rpu for FIX costs.
            if den_fix > 0.0:
                cp.urban.costs.FIX_local_overcost_u = fix_cost_LPG / den_fix
                cp.rural.costs.FIX_local_overcost_r = overcost_factor_fix * cp.urban.costs.FIX_local_overcost_u
                
            else:
                cp.urban.costs.FIX_local_overcost_u = cp.rural.costs.FIX_local_overcost_r  = 0.0
            
            # Calculate Upu and Rpu for VAR costs.
            if den_var > 0.0:
                cp.urban.costs.VAR_local_overcost_u = var_cost_LPG / den_var
                cp.rural.costs.VAR_local_overcost_r = overcost_factor_var * cp.urban.costs.VAR_local_overcost_u
                
            else:
                cp.urban.costs.VAR_local_overcost_u = cp.rural.costs.VAR_local_overcost_r = 0.0
                
            
            logging.info("LPG Upu/Rpu Costs calculated: Rural Rpu Fix = %.4f, Urban Upu Fix = %.4f, Rural Rpu Var = %.4f, Urban Upu Var = %.4f",
                        cp.rural.costs.FIX_local_overcost_r, cp.urban.costs.FIX_local_overcost_u,
                        cp.rural.costs.VAR_local_overcost_r, cp.urban.costs.VAR_local_overcost_u)
        except Exception as e:
            logging.error("Error calculating LPG Upu/Rpu costs: %s", str(e))
            raise

    def calculate_lpg_cost_splits(self):
        """
        Calculates the LPG cost splits (upstream cost splits) for the current LPG group.
        
        For FIX costs:
        - Rural FIX Split Cost = (overCostFactor_FIX * upu_FIX) + total_capacity_rural
        - Urban FIX Split Cost = upu_FIX * total_capacity_urban
        
        For VAR costs:
        - Rural VAR Split Cost = (overCostFactor_VAR * upu_VAR) + total_demand_rural
        - Urban VAR Split Cost = upu_VAR * total_demand_urban
        
        These values are stored in the LPGCostParameters instance:
        - self.lpg_cost_parameters.rural.costs.FIX_Ups_Cost_r
        - self.lpg_cost_parameters.urban.costs.FIX_Ups_Cost_u
        - self.lpg_cost_parameters.rural.costs.VAR_Ups_Cost_r
        - self.lpg_cost_parameters.urban.costs.VAR_Ups_Cost_u
        """
        try:
            # Retrieve the already computed Upu and Rpu costs.
            cp = self.lpg_cost_parameters
            adj_adop = cp.general.consumption.Adjusted_Adoption 
            ups_fix = cp.general.costs.Ups_FIX_Cost
            ups_var = cp.general.costs.Ups_VAR_Cost
            
            # Calculate FIX cost splits:
            if (adj_adop > 0.0 and self.current_ch_demand["rural"] > 0.0):
                rural_fix_split = ups_fix * self.current_ch_demand["rural"] / adj_adop 
                urban_fix_split = ups_fix  - rural_fix_split
            else:
                rural_fix_split =  0.0
                urban_fix_split = ups_fix  - rural_fix_split
                
                
            # Calculate VAR cost splits:
            if (adj_adop > 0.0 and self.current_ch_demand["rural"] > 0.0):
                rural_var_split = ups_var * self.current_ch_demand["rural"] / adj_adop 
                urban_var_split = ups_var  - rural_var_split
            else:
                rural_var_split =  0.0
                urban_var_split = ups_var  - rural_var_split
                

            # Store the results in the cost parameters structure.
            cp = self.lpg_cost_parameters
            cp.rural.costs.FIX_Ups_Cost_r = rural_fix_split
            cp.urban.costs.FIX_Ups_Cost_u = urban_fix_split
            cp.rural.costs.VAR_Ups_Cost_r = rural_var_split
            cp.urban.costs.VAR_Ups_Cost_u = urban_var_split

            logging.info("LPG Cost Splits calculated: Rural FIX = %.4f, Urban FIX = %.4f, Rural VAR = %.4f, Urban VAR = %.4f",
                        rural_fix_split, urban_fix_split, rural_var_split, urban_var_split)
        except Exception as e:
            logging.error("Error calculating LPG cost splits: %s", str(e))
            raise



    def calculate_ratios(self):
        """
        Calculate the cost-benefit ratios for LPG in rural and urban areas.

        Formula used:
        Ratio = min((Ups_FIX_Cost + Local_Overcost_Fix + Ups_VAR_Cost ) / current_demand, 5)

        Returns:
            dict: Ratios for "rural" and "urban".
        """
        try:
            cp = self.lpg_cost_parameters
            ratios = {}

            for area_type in ["rural", "urban"]:
                area_cp = cp.rural if area_type == "rural" else cp.urban

                ups_fix = area_cp.costs.FIX_Ups_Cost_r if area_type == "rural" else area_cp.costs.FIX_Ups_Cost_u
                local_fix = area_cp.costs.FIX_local_overcost_r if area_type == "rural" else area_cp.costs.FIX_local_overcost_u
                ups_var = area_cp.costs.VAR_Ups_Cost_r if area_type == "rural" else area_cp.costs.VAR_Ups_Cost_u
                #local_var = area_cp.costs.VAR_local_overcost_r if area_type == "rural" else area_cp.costs.VAR_local_overcost_u
                
                # cp.urban.costs.FIX_local_overcost_u
                demand = self.current_ch_demand.get(area_type, 0.0)

                if demand > 0:
                    #ratio = min((ups_fix + local_fix + ups_var + local_var) / demand, 5)
                    ratio = min((ups_fix + local_fix + ups_var) / demand, 5)
                else:
                    ratio = 5

                self.add_lpgarea_result(self.lpg_area, area_type, ratio, demand)
                ratios[area_type] = ratio

            return ratios
        except Exception as e:
            logging.error("Error calculating LPG ratios: %s", str(e), exc_info=True)
            raise


    def add_lpgarea_result(self, lpg_area_id, area_type, ratio, current_area_demand):
        """
        Stores the LPG area-level result.
        
        :param lpg_area_id: Identifier for the LPG supply area.
        :param area_type: "rural" or "urban".
        :param ratio: Calculated cost-benefit ratio for this segment.
        :param current_area_demand: Current CH demand for the segment (MCooks/year).
        """
        # Update total country demand with the current segment's demand.
        self.total_country_demand += current_area_demand
        # Append the result as a dictionary to the aggregated LPG area results.
        self.area_ratios.append({
            "lpg_area_id": lpg_area_id,
            "area_type": area_type,
            "ratio": ratio,
            "demand": current_area_demand
        })
        logging.info("LPG Area result added: ID %s, Type %s, Ratio: %.4f, Demand: %.2f",
                    lpg_area_id, area_type, ratio, current_area_demand)

   

    def get_sorted_area_ratios(self):
        """
        Retuns the list of area ratios sorted by the ratio value.
        :return: dict with keys: id, area_type, ratio, demand.
        """
        return sorted(self.area_ratios, key=lambda x: x["ratio"])


    def adjust_final_cost_lpg_from_parameters(self, cost_parameters, area_type, lpg_area_id):
        """
        Adjusts the final LPG costs based on cost variation parameters from the state.
        """
        try:
            # Coger los datos del estado para el fuel LPG 
            dep_cost_variation = self.state.get_dep_cost_variation(self.fuel_id)
            # Obtener Process & Transport de esta estructura % de crecimiento anual 
            process_cost = dep_cost_variation['Process']
            transport_cost = dep_cost_variation['Transport']
            molecule_cost = dep_cost_variation['Molecule']

            cp = cost_parameters 
            df = self.lpg_cost_breakdown

            if self.prev_state is not None:
                # Si no hay estado previo, usamos el actual
                #dep_cost_variation_prev = dep_cost_variation
                # Obtener Process & Transport de esta estructura % de crecimiento anual
                


                dep_cost_variation_prev = self.prev_state.get_dep_cost_variation(self.fuel_id)
                # Obtener Process & Transport de esta estructura % de crecimiento anual
                process_cost_prev = dep_cost_variation_prev['Process']
                transport_cost_prev = dep_cost_variation_prev['Transport']  
                molecule_cost_prev = dep_cost_variation_prev['Molecule'] # % de crecimiento anual

                areas_lpg_deployed_prev = self.prev_state.get_lpg_deployed_areas()
                areas_lpg_deployed_prev = list(areas_lpg_deployed_prev)
                #if (lpg_area_id, area_type) in areas_lpg_deployed_prev:
                lpg_cost_params_prev = self.prev_state.get_lpg_cost_parameters(lpg_area_id)
                lpg_cost_params_prev = lpg_cost_params_prev['cost_parameters']

            # Noizamos los costes del año base 

            
                # ESTO YA LO HAGO EN EL MÉTODO EN LA CLASE STATE 
                Factor_Fix_Upstream_prev = (1 + transport_cost_prev) * df.loc[df['Data'] == 'Transport_fraction_FIX', 'Upstream'].values[0] + \
                                    (1 + process_cost_prev) * df.loc[df['Data'] == 'Process_fraction_FIX', 'Upstream'].values[0]
                Factor_Fix_Local_prev = (1 + transport_cost_prev) * df.loc[df['Data'] == 'Transport_fraction_FIX', 'Local'].values[0] + \
                                (1 + process_cost_prev) * df.loc[df['Data'] == 'Process_fraction_FIX', 'Local'].values[0]
            
            
                
                if area_type == "rural":
                    
                    cp.rural.costs.FIX_Ups_Cost_r = max(lpg_cost_params_prev.rural.costs.FIX_Ups_Cost_r / Factor_Fix_Upstream_prev, cp.rural.costs.FIX_Ups_Cost_r)
                    cp.rural.costs.FIX_local_overcost_r =  max(lpg_cost_params_prev.rural.costs.FIX_local_overcost_r / Factor_Fix_Local_prev, cp.rural.costs.FIX_local_overcost_r)
                
                if area_type == "urban":
                    cp.urban.costs.FIX_Ups_Cost_u  = max(lpg_cost_params_prev.urban.costs.FIX_Ups_Cost_u / Factor_Fix_Upstream_prev,  cp.urban.costs.FIX_Ups_Cost_u )
                    cp.urban.costs.FIX_local_overcost_u = max(lpg_cost_params_prev.urban.costs.FIX_local_overcost_u / Factor_Fix_Local_prev, cp.urban.costs.FIX_local_overcost_u)
                
                


            # # tenemos que aplicar el crecimiento con respecto al año cero (1+ porcentaje de crecimiento) ^ (num de años entre el estado inicial y el actual - 1)
            # transport_cost = (1 + transport_cost) ** (self.state.current_year - self.state.base_year) - 1
            # process_cost = (1 + process_cost) ** (self.state.current_year - self.state.base_year) - 1
            # molecule_cost = (1 + molecule_cost) ** (self.state.current_year - self.state.base_year) - 1
            # # Camculamos el coste de la molécula 
            # Cost_pu del raw mat  ($/Kg o kwh) 
            cost_for_my_fuel = self.fuel_to_cost.get(self.fuel_id) #$/kg o $/kwh
            # comsumption_due_to_ch = self.state.get_total_fuel_consumption(self, demand_area_id, area_type)
            #Método que calcula los consumos agrupados de todas las áreas que pertenecen a un área LPG y para un mismo fuel 
            lpg_area_consumption_due_to_ch = self.state.get_total_lpg_consumption_due_toCH(lpg_area_id,  area_type)# *1e6 # Ktons/yr a Kg/yr -- Ya viene en KTons/yr
            year_diff = self.state.year - self.growth_scenario.base_year

            # Calculamos el coste de la molécula para el área LPG
            if lpg_area_consumption_due_to_ch > 0:
                final_import  = cost_for_my_fuel * lpg_area_consumption_due_to_ch * (1+ molecule_cost)#/1e6#**(year_diff)/1e6 # M$/yr
            else:
                final_import = 0.0



            # Tomo los datos de self.dep_cost_breakdown para el fuel LPG
           

            Factor_Fix_Upstream = (1 + transport_cost) * df.loc[df['Data'] == 'Transport_fraction_FIX', 'Upstream'].values[0] + \
                                (1 + process_cost) * df.loc[df['Data'] == 'Process_fraction_FIX', 'Upstream'].values[0]
            Factor_Fix_Local = (1 + transport_cost) * df.loc[df['Data'] == 'Transport_fraction_FIX', 'Local'].values[0] + \
                            (1 + process_cost) * df.loc[df['Data'] == 'Process_fraction_FIX', 'Local'].values[0]
            Factor_Var_Upstream = (1 + transport_cost) * df.loc[df['Data'] == 'Transport_fraction_VAR', 'Upstream'].values[0] + \
                                (1 + process_cost) * df.loc[df['Data'] == 'Process_fraction_VAR', 'Upstream'].values[0]
            Factor_Var_Local = (1 + transport_cost) * df.loc[df['Data'] == 'Transport_fraction_VAR', 'Local'].values[0] + \
                            (1 + process_cost) * df.loc[df['Data'] == 'Process_fraction_VAR', 'Local'].values[0]
            
            # Pasamos los parçametros a porcentajes unitarios
            # Factor_Fix_Upstream = Factor_Fix_Upstream #/ 100.0
            # Factor_Fix_Local = Factor_Fix_Local #/ 100.0
            # Factor_Var_Upstream = Factor_Var_Upstream #/ 100.0
            # Factor_Var_Local = Factor_Var_Local #/ 100.0

            if area_type == "rural": 
                cp.rural.costs.FINAL_FIX_Cost_Upstream = cp.rural.costs.FIX_Ups_Cost_r * Factor_Fix_Upstream
                cp.rural.costs.FINAL_FIX_Cost_Local = cp.rural.costs.FIX_local_overcost_r * Factor_Fix_Local
                cp.rural.costs.FINAL_VAR_Cost_Upstream = cp.rural.costs.VAR_Ups_Cost_r * Factor_Var_Upstream
                cp.rural.costs.FINAL_VAR_Cost_Local = cp.rural.costs.VAR_local_overcost_r * Factor_Var_Local
                cp.rural.costs.FINAL_VAR_Cost_Import = final_import #* Factor_Var_Upstream# Añadimos el coste de importación para el área rural

            elif area_type == "urban":
                cp.urban.costs.FINAL_FIX_Cost_Upstream = cp.urban.costs.FIX_Ups_Cost_u * Factor_Fix_Upstream
                cp.urban.costs.FINAL_FIX_Cost_Local = cp.urban.costs.FIX_local_overcost_u * Factor_Fix_Local
                cp.urban.costs.FINAL_VAR_Cost_Upstream = cp.urban.costs.VAR_Ups_Cost_u * Factor_Var_Upstream
                cp.urban.costs.FINAL_VAR_Cost_Local = cp.urban.costs.VAR_local_overcost_u * Factor_Var_Local
                cp.urban.costs.FINAL_VAR_Cost_Import = final_import #* Factor_Var_Upstream # Añadimos el coste de importación para el área urbana
                

            logging.info("Ajuste de costes finales LPG completado para área %s (%s)", lpg_area_id, area_type)

        except Exception as e:
            logging.error("Error ajustando costes finales LPG (%s - %s): %s", lpg_area_id, area_type, str(e), exc_info=True)
            raise

    # def _compute_lpg_block_multipliers(self, proc_incr: float, tran_incr: float, df) -> dict:
    #     """
    #     Build weighted multipliers for LPG FIX/VAR, Local/Upstream:
    #     fix_mult_up, fix_mult_lo, var_mult_up, var_mult_lo
    #     Fractions in df are already p.u. We renormalize defensively so process+transport ≈ 1 per block.
    #     """
    #     try:
    #         def pick(label, col):
    #             vals = df.loc[df['Data'] == label, col].values
    #             if len(vals) == 0:
    #                 raise ValueError(f"Missing '{label}' for column '{col}' in lpg_cost_breakdown.")
    #             return float(vals[0])

    #         def renorm(a, b):
    #             s = a + b
    #             return (0.0, 0.0) if s <= 0 else (a / s, b / s)

    #         # Shares (p.u.), renormalize as safety
    #         p_fix_loc,  t_fix_loc  = renorm(pick('Process_fraction_FIX','Local'),   pick('Transport_fraction_FIX','Local'))
    #         p_fix_up,   t_fix_up   = renorm(pick('Process_fraction_FIX','Upstream'),pick('Transport_fraction_FIX','Upstream'))
    #         p_var_loc,  t_var_loc  = renorm(pick('Process_fraction_VAR','Local'),   pick('Transport_fraction_VAR','Local'))
    #         p_var_up,   t_var_up   = renorm(pick('Process_fraction_VAR','Upstream'),pick('Transport_fraction_VAR','Upstream'))

    #         # Multipliers (current cumulative increments vs base)
    #         fix_proc_mult = 1.0 + float(proc_incr)
    #         fix_tran_mult = 1.0 + float(tran_incr)
    #         var_proc_mult = 1.0 + float(proc_incr)
    #         var_tran_mult = 1.0 + float(tran_incr)

    #         return {
    #             "fix_mult_up": fix_tran_mult * t_fix_up + fix_proc_mult * p_fix_up,
    #             "fix_mult_lo": fix_tran_mult * t_fix_loc + fix_proc_mult * p_fix_loc,
    #             "var_mult_up": var_tran_mult * t_var_up + var_proc_mult * p_var_up,
    #             "var_mult_lo": var_tran_mult * t_var_loc + var_proc_mult * p_var_loc,
    #         }
    #     except Exception as e:
    #         logging.error("Failed to compute LPG multipliers: %s", str(e), exc_info=True)
    #         raise


    # def adjust_final_cost_lpg_from_parameters(self, cost_parameters, area_type, lpg_area_id):
    #     """
    #     Adjust final LPG costs using cumulative (already compounded) variations vs base-year.
    #     ALWAYS normalize back to base when prev_state exists, regardless of whether the area was 'deployed'.
    #     No double exponent for molecule import: use (1 + mol_incr) only.
    #     """
    #     try:
    #         if area_type not in ("rural", "urban"):
    #             raise ValueError(f"Invalid area_type='{area_type}'")

    #         fuel_id = self.fuel_id  # LPG=2
    #         cp = cost_parameters
    #         df = self.lpg_cost_breakdown

    #         # -- Current cumulative increments (vs base) --
    #         dep = self.state.get_dep_cost_variation(fuel_id) or {'Process':0.0,'Transport':0.0,'Molecule':0.0}
    #         proc_incr = float(dep['Process'])
    #         tran_incr = float(dep['Transport'])
    #         mol_incr  = float(dep['Molecule'])

    #         # -- Current-state multipliers (from df + current increments) --
    #         cur_mult = self._compute_lpg_block_multipliers(proc_incr, tran_incr, df)

    #         # -- Previous-state multipliers (identity if no prev_state) --
    #         prev_fix_mult_up = prev_fix_mult_lo = prev_var_mult_up = prev_var_mult_lo = 1.0
    #         prev_cp = None
    #         if self.prev_state is not None:
    #             prev_dep = self.prev_state.get_dep_cost_variation(fuel_id) or {'Process':0.0,'Transport':0.0}
    #             prev_mult = self._compute_lpg_block_multipliers(prev_dep['Process'], prev_dep['Transport'], df)
    #             prev_fix_mult_up = prev_mult["fix_mult_up"]
    #             prev_fix_mult_lo = prev_mult["fix_mult_lo"]
    #             prev_var_mult_up = prev_mult["var_mult_up"]
    #             prev_var_mult_lo = prev_mult["var_mult_lo"]

    #             # 🔴 YA NO comprobamos “áreas desplegadas”: intentamos leer SIEMPRE los costes previos
    #             params_prev = self.prev_state.get_lpg_cost_parameters(lpg_area_id)
    #             if params_prev and 'cost_parameters' in params_prev:
    #                 prev_cp = params_prev['cost_parameters']

    #         # -- Normalize ALWAYS to base when we have prev_state data for this area --
    #         eps = 1e-12
    #         if prev_cp is not None:
    #             if area_type == "rural":
    #                 cp.rural.costs.FIX_Ups_Cost_r       = prev_cp.rural.costs.FIX_Ups_Cost_r       / max(prev_fix_mult_up, eps)
    #                 cp.rural.costs.FIX_local_overcost_r = prev_cp.rural.costs.FIX_local_overcost_r / max(prev_fix_mult_lo, eps)
    #                 cp.rural.costs.VAR_Ups_Cost_r       = prev_cp.rural.costs.VAR_Ups_Cost_r       / max(prev_var_mult_up, eps)
    #                 cp.rural.costs.VAR_local_overcost_r = prev_cp.rural.costs.VAR_local_overcost_r / max(prev_var_mult_lo, eps)
    #             else:
    #                 cp.urban.costs.FIX_Ups_Cost_u       = prev_cp.urban.costs.FIX_Ups_Cost_u       / max(prev_fix_mult_up, eps)
    #                 cp.urban.costs.FIX_local_overcost_u = prev_cp.urban.costs.FIX_local_overcost_u / max(prev_fix_mult_lo, eps)
    #                 cp.urban.costs.VAR_Ups_Cost_u       = prev_cp.urban.costs.VAR_Ups_Cost_u       / max(prev_var_mult_up, eps)
    #                 cp.urban.costs.VAR_local_overcost_u = prev_cp.urban.costs.VAR_local_overcost_u / max(prev_var_mult_lo, eps)
    #         # Si no hay prev_cp, asumimos que cp ya está en base (no hacemos nada).

    #         # -- Molecule import (NO double exponent). Confirm units of consumption. --
    #         cost_per_unit = float(self.fuel_to_cost.get(fuel_id, 0.0))  # $/kg o $/kWh
    #         cons_kton = float(self.state.get_total_lpg_consumption_due_toCH(lpg_area_id, area_type) or 0.0)
    #         cons_kg = cons_kton * 1e6  # Kton → kg (si tu método da ton, cambia a *1e3)
    #         import_mult = 1.0 + mol_incr
    #         final_import_musd = (cost_per_unit * cons_kg * import_mult) / 1e6  # M$/yr

    #         # -- Apply current multipliers to base to get FINAL_* --
    #         def clamp_nonneg(x):
    #             if x < 0 and x > -1e-9: 
    #                 return 0.0
    #             return x

    #         if area_type == "rural":
    #             cp.rural.costs.FINAL_FIX_Cost_Upstream = clamp_nonneg(cp.rural.costs.FIX_Ups_Cost_r       * cur_mult["fix_mult_up"])
    #             cp.rural.costs.FINAL_FIX_Cost_Local    = clamp_nonneg(cp.rural.costs.FIX_local_overcost_r * cur_mult["fix_mult_lo"])
    #             cp.rural.costs.FINAL_VAR_Cost_Upstream = clamp_nonneg(cp.rural.costs.VAR_Ups_Cost_r       * cur_mult["var_mult_up"])
    #             cp.rural.costs.FINAL_VAR_Cost_Local    = clamp_nonneg(cp.rural.costs.VAR_local_overcost_r * cur_mult["var_mult_lo"])
    #             cp.rural.costs.FINAL_VAR_Cost_Import   = clamp_nonneg(final_import_musd)
    #         else:
    #             cp.urban.costs.FINAL_FIX_Cost_Upstream = clamp_nonneg(cp.urban.costs.FIX_Ups_Cost_u       * cur_mult["fix_mult_up"])
    #             cp.urban.costs.FINAL_FIX_Cost_Local    = clamp_nonneg(cp.urban.costs.FIX_local_overcost_u * cur_mult["fix_mult_lo"])
    #             cp.urban.costs.FINAL_VAR_Cost_Upstream = clamp_nonneg(cp.urban.costs.VAR_Ups_Cost_u       * cur_mult["var_mult_up"])
    #             cp.urban.costs.FINAL_VAR_Cost_Local    = clamp_nonneg(cp.urban.costs.VAR_local_overcost_u * cur_mult["var_mult_lo"])
    #             cp.urban.costs.FINAL_VAR_Cost_Import   = clamp_nonneg(final_import_musd)

    #         logging.info("LPG costs adjusted (area_id=%s, %s).", lpg_area_id, area_type)

    #     except Exception as e:
    #         logging.error("Error adjusting LPG final costs (%s - %s): %s", lpg_area_id, area_type, str(e), exc_info=True)
    #         raise

    

    

        

        
    def export_lpg_cost_debug_info(self, output_path, state_id):
        """
        Exports all relevant cost and consumption parameters for the LPG model to a TSV file.
        Includes costs, factors, consumptions, ratios, projected adoptions, and number of demand areas.
        """
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            with open(output_path, "a", newline='') as tsvfile:
                writer = csv.writer(tsvfile, delimiter="\t")

                # Encabezado si el archivo está vacío
                if os.stat(output_path).st_size == 0:
                    writer.writerow([
                        "State_ID", "LPGArea_ID", "AreaType",
                        "Number_of_DemandAreas",  # <--- nueva columna
                        "FIX_Cost", "VAR_Cost", "Local_Distance",
                        "Ups_FIX_Cost", "Ups_VAR_Cost",
                        "FIX_local_overcost_factor", "VAR_local_overcost_factor",
                        "FIX_local_overcost", "VAR_local_overcost",
                        "Ups_FIX_Cost_Split", "Ups_VAR_Cost_Split",
                        "Projected_Adoption",
                        "Ratio", "Total_Demand",
                        "FINAL_FIX_Cost_Upstream", "FINAL_FIX_Cost_Local",
                        "FINAL_VAR_Cost_Upstream", "FINAL_VAR_Cost_Local"
                    ])

                cp = self.lpg_cost_parameters
                num_demand_areas = len(self.demand_areas)  # <--- número de áreas que forman el área LPG

                for area_type in ["rural", "urban"]:
                    area_cp = cp.rural if area_type == "rural" else cp.urban

                    ratio_entry = next((entry for entry in self.area_ratios if entry["area_type"] == area_type), None)
                    ratio_value = ratio_entry["ratio"] if ratio_entry else 0
                    total_demand = ratio_entry["demand"] if ratio_entry else 0

                    writer.writerow([
                        state_id,
                        self.lpg_area,
                        area_type,
                        num_demand_areas,  # <--- añadimos el número aquí
                        round(cp.general.costs.FIX_Cost, 4),
                        round(cp.general.costs.VAR_Cost, 4),
                        round(cp.general.costs.Local_Distance, 4),
                        round(cp.general.costs.Ups_FIX_Cost, 4),
                        round(cp.general.costs.Ups_VAR_Cost, 4),
                        round(cp.general.costs.FIX_local_overcost_factor, 4),
                        round(cp.general.costs.VAR_local_overcost_factor, 4),
                        round(area_cp.costs.FIX_local_overcost_r if area_type == "rural" else area_cp.costs.FIX_local_overcost_u, 4),
                        round(area_cp.costs.VAR_local_overcost_r if area_type == "rural" else area_cp.costs.VAR_local_overcost_u, 4),
                        round(area_cp.costs.FIX_Ups_Cost_r if area_type == "rural" else area_cp.costs.FIX_Ups_Cost_u, 4),
                        round(area_cp.costs.VAR_Ups_Cost_r if area_type == "rural" else area_cp.costs.VAR_Ups_Cost_u, 4),
                        round(self.current_projected_adoption_chdemand[area_type], 4),
                        round(ratio_value, 4),
                        round(total_demand, 4),
                        round(area_cp.costs.FINAL_FIX_Cost_Upstream, 4),
                        round(area_cp.costs.FINAL_FIX_Cost_Local, 4),
                        round(area_cp.costs.FINAL_VAR_Cost_Upstream, 4),
                        round(area_cp.costs.FINAL_VAR_Cost_Local, 4)
                    ])
            logging.info("Extended LPG cost debug info exported to %s", output_path)
        except Exception as e:
            logging.error("Error exporting LPG cost debug info: %s", str(e), exc_info=True)
            raise

    def export_lpg_final_cost_debug_info(self, output_path, state_id, cost_parameters, area_type, lpg_area_id):
        """
        Exporta los costes finales de LPG para un área LPG y un tipo de área ("rural" o "urban").
        Solo escribe una fila por llamada.
        """
        try:
            import os
            import csv

            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Determinar si hay que escribir encabezado
            write_header = not os.path.exists(output_path) or os.stat(output_path).st_size == 0

            with open(output_path, "a", newline='') as tsvfile:
                writer = csv.writer(tsvfile, delimiter="\t")

                if write_header:
                    writer.writerow([
                        "State_ID", "LPGArea_ID", "AreaType",
                        "Number_of_DemandAreas",
                        "FIX_Cost", "VAR_Cost", "Local_Distance",
                        "Ups_FIX_Cost", "Ups_VAR_Cost",
                        "FIX_local_overcost_factor", "VAR_local_overcost_factor",
                        "FIX_local_overcost", "VAR_local_overcost",
                        "Ups_FIX_Cost_Split", "Ups_VAR_Cost_Split",
                        "Projected_Adoption",
                        #"Ratio", "Total_Demand",
                        "FINAL_FIX_Cost_Upstream", "FINAL_FIX_Cost_Local",
                        "FINAL_VAR_Cost_Upstream", "FINAL_VAR_Cost_Local"
                    ])

                cp = cost_parameters
                area_cp = cp.rural if area_type == "rural" else cp.urban

                # Buscar ratio y demanda asociada
                #ratio_entry = next((entry for entry in cp.area_ratios if entry["area_type"] == area_type), None)
                #ratio_value = ratio_entry["ratio"] if ratio_entry else 0
                #total_demand = ratio_entry["demand"] if ratio_entry else 0

                num_demand_areas = getattr(cp, "num_demand_areas", 1)  # por si está almacenado

                writer.writerow([
                    state_id,
                    lpg_area_id,
                    area_type,
                    num_demand_areas,
                    round(cp.general.costs.FIX_Cost, 4),
                    round(cp.general.costs.VAR_Cost, 4),
                    round(cp.general.costs.Local_Distance, 4),
                    round(cp.general.costs.Ups_FIX_Cost, 4),
                    round(cp.general.costs.Ups_VAR_Cost, 4),
                    round(cp.general.costs.FIX_local_overcost_factor, 4),
                    round(cp.general.costs.VAR_local_overcost_factor, 4),
                    round(area_cp.costs.FIX_local_overcost_r if area_type == "rural" else area_cp.costs.FIX_local_overcost_u, 4),
                    round(area_cp.costs.VAR_local_overcost_r if area_type == "rural" else area_cp.costs.VAR_local_overcost_u, 4),
                    round(area_cp.costs.FIX_Ups_Cost_r if area_type == "rural" else area_cp.costs.FIX_Ups_Cost_u, 4),
                    round(area_cp.costs.VAR_Ups_Cost_r if area_type == "rural" else area_cp.costs.VAR_Ups_Cost_u, 4),
                    round(cp.general.consumption.Adjusted_Adoption, 4),  # valor común
                    #round(ratio, 4),
                    #round(total_demand, 4),
                    round(area_cp.costs.FINAL_FIX_Cost_Upstream, 4),
                    round(area_cp.costs.FINAL_FIX_Cost_Local, 4),
                    round(area_cp.costs.FINAL_VAR_Cost_Upstream, 4),
                    round(area_cp.costs.FINAL_VAR_Cost_Local, 4)
                ])

            logging.info("Final LPG costs for area %s (%s) exported to %s", lpg_area_id, area_type, output_path)

        except Exception as e:
            logging.error("Error exporting final LPG costs (%s, %s): %s", lpg_area_id, area_type, str(e), exc_info=True)
            raise

