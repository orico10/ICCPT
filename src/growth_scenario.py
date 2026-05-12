import pandas as pd
import logging


class GrowthScenario:
    def __init__(self,scenario_id, scenario_name):
        self.scenario_id = scenario_id
        self.scenario_name = scenario_name
        # Estas propiedades se rellenarán con los datos filtrados de cada DataFrame
        self.app_ret_price = None      # De ScenGrow_appRetPrice
        self.dem_elast = None          # De ScenGrow_demElast
        self.dem_mult = None           # De ScenGrow_demMult
        self.dep_fuel_cost_var = None  # De ScenGrow_depFuelCostVar
        self.fuel_ret_price = None     # De ScenGrow_fuelRetPrice
        self.soc_clus = None           # De ScenGrow_socClus
        self.base_year = None

    def set_app_ret_price(self, data):
        self.app_ret_price = data

    def set_dem_elast(self, data):
        self.dem_elast = data

    def set_dem_mult(self, data):
        self.dem_mult = data

    def set_dep_fuel_cost_var(self, data):
        self.dep_fuel_cost_var = data

    def set_fuel_ret_price(self, data):
        self.fuel_ret_price = data

    def set_soc_clus(self, data):
        self.soc_clus = data

    def get_info(self):
        return {
            'GrowthPat_Id': self.scenario_id,
            'GrowthPat_Name': self.scenario_name,
            'App_Retail_Price': self.app_ret_price,
            'Demand_Elasticity': self.dem_elast,
            'Demand_Multiplier': self.dem_mult,
            'Dep_Fuel_Cost_Variation': self.dep_fuel_cost_var,
            'Fuel_Retail_Price': self.fuel_ret_price,
            'Soc_Clust_Parameters': self.soc_clus
        }