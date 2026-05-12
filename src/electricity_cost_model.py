
import numpy as np
from src.el_cost_params import CostParameters

import logging
import csv 
import os 

class ElectricityCostModel:
    def __init__(self, state, prev_state, mixed_states, data_manager, demand_area, adoption_model):
        self.state = state
        self.prev_state = prev_state
        self.mixed_states = mixed_states
        self.data_manager = data_manager
        self.demand_area = demand_area
        self.adoption_model = adoption_model
        #self.income_model = income_model

        #Current Demand Area id
        self.demand_area_id = demand_area.id
        #Current Demand Area EL_ID 
        self.demand_area_el_id = demand_area.el_area
        self.demand_area_el_id = int(self.demand_area_el_id)

        #Uso estructuras del adoption model 

        # Usamos el DataFrame Electricity_areas para obtener los datos de la demanda de electricidad
        self.electric_plan = data_manager.get_dataframe("Electricity_areas")
        self.electric_plan_row = self.electric_plan.loc[self.electric_plan["ElArea_Id"] == self.demand_area_el_id]
        self.electric_cost_breakdown = data_manager.get_dataframe("Electricity_costBreakdown")
        self.technologies = adoption_model.technologies

        # Extraer Diesel _emission_rate del main config
        self.general_cofig = self.data_manager.get_config()
        self.diesel_emission_rate = self.general_cofig.get("Diesel_emissions")
        self.electricity_adoption = self.general_cofig.get("Electricity_adoption") #Iniital adoption rate for electricity for the whole country 
        self.power_losses_factor = self.general_cofig.get("Power_losses_factor") #/100  #Pasamos el porcentaje a decimal
        self.generation_CAPEX = self.general_cofig.get("Generation_CAPEX")  # $/KWh (ej. 0.11)
        self.generation_OPEX = self.general_cofig.get("Generation_OPEX")    # $/KWh (ej. 0.03)


        # Reutilizamos los mapeos ya obtenidos.
        self.fuel_id_to_name = adoption_model.fuel_id_to_name
        self.appl_id_to_name = adoption_model.appl_id_to_name
        #Extraer growth scenario del adopcion model 
        self.growth_scenario = adoption_model.growth


        # Inicialio la información relevante para el fuel de electricidad
        self.fuel_id = 1

        #Extraer el nombre del fuel de electricidad
        fuel_name = self.fuel_id_to_name.get(self.fuel_id, "Unknown_Fuel")

        
        # deployment_plan_details = state.deployment_plan.details 
        # self.deployment_plan_fuels_data = deployment_plan_details.get("fuel_reference", [])
        #Extraer el Ref_capacity y Margin del fuel de electricidad (suponiendo que Fuel_id == 1 corresponde a electricidad)
        # self.electricity_fuel_data = next((fuel for fuel in self.deployment_plan_fuels_data if fuel["Fuel_id"] == self.fuel_id), None)
        # if self.electricity_fuel_data is None:
        #     raise ValueError("No se encontró el fuel de electricidad con Fuel_id==1")

        # self.electricity_fuel_ref_capacity = self.electricity_fuel_data["Ref_capacity"]
        # self.electricity_fuel_margin = self.electricity_fuel_data["Margin"]

        

        # Extraer el target de electricidad a través del fuel_name (por ejemplo, "Electricity") salvo si es el estado base 
        self.base_year = self.growth_scenario.base_year 
        self.first_semester = "first"
        self.base_year_state = self.find_state(self.mixed_states, self.base_year, "first")

        #if ( self.base_year_state == state.year) and state.semester == "first":
        if self.state.year == self.base_year and self.state.semester == "first":
            self.electricity_target = None
            deployment_plan_details = state.deployment_plan.details 
            self.deployment_plan_fuels_data = deployment_plan_details.get("fuel_reference", [])
            self.deployment_plan_fuels_target = deployment_plan_details.get("fuels_target", [])
            self.electricity_fuel_data = next((fuel for fuel in self.deployment_plan_fuels_data if fuel["Fuel_id"] == self.fuel_id), None)
            self.electricity_fuel_ref_capacity = self.electricity_fuel_data["Ref_capacity"]
            self.electricity_fuel_margin = self.electricity_fuel_data["Margin"]
        else:
            #Extraer los detalles del plan de despliegue desde el state
            deployment_plan_details = prev_state.deployment_plan.details 
            self.deployment_plan_fuels_data = deployment_plan_details.get("fuel_reference", [])
            self.deployment_plan_fuels_target = deployment_plan_details.get("fuels_target", [])
            # Obtener el dep_plan_id actual desde el state
            
            
            # Extraer el target de electricidad de la fila encontrada
            self.electricity_target = self.deployment_plan_fuels_target[0].get(fuel_name)


            self.electricity_fuel_data = next((fuel for fuel in self.deployment_plan_fuels_data if fuel["Fuel_id"] == self.fuel_id), None)
            self.electricity_fuel_ref_capacity = self.electricity_fuel_data["Ref_capacity"]
            self.electricity_fuel_margin = self.electricity_fuel_data["Margin"]
        
        if self.electricity_fuel_data is None:
            raise ValueError("No se encontró el fuel de electricidad con Fuel_id==1")

        #Extraer datos necesatios para el modelo de coste -- carga los datos de modelo income YA HACIENDO LA CONVERSIÓN A GWh Y MCOOK 
        #Año 0 - Demanda Eléctrica total = 100% de adopción de tecnologías eléctricas
        self.base_electricity_demand = {"rural": {}, "urban": {}}
        #Año 0 - Demanda C+H total = 100% de adopción de tecnologías de calefacción y cocinado eléctricas 
        self.base_ch_demand = {"rural": {}, "urban": {}}
        
        #Para el modelo de costes eléctrico y de C+H

        #Demanda del estado actual electrica 
        self.current_electricity_demand = {"rural": {}, "urban": {}}
        #Demanda del estado actual de calefacción y cocinado eléctrica
        self.current_ch_demand = {"rural": {}, "urban": {}}

        #Parámetros calculados para el estado actual para el área de demanda actual --------------------------------

        #Factor de combustible de ingresos
        self.fuel_consumption = {"rural": {}, "urban": {}}
        #Adopción actual Dis-Electricity = factor de combustible / demanda actual de calefacción y cocinado
        self.actual_adoption_dis_electricity = {"rural": {}, "urban": {}}
        #Adopción potencial actual 
        self.potential_adoption = {"rural": {}, "urban": {}}
        #Demanda total E  (EDEMAND) + CH 
        self.total_current_demand = {"rural": {}, "urban": {}}
        #Demanda total CH + Margin 
        self.total_current_ch_demand_margin = {"rural": {}, "urban": {}}
        #Demanda total E + CH + Margin
        self.total_current_demand_margin = {"rural": {}, "urban": {}} 

        self.base_st1_demand = {"rural": {}, "urban": {}}
        self.base_st4_demand = {"rural": {}, "urban": {}}

        self.total_capacity_etotal = {"rural": {}, "urban": {}}
        self.total_capacity_edemand = {"rural": {}, "urban": {}}


        # Rural and urban capacities split 
        self.RC_etotal = None
        self.UC_etotal = None
        self.RC_edemand = None
        self.UC_edemand = None
        self.U_p_u_etotal = None
        self.U_p_u_edemand = None
        #Adopción proyectada
        self.current_projected_adoption_etotal = {"rural": {}, "urban": {}}  
        self.current_projected_adoption_edemand = {"rural": {}, "urban": {}}
        #Pesos de adopción proyectada 
        self.projection__multilinear_weights_etotal = None
        self.projection__multilinear_weights_edemand = None

        #Parámetros de coste -- Importo la estructura de costes de cost_params.py
        self.cost_parameters = {
            "ElecTotal": CostParameters(),
            "EDemand": CostParameters()
        }

        # Inicializamos el diccionario para costes finales
        self.final_costs_data = {}
        self.ratios = {"rural": {}, "urban": {}} 

        # Se guardarán objetos con: id, tipo de área, ratio y demanda total (E + CH)
        self.area_ratios = []
        # Variable para almacenar la demanda total del país (suma de consumos totales de E y CH)
        self.total_country_demand = 0.0
        self.final_offGrid_percentage = 0.0
    @staticmethod
    def find_state(states_list, year, semester):
        return next((s for s in states_list if s.year == year and s.semester == semester), None)
    
    @property
    def area_types(self):
        """
        Returns ['rural'] or ['urban'] if self.demand_area.area_type is defined,
        or both ['rural', 'urban'] if it is not defined (None).
        """
        return [self.demand_area.area_type] if self.demand_area.area_type else ['rural', 'urban']
    
    @staticmethod
    def _as4(stages):
        """Convierte [stage0..stage3] a np.array([v0,v1,v2,v3]) en float."""
        vals = []
        for s in stages:
            # s puede ser Series, DataFrame de 1x1, escalar…
            if hasattr(s, "iloc"):
                # Series: tomamos el único valor; DataFrame: primera celda
                try:
                    vals.append(float(s.iloc[0]))
                except Exception:
                    # DataFrame 1x1
                    vals.append(float(np.asarray(s).ravel()[0]))
            else:
                vals.append(float(s))
        a = np.asarray(vals, dtype=np.float64)
        # seguridad: rellenar si faltase algo
        if a.size != 4:
            a = np.pad(a[:4], (0, max(0, 4 - a.size)), constant_values=0.0)
        return a

    @staticmethod
    def _w4(weights):
        """Extrae pesos W1..W4 a np.array([w1..w4])."""
        if isinstance(weights, dict):
            return np.array([weights.get("W1",0.0),weights.get("W2",0.0),
                            weights.get("W3",0.0),weights.get("W4",0.0)], dtype=np.float64)
        # Series/DataFrame/arraylike
        try:
            return weights.loc[["W1","W2","W3","W4"]].to_numpy(dtype=np.float64)
        except Exception:
            w = np.asarray(weights, dtype=np.float64).ravel()
            return np.pad(w[:4], (0, max(0, 4 - w.size)), constant_values=0.0)


    def run_simulation(self):
        
        try:
            logging.info("Ejecutando modelo de coste para electricidad para Demand Area %s", self.demand_area.id)
            # Lógica de cálculo de incomes
            # Al final de run_simulation() o calculate_final_costs()
            both_types = set(self.area_types)
            if "rural" in both_types and "urban" not in both_types:
                self._force_zero_values_for("urban")
            elif "urban" in both_types and "rural" not in both_types:
                self._force_zero_values_for("rural")
            # Calcular demanda de electricidad y calefacción/cocinado + proyección de la adopción 
            self.calculate_initial_params()
            # Calcular las proyecciones de pesos de adopción
            self.calculate_projection_weights()
            #get State values for El Area 
            base_values = self.get_stage_values()
            # Calcular costes generales 
            self.calculate_general_cost(base_values)
            # Calcular consumos generales
            self.calculate_general_consumptions()
            # Calcular consumos específicos  
            self.calculate_specific_consumptions()
            #Calcular ultimo coste general VAR_OGgen
            self.calculateVAROGgen()
            # Calcular costes específicos
            self.calculate_specific_costs()
            # Calcular costes finales
            self.calculate_final_costs()

            # OJO FORZAMOS A CERO EL ÄREA NO ELECTRIFICADA 
            

            # Calcular ratios
            self.calculate_ratios()

            self.state.store_electricity_cost_parameters(
                self.demand_area_id,
                self.cost_parameters,
                self.ratios
            )

            # Guardar coste base EDemand si aplica
            self.maybe_store_base_edemand_cost_for_area(area_id=self.demand_area_id, area_type="urban", block="EDemand")
            self.maybe_store_base_edemand_cost_for_area(area_id=self.demand_area_id, area_type="rural", block="EDemand")

                
                
                

        except Exception as e:
            logging.error("Error en el cálculo de costes de electricidad: %s", str(e))
            raise
        
        

    def calculate_initial_params(self):
        "Initialize the initial parameters for the electricity cost model."
        try:
            for area_type in self.area_types: #["rural", "urban"]:
                #Obtener la adopción potencial del estado actual 
                #self.potential_adoption[area_type] = self.state.get_potential_adoption(self.demand_area_id, area_type) -- Esto no lo quiero para nada de momento 
                #Get income fuel factor 
                #self.fuel_consumption[area_type] = self.income_model.get_total_fuel_consumption(self.fuel_id,  area_type)
                self.fuel_consumption[area_type] = self.state.get_total_fuel_consumption(self.demand_area_id , area_type).get(self.fuel_id, 0.0)
                


                #Parámetros del estado base -- paso las demandas  de Kwh/year a Gwh/year
                
                self.base_electricity_demand[area_type] = self.base_year_state.get_electric_consumption(self.demand_area_id, area_type)[area_type]
                self.base_ch_demand[area_type] = self.base_year_state.get_CH_consumption(self.demand_area_id, area_type)[area_type]
                #self.total_base_demand[area_type] = self.base_electricity_demand[area_type] + self.base_ch_demand[area_type]
                #Parámetros del estado actual 
                self.current_electricity_demand[area_type] = self.state.get_electric_consumption(self.demand_area_id, area_type)[area_type]
                #self.current_ch_demand[area_type] = self.state.get_CH_consumption(self.demand_area_id, area_type) 
                # extraer el valor directamente
                self.current_ch_demand[area_type] = self.state.get_CH_consumption(self.demand_area_id, area_type)[area_type] ## Como si todo el mundo cocinara con electricidad 
                #
                #  Nuevo chequeo: si no hay demanda de cocinado ni de electricidad, la zona se descarta
                if self.current_ch_demand[area_type] == 0 and self.current_electricity_demand[area_type] == 0:
                    logging.info(f"Área '{area_type}' sin demanda. Se inicializa con valores cero.")
                    self.actual_adoption_dis_electricity[area_type] = 0.0
                    self.total_current_demand[area_type] = 0.0
                    self.total_current_ch_demand_margin[area_type] = 0.0
                    self.total_current_demand_margin[area_type] = 0.0
                    self.current_projected_adoption_etotal[area_type] = 0.0
                    self.current_projected_adoption_edemand[area_type] = 0.0
                    

                    continue  # saltamos el resto del bucle para este área

            # --- Resto de cálculos si sí tiene demanda ---

                # Calculo la adopciñón actual de electricidad 
                #Actual adoption Dis-Electricity = fuel comsumption /ch demand actual 
                self.actual_adoption_dis_electricity[area_type] = self.fuel_consumption[area_type] / self.current_ch_demand[area_type]


                # Calcular la demanda total (Nota: Ajustando la demanda de cocinado por la adopción eléctrica del fuel electricidad)
                self.total_current_demand[area_type] = self.current_electricity_demand[area_type] + (self.current_ch_demand[area_type] * self.actual_adoption_dis_electricity[area_type])
                # Calcular la demanda total con margen
                self.total_current_ch_demand_margin[area_type] = self.current_ch_demand[area_type] * (self.electricity_fuel_margin + self.actual_adoption_dis_electricity[area_type])
                self.total_current_demand_margin[area_type] = self.total_current_demand[area_type] + (self.electricity_fuel_margin * self.total_current_demand[area_type])
                
                
                # Calcular la adopción proyectada = (CH+E_current - E_base)/ (CH_Base) -- INTERPOLO EN EL ESTADO ACTUAL %
                #Nota -- La demanda del estado base no hay que ajustarla con la adopción potencial porqe se entiende que es el 100% de adopción en el estado base ---- 
                # self.current_projected_adoption_etotal[area_type] = (self.total_current_demand[area_type] - self.base_electricity_demand[area_type]) / self.base_ch_demand[area_type]
                # self.current_projected_adoption_edemand[area_type] = (self.current_electricity_demand[area_type] / self.base_electricity_demand[area_type])
                # Demanda puramente eléctrica (St1)
                self.base_st1_demand[area_type] = self.base_electricity_demand[area_type]

                # Demanda completa a 100% de adopción (St4): E + Ref * (CH_rural + CH_urban)
                self.base_st4_demand[area_type] = (
                    self.base_electricity_demand[area_type] + 
                    self.electricity_fuel_ref_capacity * self.base_ch_demand[area_type]
                )
                denominator = self.base_st4_demand[area_type] - self.base_st1_demand[area_type]
                # EDemand: % de la demanda eléctrica actual con respecto a St1
                if denominator > 0:
                    self.current_projected_adoption_edemand[area_type] = (
                        (self.current_electricity_demand[area_type] - self.base_st1_demand[area_type])/ denominator
                    )
                else:
                    self.current_projected_adoption_edemand[area_type] = 0

                # ElecTotal: avance del total actual desde St1 hacia St4
                
                if self.base_st4_demand[area_type] > 0:
                    self.current_projected_adoption_etotal[area_type] = (
                        (self.total_current_demand[area_type] - self.base_st1_demand[area_type]) / self.base_st4_demand[area_type]
                    )
                else:
                    self.current_projected_adoption_etotal[area_type] = 0


               
            self.calculateUpu()


        except Exception as e:
            logging.error("Error al calcular los parámetros iniciales para electricidad: %s", str(e))
            raise

    def calculateUpu(self):
        "Calculate U.pu for the current state"
        

        try: 
            #Consumos reales: 
            
            self.total_capacity_etotal["rural"] = self.current_ch_demand["rural"] * (self.actual_adoption_dis_electricity["rural"] + self.electricity_fuel_margin)
            self.total_capacity_etotal["urban"] = self.current_ch_demand["urban"] * (self.actual_adoption_dis_electricity["urban"] + self.electricity_fuel_margin)
            #Para E-Total
            
            self.RC_etotal = self.total_capacity_etotal["rural"] + self.current_electricity_demand["rural"] 
            self.UC_etotal = self.total_capacity_etotal["urban"] + self.current_electricity_demand["urban"]
            self.RC_edemand = self.current_electricity_demand["rural"] + (self.electricity_fuel_margin * self.current_ch_demand["rural"])
            self.UC_edemand = self.current_electricity_demand["urban"] + (self.electricity_fuel_margin * self.current_ch_demand["urban"])

            if (self.RC_etotal + self.UC_etotal) > 0:
                self.U_p_u_etotal = self.UC_etotal / (self.RC_etotal + self.UC_etotal)
            else:
                self.U_p_u_etotal = 0
            
            if (self.RC_edemand + self.UC_edemand) > 0:
                self.U_p_u_edemand = self.UC_edemand / (self.RC_edemand + self.UC_edemand)
            else:
                self.U_p_u_edemand = 0

        except Exception as e:
            logging.error("Error al calcular U.pu: %s", str(e))
            raise


    def _compute_projection_weights(self, adop_rur, adop_urb, Ref, Margin):
        """
        Aux method to compute the projection weights using the formula 
        params: adop_rur: float, adop_urb: float, Ref: float, Margin: float
        return: dict
        """
        W1 = (Ref - adop_rur - Margin) * (Ref - adop_urb - Margin) / (Ref * Ref)
        W2 = (Ref - adop_rur - Margin) * (adop_urb + Margin) / (Ref * Ref)
        W3 = (adop_rur + Margin) * (Ref - adop_urb - Margin) / (Ref * Ref)
        W4 = (adop_rur + Margin) * (adop_urb + Margin) / (Ref * Ref)
        return {"W1": W1, "W2": W2, "W3": W3, "W4": W4}
    
    def rural_only_weights(self, adop_rur, Ref, Margin):
        # St1 = (0% adop), St3 = (100% rural adop)
        # Linear interpolation between W1 (St1) and W3 (St3)
        alpha = (adop_rur + Margin) / Ref  # normalized position
        W1 = 1 - alpha
        W3 = alpha
        return {"W1": W1, "W2": 0.0, "W3": W3, "W4": 0.0}
    def urban_only_weights(self, adop_urb, Ref, Margin):
        # Interpolación entre W1 (St1) y W2 (St2)
        alpha = (adop_urb + Margin) / Ref
        W1 = 1 - alpha
        W2 = alpha
        return {"W1": W1, "W2": W2, "W3": 0.0, "W4": 0.0}


    def calculate_projection_weights(self):
        """
        Projected adoption for rural and urban".
        """
        try:
            Ref = self.electricity_fuel_ref_capacity
            Margin = self.electricity_fuel_margin

            rural_exists = self.current_ch_demand["rural"] > 0 or self.current_electricity_demand["rural"] > 0
            urban_exists = self.current_ch_demand["urban"] > 0 or self.current_electricity_demand["urban"] > 0

            if rural_exists and not urban_exists:
                self.projection__multilinear_weights_etotal = self.rural_only_weights(
                    self.current_projected_adoption_etotal["rural"], Ref, Margin)
                self.projection__multilinear_weights_edemand = self.rural_only_weights(
                    self.current_projected_adoption_edemand["rural"], Ref, Margin)

            elif urban_exists and not rural_exists:
                self.projection__multilinear_weights_etotal = self.urban_only_weights(
                    self.current_projected_adoption_etotal["urban"], Ref, Margin)
                self.projection__multilinear_weights_edemand = self.urban_only_weights(
                    self.current_projected_adoption_edemand["urban"], Ref, Margin)

            elif rural_exists and urban_exists:
                self.projection__multilinear_weights_etotal = self._compute_projection_weights(
                    self.current_projected_adoption_etotal["rural"],
                    self.current_projected_adoption_etotal["urban"],
                    Ref, Margin
                )
                self.projection__multilinear_weights_edemand = self._compute_projection_weights(
                    self.current_projected_adoption_edemand["rural"],
                    self.current_projected_adoption_edemand["urban"],
                    Ref, Margin
                )
            else:
                self.projection__multilinear_weights_etotal = {"W1": 0, "W2": 0, "W3": 0, "W4": 0}
                self.projection__multilinear_weights_edemand = {"W1": 0, "W2": 0, "W3": 0, "W4": 0}

            logging.info("Projection weights (ElecTotal) calculated: %s",  self.projection__multilinear_weights_etotal)
            logging.info("Projection weights (EDemand) calculated: %s", self.projection__multilinear_weights_edemand)

        except Exception as e:
            logging.error("Error al calcular los pesos de proyección: %s", str(e))
            raise


   

    def weighted_sum(self, values, weights):
            """Calculate the weighted sum of the given values using the projection weights."""
            w = weights
            return (w["W1"] * values[0] + w["W2"] * values[1] +
                    w["W3"] * values[2] + w["W4"] * values[3])

    def _normalize_weights(self, weights: dict, label: str) -> dict:
        """
        Normalize the weights so that they sum to 1. If already normalized, return as-is.
        Logs a warning if normalization is applied.
        """
        total = sum(weights.values())
        if abs(total - 1.0) > 1e-6:
            logging.warning(f"[{label}] Pesos no normalizados (suman {total:.6f}). Se normalizan: {weights}")
            if total > 0:
                return {k: v / total for k, v in weights.items()}
            else:
                logging.error(f"[{label}] La suma de pesos es 0 o negativa. Retornando pesos originales.")
                return weights  # No se puede normalizar si total <= 0
        return weights


    def get_stage_values(self):
        """
        Obtain the values for the current stage.
        """
        try:
            row = self.electric_plan_row
            return {
                "fix_cost": [row["St1_CAPEX"], row["St2_CAPEX"], row["St3_CAPEX"], row["St4_CAPEX"]],
                "og_g_var": [row["St1_OPEX_OG"], row["St2_OPEX_OG"], row["St3_OPEX_OG"], row["St4_OPEX_OG"]],
                "og_diesel_rate": [row["St1_Emissions_OG"], row["St2_Emissions_OG"], row["St3_Emissions_OG"], row["St4_Emissions_OG"]],
                "grcap_pu": [row["St1_OnGrid"], row["St2_OnGrid"], row["St3_OnGrid"], row["St4_OnGrid"]],
                "grcapU_pu": [row["St1_U_OnGrid"], row["St2_U_OnGrid"], row["St3_U_OnGrid"], row["St4_U_OnGrid"]]
            }


        except Exception as e:
            logging.error("Error al obtener los valores del estado base: %s", str(e))
            raise


    # def calculate_general_cost(self, base_values): 
    #     """
    #     Calculate general costs using the base values.
    #     Assign the results to self.general_costs_data and update the general part in self.cost_parameters
    #     """
    #     try:
    #         #base_values = self.get_stage_values()
    #         fix_cost_stages = base_values["fix_cost"]
    #         og_g_var_stages = base_values["og_g_var"]
    #         og_diesel_rate_stages = base_values["og_diesel_rate"]
    #         grcap_pu_stages = base_values["grcap_pu"]
    #         grcapU_pu_stages = base_values["grcapU_pu"]
            
    #         #Para ElecTotal
    #         weights_etotal = self.projection__multilinear_weights_etotal
    #         # FIX Cost ElecTotal: comparar escalar del peso vs etapa 0
    #         fix_weighted_etotal = self.weighted_sum(fix_cost_stages, weights_etotal)
    #         v1 = fix_weighted_etotal.iloc[0]
    #         v2 = fix_cost_stages[0].iloc[0]
    #         fix_cost_electotal = max(v1, v2)

    #         # OG_G_VAR ElecTotal: clamp escalar entre etapas 0 y 3
    #         og_weighted_etotal = self.weighted_sum(og_g_var_stages, weights_etotal)
    #         min_og = min(og_g_var_stages[0].iloc[0], og_g_var_stages[3].iloc[0])
    #         max_og = max(og_g_var_stages[0].iloc[0], og_g_var_stages[3].iloc[0])
    #         v3 = og_weighted_etotal.iloc[0]
    #         og_g_var_electotal = min(max(v3, min_og), max_og)

    #         # OG_Diesel ElecTotal: clamp escalar entre etapas 0 y 3
    #         og_diesel_weighted_etotal = self.weighted_sum(og_diesel_rate_stages, weights_etotal)
    #         min_diesel = min(og_diesel_rate_stages[0].iloc[0], og_diesel_rate_stages[3].iloc[0])
    #         max_diesel = max(og_diesel_rate_stages[0].iloc[0], og_diesel_rate_stages[3].iloc[0])
    #         v4 = og_diesel_weighted_etotal.iloc[0]
    #         og_diesel_electotal = min(max(v4, min_diesel), max_diesel)

    #         # GrCap_pu ElecTotal: clamp escalar
    #         gr_pu = self.weighted_sum(grcap_pu_stages, weights_etotal).iloc[0]
    #         grcap_pu_etotal = max(min(gr_pu, 1), 0) #Porcentaje de gente conectada a la red electrica

    #         # GrCapU_pu ElecTotal: condicional escalar
    #         grU_pu = self.weighted_sum(grcapU_pu_stages, weights_etotal).iloc[0] # Porcentage de gente conectada a la red electrica URBANOS 
    #         grU_pu = min(grU_pu, 1.0)
    #         #Porcentaje de gente conectada a la red urbano es x con es con respecto al porcentaje total conectada a la red electrica
    #         real_percentaje_urban = grU_pu * grcap_pu_etotal

    #         # No puede haber más porcentaje urbano conectado que total conectado
    #         max_allowed = min(self.U_p_u_etotal, grcap_pu_etotal)

    #         if real_percentaje_urban > max_allowed and grcap_pu_etotal > 0:
    #             grcapU_pu_etotal = max_allowed
    #         elif real_percentaje_urban <= max_allowed and grcap_pu_etotal > 0:
    #             grcapU_pu_etotal = real_percentaje_urban
    #         else:
    #             grcapU_pu_etotal = 0



            
    #         # Proyección EDemand
    #         weights_edemand = self.projection__multilinear_weights_edemand

    #         # FIX Cost EDemand
    #         fix_ed = self.weighted_sum(fix_cost_stages, weights_edemand).iloc[0]
    #         fix_cost_edemand = max(fix_ed, 0)

    #         # OG_G_VAR EDemand
    #         og_ed = self.weighted_sum(og_g_var_stages, weights_edemand).iloc[0]
    #         og_g_var_edemand = max(og_ed, 0)

    #         # OG_Diesel EDemand
    #         od_ed = self.weighted_sum(og_diesel_rate_stages, weights_edemand).iloc[0]
    #         og_diesel_edemand = min(max(od_ed, 0), 1)

    #         # GrCap_pu EDemand
    #         gp_ed = self.weighted_sum(grcap_pu_stages, weights_edemand).iloc[0]
    #         grcap_pu_edemand = min(max(gp_ed, 0), 1)

    #         # GrCapU_pu EDemand
    #         gU_ed = self.weighted_sum(grcapU_pu_stages, weights_edemand).iloc[0]
    #         gU_ed = min(gU_ed, 1.0)
            

    #         #Porcentaje de gente conectada a la red urbano es x con es con respecto al porcentaje total conectada a la red electrica
    #         real_percentaje_urban_ed = gU_ed * grcap_pu_edemand
    #         max_allowed_ed = min(self.U_p_u_edemand, grcap_pu_edemand)
    #         if real_percentaje_urban_ed > max_allowed_ed and grcap_pu_edemand > 0:
    #             #lower = (grcap_pu_etotal - 1 + self.U_p_u_etotal) / grcap_pu_etotal
    #             #upper = self.U_p_u_etotal / grcap_pu_etotal
    #             #grcapU_pu_etotal = min(max(real_percentaje_urban, lower), upper)
    #             grcapU_pu_edemand = max_allowed_ed
    #         elif real_percentaje_urban <= self.U_p_u_edemand and grcap_pu_edemand > 0:
    #             upper = self.U_p_u_edemand / grcap_pu_edemand
    #             grcapU_pu_edemand = real_percentaje_urban_ed
    #         else:
    #             grcapU_pu_edemand = 0

            


    #         self.general_costs_data = {
    #         "ElecTotal": {
    #             "fix_cost": fix_cost_electotal,
    #             "og_g_var": og_g_var_electotal,
    #             "og_diesel": og_diesel_electotal,
    #             "grcap_pu": grcap_pu_etotal,
    #             "grcapU_pu": grcapU_pu_etotal
    #         },
    #         "EDemand": {
    #             "fix_cost": fix_cost_edemand,
    #             "og_g_var": og_g_var_edemand,
    #             "og_diesel": og_diesel_edemand,
    #             "grcap_pu": grcap_pu_edemand,
    #             "grcapU_pu": grcapU_pu_edemand
    #         }
    #     }

    #     # Actualizar la parte general de la estructura de costes:
    #         for block in ["ElecTotal", "EDemand"]:
    #             cp = self.cost_parameters[block]
    #             if block == "ElecTotal":
    #                 cp.general.costs.FIX_Cost = self.general_costs_data["ElecTotal"]["fix_cost"]
    #                 cp.general.costs.OG_G_VAR = self.general_costs_data["ElecTotal"]["og_g_var"]
    #                 cp.general.costs.OG_G_Diesel_rate = self.general_costs_data["ElecTotal"]["og_diesel"]
    #                 cp.general.costs.GrCap_pu = self.general_costs_data["ElecTotal"]["grcap_pu"]
    #                 cp.general.costs.GrCapU_pu = self.general_costs_data["ElecTotal"]["grcapU_pu"]
    #             else:
    #                 cp.general.costs.FIX_Cost = self.general_costs_data["EDemand"]["fix_cost"]
    #                 cp.general.costs.OG_G_VAR = self.general_costs_data["EDemand"]["og_g_var"]
    #                 cp.general.costs.OG_G_Diesel_rate = self.general_costs_data["EDemand"]["og_diesel"]
    #                 cp.general.costs.GrCap_pu = self.general_costs_data["EDemand"]["grcap_pu"]
    #                 cp.general.costs.GrCapU_pu = self.general_costs_data["EDemand"]["grcapU_pu"]

    #         logging.info("General costs calculated and assigned: %s", self.general_costs_data)
        
    #     except Exception as e:
    #         logging.error("Error al calcular los costes generales: %s", str(e))
    #         raise
    

    def calculate_general_cost(self, base_values):
        try:
            # --- prepara arrays 4x1 de una vez
            fix4   = self._as4(base_values["fix_cost"])
            ogv4   = self._as4(base_values["og_g_var"])
            odr4   = self._as4(base_values["og_diesel_rate"])
            gp4    = self._as4(base_values["grcap_pu"])
            gUp4   = self._as4(base_values["grcapU_pu"])

            wE = self._w4(self.projection__multilinear_weights_etotal)
            wD = self.  _w4(self.projection__multilinear_weights_edemand)

            # ElecTotal
            fix_wE = float(fix4.dot(wE))
            fix_cost_electotal = max(fix_wE, float(fix4[0]))

            og_wE = float(ogv4.dot(wE))
            og_min, og_max = float(min(ogv4[0], ogv4[3])), float(max(ogv4[0], ogv4[3]))
            og_g_var_electotal = min(max(og_wE, og_min), og_max)

            od_wE = float(odr4.dot(wE))
            od_min, od_max = float(min(odr4[0], odr4[3])), float(max(odr4[0], odr4[3]))
            og_diesel_electotal = min(max(od_wE, od_min), od_max)

            gr_pu_E = float(gp4.dot(wE))
            grcap_pu_etotal = max(min(gr_pu_E, 1.0), 0.0)

            grU_pu_E = float(gUp4.dot(wE))
            grU_pu_E = min(grU_pu_E, 1.0)
            real_percentaje_urban = grU_pu_E * grcap_pu_etotal
            max_allowed = min(self.U_p_u_etotal, grcap_pu_etotal)
            if real_percentaje_urban > max_allowed and grcap_pu_etotal > 0:
                grcapU_pu_etotal = max_allowed
            elif real_percentaje_urban <= max_allowed and grcap_pu_etotal > 0:
                grcapU_pu_etotal = real_percentaje_urban
            else:
                grcapU_pu_etotal = 0.0

            # EDemand
            fix_ed = float(fix4.dot(wD))
            fix_cost_edemand = max(fix_ed, 0.0)

            og_ed = float(ogv4.dot(wD))
            og_g_var_edemand = max(og_ed, 0.0)

            od_ed = float(odr4.dot(wD))
            og_diesel_edemand = min(max(od_ed, 0.0), 1.0)

            gp_ed = float(gp4.dot(wD))
            grcap_pu_edemand = min(max(gp_ed, 0.0), 1.0)

            gU_ed = float(gUp4.dot(wD))
            gU_ed = min(gU_ed, 1.0)
            real_percentaje_urban_ed = gU_ed * grcap_pu_edemand
            max_allowed_ed = min(self.U_p_u_edemand, grcap_pu_edemand)
            if real_percentaje_urban_ed > max_allowed_ed and grcap_pu_edemand > 0:
                grcapU_pu_edemand = max_allowed_ed
            elif real_percentaje_urban_ed <= self.U_p_u_edemand and grcap_pu_edemand > 0:
                # (nota: aquí tu “upper” no se usa; conservo tu lógica de asignar directamente)
                grcapU_pu_edemand = real_percentaje_urban_ed
            else:
                grcapU_pu_edemand = 0.0

            self.general_costs_data = {
                "ElecTotal": {
                    "fix_cost":  fix_cost_electotal,
                    "og_g_var":  og_g_var_electotal,
                    "og_diesel": og_diesel_electotal,
                    "grcap_pu":  grcap_pu_etotal,
                    "grcapU_pu": grcapU_pu_etotal,
                },
                "EDemand": {
                    "fix_cost":  fix_cost_edemand,
                    "og_g_var":  og_g_var_edemand,
                    "og_diesel": og_diesel_edemand,
                    "grcap_pu":  grcap_pu_edemand,
                    "grcapU_pu": grcapU_pu_edemand,
                },
            }

            # asignación a cost_parameters (igual que tenías)
            for block in ["ElecTotal", "EDemand"]:
                cp = self.cost_parameters[block]
                data = self.general_costs_data[block]
                cp.general.costs.FIX_Cost          = data["fix_cost"]
                cp.general.costs.OG_G_VAR          = data["og_g_var"]
                cp.general.costs.OG_G_Diesel_rate  = data["og_diesel"]
                cp.general.costs.GrCap_pu          = data["grcap_pu"]
                cp.general.costs.GrCapU_pu         = data["grcapU_pu"]

            logging.info("General costs calculated and assigned: %s", self.general_costs_data)

        except Exception as e:
            logging.error("Error al calcular los costes generales: %s", str(e))
            raise


            # --- 2. Cálculo de consumos generales ---
    def calculate_general_consumptions(self):
        """
        Calculate general consumptions using the general costs.
        Assign the results to self.general_consumptions_data and update the general part in self.cost_parameters.
        """
        try: 
            grcap_pu_value_etotal = self.general_costs_data.get("ElecTotal", {}).get("grcap_pu", 0)
            grcap_pu_value_edemand = self.general_costs_data.get("EDemand", {}).get("grcap_pu", 0)
            RC_etotal = self.RC_etotal
            UC_total= self.UC_etotal
            RC_edemand = self.RC_edemand
            UC_edemand = self.UC_edemand
            GC_etotal = (RC_etotal + UC_total) * grcap_pu_value_etotal
            OG_etotal = (RC_etotal + UC_total) - GC_etotal
            GC_edemand = (RC_edemand + UC_edemand) * grcap_pu_value_edemand
            OG_edemand = (RC_edemand + UC_edemand) - GC_edemand
            self.general_consumptions_data = {
            "ElecTotal": (GC_etotal, OG_etotal),
            "EDemand": (GC_edemand, OG_edemand)
        }
        # Actualizar la parte general de la estructura de costes:
            for block in ["ElecTotal", "EDemand"]:
                cp = self.cost_parameters[block]
                if block == "ElecTotal":
                    cp.general.consumption.GC = GC_etotal
                    cp.general.consumption.OG = OG_etotal
                else:
                    cp.general.consumption.GC = GC_edemand
                    cp.general.consumption.OG = OG_edemand
            logging.info("General consumptions calculated and assigned: %s", self.general_consumptions_data)
        except Exception as e:
            logging.error("Error al calcular los consumos generales: %s", str(e))   
            raise

            

    
    # --- 3. Cálculo de consumos específicos (por área) ---
    def calculate_specific_consumptions(self):
        """
        Calculates specific consumptions using the adjustments of consumptions.
        Assigns the results to self.specific_consumptions_data and updates the specific part in self.cost_parameters.

        """
        try:
            specific_data = {}
            for block in ["ElecTotal", "EDemand"]:
                # Seleccionar datos según el bloque:
                if block == "ElecTotal":
                    grcapU_pu = self.general_costs_data["ElecTotal"].get("grcapU_pu", 0)
                    RC_val = self.RC_etotal  # capacidad rural específica para ElecTotal
                    UC_val = self.UC_etotal  # capacidad urbana específica para ElecTotal
                    total_dem_urban = self.total_current_demand["urban"]
                    total_dem_rural = self.total_current_demand["rural"]
                else:  # EDemand
                    grcapU_pu = self.general_costs_data.get("EDemand", {}).get("grcapU_pu", 0)
                    RC_val = self.RC_edemand  # capacidad rural para EDemand
                    UC_val = self.UC_edemand  # capacidad urbana para EDemand
                    total_dem_urban = self.current_electricity_demand["urban"]
                    total_dem_rural = self.current_electricity_demand["rural"]

                # Se extrae GC (general consumption) para el bloque ya calculado
                GC = self.general_consumptions_data[block][0]  # primer valor del tuple (GC)
                OG = self.general_consumptions_data[block][1]  # segundo valor del tuple (OG)
                # Aplicar las fórmulas ajustadas:
                GCu = GC * grcapU_pu
                GCu = min(GCu, GC)  # Limitar GCu a que no pueda ser mayor que la capacidad GRid disponible 
                OGu = UC_val - GCu
                OGu = min(OG, max(OGu,0))  # Limitar OCu a que no pueda ser mayor que la capacidad OGrid disponible
                GCr = GC - GCu
                OGr = OG - OGu
                OGr = max(OGr,0)  # Limitar OGr a que no pueda ser negaivo

                # Calcular ajustes, evitando división por cero
                gcu = (GCu / UC_val) * total_dem_urban if UC_val > 0 else 0
                ogu = (OGu / UC_val) * total_dem_urban if UC_val > 0 else 0
                grc = (GCr / RC_val) * total_dem_rural if RC_val > 0 else 0
                ogr = (OGr / RC_val) * total_dem_rural if RC_val > 0 else 0

                specific_data[block] = (GCu, OGu, GCr, OGr, gcu, ogu, grc, ogr)

                # Actualizar la parte específica de la estructura para el bloque
                cp = self.cost_parameters[block]
                (GCu_val, OGu_val, GCr_val, OGr_val, gcu_val, ogu_val, grc_val, ogr_val) = specific_data[block]
                cp.urban.consumption.GCu = GCu_val
                cp.urban.consumption.OGu = OGu_val
                cp.urban.consumption.gcu = gcu_val
                cp.urban.consumption.ogu = ogu_val
                cp.rural.consumption.GCr = GCr_val
                cp.rural.consumption.OGr = OGr_val
                cp.rural.consumption.grc = grc_val
                cp.rural.consumption.ogr = ogr_val

            self.specific_consumptions_data = specific_data
            logging.info("Specific consumptions calculated and assigned: %s", self.specific_consumptions_data)
        except Exception as e:
                logging.error("Error calculating specific consumptions: %s", str(e))
                raise
        
        
    def calculateVAROGgen(self):
        #((Country data (Loss pu) +1)/2)*OG_G_var*(ogu+ogr)
        try: 
            for block in ["ElecTotal", "EDemand"]:
                cp_general = self.general_costs_data.get(block, {})
                og_g_var_value = cp_general.get("og_g_var")
                # Get ogu and ogr from specific consumptions for the block
                # self.specific_consumptions_data[block] is a tuple: (GCu, OGu, GCr, OGr, gcu, ogu, grc, ogr)
                _, _, _, _, _, ogu, _, ogr = self.specific_consumptions_data[block]
                var_oggen = ((self.power_losses_factor + 1) / 2) * og_g_var_value * (ogu + ogr)
                # Update the general costs data for the block
                self.general_costs_data[block]["var_oggen"] = var_oggen
                self.cost_parameters[block].general.costs.VAR_OGgen = var_oggen
            logging.info("VAR_OGgen calculated and assigned: %s", self.general_costs_data)
        
        except Exception as e:
            logging.error("Error al calcular los costes específicos: %s", str(e))
            raise


    # --- 4. Cálculo de costes específicos (por área) ---
    def calculate_specific_costs(self):
        """
        Calculates specific costs using the adjustments of costs.
        Assigns the results to self.specific_costs_data and updates the specific part in self.cost_parameters
        """
        try:
            self.specific_costs_data = {}
            # Iterate over each block to calculate specific cost adjustments.
            for block in ["ElecTotal", "EDemand"]:
                # Retrieve general cost data for the block.
                cp_gen = self.general_costs_data.get(block, {})
                fix_cost = cp_gen.get("fix_cost")
                og_g_var = cp_gen.get("og_g_var")
                
                # Select the U_p_u factor depending on the block.
                if block == "ElecTotal":
                    U_p_u_value = self.U_p_u_etotal 
                else:
                    U_p_u_value = self.U_p_u_edemand 

                # Retrieve specific consumption adjustments for the block.
                # The specific consumptions tuple is assumed to be:
                # (GCu, OGu, GCr, OGr, gcu, ogu, grc, ogr)
                (GCu, OGu, GCr, OGr, _, ogu, _, ogr) = self.specific_consumptions_data[block]

                # Calculate urban specific cost adjustments:
                urban_fix = fix_cost * U_p_u_value
                # Calculate rural cost adjustment as the difference.
                rural_fix = fix_cost - urban_fix

                # Calculate VAR_OGgen for each area using the formula.
                factor = (self.power_losses_factor + 1) / 2
                urban_var = ogu * og_g_var * factor
                rural_var = ogr * og_g_var * factor

                # Store results in a dictionary by block.
                self.specific_costs_data[block] = {
                    "urban": {
                        "FIX_Cost_exceptGGen": urban_fix,
                        "VAR_OGgen": urban_var
                    },
                    "rural": {
                        "FIX_Cost_exceptGGen": rural_fix,
                        "VAR_OGgen": rural_var
                    }
                }
                # Update the specific part of the cost parameters structure.
                cp = self.cost_parameters[block]
                cp.urban.costs.FIX_Cost_exceptGGen_u = self.specific_costs_data[block]["urban"]["FIX_Cost_exceptGGen"]
                cp.urban.costs.VAR_OGgen_u = self.specific_costs_data[block]["urban"]["VAR_OGgen"]
                cp.rural.costs.FIX_Cost_exceptGGen_r = self.specific_costs_data[block]["rural"]["FIX_Cost_exceptGGen"]
                cp.rural.costs.VAR_OGgen_r = self.specific_costs_data[block]["rural"]["VAR_OGgen"]
            logging.info("Specific costs calculated and assigned: %s", self.specific_costs_data)
        except Exception as e:
            logging.error("Error calculating specific costs: %s", str(e))
            raise


    #Calculo de costes finales para E-TOTAL 
    def calculate_final_costs(self):
        """
        Calculates final costs for the ETOTAL block.
        Assigns the results to self.final_costs_data and updates the final part in self.cost_parameters.

        """
        try:
            
            #block = "ElecTotal" -- Voy a guardar los resultados para ambos bloques porque lo necesito a posteriori 
            #Necesito Generation_CAPEX	0.11	$/KWh
                    #Generation_OPEX	0.03	$/Kwh
            GG_FIX = self.generation_CAPEX   # $/KWh (ej. 0.11)
            GG_VAR = self.generation_OPEX   # $/KWh (ej. 0.03)


            for block in ["ElecTotal", "EDemand"]:

                # Extraemos los consumos específicos para ETOTAL
                # self.specific_consumptions_data[block] is a tuple: (GCu, OGu, GCr, OGr, gcu, ogu, grc, ogr)
                consumptions = self.specific_consumptions_data[block]
                GCu, _, GCr, _, gcu, _, grc, _ = consumptions

                # Cálculo de FIX Grid Gen (en M$/year)
                # Nota: Dado que Generation_CAPEX está en $/KWh y los consumos en GWh/year,
                # la multiplicación se interpreta directamente en M$/year (1 GWh = 10^6 KWh y 1M$ = 10^6$).
                fix_grid_gen_urban = self.generation_CAPEX * GCu
                fix_grid_gen_rural = self.generation_CAPEX * GCr

                # Cálculo de VAR Grid Gen para cada zona (en M$/year)
                var_grid_gen_urban = self.generation_OPEX * (1 + self.power_losses_factor) * gcu
                var_grid_gen_rural = self.generation_OPEX * (1 + self.power_losses_factor) * grc

                # "Rest" y "VAR OffGrid" ya fueron calculados en calculate_specific_costs
                rest_urban = self.specific_costs_data[block]["urban"]["FIX_Cost_exceptGGen"]
                rest_rural = self.specific_costs_data[block]["rural"]["FIX_Cost_exceptGGen"]

                var_offgrid_urban = self.specific_costs_data[block]["urban"]["VAR_OGgen"]
                var_offgrid_rural = self.specific_costs_data[block]["rural"]["VAR_OGgen"]

                # Almacenamos los resultados en un diccionario
                self.final_costs_data[block] = {
                    "urban": {
                        "FIX_Grid_Gen": fix_grid_gen_urban,
                        "Rest": rest_urban,
                        "VAR_Grid_Gen": var_grid_gen_urban,
                        "VAR_OffGrid": var_offgrid_urban
                    },
                    "rural": {
                        "FIX_Grid_Gen": fix_grid_gen_rural,
                        "Rest": rest_rural,
                        "VAR_Grid_Gen": var_grid_gen_rural,
                        "VAR_OffGrid": var_offgrid_rural
                    }
                }

                # Se actualizan los parámetros de coste finales en la estructura cost_parameters para ETOTAL
                cp = self.cost_parameters[block]
                cp.urban.costs.FIX_Grid_Gen = fix_grid_gen_urban
                cp.urban.costs.Rest = rest_urban
                cp.urban.costs.VAR_Grid_Gen = var_grid_gen_urban
                cp.urban.costs.VAR_OffGrid = var_offgrid_urban

                cp.rural.costs.FIX_Grid_Gen = fix_grid_gen_rural
                cp.rural.costs.Rest = rest_rural
                cp.rural.costs.VAR_Grid_Gen = var_grid_gen_rural
                cp.rural.costs.VAR_OffGrid = var_offgrid_rural



                logging.info("Costes finales para ETOTAL calculados y asignados: %s", self.final_costs_data[block])
        except Exception as e:
            logging.error("Error al calcular los costes finales para ETOTAL: %s", str(e))
            raise

    #CALCULO DE RATIOS 
    def calculate_ratios(self):
        """
        Calculate the deployment ratios for each combination (area ID, isUrban) and store them
        all in a unified list, without separating by rural/urban.
        """
        try:
            block = "ElecTotal"
            for area_type in ['urban', 'rural']:
                current_demand = self.total_current_demand.get(area_type, 0)
                final_costs = self.final_costs_data[block][area_type]

                ratio = self._compute_ratio(final_costs, current_demand)
                self._store_area_ratio(self.demand_area_id, area_type, ratio, current_demand)

            logging.info("Ratios calculated: %s", self.area_ratios)
        except Exception as e:
            logging.error("Error calculating ratios: %s", str(e))
            raise


    def _compute_ratio(self, costs, demand):
        total_cost = (
            costs["FIX_Grid_Gen"] +
            costs["Rest"] +
            costs["VAR_Grid_Gen"] +
            costs["VAR_OffGrid"]
        )
        return min(total_cost / demand, 5) if demand > 0 else 5

    def _store_area_ratio(self, area_id, isUrban, ratio, demand):
        self.area_ratios.append({
            "id": area_id,
            "area_type": isUrban,
            "ratio": ratio,
            "demand": demand
        })


    def get_sorted_area_ratios(self):
        """
        Retuns the list of area ratios sorted by the ratio value.
        :return: dict with keys: id, area_type, ratio, demand.
        """
        return sorted(self.area_ratios, key=lambda x: x["ratio"])


    def use_cost_parameters(self, area_type: str, block: str):
        """
        Example of how to access the cost parameters structure.
        :param area_type: 'rural' or 'urban'
        :param block: 'ElecTotal' or 'EDemand'
        """
        cp = self.cost_parameters.get(block)
        if not cp:
            logging.error("Parameter block not found: %s", block)
            return

        if area_type.lower() == "rural":
            area_cp = cp.rural
        elif area_type.lower() == "urban":
            area_cp = cp.urban
        else:
            self.logger.error("Unrecognized area type: %s", area_type)
            return

        logging.info("Block %s - General Parameters: %s", block, cp.general)
        logging.info("Block %s - %s-Specific Parameters: %s", block, area_type, area_cp)


    

    def adjust_final_cost_electricity(self):
        """
        Adjusts the final cost based on the infrastructure parameters.
        Applies max logic for ElecTotal and scaled projection for EDemand.
        """
        try:
            # Obtener costes de proceso y transporte del estado actual
            dep_cost_variation = self.state.get_dep_cost_variation(self.fuel_id)
            process_cost = dep_cost_variation['Process']
            transport_cost = dep_cost_variation['Transport']

            # Calcular porcentaje off-grid
            (_, _, _, _, _, ogu, _, ogr) = self.specific_consumptions_data["ElecTotal"]
            total_demand = self.total_current_demand["urban"] + self.total_current_demand["rural"]
            self.final_offGrid_percentage = (ogu + ogr) / total_demand if total_demand > 0 else 0.0

            # Costes del estado previo si existe
            electricity_costs_blocks_prev = None
            prev_process_cost = 0.0
            prev_transport_cost = 0.0
            if self.prev_state is not None:
                dep_cost_variation_prev = self.prev_state.get_dep_cost_variation(self.fuel_id)
                prev_process_cost = dep_cost_variation_prev['Process']
                prev_transport_cost = dep_cost_variation_prev['Transport']
                areas_electrified_prev = set(self.prev_state.get_electrified_areas())
                if self.demand_area is not None:
                    demand_area_key = (self.demand_area.id, self.demand_area.area_type)
                    if demand_area_key in areas_electrified_prev:
                        electricity_costs_blocks_prev = self.prev_state.get_electricity_cost_parameters(self.demand_area.id)["cost_parameters"]

            # Función para proteger divisiones
            def safe_ratio(n, d): return n / d if d else 1.0

            max_costs_electotal = {}
            cost_electotal_this_state = {}

            for block in ["ElecTotal", "EDemand"]:
                for area in self.area_types:
                    final_cost_current = self.final_costs_data[block][area]

                    if block == "ElecTotal" and electricity_costs_blocks_prev is not None:
                        cp_prev = electricity_costs_blocks_prev[block].urban if area == 'urban' else electricity_costs_blocks_prev[block].rural
                        c_prev = cp_prev.costs
                        final_costs_prev = {
                            "FIX_Grid_Gen": c_prev.FINAL_FIX_Grid_Gen / (1 + prev_process_cost),
                            "Rest":         c_prev.FINAL_Rest         / (1 + prev_transport_cost),
                            "VAR_Grid_Gen": 0.0,
                            "VAR_OffGrid":  0.0
                        }

                        final_cost = {
                            "FIX_Grid_Gen": max(final_cost_current["FIX_Grid_Gen"], final_costs_prev["FIX_Grid_Gen"]),
                            "Rest":         max(final_cost_current["Rest"],         final_costs_prev["Rest"]),
                            "VAR_Grid_Gen": max(final_cost_current["VAR_Grid_Gen"], final_costs_prev["VAR_Grid_Gen"]),
                            "VAR_OffGrid":  max(final_cost_current["VAR_OffGrid"],  final_costs_prev["VAR_OffGrid"])
                        }

                        # Guardar para escalar EDemand luego
                        max_costs_electotal[area] = final_cost
                        cost_electotal_this_state[area] = final_cost_current

                    elif block == "EDemand" and electricity_costs_blocks_prev is not None:
                        electotal_max = max_costs_electotal.get(area, final_cost_current)
                        electotal_curr = cost_electotal_this_state.get(area, final_cost_current)

                        final_cost = {
                            "FIX_Grid_Gen": final_cost_current["FIX_Grid_Gen"] * safe_ratio(electotal_max["FIX_Grid_Gen"], electotal_curr["FIX_Grid_Gen"]),
                            "Rest":         final_cost_current["Rest"]         * safe_ratio(electotal_max["Rest"],         electotal_curr["Rest"]),
                            "VAR_Grid_Gen": final_cost_current["VAR_Grid_Gen"] * safe_ratio(electotal_max["VAR_Grid_Gen"], electotal_curr["VAR_Grid_Gen"]),
                            "VAR_OffGrid":  final_cost_current["VAR_OffGrid"]  * safe_ratio(electotal_max["VAR_OffGrid"],  electotal_curr["VAR_OffGrid"])
                        }
                    else:
                        final_cost = final_cost_current

                    # Guardar sin crecimiento aún
                    self.final_costs_data[block][area] = final_cost

                    # Aplicar crecimiento y guardar en cost_parameters
                    cp_area = self.cost_parameters[block].urban if area == 'urban' else self.cost_parameters[block].rural
                    cp_area.costs.FINAL_FIX_Grid_Gen = final_cost["FIX_Grid_Gen"] * (1 + process_cost)
                    cp_area.costs.FINAL_Rest = final_cost["Rest"] * (1 + transport_cost)
                    cp_area.costs.FINAL_VAR_Grid_Gen = final_cost["VAR_Grid_Gen"] * (1 + process_cost)
                    cp_area.costs.FINAL_VAR_OffGrid = final_cost["VAR_OffGrid"] * (1 + process_cost)

            logging.info("Adjusted final electricity cost completed successfully.")

        except Exception as e:
            logging.error("Error adjusting final cost of Electricity: %s", str(e), exc_info=True)
            raise



    
    # #Implemento métodos para rastrear anomalías

    def _force_zero_values_for(self, area_type):
        try: 
            """
            Forcing values to zero for the cost and consumption parameters
            for a specific area (urban or rural).
            """
            self.actual_adoption_dis_electricity[area_type] = 0.0
            self.total_current_demand[area_type] = 0.0
            self.current_ch_demand[area_type] = 0.0
            self.total_current_ch_demand_margin[area_type] = 0.0
            self.total_current_demand_margin[area_type] = 0.0
            self.current_projected_adoption_etotal[area_type] = 0.0
            self.current_projected_adoption_edemand[area_type] = 0.0
            self.current_electricity_demand[area_type] = 0.0
            
            
            for block in ["ElecTotal", "EDemand"]:
                cp = self.cost_parameters[block]
                cp_area = cp.urban if area_type == "urban" else cp.rural

                # General
                cp_area.consumption.GCu = 0.0
                cp_area.consumption.OGu = 0.0
                cp_area.consumption.gcu = 0.0
                cp_area.consumption.ogu = 0.0
                cp_area.consumption.GCr = 0.0
                cp_area.consumption.OGr = 0.0
                cp_area.consumption.grc = 0.0
                cp_area.consumption.ogr = 0.0

                # Costs
                cp_area.costs.FIX_Cost_exceptGGen_u = 0.0
                cp_area.costs.FIX_Cost_exceptGGen_r = 0.0
                cp_area.costs.VAR_OGgen_u = 0.0
                cp_area.costs.VAR_OGgen_r = 0.0
                cp_area.costs.FIX_Grid_Gen = 0.0
                cp_area.costs.Rest = 0.0
                cp_area.costs.VAR_Grid_Gen = 0.0
                cp_area.costs.VAR_OffGrid = 0.0
                cp_area.costs.FINAL_FIX_Grid_Gen = 0.0
                cp_area.costs.FINAL_Rest = 0.0
                cp_area.costs.FINAL_VAR_Grid_Gen = 0.0
                cp_area.costs.FINAL_VAR_OffGrid = 0.0

            # Y borra también los ratios, si se calcularon erróneamente
            #self.area_ratios = [r for r in self.area_ratios if r["area_type"] != area_type]
        except Exception as e:
            logging.error("Error al forzar valores a cero para %s: %s", area_type, str(e))
            raise

   

  

    def export_electric_cost_debug_info(self, output_path, state_id):
        """
        Exports all relevant cost, consumption, and projection parameters
        for the ElecTotal and EDemand blocks, differentiated by area type (rural/urban),
        into a TSV file with standardized columns.
        """
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            with open(output_path, "a", newline='') as tsvfile:
                writer = csv.writer(tsvfile, delimiter="\t")

                if os.stat(output_path).st_size == 0:
                    writer.writerow([
                        "State_ID", "DemandArea_ID", "AreaType", "Block",
                        "FIX_Cost", "OG_G_VAR", "VAR_OGgen", "OG_G_Diesel_rate",
                        "GrCap_pu", "GrCapU_pu",
                        "GC", "OG", "GCu", "OGu", "GCr", "OGr", "gcu", "ogu", "grc", "ogr",
                        "FIX_Cost_exceptGGen", "VAR_OGgen_spec",
                        "FIX_Grid_Gen", "Rest", "VAR_Grid_Gen", "VAR_OffGrid",
                        "FINAL_FIX_Grid_Gen", "FINAL_Rest", "FINAL_VAR_Grid_Gen", "FINAL_VAR_OffGrid",
                        "Ratio", "TotalDemand", "Total_EDemand",
                        "ProjectedAdoption_ETotal", "ProjectedAdoption_EDemand"
                    ])

                demand_area_id = self.demand_area_id

                for block in ["ElecTotal", "EDemand"]:
                    cp = self.cost_parameters[block]

                    for area_type in self.area_types:#["urban", "rural"]:
                        if self.current_ch_demand[area_type] == 0 and self.current_electricity_demand[area_type] == 0:
                            continue  # Excluir esta fila

                        is_urban = area_type == "urban"
                        cp_area = cp.urban if is_urban else cp.rural
                        ratio_entry = next(
                        (entry for entry in self.area_ratios if entry["area_type"] == area_type), None
                            )
                        writer.writerow([
                            state_id,
                            demand_area_id,
                            area_type,
                            block,
                            round(cp.general.costs.FIX_Cost, 4),
                            round(cp.general.costs.OG_G_VAR, 4),
                            round(cp.general.costs.VAR_OGgen, 4),
                            round(cp.general.costs.OG_G_Diesel_rate, 4),
                            round(cp.general.costs.GrCap_pu, 4),
                            round(cp.general.costs.GrCapU_pu, 4),
                            round(cp.general.consumption.GC, 4),
                            round(cp.general.consumption.OG, 4),
                            round(cp.urban.consumption.GCu, 4),
                            round(cp.urban.consumption.OGu, 4),
                            round(cp.rural.consumption.GCr, 4),
                            round(cp.rural.consumption.OGr, 4),
                            round(cp_area.consumption.gcu, 4),
                            round(cp_area.consumption.ogu, 4),
                            round(cp_area.consumption.grc, 4),
                            round(cp_area.consumption.ogr, 4),
                            round(cp_area.costs.FIX_Cost_exceptGGen_u if is_urban else cp_area.costs.FIX_Cost_exceptGGen_r, 4),
                            round(cp_area.costs.VAR_OGgen_u if is_urban else cp_area.costs.VAR_OGgen_r, 4),
                            round(cp_area.costs.FIX_Grid_Gen, 4),
                            round(cp_area.costs.Rest, 4),
                            round(cp_area.costs.VAR_Grid_Gen, 4),
                            round(cp_area.costs.VAR_OffGrid, 4),
                            round(cp_area.costs.FINAL_FIX_Grid_Gen, 4),
                            round(cp_area.costs.FINAL_Rest, 4),
                            round(cp_area.costs.FINAL_VAR_Grid_Gen, 4),
                            round(cp_area.costs.FINAL_VAR_OffGrid, 4),
                            round(ratio_entry["ratio"], 4)if ratio_entry else 0,
                            round(self.total_current_demand[area_type], 4),
                            round(self.current_electricity_demand[area_type], 4),
                            round(self.current_projected_adoption_etotal[area_type], 4),
                            round(self.current_projected_adoption_edemand[area_type], 4)
                        ])
            logging.info("Electric cost debug info exported to %s", output_path)
        except Exception as e:
            logging.error("Error exporting electric cost debug info: %s", str(e), exc_info=True)
            raise


    def _is_base_state(self) -> bool:
        """
        Returns true if the current state is the base/initial state.
        Adjust the conditions to your criteria for a real base.
        """
        try:
            return getattr(self.state, "stage_id", None) == 0 and str(getattr(self.state, "semester", "")).lower() == "first"
        except Exception:
            return False


    def maybe_store_base_edemand_cost_for_area(self, area_id: int, area_type: str, block: str = "EDemand") -> None:
        """
        If we are in the base state, sum FIX_Grid_Gen + Rest + VAR_Grid_Gen + VAR_OffGrid
        from the EDemand block and store the result by area/type in the State.
        """
        try:
            if not self._is_base_state():
                return
            # Debe existir final_costs_data[block][area_type] con las 4 partidas
            area_dict = (
                self.final_costs_data
                .get(block, {})
                .get(area_type, {})
            )
            if not area_dict:
                # Nada que guardar
                return

            fix_grid_gen = float(area_dict.get("FIX_Grid_Gen", 0.0) or 0.0)
            rest         = float(area_dict.get("Rest", 0.0) or 0.0)
            var_grid_gen = float(area_dict.get("VAR_Grid_Gen", 0.0) or 0.0)
            var_offgrid  = float(area_dict.get("VAR_OffGrid", 0.0) or 0.0)

            base_cost_edemand = fix_grid_gen + rest + var_grid_gen + var_offgrid

            # Guardamos en State por área/tipo
            self.state.set_base_edemand_cost_for_area(int(area_id), str(area_type), base_cost_edemand)

        except Exception as e:
            self.logger.error("Error guardando coste_base_edemand (area=%s, type=%s): %s",
                            area_id, area_type, str(e), exc_info=True)
            raise



   