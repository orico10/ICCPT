import logging
import os
import csv
from collections import defaultdict


from src.non_deploy_fuel_cost_model import ApplFuelCostModel

class LPGDeployModel:
   
    def __init__(self, prev_state,state, simulation_growth_scenario,  data_manager, sorted_areas, total_demand):
            """
            Initialize the LPG deployment for the current state.

            :param base_state: Base state (reference value).
            :param prev_state: Previous state (None if base).
            :param current_state: Current state.
            :param sorted_areas: List of areas sorted by ratio (each element: {"id", "area_type", "ratio", "demand"}).
            :param total_demand: Total country demand for the current state.
            :param target_electrification: Electrification target (percentage) for the current state.
            :param areas_electrified_prev: List of electrified areas in the previous state, as tuples (id, area_type).
            """
            
            self.prev_state = prev_state
            self.state = state
            self.growth_scenario = simulation_growth_scenario
            self.data_manager = data_manager    
            self.sorted_areas = sorted_areas #Entran como áreas LPG 
            self.total_demand = total_demand
            self.target_lpg_deploy = None #Asignamos más adelante 
            self.areas_LPG_deployed_prev = [] #areas_electrified_prev if areas_electrified_prev is not None else [] -- de momento no sé como se usaría 
            self.area_pct = 0.0 # Porcentaje que supone el área de la demanda total
            # Inicialio la información relevante para el fuel de electricidad
            self.fuel_id = 2
            #Extraer el nombre del fuel de electricidad
            self.fuel_id_to_name = dict(zip(
                self.data_manager.get_dataframe("Cooking_fuels")["Fuel_id"],
                self.data_manager.get_dataframe("Cooking_fuels")["Fuel_name"]
            ))
            self.fuel_name = self.fuel_id_to_name.get(self.fuel_id, "Unknown_Fuel")
            

            
            # deployment_plan_details = state.deployment_plan.details 
            # self.deployment_plan_fuels_data = deployment_plan_details.get("fuel_reference", [])
            #Extraer el Ref_capacity y Margin del fuel de electricidad (suponiendo que Fuel_id == 1 corresponde a electricidad)
            # self.lpg_fuel_data = next((fuel for fuel in self.deployment_plan_fuels_data if fuel["Fuel_id"] == self.fuel_id), None)
            # if self.lpg_fuel_data is None:
            #     raise ValueError("No se encontró el fuel de LPG con Fuel_id==2")

            # self.lpg_fuel_ref_capacity = self.lpg_fuel_data["Ref_capacity"]
            # self.lpg_fuel_margin = self.lpg_fuel_data["Margin"]

            #Extraer el config para rellenar datos necesarios 
            self.general_cofig = self.data_manager.get_config()

            # Extraer el target de electricidad a través del fuel_name (por ejemplo, "Electricity") salvo si es el estado base 
            self.base_year = self.growth_scenario.base_year 
            #self.base_year_state = state.get_state(self.base_year)
            if ( self.base_year == state.year) and state.semester == "first":
                # Extraer el taret de electricidad para el estado inicial o base 
                deployment_plan_details = state.deployment_plan.details 
                self.deployment_plan_fuels_data = deployment_plan_details.get("fuel_reference", [])
                
                self.deployment_plan_fuels_target = deployment_plan_details.get("fuels_target", [])
                self.target_lpg = self.general_cofig.get("LPG_adoption")
                self.lpg_fuel_data = next((fuel for fuel in self.deployment_plan_fuels_data if fuel["Fuel_id"] == self.fuel_id), None)
                if self.lpg_fuel_data is None:
                    raise ValueError("No se encontró el fuel de LPG con Fuel_id==2")

                self.lpg_fuel_ref_capacity = self.lpg_fuel_data["Ref_capacity"]
                self.lpg_fuel_margin = self.lpg_fuel_data["Margin"]
            else:
                #Extraer los detalles del plan de despliegue desde el state
                deployment_plan_details = prev_state.deployment_plan.details 
                self.deployment_plan_fuels_data = deployment_plan_details.get("fuel_reference", [])
                
                self.deployment_plan_fuels_target = deployment_plan_details.get("fuels_target", [])
                # Obtener el dep_plan_id actual desde el state
                
                
                # Extraer el target de electricidad de la fila encontrada
                #self.target_lpg = self.deployment_plan_fuels_target[0].get(self.fuel_name) * 100 if self.deployment_plan_fuels_target else 0.0 #Porque me entra como p.u 
                self.target_lpg = self.deployment_plan_fuels_target[0].get(self.fuel_name) if self.deployment_plan_fuels_target else 0.0
                self.lpg_fuel_data = next((fuel for fuel in self.deployment_plan_fuels_data if fuel["Fuel_id"] == self.fuel_id), None)
                if self.lpg_fuel_data is None:
                    raise ValueError("No se encontró el fuel de LPG con Fuel_id==2")

                self.lpg_fuel_ref_capacity = self.lpg_fuel_data["Ref_capacity"]
                self.lpg_fuel_margin = self.lpg_fuel_data["Margin"]
            # Almacenes de salida:
            self.lpg_deployed_areas = []    # Lista de áreas electrificadas en el estado actual (tuplas (id, area_type))
            self.not_lpg_deployed_areas = []  # Lista de áreas que quedan sin electrificar
            # Porcentajes
            self.already_lpg_deployed_percentage = 0.0  # % de demanda ya electrificada (del estado previo, si corresponde)
            self.current_lpg_deployed_percentage = 0.0  # % total electrificado al finalizar el despliegue


            # Si no se pasan áreas electrificadas, se intentan obtener del estado; si no, se usa lista vacía.
            self.areas_lpg_deployed_prev = prev_state.get_lpg_deployed_areas() if prev_state else {}


    def run_deployment(self):
        """
        Call the necessary methods to execute the LPG deployment.
        """
        try: 
            deployment_results = self.deploy()
            current_deployed= deployment_results["lpg_deployed"]
            #print(type(current_deployed))
            current_not_deployed = deployment_results["not_lpg_deployed"]

            # Se almacenan en el estado actual
            self.state.set_lpg_deployed_areas(current_deployed)
            self.state.set_not_lpg_deployed_areas(current_not_deployed)
            self.state.set_total_country_lpg_demand(self.total_demand)

        except Exception as e:
            raise ValueError(f"Error en el despliegue LPG: {str(e)}")

    def calculate_area_percentage(self, area):
        """
        Calculates the percentage of total demand represented by an area.

        :param area: Dictionary with key "demand".
        :return: Percentage (float).
        """
        #return (area["demand"] / self.total_demand) * 100 if self.total_demand > 0 else 0
        return (area["demand"] / self.total_demand)  if self.total_demand > 0 else 0
    
    
    def get_previously_lpg_deployed_percentage(self):
            """
            Cover the areas of the current state (sorted_areas) and accumulate the demand percentage
            of those that have already been deployed with LPG in the previous state.

            The percentage is calculated with respect to the total demand of the current state.
            The accumulated percentage per area is also stored in area_accumulated_percentages.

            :return: Accumulated percentage (float).
            """
            total = 0.0
            self.area_accumulated_percentages = {}

            for area in self.sorted_areas:
                key = (int(area["lpg_area_id"]), area["area_type"])

                if key in self.areas_lpg_deployed_prev:
                    area_pct = self.calculate_area_percentage(area)  # Siempre sobre demanda actual
                    total += area_pct
                    #self.area_accumulated_percentages[key] = total  # Para exportar o trazar

            self.already_lpg_deployed_percentage = total
            return total 
    
    def deploy(self):
        try:
            # 1) Áreas ya desplegadas en el estado previo
            deployed_prev_keys = set(self.areas_lpg_deployed_prev.keys())
            self.deployed_areas = [
                area for area in self.sorted_areas
                if (int(area["lpg_area_id"]), area["area_type"]) in deployed_prev_keys
            ]
            deployed_keys = {(int(a["lpg_area_id"]), a["area_type"]) for a in self.deployed_areas}

            # 2) Porcentaje ya desplegado (respecto a la demanda TOTAL del estado actual)
            self.area_accumulated_percentages = {}
            current_percentage = self.get_previously_lpg_deployed_percentage()

            # Tolerancia en p.u. (ya la usabas así)
            tolerance = 0.05

            # Si ya estamos en objetivo, salimos pronto
            if current_percentage >= self.target_lpg:
                self.current_lpg_deployed_percentage = current_percentage
                self.not_lpg_deployed_areas = [
                    area for area in self.sorted_areas
                    if (int(area["lpg_area_id"]), area["area_type"]) not in deployed_keys
                ]
                print(f"[INFO] Target LPG ({self.target_lpg:.2%}) previously achieved {self.prev_state.stage_id} "
                    f"({self.prev_state.year} {self.prev_state.semester}). No further deployment needed.")
                logging.warning(f"⚠️  [WARNING] Target de LPG ({self.target_lpg:.2%}) ya superado en estado "
                                f"{self.state.stage_id} ({self.state.year} {self.state.semester}). No se conectan nuevas áreas.")
                return {
                    "lpg_deployed": {
                        (int(a["lpg_area_id"]), a["area_type"]): a for a in self.deployed_areas
                    },
                    "not_lpg_deployed": {
                        (int(a["lpg_area_id"]), a["area_type"]): a for a in self.not_lpg_deployed_areas
                    },
                    "current_percentage": self.current_lpg_deployed_percentage
                }

            # 3) Candidatas ordenadas por ratio (ya vienen ordenadas en self.sorted_areas)
            candidates = [
                a for a in self.sorted_areas
                if a.get("ratio", None) != 5 and (int(a["lpg_area_id"]), a["area_type"]) not in deployed_keys
            ]

            # Helper para calcular % que ocupa un área (en p.u.)
            def pct(a):
                return self.calculate_area_percentage(a)

            i = 0
            while i < len(candidates) and current_percentage < self.target_lpg + tolerance:
                remaining = self.target_lpg + tolerance - current_percentage
                # Ventana deslizante: la actual y hasta las dos siguientes
                window = candidates[i:i+3]

                # 3.1 Intento greedy estándar: si cabe la primera, adelante
                chosen = []
                if window and pct(window[0]) <= remaining:
                    chosen = [window[0]]
                else:
                    # 3.2 Look-ahead: probar la 2ª sola, la 3ª sola, y combinaciones (2+3)
                    best_sum = -1.0
                    best_choice = []

                    # probar individuales (2ª y 3ª)
                    for idx in range(1, min(3, len(window))):
                        s = pct(window[idx])
                        if s <= remaining and s > best_sum:
                            best_sum = s
                            best_choice = [window[idx]]

                    # probar combinación de 2ª + 3ª (si existen)
                    if len(window) >= 3:
                        s = pct(window[1]) + pct(window[2])
                        if s <= remaining and s > best_sum:
                            best_sum = s
                            best_choice = [window[1], window[2]]

                    chosen = best_choice

                if not chosen:
                    # Ninguna opción de la ventana cabe: avanzamos el puntero para re-evaluar con siguiente base.
                    # Como el remaining solo decrece, si la primera no cabe ahora, no cabrá más adelante,
                    # y tiene sentido saltarla (no la eliminamos globalmente por si quieres analizarla en debug).
                    i += 1
                    continue

                # Añadir las elegidas
                for a in chosen:
                    key = (int(a["lpg_area_id"]), a["area_type"])
                    if key in deployed_keys:
                        continue  # seguridad
                    self.deployed_areas.append(a)
                    deployed_keys.add(key)
                    current_percentage += pct(a)
                    self.area_accumulated_percentages[key] = current_percentage

                # Eliminar elegidas del array de candidatas y NO incrementar i si hemos quitado la i-ésima
                # (re-evaluamos desde la misma posición tras compactar la lista)
                chosen_set = set(id(x) for x in chosen)
                # reconstruir la lista eliminando las elegidas
                new_candidates = []
                for idx, a in enumerate(candidates):
                    if id(a) in chosen_set:
                        continue
                    new_candidates.append(a)
                # Recalcular i: si elegimos la primera (candidates[i]), mantenemos i;
                # si elegimos solo 2ª/3ª, también mantenemos i para revisar la nueva "primera" en esta posición.
                candidates = new_candidates

                # Si ya alcanzamos target (con tolerancia), salimos del bucle
                if current_percentage >= self.target_lpg + 1e-12 or current_percentage >= self.target_lpg:
                    break

            self.current_lpg_deployed_percentage = current_percentage
            self.not_lpg_deployed_areas = [
                a for a in self.sorted_areas
                if (int(a["lpg_area_id"]), a["area_type"]) not in deployed_keys
            ]

            return {
                "lpg_deployed": {
                    (int(a["lpg_area_id"]), a["area_type"]): a for a in self.deployed_areas
                },
                "not_lpg_deployed": {
                    (int(a["lpg_area_id"]), a["area_type"]): a for a in self.not_lpg_deployed_areas
                },
                "current_percentage": self.current_lpg_deployed_percentage
            }

        except Exception as e:
            raise ValueError(f"Error en el despliegue de LPG: {str(e)}")


    # def deploy(self):
    #     try:
    #         deployed_prev_keys = set(self.areas_lpg_deployed_prev.keys())
    #         self.deployed_areas = [
    #             area for area in self.sorted_areas
    #             if (int(area["lpg_area_id"]), area["area_type"]) in deployed_prev_keys
    #         ]
    #         self.area_accumulated_percentages = {}
    #         current_percentage = self.get_previously_lpg_deployed_percentage()
    #         tolerance = 0.05#Dato en p.u 

    #         deployed_keys = {
    #             (int(area["lpg_area_id"]), area["area_type"]) for area in self.deployed_areas
    #         }

    #         if current_percentage >= self.target_lpg:
    #             self.current_lpg_deployed_percentage = current_percentage
    #             self.not_lpg_deployed_areas = [
    #                 area for area in self.sorted_areas
    #                 if (int(area["lpg_area_id"]), area["area_type"]) not in deployed_keys
    #             ]
    #             # print(f" [INFO] Target LPG ({self.target_lpg:.2f}%) previously achieved {self.state.stage_id} ({self.state.year} {self.state.semester}) no further deployment needed.")
    #             # logging.warning(f"⚠️  [WARNING] Target de LPG ({self.target_lpg:.2f}%) ya superado en estado {self.state.stage_id} ({self.state.year} {self.state.semester}). No se conectan nuevas áreas.")
    #             #print(f" [INFO] Target LPG ({self.target_lpg:.2f}%) previously achieved {self.state.stage_id} ({self.state.year} {self.state.semester}) no further deployment needed.")
    #             print(f"[INFO] Target LPG ({self.target_lpg:.2%}) previously achieved {self.state.stage_id} ({self.state.year} {self.state.semester}). No further deployment needed.")
    #             logging.warning(f"⚠️  [WARNING] Target de LPG ({self.target_lpg:.2%}) ya superado en estado {self.state.stage_id} ({self.state.year} {self.state.semester}). No se conectan nuevas áreas.")

                
    #             return {
    #                 "lpg_deployed": {
    #                     (int(area["lpg_area_id"]), area["area_type"]): area for area in self.deployed_areas
    #                 },
    #                 "not_lpg_deployed": {
    #                     (int(area["lpg_area_id"]), area["area_type"]): area for area in self.not_lpg_deployed_areas
    #                 },
    #                 "current_percentage": self.current_lpg_deployed_percentage
    #             }

    #         for area in self.sorted_areas:
    #             key = (int(area["lpg_area_id"]), area["area_type"])
    #             if area["ratio"] == 5 or key in deployed_keys:
    #                 continue
    #             area_pct = self.calculate_area_percentage(area)
    #             if current_percentage + area_pct <= self.target_lpg + tolerance:
    #                 self.deployed_areas.append(area)
    #                 deployed_keys.add(key)
    #                 current_percentage += area_pct
    #                 self.area_accumulated_percentages[key] = current_percentage
    #             else:
    #                 break

    #         self.current_lpg_deployed_percentage = current_percentage
    #         self.not_lpg_deployed_areas = [
    #             area for area in self.sorted_areas
    #             if (int(area["lpg_area_id"]), area["area_type"]) not in deployed_keys
    #         ]

    #         return {
    #             "lpg_deployed": {
    #                 (int(area["lpg_area_id"]), area["area_type"]): area for area in self.deployed_areas
    #             },
    #             "not_lpg_deployed": {
    #                 (int(area["lpg_area_id"]), area["area_type"]): area for area in self.not_lpg_deployed_areas
    #             },
    #             "current_percentage": self.current_lpg_deployed_percentage
    #         }

    #     except Exception as e:
    #         raise ValueError(f"Error en el despliegue de LPG: {str(e)}")


    def export_lpg_deployment_debug_info(self, output_path):
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            write_header = not os.path.isfile(output_path) or os.stat(output_path).st_size == 0

            with open(output_path, mode='a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file, delimiter='\t')
                if write_header:
                    writer.writerow([
                        "State_ID", "Year", "Semester", "LpgArea_Id", "AreaType",
                        "LPG_Deployed_Current", "LPG_Deployed_Previous",
                        "Area_Ratio", "Area_Percentage", "Accumulated_Percentage",
                        "Target_Current", "Target_Previous",
                        "Country_Demand_Current", "Country_Demand_Previous"
                    ])

                prev_target = self.already_lpg_deployed_percentage if self.prev_state else 0.0
                prev_total_demand = self.prev_state.get_total_country_lpg_demand() if self.prev_state else 0.0
                deployed_keys = {
                    (int(area["lpg_area_id"]), area["area_type"]) for area in self.deployed_areas
                }
                deployed_prev_keys = set(self.areas_lpg_deployed_prev.keys())

                for area in self.sorted_areas:
                    key = (int(area["lpg_area_id"]), area["area_type"])
                    deployed_now = 1 if key in deployed_keys else 0
                    deployed_prev = 1 if key in deployed_prev_keys else 0
                    area_pct = self.calculate_area_percentage(area)
                    accumulated_pct = self.area_accumulated_percentages.get(key, 0.0)

                    writer.writerow([
                        self.state.stage_id,
                        self.state.year,
                        self.state.semester,
                        area["lpg_area_id"],
                        area["area_type"],
                        deployed_now,
                        deployed_prev,
                        area["ratio"],
                        f"{area_pct:.4f}",
                        f"{accumulated_pct:.4f}",
                        f"{self.target_lpg:.2f}",
                        f"{prev_target:.2f}",
                        f"{self.total_demand:.2f}",
                        f"{prev_total_demand:.2f}"
                    ])
        except Exception as e:
            raise ValueError(f"Error exportando LPG deployment debug info: {str(e)}")



