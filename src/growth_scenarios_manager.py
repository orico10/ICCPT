import logging
from src.growth_scenario import GrowthScenario


class GrowthScenarioManager:
    def __init__(self, data_manager):
        self.data_manager = data_manager
        self.logger = logging.getLogger("GrowthScenarioManager")
        self.growth_scenarios = self._load_growth_scenarios()

    def _load_growth_scenarios(self):
        scenarios = {}
        try:
            # Primero, cargar el DataFrame de configuración de escenarios
            config_df = self.data_manager.get_dataframe("ScenGrow_config")
            if config_df is None:
                raise Exception("El DataFrame 'ScenGrow_config' no se encuentra en el DataManager.")
            
            # Se asume que el DataFrame tiene las columnas: GrowthPat_Id y GrowthPat_Name
            for _, row in config_df.iterrows():
                scenario_id = row["GrowthPat_Id"]
                scenario_name = row["GrowthPat_Name"]
                if scenario_id not in scenarios:
                    scenarios[scenario_id] = GrowthScenario(scenario_id, scenario_name)
        except Exception as e:
            self.logger.critical(f"Error loading growth scenario configuration: {e}", exc_info=True)
            raise

        # Ahora, enriquecer cada escenario filtrando los otros DataFrames
        self._enrich_growth_scenarios(scenarios)
        return scenarios

    def _enrich_growth_scenarios(self, scenarios):
        # Obtener los DataFrames adicionales
        app_ret_price_df = self.data_manager.get_dataframe("ScenGrow_appRetPrice")
        dem_elast_df = self.data_manager.get_dataframe("ScenGrow_demElast")
        dem_mult_df = self.data_manager.get_dataframe("ScenGrow_demMult")
        dep_fuel_cost_var_df = self.data_manager.get_dataframe("ScenGrow_depFuelCostVar")
        fuel_ret_price_df = self.data_manager.get_dataframe("ScenGrow_fuelRetPrice")
        soc_clus_df = self.data_manager.get_dataframe("ScenGrow_socClus")
        
        for scenario in scenarios.values():
            sid = scenario.scenario_id
            # Filtrar cada DataFrame por GrowthPat_Id y convertir a diccionario
            scenario.set_app_ret_price(
                app_ret_price_df[app_ret_price_df["GrowthPat_Id"] == sid].to_dict(orient="records")
                if app_ret_price_df is not None else None
            )
            scenario.set_dem_elast(
                dem_elast_df[dem_elast_df["GrowthPat_Id"] == sid].to_dict(orient="records")
                if dem_elast_df is not None else None
            )
            scenario.set_dem_mult(
                dem_mult_df[dem_mult_df["GrowthPat_Id"] == sid].to_dict(orient="records")
                if dem_mult_df is not None else None
            )
            scenario.set_dep_fuel_cost_var(
                dep_fuel_cost_var_df[dep_fuel_cost_var_df["GrowthPat_Id"] == sid].to_dict(orient="records")
                if dep_fuel_cost_var_df is not None else None
            )
            scenario.set_fuel_ret_price(
                fuel_ret_price_df[fuel_ret_price_df["GrowthPat_Id"] == sid].to_dict(orient="records")
                if fuel_ret_price_df is not None else None
            )
            scenario.set_soc_clus(
                soc_clus_df[soc_clus_df["GrowthPat_Id"] == sid].to_dict(orient="records")
                if soc_clus_df is not None else None
            )

    def get_growth_scenario(self, scenario_id):
        return self.growth_scenarios.get(scenario_id)

    def iterate_growth_scenarios(self):
        for scenario in self.growth_scenarios.values():
            yield scenario
