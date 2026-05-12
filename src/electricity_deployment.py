import os
import csv
import logging


class DeployElectricity:
    
    def __init__(self, prev_state, state, simulation_growth_scenario, data_manager, sorted_areas, total_demand, demand_area_manager):
        """
        Initialize the DeployElectricity class with necessary parameters.
        :param prev_state: Previous state (None if first state).
        :param state: Current state (State object).
        :param simulation_growth_scenario: Simulation growth scenario.
        :param data_manager: Access to data and configurations.
        :param sorted_areas: List of areas sorted by ratio.
        :param total_demand: Total country demand for the current state.
        :param demand_area_manager: Manager for demand areas.

        """
        
        self.prev_state = prev_state
        self.state = state
        self.growth_scenario = simulation_growth_scenario
        self.data_manager = data_manager
        self.sorted_areas = sorted_areas
        self.total_demand = total_demand
        self.demand_area_manager = demand_area_manager

        self.target_electrification = None #Asignamos más adelante 
        self.areas_electrified_prev = [] #areas_electrified_prev if areas_electrified_prev is not None else [] -- de momento no sé como se usaría 
        self.prev_elec_pct = 0.0 # Porcentaje de electrificación previo
        # Inicialio la información relevante para el fuel de electricidad
        self.fuel_id = 1
       
        

        #Extraer el nombre del fuel de electricidad
        self.fuel_id_to_name = dict(zip(
            self.data_manager.get_dataframe("Cooking_fuels")["Fuel_id"],
            self.data_manager.get_dataframe("Cooking_fuels")["Fuel_name"]
        ))
        fuel_name = self.fuel_id_to_name.get(self.fuel_id, "Unknown_Fuel")

        
        # deployment_plan_details = state.deployment_plan.details 
        # self.deployment_plan_fuels_data = deployment_plan_details.get("fuel_reference", [])
        #Extraer el Ref_capacity y Margin del fuel de electricidad (suponiendo que Fuel_id == 1 corresponde a electricidad)
        # self.electricity_fuel_data = next((fuel for fuel in self.deployment_plan_fuels_data if fuel["Fuel_id"] == self.fuel_id), None)
        # if self.electricity_fuel_data is None:
        #     raise ValueError("No se encontró el fuel de electricidad con Fuel_id==1")

        # self.electricity_fuel_ref_capacity = self.electricity_fuel_data["Ref_capacity"]
        # self.electricity_fuel_margin = self.electricity_fuel_data["Margin"]

        #Extraer el config para rellenar datos necesarios 
        self.general_cofig = self.data_manager.get_config()

        # Extraer el target de electricidad a través del fuel_name (por ejemplo, "Electricity") salvo si es el estado base 
        self.base_year = self.growth_scenario.base_year 
        #self.base_year_state = state.get_state(self.base_year)
        # Extraer el target de electricidad a través del fuel_name (por ejemplo, "Electricity") salvo si es el estado base 
        self.base_year = self.growth_scenario.base_year 
        self.first_semester = "first"
        #self.base_year_state = self.find_state(self.mixed_states, self.base_year, "first")

        if ( self.base_year == state.year) and state.semester == "first":
             # Extraer el taret de electricidad para el estado inicial o base 
            self.target_electrification = self.general_cofig.get("Electricity_adoption")
            deployment_plan_details = state.deployment_plan.details 
            self.deployment_plan_fuels_data = deployment_plan_details.get("fuel_reference", [])
            
            self.deployment_plan_fuels_target = deployment_plan_details.get("fuels_target", [])
            # Obtener el dep_plan_id actual desde el state
            # Extraer el target de electricidad de la fila encontrada
            
            self.electricity_fuel_data = next((fuel for fuel in self.deployment_plan_fuels_data if fuel["Fuel_id"] == self.fuel_id), None)
            if self.electricity_fuel_data is None:
                raise ValueError("No se encontró el fuel de electricidad con Fuel_id==1")

            self.electricity_fuel_ref_capacity = self.electricity_fuel_data["Ref_capacity"]
            self.electricity_fuel_margin = self.electricity_fuel_data["Margin"]
        else:
            #Extraer los detalles del plan de despliegue desde el state
            deployment_plan_details = prev_state.deployment_plan.details 
            self.deployment_plan_fuels_data = deployment_plan_details.get("fuel_reference", [])
            
            self.deployment_plan_fuels_target = deployment_plan_details.get("fuels_target", [])
            # Obtener el dep_plan_id actual desde el state
            # Extraer el target de electricidad de la fila encontrada
            self.target_electrification = self.deployment_plan_fuels_target[0].get(fuel_name) #* 100 #Porque el dato me entra como p.u 
            self.electricity_fuel_data = next((fuel for fuel in self.deployment_plan_fuels_data if fuel["Fuel_id"] == self.fuel_id), None)
            if self.electricity_fuel_data is None:
                raise ValueError("No se encontró el fuel de electricidad con Fuel_id==1")

            self.electricity_fuel_ref_capacity = self.electricity_fuel_data["Ref_capacity"]
            self.electricity_fuel_margin = self.electricity_fuel_data["Margin"]
        # Almacenes de salida:
        self.electrified_areas = []    # Lista de áreas electrificadas en el estado actual (tuplas (id, area_type))
        self.not_electrified_areas = []  # Lista de áreas que quedan sin electrificar
        # Porcentajes
        self.already_electrified_percentage = 0.0  # % de demanda ya electrificada (del estado previo, si corresponde)
        self.current_electrification_percentage = 0.0  # % total electrificado al finalizar el despliegue

        

        # Si no se pasan áreas electrificadas, se intentan obtener del estado; si no, se usa lista vacía.
        if prev_state is None:
            self.areas_electrified_prev = []
            self.lpg_deployed_prev = []
        else:
            self.areas_electrified_prev = prev_state.get_electrified_areas()
            self.lpg_deployed_prev = prev_state.get_lpg_deployed_areas()
    
    # @staticmethod
    # def find_state(states_list, year, semester):
    #     return next((s for s in states_list if s.year == year and s.semester == semester), None)

    def run_deployment(self):
        """
        Call the necessary methods to execute the electricity deployment.
        """
        try: 
            deployment_results = self.deploy()
            current_electrified = deployment_results["electrified"]
            current_not_electrified = deployment_results["not_electrified"]

            # Se almacenan en el estado actual
            self.state.set_electrified_areas(current_electrified)
            self.state.set_not_electrified_areas(current_not_electrified)
            self.state.set_total_country_el_demand(self.total_demand)
            

        except Exception as e:
            raise ValueError(f"Error en el despliegue eléctrico: {str(e)}")

    def calculate_area_percentage(self, area):
        """
        Calculate the percentage of the total demand that an area represents.

        :param area: Dictionary with key "demand".
        :return: Percentage (float).
        """
        #return (area["demand"] / self.total_demand) * 100 if self.total_demand > 0 else 0
        return (area["demand"] / self.total_demand)  if self.total_demand > 0 else 0
    
    
    def get_previously_electrified_percentage(self):
        """
        Recovers the sorted_areas list and accumulates the percentage of demand from those areas
        that have already been electrified in the previous state.

        :return: Accumulated percentage already electrified.
        """
        total = 0.0
        for area in self.sorted_areas:
            key = (area["id"], area["area_type"])
            if key in self.areas_electrified_prev:
                total += self.calculate_area_percentage(area)
        self.already_electrified_percentage = total
        return total

    def deploy(self):
        """
        Execute the improved electricity deployment.
        - If the target is exceeded, keep the previous areas and issue a warning.
        - If not, deploy new areas until the target is reached.
        """
        try:
            # --- Inicializar
            self.electrified_areas = list(self.areas_electrified_prev)  # ⚡ MANTENER ELECTRIFICADAS
            self.area_accumulated_percentages = {}
            current_percentage = self.get_previously_electrified_percentage()
            

            tolerance = 0.05  # Tolerancia del 0.05%

            # Si ya superamos el target
            if current_percentage >= self.target_electrification:
                self.current_electrification_percentage = current_percentage
                self.not_electrified_areas = []
                for area in self.sorted_areas:
                    key = (area["id"], area["area_type"])
                    if key not in self.electrified_areas:
                        self.not_electrified_areas.append(key)
                # print(f" [INFO] Electrification target ({self.target_electrification:.2f * 100} %) previously achieved {self.state.stage_id} ({self.state.year} {self.state.semester}) no further deployment needed..")
                # logging.warning(f"⚠️  [WARNING] Target de electrificación ({self.target_electrification:.2f}%) ya superado en estado {self.state.stage_id} ({self.state.year} {self.state.semester}). No se conectan nuevas áreas.")
                print(f"[INFO] Electrification target ({self.target_electrification:.2%}) previously achieved {self.prev_state.stage_id} ({self.prev_state.year} {self.prev_state.semester}) no further deployment needed..")
                logging.warning(f"⚠️  [WARNING] Target de electrificación ({self.target_electrification:.2%}) ya superado en estado {self.prev_state.stage_id} ({self.prev_state.year} {self.prev_state.semester}). No se conectan nuevas áreas.")

                return {
                    "electrified": self.electrified_areas,
                    "not_electrified": self.not_electrified_areas,
                    "current_percentage": self.current_electrification_percentage
                }

            # --- Proceder normalmente
            for area in self.sorted_areas:
                key = (area["id"], area["area_type"])
                area_ratio = area["ratio"]
                demand_area = self.demand_area_manager.get_demand_area_by_id_and_type(*key)
                lpg_area_id = int(demand_area.lpg_area)   #["lpg_area"]
                key_lpg = (lpg_area_id, demand_area.area_type)

                if area_ratio == 5:
                    continue  # Ignorar áreas no electrificables

                if key in self.areas_electrified_prev:
                    continue  # Ya estaba electrificado, lo dejamos como está
                if key_lpg in self.lpg_deployed_prev:
                    continue # Si el área pertenece al conjunto que anteriormente se desplegó lpg, no se electrifica


                area_pct = self.calculate_area_percentage(area)

                if current_percentage + area_pct <= self.target_electrification + tolerance:
                    self.electrified_areas.append(key)
                    current_percentage += area_pct
                    self.area_accumulated_percentages[key] = current_percentage
                else:
                    break

            self.current_electrification_percentage = current_percentage

            self.not_electrified_areas = []
            for area in self.sorted_areas:
                key = (area["id"], area["area_type"])
                if key not in self.electrified_areas:
                    self.not_electrified_areas.append(key)

            return {
                "electrified": self.electrified_areas,
                "not_electrified": self.not_electrified_areas,
                "current_percentage": self.current_electrification_percentage
            }

        except Exception as e:
            raise ValueError(f"Error en el despliegue eléctrico: {str(e)}")







    def export_electrification_debug_info(self, output_path):
        """
        Exports detailed information about the electricity deployment to a single TSV file (append by state).
        Designed to be compatible with Tableau.
        """
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            file_exists = os.path.isfile(output_path)
            write_header = not file_exists or os.stat(output_path).st_size == 0

            with open(output_path, mode='a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file, delimiter='\t')

                if write_header:
                    # Cabeceras
                    writer.writerow([
                        "State_ID", "Year", "Semester", "DemandArea_ID", "AreaType", "ElArea_Id",
                        "Electrified_Current", "Electrified_Previous",
                        "Area_Ratio", "Area_Percentage", "Accumulated_Percentage",
                        "Target_Current", "Target_Previous",
                        "Country_Demand_Current", "Country_Demand_Previous"
                    ])

                prev_target = 0.0
                prev_total_demand = 0.0
                if self.prev_state:
                    prev_target = self.already_electrified_percentage 
                    prev_total_demand = self.prev_state.get_total_country_el_demand()

                for area in self.sorted_areas:
                    key = (area["id"], area["area_type"])
                    area_ratio = area["ratio"]
                    demand_area = self.demand_area_manager.get_demand_area_by_id_and_type(area["id"], area["area_type"])

                    electrified_now = 1 if key in self.electrified_areas else 0
                    electrified_prev = 1 if key in self.areas_electrified_prev else 0
                    area_pct = self.calculate_area_percentage(area)
                    accumulated_pct = self.area_accumulated_percentages.get(key, 0.0)

                    writer.writerow([
                        self.state.stage_id,
                        self.state.year,
                        self.state.semester,
                        area["id"],
                        area["area_type"],
                        demand_area.el_area,
                        electrified_now,
                        electrified_prev,
                        area_ratio,
                        f"{area_pct:.4f}",
                        f"{accumulated_pct:.4f}",
                        f"{self.target_electrification:.2f}",
                        f"{prev_target:.2f}",
                        f"{self.total_demand:.2f}",
                        f"{prev_total_demand:.2f}"
                    ])
        except Exception as e:
            raise ValueError(f"Error exporting electrification debug info: {str(e)}")

