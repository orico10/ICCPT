import logging
import numpy as np
import pandas as pd
import os
import csv

class ApplFuelCostModel:
    """
    Model to calculate the costs of apliances and fuels."""

    def __init__(self, state, data_manager, demand_area, adoption_model, income_model, tech_df):
        self.state = state
        self.data_manager = data_manager
        self.demand_area = demand_area
        #self.area_type = None 
        
        self.adoption_model = adoption_model
        self.income_model = income_model
        self.tech_df = tech_df  # Le paso la tecnología que toque en cada momento 
        #self.all_techs_df = all_techs_df  # Todas las tecnologías posibles

        self.demand_area_id = demand_area.id

        # Extrae los planes de precio del estado
        price_details = self.state.price_plan.details
        self.fuel_price_plan = price_details.get("fuel_price", [])
        self.appl_price_plan = price_details.get("app_price", [])

        # Inicializa resultados
        self.final_total_income_appliances = {"rural": 0.0, "urban": 0.0}
        self.final_appl_income_by_fuel = {"rural": {}, "urban": {}}
        self.final_income_participation_per_appliance_by_fuel = {"rural": {}, "urban": {}}
        
    @property
    def area_types(self):
        """
        Returns ['rural'] or ['urban'] if self.demand_area.area_type is defined,
        or both ['rural', 'urban'] if it is not defined (None).
        """
        return [self.demand_area.area_type] if self.demand_area.area_type else ['rural', 'urban']
    
   
    def run_simulation(self):
        """
        Executes the simulation of technology and fuel costs.
        Vectorizes the calculation for each area type sin pandas pesados.
        """
        try:
            techs = self.tech_df  # NO copy
            tech_ids = techs["Technologies_id"].to_numpy(copy=False)
            appl_id  = techs["Appliance_id"].to_numpy(copy=False)
            fuel_id  = techs["Fuel_id"].to_numpy(copy=False)
            appl_price = techs["AppliancePrice"].to_numpy(copy=False)

            # Construye un mapeo (único) Appliance_id -> PriceMultiplier
            price_map_appl = {}
            for plan in self.appl_price_plan:      # [{'Kettle':0.9,...}, ...] o {appl_id:mult}
                price_map_appl.update(plan)

            # Si tus planes están por NOMBRE de appliance y no por ID,
            # traduce aquí: appl_id -> name -> multiplier
            # (si ya están por ID, esto devolverá 1.0 sin coste)
            appl_id_to_name = self.adoption_model.appl_id_to_name
            def _mult_for_appl_id(aid):
                name = appl_id_to_name.get(int(aid))
                if name is None:  # planes por ID
                    return float(price_map_appl.get(int(aid), 1.0))
                # planes por NOMBRE
                return float(price_map_appl.get(name, price_map_appl.get(int(aid), 1.0)))

            price_multiplier = np.fromiter((_mult_for_appl_id(a) for a in appl_id),
                                        dtype=np.float64, count=len(appl_id))

            # Factor de coste por appliance (igual que antes)
            appl_income_cost_factor = appl_price.astype(np.float64) * (price_multiplier - 1.0)

            # Prepara estructuras destino por área
            for area_type in self.area_types:
                logging.info("Iniciando simulación de costes de tecnologías para área %s", self.demand_area.id)

                # 1) Demanda de cocina base
                base_cook = self.demand_area.data.get("demand_census_rur_urb", {}).get(area_type, {}).get("cooking", 0)
                if base_cook == 0:
                    logging.warning("Demanda de cocina cero para área %s (%s), se ignora.", self.demand_area_id, area_type)
                    self.final_total_income_appliances[area_type] = 0.0
                    self.final_appl_income_by_fuel[area_type] = {}
                    # asegura el contenedor para participación
                    if area_type not in self.final_income_participation_per_appliance_by_fuel:
                        self.final_income_participation_per_appliance_by_fuel[area_type] = {}
                    continue  # no abortes toda la simulación

                # 2) Adopciones potenciales (dict {tech_id: adoption} -> array)
                adoption_dict = self.state.get_potential_adoption(self.demand_area_id, area_type)
                adoption = np.array([float(adoption_dict.get(int(tid), 0.0)) for tid in tech_ids], dtype=np.float64)

                # 3) Consumo de cocinado del área
                ch = float(self.state.get_CH_consumption(self.demand_area_id, area_type)[area_type])

                # 4) Coste final por tecnología (vectorizado)
                final_appl_cost = adoption * ch * appl_income_cost_factor  # == "FinalApplCost"

                # 5) Agregado por Fuel_id (sin groupby)
                uniq_fuels, inv_fuels = np.unique(fuel_id.astype(np.int64), return_inverse=True)
                cost_sum_by_fuel = np.bincount(inv_fuels, weights=final_appl_cost)
                cost_by_fuel = {int(fid): float(val) for fid, val in zip(uniq_fuels, cost_sum_by_fuel)}
                self.final_appl_income_by_fuel[area_type] = cost_by_fuel

                # 6) Total área
                self.final_total_income_appliances[area_type] = float(final_appl_cost.sum())

                # 7) Participación por appliance dentro de cada fuel (sin groupby/set_index)
                #    Creamos/actualizamos el dict anidado: area_type -> fuel_id -> appliance_id -> valor
                per_area = self.final_income_participation_per_appliance_by_fuel.setdefault(area_type, {})
                # Acumula con un bucle simple (rápido en numpy + dict)
                for i in range(final_appl_cost.size):
                    fid = int(fuel_id[i])
                    aid = int(appl_id[i])
                    val = float(final_appl_cost[i])
                    if val == 0.0:
                        continue
                    bucket = per_area.setdefault(fid, {})
                    bucket[aid] = bucket.get(aid, 0.0) + val

                # 8) Guarda en estado
                self._save_to_state(area_type, cost_by_fuel)

        except Exception as e:
            logging.error("Error en run_simulation de NonDeployFuelCostModel: %s", e, exc_info=True)
            raise


    # def run_simulation(self):
    #     """
    #     Executes the simulation of technology and fuel costs.
    #     Vectorizes the calculation for each area type.
    #     """
    #     try:
            
    #         for area_type in self.area_types:
    #             logging.info("Iniciando simulación de costes de tecnologías para área %s", self.demand_area.id)
    #             # Paso 1: chequeo de demanda cero
    #             base_cook = self.demand_area.data.get("demand_census_rur_urb", {}).get(area_type, {}).get("cooking", 0)
    #             if base_cook == 0:
    #                 logging.warning("Demanda de cocina cero para área %s (%s), se ignora.", self.demand_area_id, area_type)
    #                 self.final_total_income_appliances[area_type] = {}
    #                 self.final_appl_income_by_fuel[area_type] = {}
    #                 return  # Salimos sin hacer cálculos


    #             # Construye un mapeo de multiplicadores de precio por Appliance_id 
    #             price_map_appl = {}
    #             for plan in self.appl_price_plan:
    #                 price_map_appl.update(plan)

    #             techs = self.tech_df.copy()
    #             techs["PriceMultiplier"] = techs["Appliance_id"].map(price_map_appl).fillna(1.0)
    #             techs["ApplianceIncomeCostFactor"] = techs["AppliancePrice"] * (techs["PriceMultiplier"] - 1) 

    #             # Obtenemos las adopciones potenciales de cada tecnhología
    #             adoption_series = pd.Series(self.state.get_potential_adoption(self.demand_area_id, area_type)) # Lo cambiamos a obtenerlo del estado state.get_potential_adoption(da_id, area_type)
    #             # Obtenemos la demanda de cocinado de cada área 
    #             ch = self.state.get_CH_consumption(self.demand_area_id, area_type)[area_type]

    #             # Calculamos el Appliance income by type como ch_consumption (misma para todas las tech) * adoption (de las tecnologías que pertenecen al mismo fuel) * ApplianceIncomeCostFactor (de las technologías que pertenecen al mismo fuel)
    #             techs["Adoption"] = techs["Technologies_id"].map(adoption_series).fillna(0.0)
                
    #             techs["ApplianceIncomeCostFactor"] = techs["ApplianceIncomeCostFactor"].astype(float)
    #             techs["FinalApplCost"] = techs["Adoption"] *  ch * techs["ApplianceIncomeCostFactor"]#
                
    #             # Asignamos a la variable final_income_costs_appl el coste de appliances por área y para fuel id (en technologies están los ids de cada fuel, tech y apliance)
    #             cost_by_fuel = techs.groupby("Fuel_id")["FinalApplCost"].sum().to_dict()
    #             self.final_appl_income_by_fuel[area_type] = cost_by_fuel
                
    #             # Suma de todos los costes de appliances para el área
    #             self.final_total_income_appliances[area_type] = sum(cost_by_fuel.values())


    #                 # Participation by tech calculamos para cada appliance que pertenece a un fuel su porcentaje de partificación como : 
    #                 # Para todas las appliances que pertenecen a un fuel, asignamos en un diccionario fuel id, appliance id su valor de coste* ch * adopcion
    #                 # for fuel_id, group in techs.groupby("Fuel_id"):
    #                 #     self.final_income_participation_per_appliance_by_fuel[area_type][fuel_id] = group.set_index("Appliance_id")["FinalApplCost"].to_dict()
    #                 # # Guardamos los resultados en el estado
    #                 # 7️⃣ Acumular appliances por fuel_id y appliance_id
    #             if area_type not in self.final_income_participation_per_appliance_by_fuel:
    #                 self.final_income_participation_per_appliance_by_fuel[area_type] = {}

    #             for fuel_id, group in techs.groupby("Fuel_id"):
    #                 appliances_dict = group.set_index("Appliance_id")["FinalApplCost"].to_dict()
    #                 if fuel_id not in self.final_income_participation_per_appliance_by_fuel[area_type]:
    #                     self.final_income_participation_per_appliance_by_fuel[area_type][fuel_id] = {}
    #                 for appliance_id, value in appliances_dict.items():
    #                     existing = self.final_income_participation_per_appliance_by_fuel[area_type][fuel_id].get(appliance_id, 0.0)
    #                     self.final_income_participation_per_appliance_by_fuel[area_type][fuel_id][appliance_id] = existing + value

    #             self._save_to_state(area_type, cost_by_fuel)





            
       
        except Exception as e:
            logging.error("Error en run_simulation de NonDeployFuelCostModel: %s", e, exc_info=True)
            raise

    

    def _save_to_state(self, area_type, cost_by_fuel):
        """
        Saves the cost results to the state.
        """
        try:
            # Guardamos los resultados en el estado
            self.state.set_final_income_costs_appl(self.demand_area_id, area_type, self.final_total_income_appliances[area_type])
            self.state.set_final_income_costs_fuel(self.demand_area_id, area_type, cost_by_fuel)
            self.state.set_final_income_participation_per_appliance_by_fuel(self.demand_area_id, area_type, self.final_income_participation_per_appliance_by_fuel[area_type])
            logging.info("Resultados guardados en el estado para área %s: %s", area_type, cost_by_fuel)
        except Exception as e:
            logging.error("Error al guardar resultados en el estado: %s", str(e), exc_info=True)
            raise

    def export_rest_cost_debug_info(self, output_path, state_id):
        """
        Exports the results in tabular format with append to a TSV file.
        Columns: DemandArea_ID, State_ID, AreaType, ApplianceSet_ID, ApplianceFinalCost, Fuel_ID, FuelFinalCost
        """
        try:
            for area_type in self.area_types:
                if not self.final_total_income_appliances.get(area_type) and not self.final_appl_income_by_fuel.get(area_type):
                    logging.warning("Área %s (%s) ignorada en exportación porque no tiene datos calculados.", self.demand_area_id, area_type)
                    return  # Ignoramos la impresión

                os.makedirs(os.path.dirname(output_path), exist_ok=True)

                with open(output_path, "a", newline='') as tsvfile:
                    writer = csv.writer(tsvfile, delimiter="\t")

                    # Escribir encabezado si el archivo está vacío
                    if os.stat(output_path).st_size == 0:
                        writer.writerow([
                            "DemandArea_ID", "State_ID", "AreaType",
                            "ApplianceSet_ID", "ApplianceFinalCost",
                            "Fuel_ID", "FuelFinalCost"
                        ])

                    # Escribir costos de appliances
                    for appl_id, cost in self.final_income_participation_per_appliance_by_fuel[area_type].items():
                        writer.writerow([
                            self.demand_area_id,
                            state_id,
                            area_type,
                            appl_id,
                            cost,
                            None,
                            None
                        ])

                    # Escribir costos de fuel
                    for fuel_id, cost in self.final_appl_income_by_fuel[area_type].items():
                        writer.writerow([
                            self.demand_area_id,
                            state_id,
                            area_type,
                            None,
                            None,
                            fuel_id,
                            cost
                        ])

                logging.info("Rest cost debug info exported to %s", output_path)
        except Exception as e:
            logging.error("Error exporting rest cost debug info: %s", str(e), exc_info=True)
            raise
