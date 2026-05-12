import pandas as pd
import logging
import os
import csv
from typing import Dict
from dataclasses import dataclass, field
import numpy as np


@dataclass
class DemandAreaSocialCosts:
    health: float = 0.0
    gender: float = 0.0
    deforestation: float = 0.0

@dataclass
class AggregatedSocialCosts:
    health_costs: Dict[int, float] = field(default_factory=dict)
    gender_costs: Dict[int, float] = field(default_factory=dict)
    #emissions_costs: Dict[int, float] = field(default_factory=dict)
    deforestation_costs: Dict[int, float] = field(default_factory=dict)

class SocialCostModel:
    def __init__(self, state, data_manager, demand_area):
        """
        Constructor for SocialCostModel for a single demand area.
        
        :param state: Current state.
        :param data_manager: Data manager used to retrieve the full Technologies dataframe.
        :param demand_area: Identifier (or object) for the demand area.
        :param final_adoption: Dictionary with keys "rural" and "urban", where each maps
                               technology IDs to absolute adoption (in Mcooks/year) for that demand area.
                               Example:
                               {
                                   "rural": {tech_id: adoption_value, ...},
                                   "urban": {tech_id: adoption_value, ...}
                               }
        """
        self.state = state
        self.data_manager = data_manager
        self.demand_area = demand_area
        #self.income_model = income_model # Assuming demand_area has an income_model attribute
        
        # Load the complete Technologies dataframe (which must include social cost parameters)
        self.df_technologies = data_manager.get_dataframe("enriched_technologies")
        # self.df_technologies["Technologies_id"] = self.df_technologies["Technologies_id"].astype("int32")
        # self.df_technologies["Fuel_id"] = self.df_technologies["Fuel_id"].astype("int32")  # si no hay nulos
 



        # Columnas necesarias (solo lectura)
        tech_id_col = self.df_technologies["Technologies_id"]
        fuel_id_col = self.df_technologies["Fuel_id"]

        # Caché: Tech_id -> Fuel_id (sin set_index/merge/copy)
        self._tech_to_fuel = pd.Series(
            fuel_id_col.to_numpy(copy=False),
            index=tech_id_col.to_numpy(copy=False)
        ).to_dict()

        # Arrays alineados al orden del DF (para vectorizado rápido)
        self._tech_ids = tech_id_col.to_numpy(copy=False)
        self._health   = self.df_technologies["Health"].to_numpy(copy=False)
        self._timegen  = (
            self.df_technologies["FuelTimeGen"].to_numpy(copy=False) +
            self.df_technologies["ApplianceTimeGen"].to_numpy(copy=False)
        )
        self._defor    = self.df_technologies["Deforestation"].to_numpy(copy=False)

        # Instead of summing over all technologies, store per-technology details:
        self.rural_details = {}  # key: tech_id, value: DemandAreaSocialCosts for rural part
        self.urban_details = {}  # key: tech_id, value: DemandAreaSocialCosts for urban part

    @property
    def area_types(self):
        """
        Returns ['rural'] or ['urban'] if self.demand_area.area_type is defined,
        or both ['rural', 'urban'] if not defined (None).
        """
        return [self.demand_area.area_type] if self.demand_area.area_type else ['rural', 'urban']
    
    def run_simulation(self):
        """
        Calcula costes sociales por tecnología y los agrega por fuel después.
        Devuelve {"rural": {...}, "urban": {...}} con detalles por tecnología.
        """
        try:
            logging.info("Iniciando simulación de costes sociales para área %s", self.demand_area.id)

            tech_ids_series = pd.Series(self._tech_ids)

            for area_type in self.area_types:
                base_cook = (
                    self.demand_area.data
                    .get("demand_census_rur_urb", {})
                    .get(area_type, {})
                    .get("cooking", 0)
                )
                if base_cook == 0:
                    logging.warning("Demanda de cocina cero para área %s (%s), se ignora.",
                                    self.demand_area.id, area_type)
                    if area_type == "rural": self.rural_details = {}
                    else: self.urban_details = {}
                    # aun así guarda vacíos por fuel
                    self.save_social_costs(area_type, AggregatedSocialCosts())
                    continue

                # Adopción absoluta por tech_id (dict -> Serie -> reindex a orden del DF)
                absolute_income = self.state.get_absolute_income_adoption(self.demand_area.id, area_type)
                s_abs = pd.Series(absolute_income, dtype="float64")
                s_abs = s_abs.reindex(tech_ids_series).fillna(0.0)
                a = s_abs.to_numpy(copy=False)

                if not np.any(a):
                    # guardar vacíos por fuel y continuar
                    if area_type == "rural": self.rural_details = {}
                    else: self.urban_details = {}
                    self.save_social_costs(area_type, AggregatedSocialCosts())
                    continue

                # Cálculos vectorizados
                v_health = a * self._health
                v_gender = a * self._timegen
                v_defor  = (a * self._defor) / 1000.0

                nz = a != 0.0
                tech_ids_nz = self._tech_ids[nz]

                # Construir detalles por tecnología solo para las que tienen adopción > 0
                details = {
                    int(tid): DemandAreaSocialCosts(
                        health=float(v_health[i]),
                        gender=float(v_gender[i]),
                        deforestation=float(v_defor[i])
                    )
                    for i, tid in enumerate(self._tech_ids) if nz[i]
                }

                if area_type == "rural":
                    self.rural_details = details
                else:
                    self.urban_details = details

                # Agregar por fuel (una sola vez por área)
                self.save_social_costs(area_type, AggregatedSocialCosts())

            results = {"rural": self.rural_details, "urban": self.urban_details}
            logging.info("Social costs for demand area %s calculados.", self.demand_area.id)
            return results

        except Exception as e:
            logging.error("Error en run_simulation para área %s: %s", self.demand_area, e, exc_info=True)
            raise


    # def run_simulation(self):
    #     """
    #     Calculates social costs for the given demand area per technology, separately for rural and urban,
    #     using the formulas:
        
    #         Health = Absolute Adoption * tech(health)
    #         Gender = Absolute Adoption * (tech(f_timeGen) + tech(a_timeGen))
    #         Deforestation = (Absolute Adoption * tech(deforestation)) / 1000
        
    #     The computed values are stored in dictionaries keyed by technology ID.
        
    #     Returns:
    #         A dictionary with keys "rural" and "urban", where each maps to another dictionary:
    #             { tech_id: DemandAreaSocialCosts, ... }
    #     """
    
    #     try:
    #           # Salimos sin hacer cálculos
            
    #         logging.info("Iniciando simulación de costes sociales para área %s", self.demand_area.id)
    #         for area_type in self.area_types: #["rural", "urban"]:
    #             base_cook = self.demand_area.data.get("demand_census_rur_urb", {}).get(area_type, {}).get("cooking", 0)
    #             if base_cook == 0:
    #                 logging.warning("Demanda de cocina cero para área %s (%s), se ignora.", self.demand_area.id, area_type)
    #                 if area_type == "rural":
    #                         self.rural_details = {}
    #                 else:
    #                         self.urban_details = {}
    #                 return
    #             absolute_income  = self.state.get_absolute_income_adoption(self.demand_area.id,area_type)#.get(tech_id, {})
    #             #self.income_model.absolute_income_adoption.get(area_type, {}).get(tech_id, 0.0)
    #             for tech_id, adoption_value in absolute_income.items():
    #                 # Retrieve technology parameters from the dataframe.
    #                 tech_row = self.df_technologies[self.df_technologies["Technologies_id"] == tech_id]
    #                 if tech_row.empty:
    #                     logging.warning("Technology %s not found in Technologies dataframe", tech_id)
    #                     continue
    #                 tech_data = tech_row.iloc[0]
                    
    #                 # Extract social cost factors (defaulting to 0.0 if not present)
    #                 health_factor = tech_data.get("Health", 0.0)
    #                 f_timeGen = tech_data.get("FuelTimeGen", 0.0)
    #                 a_timeGen = tech_data.get("ApplianceTimeGen", 0.0)
    #                 deforestation_factor = tech_data.get("Deforestation", 0.0)
                    
    #                 # Compute the social cost components for this technology. -- MUnits/year es decir, adp absolutas
    #                 health_cost = adoption_value * health_factor
    #                 gender_cost = adoption_value * (f_timeGen + a_timeGen)
    #                 deforestation_cost = (adoption_value * deforestation_factor) / 1000.0
                    
    #                 cost_details = DemandAreaSocialCosts(
    #                     health=health_cost,
    #                     gender=gender_cost,
    #                     deforestation=deforestation_cost
    #                 )
                    
    #                 # Store the result in the appropriate dictionary.
    #                 if area_type == "rural":
    #                     self.rural_details[tech_id] = cost_details
    #                     self.save_social_costs("rural", AggregatedSocialCosts())
    #                 else:
    #                     self.urban_details[tech_id] = cost_details
    #                     self.save_social_costs("urban", AggregatedSocialCosts())

                    
                       
                        
    #             logging.info("Completed social cost calculation for %s area of demand %s", area_type, self.demand_area)
            
    #         results = {"rural": self.rural_details, "urban": self.urban_details}
    #         # Save results to the State by fuel if 
            
    #         #self.state.save_social_costs(self.demand_area.id, area_type, cost_details)
    #         logging.info("Social costs for demand area %s: %s", self.demand_area, results)
    #         return results
    #     except Exception as e:
    #         logging.error("Error in SocialCostModel run_simulation for demand area %s: %s", self.demand_area, e, exc_info=True)
    #         raise

        
    def export_social_costs_debug_info(self, output_path, state_id):
        """
        Exports the social cost results by technology to a TSV file.
        
        Columnas:
        - DemandArea_ID
        - State_ID
        - AreaType
        - Technology_ID
        - SocialCost_Health
        - SocialCost_Gender
        - SocialCost_Deforestation
        """
        try:
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            write_header = not os.path.exists(output_path) or os.stat(output_path).st_size == 0

            with open(output_path, "a", newline='') as tsvfile:
                writer = csv.writer(tsvfile, delimiter="\t")
                
                if write_header:
                    writer.writerow([
                        "DemandArea_ID", "State_ID", "AreaType",
                        "Technology_ID",
                        "SocialCost_Health", "SocialCost_Gender", "SocialCost_Deforestation"
                    ])

                for area_type in self.area_types:
                    details = self.rural_details if area_type == "rural" else self.urban_details
                    if not details:
                        logging.warning("No social cost results to export for area %s (%s)", self.demand_area.id, area_type)
                        continue

                    for tech_id, cost_obj in details.items():
                        writer.writerow([
                            self.demand_area.id,
                            state_id,
                            area_type,
                            tech_id,
                            cost_obj.health,
                            cost_obj.gender,
                            cost_obj.deforestation
                        ])
            logging.info("Social cost debug info exported to %s", output_path)
        except Exception as e:
            logging.error("Error exporting social cost debug info: %s", str(e), exc_info=True)
            raise

    def save_social_costs(self, area_type: str, social_costs: AggregatedSocialCosts):
        if area_type not in ("rural", "urban"):
            raise ValueError("Invalid area type. Must be 'rural' or 'urban'.")

        per_tech = self.rural_details if area_type == "rural" else self.urban_details
        if not per_tech:
            social_costs.health_costs = {}
            social_costs.gender_costs = {}
            social_costs.deforestation_costs = {}
            self.state.save_aggregated_social_costs(self.demand_area.id, area_type, social_costs)
            return

        m = self._tech_to_fuel  # cache Tech_id -> Fuel_id

        fuels = []
        h = []; g = []; d = []
        for tid, c in per_tech.items():
            fid = m.get(int(tid))
            if fid is None:
                # si no hay mapping, ignora esa tecnología
                continue
            fuels.append(int(fid))
            h.append(float(c.health)); g.append(float(c.gender)); d.append(float(c.deforestation))

        if not fuels:
            social_costs.health_costs = {}
            social_costs.gender_costs = {}
            social_costs.deforestation_costs = {}
            self.state.save_aggregated_social_costs(self.demand_area.id, area_type, social_costs)
            return

        fuels = np.asarray(fuels, dtype=np.int64)
        h = np.asarray(h, dtype=np.float64)
        g = np.asarray(g, dtype=np.float64)
        d = np.asarray(d, dtype=np.float64)

        uniq, inv = np.unique(fuels, return_inverse=True)
        H = np.bincount(inv, weights=h)
        G = np.bincount(inv, weights=g)
        D = np.bincount(inv, weights=d)

        social_costs.health_costs        = {int(fid): float(val) for fid, val in zip(uniq, H)}
        social_costs.gender_costs        = {int(fid): float(val) for fid, val in zip(uniq, G)}
        social_costs.deforestation_costs = {int(fid): float(val) for fid, val in zip(uniq, D)}

        self.state.save_aggregated_social_costs(self.demand_area.id, area_type, social_costs)




    # Addicional method for saving results into state by fuel type, taking into acount that they are alrady save by technology,
    #  into AggregatedSocialCosts where the int is the fuel id and the var is the social cost but it need to be associated to the demand area and type 
    # def save_social_costs(self, area_type: str, social_costs: AggregatedSocialCosts):
    #     """
    #     Save the aggregated social costs for a specific area type (rural or urban) into the state.
        
    #     :param area_type: "rural" or "urban"
    #     :param social_costs: AggregatedSocialCosts object (vacío) que se completará con los
    #                          costes agregados por fuel_id para este demand_area y área.
    #     """
    #     if area_type not in ("rural", "urban"):
    #         raise ValueError("Invalid area type. Must be 'rural' or 'urban'.")

    #     per_tech = self.rural_details if area_type == "rural" else self.urban_details
    #     if not per_tech:
    #         # Nada que agregar
    #         social_costs.health_costs = {}
    #         social_costs.gender_costs = {}
    #         social_costs.deforestation_costs = {}
    #         self.state.save_aggregated_social_costs(self.demand_area.id, area_type, social_costs)
    #         return

    #     # 1) DataFrame con costes por tecnología
    #     # Evita .append en bucle: list of dicts → DataFrame de golpe
    #     rows = [
    #         {
    #             "Technologies_id": tid,
    #             "health": c.health,
    #             "gender": c.gender,
    #             "deforestation": c.deforestation,
    #         }
    #         for tid, c in per_tech.items()
    #     ]
    #     df_costs = pd.DataFrame.from_records(rows)

    #     # 2) Join con tecnologías para obtener Fuel_id una sola vez
    #     # (asegura columnas clave y dtypes)
    #     df_tech = self.df_technologies[["Technologies_id", "Fuel_id"]]
    #     df = df_costs.merge(df_tech, on="Technologies_id", how="left", validate="many_to_one")

    #     # 3) Groupby por fuel y suma
    #     g = df.groupby("Fuel_id", dropna=True, observed=True)[["health", "gender", "deforestation"]].sum()

    #     # 4) Volcado a dicts
    #     social_costs.health_costs = g["health"].to_dict()
    #     social_costs.gender_costs = g["gender"].to_dict()
    #     social_costs.deforestation_costs = g["deforestation"].to_dict()

    #     self.state.save_aggregated_social_costs(self.demand_area.id, area_type, social_costs)

    # def save_social_costs(self, area_type: str, social_costs: AggregatedSocialCosts):
    #     """
    #     Save the aggregated social costs for a specific area type (rural or urban) into the state.
        
    #     :param area_type: "rural" or "urban"
    #     :param social_costs: AggregatedSocialCosts object (vacío) que se completará con los
    #                          costes agregados por fuel_id para este demand_area y área.
    #     """
    #     if area_type not in ["rural", "urban"]:
    #         raise ValueError("Invalid area type. Must be 'rural' or 'urban'.")

    #     # 1) Elegimos el diccionario que contiene los costes a nivel de tecnologías
    #     if area_type == "rural":
    #         per_tech: Dict[int, DemandAreaSocialCosts] = self.rural_details
    #     else:
    #         per_tech: Dict[int, DemandAreaSocialCosts] = self.urban_details

    #     # 2) Creamos diccionarios vacíos para acumular los costes totales por fuel_id
    #     health_agg: Dict[int, float] = {}
    #     gender_agg: Dict[int, float] = {}
    #     deforestation_agg: Dict[int, float] = {}

    #     # 3) Para cada tecnología, recuperamos su fuel_id y sumamos sus componentes de coste
    #     for tech_id, cost_obj in per_tech.items():
    #         # Buscamos la fila de la tecnología en el DataFrame (ID -> Fuel_id)
    #         tech_row = self.df_technologies[self.df_technologies["Technologies_id"] == tech_id]
    #         if tech_row.empty:
    #             logging.warning("No se encontró Technology %s al agrupar por fuel_id; se ignora.", tech_id)
    #             continue

    #         fuel_id = tech_row.iloc[0].get("Fuel_id", None)
    #         if fuel_id is None:
    #             logging.warning(
    #                 "La tecnología %s no tiene Fuel_id en el DataFrame; se ignora para agregación.", tech_id
    #             )
    #             continue

    #         # Acumulamos,
    #         #    - si el fuel_id no existe aún, lo inicializamos a 0.0
    #         health_agg[fuel_id] = health_agg.get(fuel_id, 0.0) + cost_obj.health
    #         gender_agg[fuel_id] = gender_agg.get(fuel_id, 0.0) + cost_obj.gender
    #         deforestation_agg[fuel_id] = deforestation_agg.get(fuel_id, 0.0) + cost_obj.deforestation

    #     # 4) Rellenamos el objeto AggregatedSocialCosts
    #     social_costs.health_costs = health_agg
    #     social_costs.gender_costs = gender_agg
    #     social_costs.deforestation_costs = deforestation_agg

    #     # 5) Finalmente, llamamos al state para guardar estos costes agregados.
    #     #    Ajusta el nombre del método si tu state utiliza otro.
    #     try:
    #         self.state.save_aggregated_social_costs(self.demand_area.id, area_type, social_costs)
    #         logging.info(
    #             "Costes sociales agregados guardados para DemandArea %s (%s): %s",
    #             self.demand_area.id, area_type, social_costs
    #         )
    #     except Exception as e:
    #         logging.error(
    #             "Error al guardar costes sociales agregados para DemandArea %s (%s): %s",
    #             self.demand_area.id, area_type, e,
    #             exc_info=True
    #         )
    #         raise


        

        

 



