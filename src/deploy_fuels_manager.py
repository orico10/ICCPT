import logging
from src.income_model import IncomeModel
from src.adoption_model import AdoptionModel
from src.electricity_cost_model import ElectricityCostModel
from src.lpg_deploy_model import LPGDeployModel





class DeployFuelsManager:
    def __init__(self, state, data_manager, demand_area):
        self.state = state
        self.data_manager = data_manager
        self.demand_area = demand_area
        
        # Extract plam dep fuels data
        dep_fuels_df = self.data_manager.get_dataframe("Plan_depFuels")  
        self.deploy_fuel_list = dep_fuels_df.to_dict(orient="records")      
        deployment_plan_details = state.deployment_plan.details 
        self.deployment_plan_fuels_target = deployment_plan_details.get("fuels_target", [])
        
        
        

    def _get_electricity_params(self, state, demand_area):
        """
        Prepare the necessary parameters to initialize ElectricityDeployModel.
        Extract the row of fuel with Fuel_id==1 and associate the deployment plan.
        """
        # Extract electricity information
        electricity_fuel_data = next((fuel for fuel in self.deploy_fuel_list if fuel["Fuel_id"] == 1), None)
        if electricity_fuel_data is None:
            raise ValueError("There is no data for electricity (Fuel_id==1)")
        
        # Selecciona el plan de despliegue correspondiente al simulation_plan
        try:
            deploy_plan_row = self.deploy_targets[self.deploy_targets["DepPlan_id"] == self.selected_dep_plan_id].iloc[0]
        except IndexError:
            raise ValueError(f"Deployment plan not found with DepPlan_id=={self.selected_dep_plan_id}")
        deploy_plan = deploy_plan_row.to_dict()

        params = {
            "state": state,
            "demand_area": demand_area,
            "fuel_data": electricity_fuel_data,  # Datos de Plan_depFuels para electricidad
            "deploy_plan": deploy_plan,          # Datos del plan de despliegue para electricidad
            "virtual_manager": self.virtual_manager,
            "simulation_plan": self.simulation_plan  # Información del escenario y plan actual
        }
        return params

    def _get_lpg_params(self, state, demand_area):
        """
        Prepare the necessary parameters to initialize LPGDeployModel.
        Extract the row of fuel with Fuel_id==2 and associate the deployment plan.
        """
        # Extract LPG information
        lpg_fuel_data = next((fuel for fuel in self.deploy_fuel_list if fuel["Fuel_id"] == 2), None)
        if lpg_fuel_data is None:
            raise ValueError("There is no data for LPG (Fuel_id==2)")

        try:
            deploy_plan_row = self.deploy_targets[self.deploy_targets["DepPlan_id"] == self.selected_dep_plan_id].iloc[0]
        except IndexError:
            raise ValueError(f"Deployment plan not found with DepPlan_id=={self.selected_dep_plan_id}")
        deploy_plan = deploy_plan_row.to_dict()

        params = {
            "state": state,
            "demand_area": demand_area,
            "fuel_data": lpg_fuel_data,        # Datos de Plan_depFuels para GLP
            "deploy_plan": deploy_plan,         # Datos del plan de despliegue para GLP
            "virtual_manager": self.virtual_manager,
            "simulation_plan": self.simulation_plan
        }
        return params

    def initialize_deployment_models(self, state, demand_area):
        """
        Initialize and return the deployment models for electricity and LPG.
        """
        try:
            # Inicializa el modelo de electricidad con los parámetros extraídos
            electricity_params = self._get_electricity_params(state, demand_area)
            electricity_model = ElectricityCostModel(**electricity_params)

            # Inicializa el modelo de GLP con sus respectivos parámetros
            lpg_params = self._get_lpg_params(state, demand_area)
            lpg_model = LPGDeployModel(**lpg_params)

            return electricity_model, lpg_model

        except Exception as e:
            logging.error("Error initializing deployment models: %s", str(e))
            raise
        

    def _load_fuel_data(self):
        """
        Load the deploy fuels data from Dataframe 'Plan_depFuels'
        """
        try:
            self.fuels_data = self.data_manager.load_data("Plan_depFuels")
            if not self.fuels_data:
                raise ValueError("No fuel data has been loaded")
        except Exception as e:
            logging.error("Error loading fuel data: %s", str(e))
            raise

    def _load_deployment_targets(self):
        """
        Load the deployment target data from DataFrame 'Plan_depFuelsTarg'
        """
        try:
            self.deployment_targets = self.data_manager.load_data("Plan_depFuelsTarg")
            if not self.deployment_targets:
                raise ValueError("No deployment targets have been loaded")
        except Exception as e:
            logging.error("Error loading deployment targets: %s", str(e))
            raise

    def initialize_deployment_models(self, state, demand_area):
        """
        Initialize the deployment models for each fuel.
        """
        try:
            # Inicializa el modelo para la electricidad
            electricity_params = self._get_electricity_params(state, demand_area)
            electricity_model = ElectricityCostModel(**electricity_params)

            # Inicializa el modelo para el GLP
            lpg_params = self._get_lpg_params(state, demand_area)
            lpg_model = LPGDeployModel(**lpg_params)

            return electricity_model, lpg_model

        except Exception as e:
            logging.error("Error inicializando modelos de despliegue: %s", str(e))
            raise

    

    def get_connection_threshold(self):
        return 1.0
