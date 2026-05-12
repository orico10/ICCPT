import pandas as pd
import logging
from src.deployment_plan import DeploymentPlan
from src.pricing_plan import PricePlan
from src.financial_agg_params import FinancialAggParams
from dataclasses import dataclass, field
from typing import Dict, Optional, Any
import copy
@dataclass
class AggregatedSocialCosts:
    health_costs: Dict[int, float] = field(default_factory=dict)
    gender_costs: Dict[int, float] = field(default_factory=dict)
    emissions_costs: Dict[int, float] = field(default_factory=dict)
    deforestation_costs: Dict[int, float] = field(default_factory=dict)
from dataclasses import dataclass

@dataclass
class EconomicResult:
    net_electric_total: float = 0.0     # income_E_total - (fix_grid_gen + rest + var_grid_gen + var_offgrid)
    net_lpg_total: float = 0.0          # income_LPG - (fix_upstream + fix_local + var_upstream + var_local + import)
    taxes_subsidies_total: float = 0.0  # suma de (appliances + fuels)
    grand_total: float = 0.0            # net_electric_total + net_lpg_total + taxes_subsidies_total

@dataclass
class BaseEDemandCountryCosts:
    rural: float = 0.0
    urban: float = 0.0

    @property
    def total(self) -> float:
        return self.rural + self.urban


