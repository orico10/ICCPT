import logging
import os
from src.technologies import Technologies
from src.demand_area_manager import DemandAreaManager
from src.route_configuration_loader import RouteConfigurationLoader
from src.combinedPlans_manager import CombinedPlanManager
from src.growth_scenarios_manager import GrowthScenarioManager

import logging

class PreprocessDataManager:
    def __init__(self, data_manager, output_path, demandAreas_path, base_scenario):
        """
        Initializes the data preprocessing manager.

        :param data_manager: Instance of DataManager to manage data.
        :param output_path: Path where output files will be saved.
        :param demandAreas_path: Path to demand areas data.
        """
        self.data_manager = data_manager
        self.route_configuration = data_manager.route_configuration
        self.logger = logging.getLogger("PreprocessDataManager")
        self.output_path = output_path
        self.demandAreas_path = demandAreas_path
        self.state_manager = None
        self.base_scenario = base_scenario
        
    def preprocess(self):
        """
        Performs initial data preprocessing before starting the adoption model.
        """
        self.logger.info("Starting data preprocessing.")

        try:
            # Calculate technology data
            self._calculate_technologies()

            # Create and export demand areas
            self._process_demand_areas()

        

            # Here you can add other preprocessing classes in the future
            self.logger.info("Data preprocessing completed.")
        except Exception as e:
            self.logger.critical(f"An error occurred during preprocessing: {e}", exc_info=True)
            raise
    
    def create_state_structure(self):
        """
        Creates and loads the state structure from the input dataframes.
        """
        self.logger.info("Creating state structure.")
        try:
            #self.state_manager = StatesManager(self.data_manager)
            #self.state_manager.load_states() -- redundante porque la propia llamada al constructor ya carga los estados
            self.combined_plan_manager = CombinedPlanManager(self.data_manager,  self.base_scenario)
            
        except Exception as e:
            self.logger.critical(f"Error creating state structure: {e}", exc_info=True)
            raise

    def create_growth_scenario_structure(self):
        self.logger.info("Creating growth scenario structure.")
        try:
            self.growth_scenario_manager = GrowthScenarioManager(self.data_manager)
        except Exception as e:
            self.logger.critical(f"Error creating growth scenario structure: {e}", exc_info=True)
            raise

    def _calculate_technologies(self):
        """
        Calls calculations related to technologies.
        """
        self.logger.info("Calculating technology data.")
        try:
            technologies = Technologies(self.data_manager)
            technologies.calculate_all()
        except Exception as e:
            self.logger.critical(f"Error calculating technologies: {e}", exc_info=True)
            raise

    def _process_demand_areas(self):
        """
        Processes demand areas by reading buildings and generating necessary groupings.
        """
        self.logger.info("Creating demand areas.")
        try:
            if "Territory_partition" not in self.data_manager.dataframes:
                raise ValueError("Territory_partition data is missing in the DataManager.")

            territory_partition_path = self.route_configuration.resolved_files["Territory_partition"]
            base_path = os.path.dirname(territory_partition_path)

            demand_area_manager = DemandAreaManager(self.data_manager, base_path, self.demandAreas_path)
            demand_area_manager.process_demand_areas()

            

            self.data_manager.demand_area_manager = demand_area_manager
        except Exception as e:
            self.logger.critical(f"Error processing demand areas: {e}", exc_info=True)
            raise

    

    def get_state_manager(self):
        """
        Returns the StateManager instance.

        :return: StateManager instance
        """
        return self.state_manager