class State:
    def __init__(self, stage_id, year):
        self.stage_id = stage_id
        self.year = year
        self.deployment_plan = None  # Instancia de DeploymentPlan
        self.price_plan = None       # Instancia de PricePlan
        
        self.demand_areas_data = {}  # Estructura para guardar datos por área de demanda
        self.electrified_areas = []
        self.not_electrified_areas = []  # Áreas que no se electrificaron
        self.total_country_el_demand = 0  # Demanda total de electricidad del país
        self.country_off_grid_percentage = 0.0  # Porcentaje total off-grid del país

        self.electricity_cost_results = {}  # Resultados de costos de electricidad
        
        self.lpg_cost_results = {} # Resultados de costos de LPG
        self.lpg_deployed_areas = {}  # Áreas donde se ha desplegado LPG
        self.not_lpg_deployed_areas = {}  # Áreas donde no se ha desplegado LPG
        self.total_country_lpg_demand = 0
        self.total_lpg_consumption_due_toCH = {} # Consumo total de LPG debido a cocción y calefacción Mtons/yr 



        self.cost_dep_variation = {}
        self.financial_results: FinancialAggParams = None 
        
        #self.appliance_weights = {}  # Pesos de los electrodomésticos
        self.electricity_emissions = {}
        self.lpg_emissions = {}

        #self.social_cost = {}  # Costes sociales por área de demanda
        self._aggregated_social_costs: Dict[int,Dict[str, AggregatedSocialCosts]] = {}  # Costes sociales agregados por área de demanda y tipo de área
        self.emiss_non_dep_fuels: Dict[int, Dict[str, Dict[int, float]]] = {}# Emisiones de combustibles no desplegados por área de demanda
        #self.income_by_appliance: Dict[int, Dict[str, Dict[int, float]]] = {}

        # Params for Summary results 
        self._base_price: Dict[int, Dict[str, Dict[str, Any]]] = {}
    
        self._country_base_price: dict = {}
        self._economic_result: EconomicResult | None = None
        self._base_edemand_costs_by_area: Dict[int, Dict[str, float]] = {}
        self._country_base_edemand_costs: Optional[BaseEDemandCountryCosts] = None

        self._country_adoption_shares: Dict[str, Dict[str, Dict[int, float]]] = {
            "initial": {"rural": {}, "urban": {}, "total": {}},
            "potential": {"rural": {}, "urban": {}, "total": {}},
        }

    @classmethod
    def from_parent(cls, parent: "State", **overrides):
        """
        Clona el estado sin hacer deepcopy:
        - Shallow copy del objeto.
        - Rehace copias LIGERAS de dicts pequeños que se suelen mutar.
        - Mantiene por referencia estructuras grandes (DFs/tablas en dicts).
        """
        # 1) copia superficial del objeto
        child = copy.copy(parent)

        # 2) dicts PEQUEÑOS que queremos independizar del padre (clona ligero)
        small_mutables = [
            "_base_price",
            "_country_base_price",
            "_base_edemand_costs_by_area",
            "_country_adoption_shares",
            "cost_dep_variation",
            "electricity_emissions",
            "lpg_emissions",
            "income_by_appliance",
            "_aggregated_social_costs",
            "emiss_non_dep_fuels",
            "electricity_cost_results",
            "lpg_cost_results",
            "lpg_deployed_areas",
            "not_lpg_deployed_areas",
            "demand_areas_data",
        ]
        for name in small_mutables:
            if hasattr(parent, name):
                val = getattr(parent, name)
                if isinstance(val, dict):
                    setattr(child, name, dict(val))
                else:
                    # listas pequeñas u otros contenedores
                    setattr(child, name, copy.copy(val))

        # 3) valores escalares
        child.stage_id = parent.stage_id
        child.year = parent.year
        child.semester = getattr(parent, "semester", 0)

        # 4) aplica overrides (p.ej., stage_id, semester)
        for k, v in overrides.items():
            setattr(child, k, v)

        return child
    
    def snapshot(self):
        snap = object.__new__(self.__class__)
        snap.__dict__ = self.__dict__.copy()     # 1er nivel
        # Para campos pesados que nunca mutas en prev_state, deja referencias.
        # Para los que sí cambien en el "current", duplica sólo 1er nivel:
        # snap.some_dict = dict(self.some_dict)
        return snap



    def calculate_cost_dep_variation(self, simulation_growth_scenario):


        """
        Calculate the cost of deployment variation based on the simulation growth scenario.
        """
        
        
        try:
           # Extract growth parameters
            dep_fuel_cost_var = simulation_growth_scenario.dep_fuel_cost_var
            # Extract GrowthPat_Name position 0 #suponemos que estamos en el estado general 
            
            fuelID_el = 1
            fuelID_lpg = 2
            # Se extraen los años base y actual para el cálculo
            
            base_year = simulation_growth_scenario.base_year
            actual_year = self.year
            diff_year = actual_year - base_year
            exponent = diff_year
            scenario_name = simulation_growth_scenario.scenario_name 
            for fuel_id in [fuelID_el, fuelID_lpg]:
                # Buscar en el patrón de crecimiento el registro que corresponda con el Fuel_id y el patrón 'General'
                record = next(
                    (r for r in dep_fuel_cost_var 
                    if r.get('Fuel_id') == fuel_id and r.get('GrowthPat_Name') == scenario_name ),#'General'),
                    None
                )
                if record is None:
                    # Si no se encuentra el registro para ese combustible, se puede continuar o lanzar una advertencia
                    print(f"No se encontró registro para Fuel_id {fuel_id} en el patrón 'General'.")
                    continue

                # Extraer los valores de variación para Process y Transport
                process_variation = record.get('Process', 0)
                transport_variation = record.get('Transport', 0)
                molecule_variation = record.get('Molecule', 0)  # Si existe, si no, se asigna 0

                # Calcular el factor de variación de costo incremental según la fórmula
                incremental_cost_process = ((1 + process_variation) ** exponent) -1
                incremental_cost_transport = ((1 + transport_variation) ** exponent) -1
                incremental_molecule = ((1 + molecule_variation) ** exponent) -1 

                # Guardar los resultados en el diccionario del estado, usando el Fuel_id como key
                self.cost_dep_variation[fuel_id] = {
                    'Process': incremental_cost_process,
                    'Transport': incremental_cost_transport,
                    'Molecule': incremental_molecule

                }
        except Exception as e:
            logging.error("Error al calcular la variación de costos de despliegue: %s", str(e))
            raise




           
            




    def initialize_demand_area(self, demand_area_id):
        """
        Initialize data structure for a demand area.
        """
        if demand_area_id not in self.demand_areas_data:
            self.demand_areas_data[demand_area_id] = {
                "rural": {
                    "electric_consumption": 0,
                    "CH_consumption": 0,
                    "initial_adoption": {},
                    "potential_adoption": {}
                },
                "urban": {
                    "electric_consumption": 0,
                    "CH_consumption": 0,
                    "initial_adoption": {},
                    "potential_adoption": {}
                }
            }

    def set_deployment_plan(self, dep_plan: DeploymentPlan):
        self.deployment_plan = dep_plan#copy.deepcopy(dep_plan)#

    def set_price_plan(self, price_plan: PricePlan):
        self.price_plan = price_plan#copy.deepcopy(price_plan)#price_plan

    # def reset_base_plans(
    #     self,
    #     fuel_price: list = None,
    #     app_price: list = None,
    #     fuel_max_cap: list = None,
    #     appliances_max_cap: list = None,
    #     deploy_fuels: list = None,
    #     deploy_fuels_target: list = None,
    # ) -> None:
    #     """
    #     Reset price/deployment plans **only for this State** with neutral base-scenario data.
    #     It works on the deep-copied plans stored in this State.
    #     """
    #     try:
    #         # --- Price plan ---
    #         if self.price_plan is not None:
    #             # Trabajamos sobre una copia de details para evitar compartir referencias
    #             raw_details = getattr(self.price_plan, "details", {}) or {}
    #             details = copy.deepcopy(raw_details)

    #             if fuel_price is not None:
    #                 details["fuel_price"] = copy.deepcopy(fuel_price)
    #             if app_price is not None:
    #                 details["app_price"] = copy.deepcopy(app_price)

    #             self.price_plan.details = details  # solo afecta a ESTE estado

    #         # --- Deployment plan ---
    #         if self.deployment_plan is not None:
    #             raw_details = getattr(self.deployment_plan, "details", {}) or {}
    #             details = copy.deepcopy(raw_details)

    #             if fuel_max_cap is not None:
    #                 details["fuel_max_cap"] = copy.deepcopy(fuel_max_cap)
    #             if appliances_max_cap is not None:
    #                 details["appliances_max_cap"] = copy.deepcopy(appliances_max_cap)
    #             if deploy_fuels is not None:
    #                 details["fuel_reference"] = copy.deepcopy(deploy_fuels)
    #             if deploy_fuels_target is not None:
    #                 details["fuels_target"] = copy.deepcopy(deploy_fuels_target)

    #             self.deployment_plan.details = details  # solo ESTE estado

    #     except Exception as e:
    #         logging.error("Error resetting base plans in State: %s", str(e), exc_info=True)
    #         raise

    def set_initial_adoption(self, demand_area_id, area_type, adoption_data):
        """
        Save initial adoption data for a specific demand area and area type.
        """
        try:
            if demand_area_id not in self.demand_areas_data:
                raise ValueError(f"Área de demanda {demand_area_id} no existe en el estado actual.")

            if area_type not in ["rural", "urban"]:
                raise ValueError("Tipo de área debe ser 'rural' o 'urban'.")

            self.demand_areas_data[demand_area_id][area_type]["initial_adoption"] = adoption_data
        except Exception as e:
            logging.error("Error al guardar datos de adopción inicial: %s", str(e))
            raise

    def get_initial_adoption(self, demand_area_id, area_type):
        """
        Obtain the initial adoption data for a specific demand area and area type.
        """
        try:
            if demand_area_id not in self.demand_areas_data:
                raise ValueError(f"Área de demanda {demand_area_id} no existe en el estado actual.")

            if area_type not in ["rural", "urban"]:
                raise ValueError("Tipo de área debe ser 'rural' o 'urban'.")

            return self.demand_areas_data[demand_area_id][area_type]["initial_adoption"]
        except Exception as e:
            logging.error("Error al obtener datos de adopción inicial: %s", str(e))
            raise

    def set_potential_adoption(self, demand_area_id, area_type, adoption_data):
        """
        Save potential adoption data for a specific demand area and area type.
        """
        try:
            if demand_area_id not in self.demand_areas_data:
                raise ValueError(f"Área de demanda {demand_area_id} no existe en el estado actual.")

            if area_type not in ["rural", "urban"]:
                raise ValueError("Tipo de área debe ser 'rural' o 'urban'.")

            self.demand_areas_data[demand_area_id][area_type]["potential_adoption"] = adoption_data
        except Exception as e:
            logging.error("Error al guardar datos de adopción potencial: %s", str(e))
            raise

    def get_potential_adoption(self, demand_area_id, area_type):
        """
        Obtain the potential adoption data for a specific demand area and area type.
        """
        try:
            if demand_area_id not in self.demand_areas_data:
                raise ValueError(f"Área de demanda {demand_area_id} no existe en el estado actual.")

            if area_type not in ["rural", "urban"]:
                raise ValueError("Tipo de área debe ser 'rural' o 'urban'.")
            
            result = self.demand_areas_data[demand_area_id][area_type]["potential_adoption"]

            return result
            
        except Exception as e:
            logging.error("Error al obtener datos de adopción potencial: %s", str(e))
            raise

    #Devuelve la adopcion potencal para un fuel especñifico 
    def get_potential_adoption_for_tech(self, demand_area_id, area_type, technology_id):
        #Está guardado por tecnologías, debemos extraer la del fuel que nos interesa 
        try:
            if demand_area_id not in self.demand_areas_data:
                raise ValueError(f"Área de demanda {demand_area_id} no existe en el estado actual.")

            if area_type not in ["rural", "urban"]:
                raise ValueError("Tipo de área debe ser 'rural' o 'urban'.")
            
            result = self.demand_areas_data[demand_area_id][area_type]["potential_adoption"][technology_id]

            return result
            
        except Exception as e:
            logging.error("Error al obtener datos de adopción potencial para un fuel específico: %s", str(e))
            raise

    def set_electric_consumption(self, demand_area_id, area_type, consumption_data):
        """
        Save electric consumption data for a specific demand area and area type.
        """
        try:
            if demand_area_id not in self.demand_areas_data:
                raise ValueError(f"Área de demanda {demand_area_id} no existe en el estado actual.")

            if area_type not in ["rural", "urban"]:
                raise ValueError("Tipo de área debe ser 'rural' o 'urban'.")

            self.demand_areas_data[demand_area_id][area_type]["electric_consumption"] = consumption_data
        except Exception as e:
            logging.error("Error al guardar datos de consumo eléctrico: %s", str(e))
            raise

    def get_electric_consumption(self, demand_area_id, area_type):
        """
        Obtain the electric consumption data for a specific demand area and area type.
        """
        try:
            if demand_area_id not in self.demand_areas_data:
                raise ValueError(f"Área de demanda {demand_area_id} no existe en el estado actual.")

            if area_type not in ["rural", "urban"]:
                raise ValueError("Tipo de área debe ser 'rural' o 'urban'.")

            return self.demand_areas_data[demand_area_id][area_type]["electric_consumption"]
        except Exception as e:
            logging.error("Error al obtener datos de consumo eléctrico: %s", str(e))
            raise

    def set_CH_consumption(self, demand_area_id, area_type, consumption_data):
        """
        Save cooking and heating consumption data for a specific demand area and area type.
        """
        try:
            if demand_area_id not in self.demand_areas_data:
                raise ValueError(f"Área de demanda {demand_area_id} no existe en el estado actual.")

            if area_type not in ["rural", "urban"]:
                raise ValueError("Tipo de área debe ser 'rural' o 'urban'.")

            self.demand_areas_data[demand_area_id][area_type]["CH_consumption"] = consumption_data
        except Exception as e:
            logging.error("Error al guardar datos de consumo de cocinado: %s", str(e))
            raise

    def get_CH_consumption(self, demand_area_id, area_type):
        """
        Obtain the cooking and heating consumption data for a specific demand area and area type.
        """
        try:
            if demand_area_id not in self.demand_areas_data:
                raise ValueError(f"Área de demanda {demand_area_id} no existe en el estado actual.")

            if area_type not in ["rural", "urban"]:
                raise ValueError("Tipo de área debe ser 'rural' o 'urban'.")

            return self.demand_areas_data[demand_area_id][area_type]["CH_consumption"]
        except Exception as e:
            logging.error("Error al obtener datos de consumo de cocinado: %s", str(e))
            raise

    def get_info(self):
        return {
            'stage_id': self.stage_id,
            'year': self.year,
            'deployment_plan': self.deployment_plan.get_info() if self.deployment_plan else None,
            'price_plan': self.price_plan.get_info() if self.price_plan else None,
            'demand_areas_data': self.demand_areas_data
        }
    
    #Devuelve el estado que corresponde al año que le paso como parámero 
    def get_state(self, year):
        """
        Obtain the state corresponding to a specific year.
        """
        try:
            if year == self.year:
                return self
            else:
                raise ValueError(f"Estado para el año {year} no encontrado.")
        except Exception as e:
            logging.error("Error al obtener estado para año específico: %s", str(e))
            raise
    

    #Métodos sencillos para alamcenar los los id y tipo de áreas electrificados o no electrificados 
    def get_electrified_areas(self):
        return self.electrified_areas

    def set_electrified_areas(self, areas):
        self.electrified_areas = areas

    def set_not_electrified_areas(self, areas):
        self.not_electrified_areas = areas

    def get_not_electrified_areas(self):
        return self.not_electrified_areas
    
    def get_total_country_el_demand(self):
        return self.total_country_el_demand
    
    def set_total_country_el_demand(self, demand):
        self.total_country_el_demand = demand
    #Métodos sencillos para alamcenar los los id y tipo de áreas lpg deployed 
    
    def get_total_country_lpg_demand(self):
        return self.total_country_lpg_demand

    def set_total_country_lpg_demand(self, demand):
        self.total_country_lpg_demand = demand

    def set_lpg_deployed_areas(self, areas):
        self.lpg_deployed_areas = areas

    def get_lpg_deployed_areas(self):
        return self.lpg_deployed_areas
    
    def set_not_lpg_deployed_areas(self, areas):
        self.not_lpg_deployed_areas = areas
    def get_not_lpg_deployed_areas(self):
        return self.not_lpg_deployed_areas
    
    def set_country_off_grid_percentage(self, total_off_grid_percentage):
        self.country_off_grid_percentage = total_off_grid_percentage

    def get_country_off_grid_percentage(self):
        return self.country_off_grid_percentage 
    
    def get_dep_cost_variation(self, fuelID): #For fuel id 
        """
        Obtain the deployment cost variation for a specific fuel ID.
        """
        try:
            if fuelID not in self.cost_dep_variation:
                raise ValueError(f"Variación de costo de despliegue para Fuel_id {fuelID} no encontrada.")
            
            return self.cost_dep_variation[fuelID]
        except Exception as e:
            logging.error("Error al obtener variación de costo de despliegue: %s", str(e))
            raise

    def store_electricity_cost_parameters(self, demand_area_id, cost_parameters, ratios):
        """
        Saves the electricity cost parameters and ratios by area.
        """
        if not hasattr(self, "electricity_cost_results"):
            self.electricity_cost_results = {}
        
        self.electricity_cost_results[demand_area_id] = {
            "cost_parameters": cost_parameters,
            "ratios": ratios,
        }

    def get_electricity_cost_parameters(self, demand_area_id):
        """
        Obtains the electricity cost parameters and ratios by area.
        """
        if demand_area_id in self.electricity_cost_results:
            return self.electricity_cost_results[demand_area_id]
        else:
            raise ValueError(f"Parámetros de coste de electricidad para el área {demand_area_id} no encontrados.")
    
    def store_lpg_cost_parameters(self, area_lpg_id, cost_parameters,ratios):
        """
        Saves the LPG cost parameters and ratios by area.
        """
        if not hasattr(self, "lpg_cost_results"):
            self.lpg_cost_results = {}
        
        self.lpg_cost_results[area_lpg_id] = {
            "cost_parameters": cost_parameters,
            "ratios": ratios
        }
    def get_lpg_cost_parameters(self, area_lpg_id):
        """
        Obtains the LPG cost parameters and ratios by area.
        """
        if area_lpg_id in self.lpg_cost_results:
            return self.lpg_cost_results[area_lpg_id]
        else:
            raise ValueError(f"Cost LPG params for area {area_lpg_id} not found.")


    def set_financial_results(self, financial_results: FinancialAggParams):
        """
        Set the financial results for the current state.
        """
        self.financial_results = financial_results
        
    def get_financial_results(self):
        """
        Get the financial results for the current state.
        """
        return self.financial_results
    
    def set_total_fuel_consumption(self, demand_area_id, area_type, fuel_consumption_data):
        """
        Save total fuel consumption data for a specific demand area and area type.
        """
        try:
            if demand_area_id not in self.demand_areas_data:
                raise ValueError(f"Área de demanda {demand_area_id} no existe en el estado actual.")
            if area_type not in ["rural", "urban"]:
                raise ValueError("Tipo de área debe ser 'rural' o 'urban'.")
            self.demand_areas_data[demand_area_id][area_type]["total_fuel_consumption"] = fuel_consumption_data
        except Exception as e:
            logging.error("Error al guardar datos de consumo total de fuel: %s", str(e))
            raise

    def get_total_fuel_consumption(self, demand_area_id, area_type):
        """
        Obtain total fuel consumption data for a specific demand area and area type.
        """
        try:
            if demand_area_id not in self.demand_areas_data:
                raise ValueError(f"Área de demanda {demand_area_id} no existe en el estado actual.")
            if area_type not in ["rural", "urban"]:
                raise ValueError("Tipo de área debe ser 'rural' o 'urban'.")
            return self.demand_areas_data[demand_area_id][area_type].get("total_fuel_consumption", {})
        except Exception as e:
            logging.error("Error al obtener datos de consumo total de fuel: %s", str(e))
            raise


    def set_region_income(self, demand_area_id, area_type, region_income_data):
        """
        Save region income data for a specific demand area and area type.
        """
        try:
            if demand_area_id not in self.demand_areas_data:
                raise ValueError(f"Área de demanda {demand_area_id} no existe en el estado actual.")
            if area_type not in ["rural", "urban"]:
                raise ValueError("Tipo de área debe ser 'rural' o 'urban'.")
            self.demand_areas_data[demand_area_id][area_type]["region_income"] = region_income_data
        except Exception as e:
            logging.error("Error saving region_income data: %s", str(e))
            raise
    
    def get_region_income(self, demand_area_id, area_type):
        """
        Get region income data (appliances, fuels, electric) for a specific demand area and area type.
        """
        try:
            if demand_area_id not in self.demand_areas_data:
                raise ValueError(f"Área de demanda {demand_area_id} no existe en el estado actual {self.stage_id }.")
            if area_type not in ["rural", "urban"]:
                raise ValueError("Tipo de área debe ser 'rural' o 'urban'.")
            return self.demand_areas_data[demand_area_id][area_type].get("region_income", {})
        except Exception as e:
            logging.error("Error obtaining region_income: %s", str(e))
            raise

    def set_absolute_income_adoption(self, demand_area_id, area_type, adoption_data):
        """
        Save absolute income-based adoption data for a specific demand area and area type.
        """
        try:
            if demand_area_id not in self.demand_areas_data:
                raise ValueError(f"Área de demanda {demand_area_id} no existe en el estado actual.")
            if area_type not in ["rural", "urban"]:
                raise ValueError("Tipo de área debe ser 'rural' o 'urban'.")
            self.demand_areas_data[demand_area_id][area_type]["absolute_income_adoption"] = adoption_data
        except Exception as e:
            logging.error("Error saving absolute income adoption data: %s", str(e))
            raise

    def get_absolute_income_adoption(self, demand_area_id, area_type):
        """
        Obtain absolute income-based adoption data for a specific demand area and area type.
        """
        try:
            if demand_area_id not in self.demand_areas_data:
                raise ValueError(f"Área de demanda {demand_area_id} no existe en el estado actual.")
            if area_type not in ["rural", "urban"]:
                raise ValueError("Tipo de área debe ser 'rural' o 'urban'.")
            return self.demand_areas_data[demand_area_id][area_type].get("absolute_income_adoption", {})
        except Exception as e:
            logging.error("Error obtaining absolute income adoption data: %s", str(e))
            raise
    def set_appliance_weights(self, weights):
        self.appliance_weights = weights

    def get_appliance_weights(self):
        return self.appliance_weights
    def set_electricity_emissions(self, demand_area_id, emissions_value):
        """
        Saves the total electricity emissions (e.g., eCooking or final total) for a specific area.
        """
        if not hasattr(self, "electricity_emissions"):
            self.electricity_emissions = {}
        self.electricity_emissions[demand_area_id] = emissions_value

    def get_electricity_emissions(self, demand_area_id):
        """
        Devuelve las emisiones eléctricas para un área. 
        """
        try:
            return self.electricity_emissions[demand_area_id]
        except KeyError:
            raise ValueError(f"No hay emisiones eléctricas almacenadas para el área {demand_area_id}.")
    
    def set_lpg_emissions(self, lpg_area_id, emissions_value):
        """
        Saves the total LPG emissions for an LPG area.
        """
        if not hasattr(self, "lpg_emissions"):
            self.lpg_emissions = {}
        self.lpg_emissions[lpg_area_id] = emissions_value

    def get_lpg_emissions(self, lpg_area_id):
        """
        Returns the LPG emissions for an LPG area.
        """
        try:
            return self.lpg_emissions[lpg_area_id]
        except KeyError:
            raise ValueError(f"No hay emisiones de LPG almacenadas para el área {lpg_area_id}.")

    def is_electrified(self, demand_area_id, area_type):
        """
        Check if a specific demand area is electrified. Lista de áreas electrificadas en el estado actual (tuplas (id, area_type)) in self.electrified_areas
        """
        if (demand_area_id, area_type) in self.electrified_areas:
            return True
        else:
            return False
 
        
    
    def is_lpg_deployed(self, lpg_area_id, area_type):
        """
        Check if a specific LPG area is deployed. Lista de áreas deployadas LPG en el estado actual (tuplas (id, area_type)) in self.electrified_areas
        """
        if (lpg_area_id, area_type) in self.lpg_deployed_areas:
            return True
        else:
            return False
    
        
    def set_total_lpg_consumption_due_toCH(self, lpg_area_id, area_type, consumption_value):
        """
        Saves the total LPG consumption due to cooking and heating for an LPG area.
        """
        if not hasattr(self, "total_lpg_consumption_due_toCH"):
            self.total_lpg_consumption_due_toCH = {}
        self.total_lpg_consumption_due_toCH[(lpg_area_id, area_type)] = consumption_value
    
    def get_total_lpg_consumption_due_toCH(self, lpg_area_id, area_type):
        """
        Returns the total LPG consumption due to cooking and heating for an LPG area.
        """ 
        try:
            return self.total_lpg_consumption_due_toCH[(lpg_area_id, area_type)]
        except KeyError:
            raise ValueError(f"No hay consumo de LPG debido a cocción y calefacción almacenado para el área {lpg_area_id} y tipo {area_type}.")
        
    def save_social_costs(self, demand_area, area_type, social_costs): 
        """
        Saves the social costs by technology for a specific demand area.
        """
        if demand_area not in self.social_cost:
            self.social_cost[demand_area] = {}
        
        self.social_cost[demand_area][area_type] = social_costs

    def get_social_costs(self, demand_area, area_type):
        """
        Obtains the social costs by technology for a specific demand area.
        """
        try:
            return self.social_cost[demand_area][area_type]
        except KeyError:
            raise ValueError(f"No hay costes sociales almacenados para el área {demand_area} y tipo {area_type}.")
        
    def save_non_deploy_emissions(self, demand_area, area_type, emissions):
        """
        Saves the emissions of non-deployed technologies for a specific demand area.
        """
        if demand_area not in self.emiss_non_dep_fuels:
            self.emiss_non_dep_fuels[demand_area] = {}
        
        self.emiss_non_dep_fuels[demand_area][area_type] = emissions.copy()  # Hacemos una copia para evitar modificaciones no deseadas

    def get_non_deploy_emissions(self, demand_area, area_type):
        """
        Obtains the emissions of non-deployed technologies for a specific demand area.  
        """
        try:
            if demand_area not in self.emiss_non_dep_fuels:
                raise ValueError(f"No hay emisiones de tecnologías no desplegadas almacenadas para el área {demand_area}.")
            if area_type not in self.emiss_non_dep_fuels[demand_area]:
                raise ValueError(f"No hay emisiones de tecnologías no desplegadas almacenadas para el área {demand_area}, tipo {area_type}.")
            # Devolvemos una copia para que no se modifique el original
            return self.emiss_non_dep_fuels[demand_area][area_type].copy()
        except KeyError:
            raise ValueError(f"No hay emisiones de tecnologías no desplegadas almacenadas para el área {demand_area}., tipo {area_type}.")
        
    def save_aggregated_social_costs(self, demand_area_id: int, area_type: str, social_costs: AggregatedSocialCosts)-> None:
        """
        Saves the aggregated social costs for a specific demand area and area type.
        """

        try: 
            if area_type not in ["rural", "urban"]:
                raise ValueError("Tipo de área debe ser 'rural' o 'urban'.")
            if demand_area_id not in self._aggregated_social_costs:
                self._aggregated_social_costs[demand_area_id] = {}
            
            if demand_area_id not in self._aggregated_social_costs:
                self._aggregated_social_costs[demand_area_id] = {}
            
            # Hacemos una copia del objeto AggregatedSocialCosts para evitar modificaciones no deseadas
            copied = AggregatedSocialCosts(
                health_costs=social_costs.health_costs.copy(),
                gender_costs=social_costs.gender_costs.copy(),
                deforestation_costs=social_costs.deforestation_costs.copy(),
            )
            self._aggregated_social_costs[demand_area_id][area_type] = copied
            logging.info("Costes sociales agregados guardados para el área %s y tipo %s.", demand_area_id, area_type)

        except Exception as e:
            logging.error("Error al guardar costes sociales agregados: %s", str(e))
            raise

        
    def get_aggregated_social_costs(self, demand_area_id: int,  area_type: str) -> Optional[AggregatedSocialCosts]:
        """
        Obtains the aggregated social costs for a specific demand area and area type.
        """
        try:

            if area_type not in ["rural", "urban"]:
                raise ValueError("The area type must be 'rural' or 'urban'.")
            
            entry = self._aggregated_social_costs.get(demand_area_id, {}).get(area_type)
            if entry is None:
                #return None 
                raise ValueError(f"There are no aggregated social costs stored for the area {demand_area_id} and type {area_type}.")
            # Devolvemos una copia para que no se modifique el original
            return AggregatedSocialCosts(
                health_costs=entry.health_costs.copy(),
                gender_costs=entry.gender_costs.copy(),
                deforestation_costs=entry.deforestation_costs.copy(),
            ) 
        except KeyError:
            raise ValueError(f"There are no aggregated social costs stored for the area {demand_area_id} and type {area_type}.")
        

   
    def set_final_income_costs_appl(self, demand_area_id: int, area_type: str, income_data: float) -> None:
        """ 
        save the final income costs for appliances for a specific demand area and area type.
        :param income_data: float representing the total income from appliances.
        """
        try:
            if area_type not in ["rural", "urban"]:
                raise ValueError("Tipo de área debe ser 'rural' o 'urban'.")
            if demand_area_id not in self.demand_areas_data:
                raise ValueError(f"Área de demanda {demand_area_id} no existe en el estado actual.")
            self.demand_areas_data[demand_area_id][area_type]["final_income_appliances"] = income_data
            
        except Exception as e:
            logging.error("Error al guardar ingresos finales por electrodomésticos: %s", str(e))
            raise
    def get_final_income_costs_appl(self, demand_area_id: int, area_type: str) -> float:
        """
        Obtain the final income costs for appliances for a specific demand area and area type.
        :return: float representing the total income from appliances.
        :raises ValueError: if not exists.
        """
        try:
            if area_type not in ["rural", "urban"]:
                raise ValueError("Tipo de área debe ser 'rural' o 'urban'.")
            if demand_area_id not in self.demand_areas_data:
                raise ValueError(f"Área de demanda {demand_area_id} no existe en el estado actual.")
            return self.demand_areas_data[demand_area_id][area_type]["final_income_appliances"]
        except KeyError:
            raise ValueError(f"There are no final income costs for appliances stored for the area {demand_area_id} and type {area_type}.")
    
    def set_final_income_costs_fuel(self, demand_area_id: int, area_type: str, income_data: float) -> None:
        """
        Save the final income costs for fuels for a specific demand area and area type.
        :param income_data: float representing the total income from fuels.
        """
        try:
            if area_type not in ["rural", "urban"]:
                raise ValueError("Tipo de área debe ser 'rural' o 'urban'.")
            if demand_area_id not in self.demand_areas_data:
                raise ValueError(f"Área de demanda {demand_area_id} no existe en el estado actual.")
            self.demand_areas_data[demand_area_id][area_type]["final_appl_income_by_fuels"] = income_data
            
        except Exception as e:
            logging.error("Error Saving final income costs for fuels: %s", str(e))
            raise
    def get_final_income_costs_fuel(self, demand_area_id: int, area_type: str) -> float:
        """
        Obtain the final income costs for fuels for a specific demand area and area type.
        :return: float representing the total income from fuels.
        :raises ValueError: if not exists.
        """
        try:
            if area_type not in ["rural", "urban"]:
                raise ValueError("Tipo de área debe ser 'rural' o 'urban'.")
            if demand_area_id not in self.demand_areas_data:
                raise ValueError(f"Área de demanda {demand_area_id} no existe en el estado actual.")
            return self.demand_areas_data[demand_area_id][area_type]["final_appl_income_by_fuels"]
        except KeyError:
            raise ValueError(f"There are no final income costs for fuels stored for the area {demand_area_id} and type {area_type}.")

    def set_final_income_participation_per_appliance_by_fuel(self, demand_area_id: int, area_type: str, income_data: Dict[int, float]) -> None:
        """
        Save the final income participation per appliance by fuel for a specific demand area and area type.
        :param income_data: { appliance_id: income_participation, ... }
        """
        try:
            if area_type not in ["rural", "urban"]:
                raise ValueError("Tipo de área debe ser 'rural' o 'urban'.")
            if demand_area_id not in self.demand_areas_data:
                raise ValueError(f"Área de demanda {demand_area_id} no existe en el estado actual.")
            self.demand_areas_data[demand_area_id][area_type]["final_income_participation_per_appliance_by_fuel"] = income_data
            
        except Exception as e:
            logging.error("Error Saving final income participation per appliance by fuel: %s", str(e))
            raise

    def get_final_income_participation_per_appliance_by_fuel(self, demand_area_id: int, area_type: str) -> Dict[int, float]:
        """
        Obtain the final income participation per appliance by fuel for a specific demand area and area type.
        :return: { appliance_id: income_participation, ... }
        :raises ValueError: if not exists.
        """
        try:
            if area_type not in ["rural", "urban"]:
                raise ValueError("Tipo de área debe ser 'rural' o 'urban'.")
            if demand_area_id not in self.demand_areas_data:
                raise ValueError(f"Área de demanda {demand_area_id} no existe en el estado actual.")
            return self.demand_areas_data[demand_area_id][area_type]["final_income_participation_per_appliance_by_fuel"]
        except KeyError:
            raise ValueError(f"There is no final income participation per appliance by fuel stored for the area {demand_area_id} and type {area_type}.")
        

    def set_base_price(self, demand_area_id: int, area_type: str, payload: Dict[str, Any]) -> None:
        """
        Save base price data for a ('rural'|'urban') area of a demand area.
        payload esperado:
          {
            "per_tech": Dict[int, float],     # valores ponderados por adopción por Tech_id
            "total": float,                   # suma de per_tech
            "total_times_CH": float           # total * CH_demand[area]
          }
        """
        if area_type not in ("rural", "urban"):
            raise ValueError("area_type debe ser 'rural' o 'urban'")
        per_tech = dict(payload.get("per_tech", {}))
        total = float(payload.get("total", 0.0) or 0.0)
        total_times_CH = float(payload.get("total_times_CH", 0.0) or 0.0)

        if demand_area_id not in self._base_price:
            self._base_price[demand_area_id] = {"rural": {}, "urban": {}}

        self._base_price[demand_area_id][area_type] = {
            "per_tech": per_tech,
            "total": total,
            "total_times_CH": total_times_CH,
        }

    def get_base_price(
        self,
        demand_area_id: int,
        area_type: Optional[str] = None,
        field: Optional[str] = None,
    ):
        """
        Recover the saved data.
        - area_type=None  -> returns {"rural": {...}, "urban": {...}} (or {} if no data)
        - area_type in {'rural','urban'} and field=None -> returns the area block dict
        - area_type in {'rural','urban'} and field in {'per_tech','total','total_times_CH'}
            -> returns only that field (dict or float). If it doesn't exist, returns {} or 0.0.
        """
        block = self._base_price.get(demand_area_id, {})
        if area_type is None:
            return block

        if area_type not in ("rural", "urban"):
            raise ValueError("area_type debe ser 'rural' o 'urban'")

        area_block = block.get(area_type, {})
        if field is None:
            return area_block

        if field == "per_tech":
            return dict(area_block.get("per_tech", {}))
        if field == "total":
            return float(area_block.get("total", 0.0))
        if field == "total_times_CH":
            return float(area_block.get("total_times_CH", 0.0))

        raise ValueError("field debe ser uno de {'per_tech','total','total_times_CH'} o None")

    def set_country_base_price(self, payload: dict) -> None:
        """
        Save the country summary of base price.
        Suggested structure in payload:
        {
          "rural": {
            "sum_total": float,
            "sum_total_times_CH": float,
            "areas_count": int,
            "avg_total": float,                # sum_total / max(areas_count,1)
            "per_tech": {Tech_id: float} -- Este parámetro no lo guardo, no me interesa 
          },
          "urban": { ... mismo ... },
          "all": {
            "sum_total": float,                # rural + urban
            "sum_total_times_CH": float,       # rural + urban
            "areas_count": int,                # rural + urban
            "avg_total": float                 # media simple de avg_total rural y urban, o recomputada
          }
        }
        """
        self._country_base_price = payload or {}
    def get_country_base_price(self, field: Optional[str]= None):
        """
        If field is None -> returns the entire dict.
        If field in {'rural','urban','all'} -> returns only that block.
        """
        if field is None:
            return self._country_base_price
        if field not in ("rural", "urban", "all"):
            raise ValueError("field debe ser None, 'rural', 'urban' o 'all'")
        return self._country_base_price.get(field, {})
    
    def set_economic_result(self, result: EconomicResult) -> None:
        self._economic_result = result

    def get_economic_result(self) -> Optional["EconomicResult"]:
        return self._economic_result

    def set_base_edemand_cost_for_area(self, area_id: int, area_type: str, value: float) -> None:
        """
        Save the base eDemand cost for an area and type ('rural'/'urban') in the base state.
        """
        if area_id not in self._base_edemand_costs_by_area:
            self._base_edemand_costs_by_area[area_id] = {"rural": 0.0, "urban": 0.0}
        self._base_edemand_costs_by_area[area_id][area_type] = float(value or 0.0)

    def get_base_edemand_costs_by_area(self) -> Dict[int, Dict[str, float]]:
        return self._base_edemand_costs_by_area

    def set_country_base_edemand_costs(self, rural_total: float, urban_total: float) -> None:
        """
        Save the country summary of base eDemand costs.
        """
        self._country_base_edemand_costs = BaseEDemandCountryCosts(
            rural=float(rural_total or 0.0),
            urban=float(urban_total or 0.0)
        )

    def get_country_base_edemand_costs(self) -> Optional[BaseEDemandCountryCosts]:
        return self._country_base_edemand_costs
    
    def set_country_adoption_shares(
        self,
        initial_rural: Dict[int, float],
        initial_urban: Dict[int, float],
        initial_total: Dict[int, float],
        potential_rural: Dict[int, float],
        potential_urban: Dict[int, float],
        potential_total: Dict[int, float],
    ) -> None:
        self._country_adoption_shares = {
            "initial":   {"rural": initial_rural,   "urban": initial_urban,   "total": initial_total},
            "potential": {"rural": potential_rural, "urban": potential_urban, "total": potential_total},
        }

    def get_country_adoption_shares(self, kind: str = "potential") -> Dict[str, Dict[int, float]]:
        """
        kind ∈ {"initial","potential"}
        Devuelve {"rural": {tech: frac}, "urban": {...}, "total": {...}}
        """
        return self._country_adoption_shares.get(kind, {"rural": {}, "urban": {}, "total": {}})

    