import logging
from collections import defaultdict
import os 
import csv 
from dataclasses import dataclass, field
from typing import List, Dict, Any
import numpy as np
import pandas as pd
from src.el_cost_params import CostParameters
from src.el_emissions_params import EmissionsModelParameters
from src.financial_agg_params import (
    FinancialAggParams,
    AggregatedElectricityCosts,
    AggregatedLpgCosts,
    AggregatedRestSubsidiesOrTaxesOpex,
    AggregatedSocialCosts, 
    AverageGrowthCalculationAppliances,
    IncomeTariff, 
)
from src.lpg_cost_params import LPGCostParameters
from src.lpg_emissions_params import LPGEmissionsParameters

@dataclass
class AggregatedSocialCosts_ByFuel:
    health_costs: Dict[int, float] = field(default_factory=dict)
    gender_costs: Dict[int, float] = field(default_factory=dict)
    emissions_costs: Dict[int, float] = field(default_factory=dict)
    deforestation_costs: Dict[int, float] = field(default_factory=dict)
@dataclass
class EconomicResult:
    net_electric_total: float = 0.0     # income_E_total - (fix_grid_gen + rest + var_grid_gen + var_offgrid)
    net_lpg_total: float = 0.0          # income_LPG - (fix_upstream + fix_local + var_upstream + var_local + import)
    taxes_subsidies_total: float = 0.0  # suma de (appliances + fuels)
    grand_total: float = 0.0            # net_electric_total + net_lpg_total + taxes_subsidies_total



class CountryFinancialAggregator:
    def __init__(
        self,
        state,
        data_manager,
        demand_areas: List,
        #simulation_plan, # Eliminar porque no se usa 
        growth_scenario,
        logger: logging.Logger = None
        
    ):
        self.state = state
        self.data_manager = data_manager
        self.demand_areas = demand_areas
        #self.simulation_plan = simulation_plan
        self.growth_scenario = growth_scenario
        self.logger = logger or logging.getLogger(__name__)
        self.country_cost_by_fuel =  AggregatedSocialCosts_ByFuel() 
        self.country_health_costs = 0.0  # Costes de salud todo el pais todos los fuels 
        self.country_gender_costs = 0.0 # Costes de género  todo el pais todos los fuels 
        self.country_deforestation_costs = 0.0  # Costes de deforestación todos los fuels
        self.country_emissions_costs = 0.0  # Costes de emisiones todos los fuels 
        
        
        
        self.electric_cost_breakdown = data_manager.get_dataframe("Electricity_costBreakdown")
        self.lpg_cost_breakdown = data_manager.get_dataframe("LPG_costBreakdown")
        self.df_technologies = data_manager.get_dataframe("enriched_technologies") 
        self.df_technologies['Tech_id'] = self.df_technologies.index
        self.financial_agg_params = FinancialAggParams()
        self.appliance_weights_by_fuel: Dict[int, Dict[int, float]] = {}
        # Para acumular ingresos por fuel y appliance a nivel país
        #self._appliance_income_by_fuel_appliance = defaultdict(lambda: defaultdict(float))
        #self._country_appliance_income = defaultdict(float)


     
        self.electricity_fuel_id = 1  # ID para electricidad
        self.lpg_fuel_id = 2
        # Acumuladores de costes eléctricos por bloque y área
        fields = ['final_fix_grid_gen', 'rest', 'var_grid_gen', 'var_offgrid', 'og_consumption', 'g_consumption']
        zero_dict = {k: 0.0 for k in fields}
        zero_emis = {'OG_Emiss': 0.0, 'Grid_Emiss': 0.0}  # Emisiones de electricidad

        self.country_aggregated_electricity_costs = {
            'ElecTotal':   zero_dict.copy(),
            'EDemand':  zero_dict.copy(),
        }
        self.country_aggregated_electricity_emissions = {
            'ElecTotal': zero_emis.copy(),
            'EDemand': zero_emis.copy(),
        }
        zero_values = 0.0 
        self.country_aggregated_lpg_costs = {
            'fix_costs_upstream': zero_values,
            'var_costs_upstream': zero_values,
            'fix_costs_local': zero_values,
            'var_costs_local': zero_values,
            'var_costs_import': zero_values,
        }
        self.country_aggregated_lpg_emiss = {
            'total': zero_values,  # Emisiones totales de LPG
        }
        self.ec_emiss_g = 0.0  # Emisiones de electricidad Ecooking en grid
        self.ec_emiss_of = 0.0  # Emisiones de electricidad ECooking en off-grid
        
        #self.participation_by_fuel = {}
        # Parámetros para guardar el summary result -- Balances 
       

        # Sumas país por tipo de área
        self._country_base_price_acc = {
            "rural": {
                "sum_total": 0.0,               # suma de 'total' (≈ $/cook ponderado)
                "sum_total_times_CH": 0.0,      # suma de 'total_times_CH' (≈ gasto $/año)
                "areas_count": 0               # número de áreas acumuladas
                #"per_tech": defaultdict(float)  # suma por Tech_id (ponderado por adopción)
            },
            "urban": {
                "sum_total": 0.0,
                "sum_total_times_CH": 0.0,
                "areas_count": 0
                #"per_tech": defaultdict(float)
            },
        }
        
        


    def run(self):
        try: 
            """Main method to run the aggregation process."""
            lpg_areas_already_counted = set()
            agg_subs = AggregatedRestSubsidiesOrTaxesOpex()  # Acumulador de subsidios/impuestos por fuel_id
            is_base_state = (getattr(self.state, "stage_id", None) == 0 
                 and str(getattr(self.state, "semester", "")).lower() == "first")

            base_edemand_rural_total = 0.0
            base_edemand_urban_total = 0.0
            self._init_country_adoption_accumulators()
            self._init_country_appliance_weight_accumulators()



            for area in self.demand_areas:
                area_id = area.id
                area_types = [area.area_type] if area.area_type else ['rural', 'urban']

                for area_type in area_types:
                    # Salta si no hay consumo de CH
                    base_cook = area.data.get('demand_census_rur_urb', {}).get(area_type, {}).get('cooking', 0)

                    if base_cook == 0:
                        self.logger.debug("No hay consumo de CH en el área %s, tipo %s", area_id, area_type)
                        continue
                   

                    # 1. Subsidios y taxes (income costs)
                    agg_subs = self._calculate_subsides_taxes_for_fuels_appliances(area_id, area_type, accumulator=agg_subs)
                    

                    

                    # 2. Electricidad
                    if self.state.is_electrified(area_id, area_type): #Revisar, de momento obtenemos los totales de electricidad
                        electricity_costs_blocks = self.state.get_electricity_cost_parameters(area_id)["cost_parameters"]
                        electricity_emissions_blocks = self.state.get_electricity_emissions(area_id)#['emissions_parameters']
                        blocks: dict = electricity_emissions_blocks.emissions_parameters
                        for block in ('ElecTotal', 'EDemand'):
                            if block in electricity_costs_blocks:
                                cost_params: CostParameters = electricity_costs_blocks[block]
                                area_obj = (cost_params.rural if area_type == 'rural' else cost_params.urban)
                                c = area_obj.costs
                                cons = area_obj.consumption
                                # Agregar los costes de electricidad al agregado del país
                                agg = self.country_aggregated_electricity_costs[block]
                                agg['final_fix_grid_gen'] += c.FINAL_FIX_Grid_Gen
                                agg['rest'] += c.FINAL_Rest
                                agg['var_grid_gen'] += c.FINAL_VAR_Grid_Gen
                                agg['var_offgrid'] += c.FINAL_VAR_OffGrid
                                agg['og_consumption'] += cons.ogu if area_type == 'urban' else cons.ogr
                                agg['g_consumption'] += cons.gcu if area_type == 'urban' else cons.grc
                                # Agregar las emisiones de electricidad al agregado del país
                               
                                emiss_params : EmissionsModelParameters = blocks[block]
                                area_emiss = emiss_params.urban if area_type == 'urban' else emiss_params.rural
                                agg_emiss = self.country_aggregated_electricity_emissions[block]
                                
                                agg_emiss['OG_Emiss'] += float(area_emiss.OG_Emiss) 
                                agg_emiss['Grid_Emiss'] += float(area_emiss.Grid_Emiss)
                                
                                # --- NUEVO: acumular coste base EDemand en estado base ---
                                if is_base_state and block == 'EDemand':
                                    base_cost_edemand = float(c.FINAL_FIX_Grid_Gen or 0.0) \
                                                    + float(c.FINAL_Rest or 0.0) \
                                                    + float(c.FINAL_VAR_Grid_Gen or 0.0) \
                                                    + float(c.FINAL_VAR_OffGrid or 0.0)

                                    if area_type == 'urban':
                                        base_edemand_urban_total += base_cost_edemand
                                    else:
                                        base_edemand_rural_total += base_cost_edemand
                                                        
                                                        

                                



                    


                    

                        

                    # 3. LPG
                    lpg_id = int(area.lpg_area)
                    key = (lpg_id, area_type)
                    if self.state.is_lpg_deployed(lpg_id, area_type) and key not in lpg_areas_already_counted:
                        
                        lpg_costs = self.state.get_lpg_cost_parameters(lpg_id)["cost_parameters"]
                        lpg_costs_params : LPGCostParameters = lpg_costs #.costs
                        lg_emiss = self.state.get_lpg_emissions(lpg_id).emissions_parameters
                        lpg_emiss_params : LPGEmissionsParameters = lg_emiss
                        area_obj = (lpg_costs_params.rural if area_type == 'rural' else lpg_costs_params.urban)
                        c = area_obj.costs
                    
                        agg_lpg = self.country_aggregated_lpg_costs
                        agg_lpg['fix_costs_upstream'] += c.FINAL_FIX_Cost_Upstream
                        agg_lpg['var_costs_upstream'] += c.FINAL_VAR_Cost_Upstream
                        agg_lpg['fix_costs_local'] += c.FINAL_FIX_Cost_Local
                        agg_lpg['var_costs_local'] += c.FINAL_VAR_Cost_Local
                        agg_lpg['var_costs_import'] += c.FINAL_VAR_Cost_Import
                        #agg_lpg['var_costs_import'] += c.FINAL_VAR_Cost_Upstream  # Asumiendo que es el mismo para upstream y import

                        #agg_lpg = self._aggregate_lpg_costs(**lpg_costs) #Reconversión de dict a dataclass
                        #self._add_costs_lpg(agg_lpg)
                        area_obj_emiss = (lpg_emiss_params.rural if area_type == 'rural' else lpg_emiss_params.urban)
                        # Emisiones de LPG, tenemos que agrupar la variable total: float = 0.0         # Total emissions for the area (rural or urban)
                        emiss = area_obj_emiss.total
                        
                        agg_lpg_emiss = self.country_aggregated_lpg_emiss
                        agg_lpg_emiss['total'] += emiss
                        # Aseguramos que no volvemos a contar cada demand area que pertenece a un área LPG
                        key = (lpg_id, area_type)
                        lpg_areas_already_counted.add(key)
                        
                        
                        
                    # Si el area no está electrificada ni tiene LPG, acumulo sus emissiones para todas las áreas del país 
                    #if not self.state.is_electrified(area_id, area_type) : #and not self.state.is_lpg_deployed(lpg_id, area_type):
                    area_emissions = self.state.get_non_deploy_emissions(area_id, area_type)
                        # Llamamos al método que acumula por fuel y para todo el país 
                    self._acumulate_emissions_fuel_and_country(area_emissions)
                    

                    # 4. Ingresos
                    if self.state.is_electrified(area_id, area_type) or self.state.is_lpg_deployed(lpg_id, area_type): 
                        self._accumulate_income(area_id, area_type)
                    # Costes sociales de salud, género y deforestación por demand area, y agrupo para todo el país 
                    social_costs =  self.state.get_aggregated_social_costs(area_id, area_type)
                    self._acumulate_social_costs(social_costs)
                    # MÉTODO QUE GUARDA TODAS LAS EMISIONES POR FUEL Y QUE LOS AGREGA A NIVEL PAÍS
                    self._compute_appliance_weights(area_id, area_type)# REVISAR 

                    #Acumula los incomes del país 
                    self._accumulate_all_appliances_incomes(area_id, area_type)

                   
                    self._accumulate_country_adoption_contrib(area_id, area_type)


            

            # 5. Calcular pesos y almacenar resultados en el state
            #self._calculate_appliance_weights() # REVISAR, no lo llamo porque ya lo hago en el bucle de arriba
            #Calculamos el porcentaje de de Off Grid del país 
            off_grid_percentage = self._calculateOG_percentage()
            #Calculamos los costes fnales de electricidad
            self._assign_electricity_outputs(off_grid_percentage)
            self._assign_electricity_emiss()
            self._assing_lpg_outputs(agg_lpg)
            self._assing_lpg_emiss()
            #self._assing_social_costs()
            # Acumular las emissiones totales de LPG y electricidad
            total_elec_emiss =  self.ec_emiss_g + self.ec_emiss_of
            total_lpg_emiss = self.country_aggregated_lpg_emiss['total'] 
            self.country_cost_by_fuel.emissions_costs[self.electricity_fuel_id] = total_elec_emiss
            self.country_cost_by_fuel.emissions_costs[self.lpg_fuel_id] = total_lpg_emiss
            self.country_emissions_costs  += total_elec_emiss + total_lpg_emiss
            self.financial_agg_params.aggregated_social_costs.emissions_costs = self.country_emissions_costs
            # Guardar los parámetros sociales en el FinancialAggParams
            self._add_area_costs_rest(agg_subs)
            self._assing_social_costs() #TODO
            
            
            self.finalize_and_store_appliance_weights()

            self._store_in_state()
            #self.export_financial_aggregation_tabular_for_tableau()
            self.finalize_and_store_country_appliance_incomes()
            self._finalize_and_store_country_adoption_shares()
            self.compute_and_store_economic_results(agg_subs)


            # Acumulados para el reporte de resultados & Guardados en el estado 
            if is_base_state:
                self.state.set_country_base_edemand_costs(
                    rural_total=base_edemand_rural_total,
                    urban_total=base_edemand_urban_total
                )
                self.logger.info(
                    "[BASE EDemand] Country totals saved: rural=%.3f, urban=%.3f, total=%.3f",
                    base_edemand_rural_total,
                    base_edemand_urban_total,
                    base_edemand_rural_total + base_edemand_urban_total
                )


        
        except Exception as e:
            self.logger.error("Error in the execution of CountryFinancialAggregator: %s", str(e), exc_info=True)
            raise

    def _calculateOG_percentage(self):
        """
        Calculates the Off Grid percentage of the country.
        """
        total_country_consumption = self.state.get_total_country_el_demand()
        total_grid_consumption = self.country_aggregated_electricity_costs['ElecTotal']['g_consumption']  
        total_off_grid_consumption = self.country_aggregated_electricity_costs['ElecTotal']['og_consumption']  
        total_OG_percentage = self.country_aggregated_electricity_costs['ElecTotal']['og_consumption'] / total_country_consumption if total_country_consumption > 0 else 0.0
        # if total_OG_percentage > 0.15:
        #     # Quito un 25% extra si es >15%
        #     total_OG_percentage= total_OG_percentage - 0.25

        #total_OG_percentage = (total_off_grid_consumption / (total_off_grid_consumption+total_grid_consumption)) if (total_off_grid_consumption+total_grid_consumption) > 0 else 0.0
        self.state.set_country_off_grid_percentage(total_OG_percentage)
        return total_OG_percentage #* 100  # NO Lo convierto a float para evitar problemas de división por cero
    
    

    def _calculate_subsides_taxes_for_fuels_appliances(
        self,
        area_id,
        area_type,
        accumulator: AggregatedRestSubsidiesOrTaxesOpex
    ) -> None:
        """
        Calculates and accumulates subsidies/taxes (OPEX) for appliances and fuels for a given area and type.

        :param area_id: ID of the demand area.
        :param area_type: 'rural' or 'urban'.
        :param accumulator: Accumulator object to sum subsidies/taxes by fuel_id.
        """
        try:
            # Cargamos ingresos finales de appliances y fuels
            final_appl_income_by_fuel = self.state.get_region_income(area_id, area_type).get("appliance_income_by_fuel", {})#self.state.get_final_income_costs_fuel(area_id, area_type)
            #final_fuel_income = self.state.get_final_income_costs_fuel(area_id, area_type)
            
            if not isinstance(final_appl_income_by_fuel, dict):
                logging.warning(
                    f"Warning: 'final_income_costs_appl' is expected to be a dict but found {type(final_appl_income_by_fuel)} "
                    f"in area {area_id}, type {area_type}. Using {{}} instead."
                )
                final_appl_income_by_fuel = {}
         
            
            # Obtenemos las tarifas/impuestos por fuel
            region_income = self.state.get_region_income(area_id, area_type).get("fuels", {})
            if not isinstance(region_income, dict):
                logging.warning(
                    f"Warning: 'region_income' is expected to be a dict but found {type(region_income)} "
                    f"in area {area_id}, type {area_type}. Using {{}} instead."
                )
                region_income = {}
            
            # Calculamos subsidios/impuestos para appliances y acumulamos
            for fuel_id, income_appl in final_appl_income_by_fuel.items():
                #tax_rate = region_income.get(fuel_id, 0.0)
                tax_value = float(income_appl) #* float(tax_rate)
                accumulator.appliances[int(fuel_id)] = (
                    accumulator.appliances.get(int(fuel_id), 0.0) + tax_value
                )
            
            # Calculamos subsidios/impuestos para fuels y acumulamos -- Esto no funciona básicamente porque no lo tengo bien programado desde el income model
            for fuel_id, income_fuel in region_income.items(): #TARIFFS 
                #tax_rate = region_income.get(fuel_id, 0.0)
                fuel_id = int(fuel_id)  # Aseguramos que el ID sea un entero
                if fuel_id in [self.electricity_fuel_id, self.lpg_fuel_id]:
                    # Si es electricidad o LPG, no lo consideramos como subsidio/impuesto
                    continue
                tax_sub = float(income_fuel) #* float(tax_rate)
                accumulator.fuels[int(fuel_id)] = (
                    accumulator.fuels.get(int(fuel_id), 0.0) + tax_sub
                )
            return accumulator
        
        except Exception as e:
            self.logger.error(
                "Error calculating subsidies/taxes in area %s type %s: %s",
                area_id, area_type, str(e), exc_info=True
            )
            raise




    def _add_area_costs_rest(self, costs: AggregatedRestSubsidiesOrTaxesOpex):
        """
        Assigns the OPEX subsidies/taxes costs of appliances and fuels,
        overwriting the accumulated value at the country level.
        """
        self.financial_agg_params.aggregated_rest_subsidies_or_taxes_opex.appliances = costs.appliances.copy()
        self.financial_agg_params.aggregated_rest_subsidies_or_taxes_opex.fuels = costs.fuels.copy()

            
    

    def _assign_electricity_outputs(self, off_grid_percentage: float):
        "       Assigns the final electricity costs to the aggregated parameters. "

        try: 

            # CAPEX vs OPEX per bloque
            of = self.financial_agg_params.aggregated_electricity_costs

            #Bloque ETotal - 'ElecTotal'
            elec_total = self.country_aggregated_electricity_costs['ElecTotal']
            rest = elec_total['rest']  # M$/yr
            opex_fraction_fix_grid = self.electric_cost_breakdown.loc[
                self.electric_cost_breakdown["Data"] == "OPEX_fraction_FIX", "Grid"
                ].values[0]
            edemand = self.country_aggregated_electricity_costs['EDemand']

            ed_gen_g = edemand['final_fix_grid_gen']  # M$/yr
            ed_rest = edemand['rest']  # M$/yr
            ed_var_gen_g = edemand['var_grid_gen']  # M$/yr
            ed_var_gen_og = edemand['var_offgrid']  # M$/yr
            et_var_gen_og = elec_total['var_offgrid']  # M$/yr
            et_var_gen_g = elec_total['var_grid_gen']  # M$/yr

            gen_g = elec_total['final_fix_grid_gen'] # M$/yr 
            gen_demand_percentage =  1 - off_grid_percentage  # Porcentaje de demanda en grid
            # gen_og si den_demand_percentage = 0 then rest/2 sino gen_g* off_grid_percentage / den_demand_percentage
            gen_og = (rest / 2) if gen_demand_percentage == 0 else (gen_g * off_grid_percentage / gen_demand_percentage)
            # Distribución Grid & OffGrid
            dis_og =  (rest/2) if gen_demand_percentage == 0 else ((rest - gen_og) * off_grid_percentage) # M$/yr
            dis_g = rest - dis_og - gen_og  # M$/yr -- Especial atencion 
            # Pasamos opex_fraction_fix_grid a porcentaje unitario 
            opex_fraction_fix_grid = float(opex_fraction_fix_grid) #/ 100.0  # Convertir a porcentaje unitario
            # Asignamos porcnate OG 
            of.OFFGRID_percentage = off_grid_percentage  # Porcentaje de OffGrid
            # Asignación de costes
            of.GRID_distribution_CAPEX = (1 - opex_fraction_fix_grid) * dis_g
            of.GRID_distribution_OPEX  = opex_fraction_fix_grid * dis_g
            # Generación Grid
            of.GRID_generation_CAPEX   = (1 - opex_fraction_fix_grid) * gen_g
            of.GRID_generation_OPEX    = opex_fraction_fix_grid * gen_g + et_var_gen_g
            # Distribución OffGrid
            of.OFFGRID_distribution_CAPEX = (1 - opex_fraction_fix_grid) * dis_og
            of.OFFGRID_distribution_OPEX  = opex_fraction_fix_grid * dis_og
            # Generación OffGrid
            of.OFFGRID_generation_CAPEX   = (1 - opex_fraction_fix_grid) * gen_og
            of.OFFGRID_generation_OPEX    = opex_fraction_fix_grid * gen_og + et_var_gen_og
            # Ajustes para E-Cooking
            

            ec_gen_g = gen_g - ed_gen_g  # M$/yr
            ec_rest = rest - ed_rest  # M$/yr
            ec_var_gen_g = et_var_gen_g - ed_var_gen_g  # M$/yr
            ec_var_gen_og = et_var_gen_og - ed_var_gen_og  # M$/yr

            # E-Cooking = 'ElecTotal' - 'EDemand'
            of.E_Cooking_CAPEX = (1 - opex_fraction_fix_grid) * (ec_gen_g + ec_rest)
            of.E_Cooking_OPEX = opex_fraction_fix_grid * (ec_gen_g + ec_rest) + (ec_var_gen_g + ec_var_gen_og)
            # Emissiones de electricidad = ec_emiss_grid  = etotal_grid_emiss - edemand_grid_emiss & ec_emiss_og = etotal_og_emiss - edemand_og_emiss 
        except Exception as e:
            self.logger.error("Error al asignar los outputs de electricidad: %s", str(e), exc_info=True)
            raise
    def _assign_electricity_emiss(self):
        """
        Assigns the electricity emissions to the final aggregate.
        """
        # Emissiones de electricidad = ec_emiss_grid  = etotal_grid_emiss - edemand_grid_emiss & ec_emiss_og = etotal_og_emiss - edemand_og_emiss 
        emiss_etotal = self.country_aggregated_electricity_emissions['ElecTotal']
        emiss_edemand = self.country_aggregated_electricity_emissions['EDemand']
        emiss_el = self.country_emissions_costs #self.financial_agg_params.aggregated_social_costs.emissions_costs 
        self.ec_emiss_g = emiss_etotal['Grid_Emiss'] - emiss_edemand['Grid_Emiss']
        self.ec_emiss_of = emiss_etotal['OG_Emiss'] - emiss_edemand['OG_Emiss']
        total_ec_emiss = self.ec_emiss_g + self.ec_emiss_of
        emiss_el = emiss_el + total_ec_emiss  # Acumulamos las emisiones de electricidad
        
    def _assing_lpg_outputs(self,agg_lpg):
        """
        Asigns the LPG costs to the final aggregate.
        """
        # Asignación de costes
        of = self.financial_agg_params.aggregated_lpg_costs
       
        
        # Local 
        opex_fraction_fix_local = self.lpg_cost_breakdown.loc[
            self.lpg_cost_breakdown["Data"] == "OPEX_fraction_FIX", "Local"].values[0]
        transp_fraction_fix_local = self.lpg_cost_breakdown.loc[
            self.lpg_cost_breakdown["Data"] == "Transport_fraction_FIX", "Local"].values[0]
        transp_fraction_var_local = self.lpg_cost_breakdown.loc[
            self.lpg_cost_breakdown["Data"] == "Transport_fraction_VAR", "Local"].values[0]
        process_fraction_fix_local = self.lpg_cost_breakdown.loc[
            self.lpg_cost_breakdown["Data"] == "Process_fraction_FIX", "Local"].values[0]
        process_fraction_var_local = self.lpg_cost_breakdown.loc[
            self.lpg_cost_breakdown["Data"] == "Process_fraction_VAR", "Local"].values[0]
        # Upstream
        opex_fraction_fix_upstream = self.lpg_cost_breakdown.loc[
            self.lpg_cost_breakdown["Data"] == "OPEX_fraction_FIX", "Upstream"].values[0]
        transp_fraction_fix_upstream = self.lpg_cost_breakdown.loc[
            self.lpg_cost_breakdown["Data"] == "Transport_fraction_FIX", "Upstream"].values[0]
        transp_fraction_var_upstream = self.lpg_cost_breakdown.loc[
            self.lpg_cost_breakdown["Data"] == "Transport_fraction_VAR", "Upstream"].values[0]
        process_fraction_fix_upstream = self.lpg_cost_breakdown.loc[
            self.lpg_cost_breakdown["Data"] == "Process_fraction_FIX", "Upstream"].values[0]
        process_fraction_var_upstream = self.lpg_cost_breakdown.loc[
            self.lpg_cost_breakdown["Data"] == "Process_fraction_VAR", "Upstream"].values[0]
        
        # # Convertimos a porcentaje unitario
        # opex_fraction_fix_local = opex_fraction_fix_local / 100.0
        # transp_fraction_fix_local = transp_fraction_fix_local / 100.0
        # transp_fraction_var_local = transp_fraction_var_local / 100.0
        # process_fraction_fix_local = process_fraction_fix_local / 100.0
        # process_fraction_var_local = process_fraction_var_local / 100.0
        # opex_fraction_fix_upstream = opex_fraction_fix_upstream / 100.0
        # transp_fraction_fix_upstream = transp_fraction_fix_upstream / 100.0
        # transp_fraction_var_upstream = transp_fraction_var_upstream / 100.0
        # process_fraction_fix_upstream = process_fraction_fix_upstream / 100.0
        # process_fraction_var_upstream = process_fraction_var_upstream / 100.0


        # Save results in the financial_agg_params-------------- COMENTAMOS ESTO PARA COMPROBAR 
        # of.LOCAL_processing_CAPEX = (1 - opex_fraction_fix_local) * agg_lpg['fix_costs_local'] * process_fraction_fix_local
        # of.LOCAL_processing_OPEX = opex_fraction_fix_local * agg_lpg['fix_costs_local'] * process_fraction_fix_local + \
        #      agg_lpg['var_costs_local'] * process_fraction_var_local
        # of.LOCAL_transport_CAPEX = (1 - transp_fraction_fix_local) * agg_lpg['fix_costs_local'] * transp_fraction_fix_local
        # of.LOCAL_transport_OPEX = transp_fraction_fix_local * agg_lpg['fix_costs_local'] * transp_fraction_fix_local + \
        #         agg_lpg['var_costs_local'] * transp_fraction_var_local
        #     # Upstream
        # of.UPS_processing_CAPEX = (1 - opex_fraction_fix_upstream) * agg_lpg['fix_costs_upstream'] * process_fraction_fix_upstream
        # of.UPS_processing_OPEX = opex_fraction_fix_upstream * agg_lpg['fix_costs_upstream'] * process_fraction_fix_upstream + \
        #     agg_lpg['var_costs_upstream'] * process_fraction_var_upstream
        # of.UPS_transport_CAPEX = (1 - transp_fraction_fix_upstream) * agg_lpg['fix_costs_upstream'] * transp_fraction_fix_upstream
        # of.UPS_transport_OPEX = transp_fraction_fix_upstream * agg_lpg['fix_costs_upstream'] * transp_fraction_fix_upstream + \
        #     agg_lpg['var_costs_upstream'] * transp_fraction_var_upstream
        # of.UPS_import_OPEX = agg_lpg['var_costs_import']  # Asumiendo que es el mismo para upstream y local
        

        ###
        fix_local = agg_lpg['fix_costs_local']
        var_local = agg_lpg['var_costs_local']

        # reparto del FIX entre proceso/transporte
        fix_local_proc = fix_local * process_fraction_fix_local
        fix_local_trans = fix_local * transp_fraction_fix_local

        # CAPEX/OPEX del FIX
        of.LOCAL_processing_CAPEX = (1 - opex_fraction_fix_local) * fix_local_proc
        of.LOCAL_processing_OPEX  = opex_fraction_fix_local     * fix_local_proc

        of.LOCAL_transport_CAPEX  = (1 - opex_fraction_fix_local) * fix_local_trans
        of.LOCAL_transport_OPEX   = opex_fraction_fix_local       * fix_local_trans

        # # VAR ya vienen etiquetados por bloque (usa las fracciones VAR de reparto si aplican)
        # of.LOCAL_processing_OPEX += var_local * process_fraction_var_local
        # of.LOCAL_transport_OPEX  += var_local * transp_fraction_var_local
        fix_upstream = agg_lpg['fix_costs_upstream']
        var_upstream = agg_lpg['var_costs_upstream']
        # reparto del FIX entre proceso/transporte
        fix_upstream_proc = fix_upstream * process_fraction_fix_upstream
        fix_upstream_trans = fix_upstream * transp_fraction_fix_upstream
        # CAPEX/OPEX del FIX
        of.UPS_processing_CAPEX = (1 - opex_fraction_fix_upstream) * fix_upstream_proc
        of.UPS_processing_OPEX  = opex_fraction_fix_upstream     * fix_upstream_proc
        of.UPS_transport_CAPEX  = (1 - transp_fraction_fix_upstream) * fix_upstream_trans
        of.UPS_transport_OPEX   = transp_fraction_fix_upstream       * fix_upstream_trans
        # #UPS Import OPEX
        of.UPS_import_OPEX = agg_lpg['var_costs_import']  # Asumiendo que es el mismo para upstream y local


    def _assing_lpg_emiss(self):
        """
        Assigns the LPG emissions to the final aggregate.
        """
        try: 
            # Emisiones de LPG
            emiss_lpg = self.financial_agg_params.aggregated_social_costs.emissions_costs
            emiss_lpg_agg = self.country_aggregated_lpg_emiss['total'] 
            emiss_lpg = emiss_lpg + emiss_lpg_agg
        except Exception as e:
            self.logger.error("Error assigning LPG emissions: %s", str(e), exc_info=True)
            raise

    def _acumulate_social_costs(self, social_costs: AggregatedSocialCosts):
        """
        Accumulates the social costs of health, gender, and deforestation at the country level.

        :param social_costs: AggregatedSocialCosts with costs already aggregated
                            by fuel_id for a demand area and an area_type
                            (rural or urban).
        """
        # 1) Recorremos fuel_id → health_cost
        for fuel_id, cost in social_costs.health_costs.items():
            # Si no existe aún ese fuel_id en country_costs_by_fuel, lo inicializamos a 0.0
            prev = self.country_cost_by_fuel.health_costs.get(fuel_id, 0.0)
            self.country_cost_by_fuel.health_costs[fuel_id] = prev + cost

            # Acumulamos en el total nacional de salud
            self.country_health_costs += cost
            

        # 2) Recorremos fuel_id → gender_cost
        for fuel_id, cost in social_costs.gender_costs.items():
            prev = self.country_cost_by_fuel.gender_costs.get(fuel_id, 0.0)
            self.country_cost_by_fuel.gender_costs[fuel_id] = prev + cost

            # Acumulamos en el total nacional de género
            self.country_gender_costs += cost

        # 3) Recorremos fuel_id → deforestation_cost
        for fuel_id, cost in social_costs.deforestation_costs.items():
            prev = self.country_cost_by_fuel.deforestation_costs.get(fuel_id, 0.0)
            self.country_cost_by_fuel.deforestation_costs[fuel_id] = prev + cost

            # Acumulamos en el total nacional de deforestación
            self.country_deforestation_costs += cost

        # (Si más adelante quieres manejar emissions_costs, podrías añadir un bucle análogo.)
        # Llamar una vez (p.ej. en __init__ o al cargar tecnologías)
    def _prepare_tech_lookup(self):
        
        df = self.df_technologies

        tech = pd.to_numeric(df["Technologies_id"], errors="coerce").to_numpy()
        fuel = pd.to_numeric(df["Fuel_id"], errors="coerce").to_numpy()

        # Elimina NaN y duplica por tech: nos quedamos con la primera aparición
        mask = ~np.isnan(tech) & ~np.isnan(fuel)
        tech, fuel = tech[mask].astype(np.int64), fuel[mask].astype(np.int64)

        order = np.argsort(tech, kind="mergesort")
        self._tech_ids_sorted = tech[order]
        self._fuel_ids_sorted = fuel[order]

    def _lookup_fuel_id(self, tech_id: int):
        # O(log n), sin Series ni map
        import numpy as np
        arr = self._tech_ids_sorted
        pos = np.searchsorted(arr, tech_id)
        if pos < arr.size and arr[pos] == tech_id:
            return int(self._fuel_ids_sorted[pos])
        return None

    def _acumulate_emissions_fuel_and_country(self, area_emissions: Dict[int, float]):
        if not hasattr(self, "_tech_ids_sorted"):
            self._prepare_tech_lookup()

        for tech_id, emiss in area_emissions.items():
            try:
                tid = int(tech_id)
            except (TypeError, ValueError):
                logging.warning("Technology %s no numérica; omitida.", tech_id)
                continue

            fuel_id = self._lookup_fuel_id(tid)
            if fuel_id is None:
                logging.warning("Technology %s no encontrada o sin Fuel_id; omitida.", tech_id)
                continue

            self.country_cost_by_fuel.emissions_costs[fuel_id] = (
                self.country_cost_by_fuel.emissions_costs.get(fuel_id, 0.0) + float(emiss)
            )
            self.country_emissions_costs += float(emiss)



    # def _acumulate_emissions_fuel_and_country(self, area_emissions: Dict[int, float]):
    #     """
    #     Accumulates the emissions of technologies (received by tech_id) in:
    #     1) self.country_cost_by_fuel.emissions_costs[fuel_id]
    #     2) self.country_emissions_costs  (national total)

    #     :param area_emissions: Dict[tech_id, emission_value]
    #     """
    #     for tech_id, emiss in area_emissions.items():
    #         # 1) Buscamos la fila en el DataFrame para obtener fuel_id
    #         tech_row = self.df_technologies[self.df_technologies["Technologies_id"] == tech_id]
    #         if tech_row.empty:
    #             # Si la tecnología no existe en el DataFrame, avisamos y saltamos
    #             logging.warning(
    #                 "Technology %s not found in df_technologies; its emissions are omitted.",
    #                 tech_id
    #             )
    #             continue

    #         # Extraemos fuel_id (si no existiera, saltamos)
    #         fuel_id = tech_row.iloc[0].get("Fuel_id", None)
    #         if fuel_id is None:
    #             logging.warning(
    #                 "Fuel_id absent for technology %s; its emissions cannot be grouped.",
    #                 tech_id
    #             )
    #             continue

    #         # 2) Acumulamos esta emisión en el desglose por fuel

    #         prev_val = self.country_cost_by_fuel.emissions_costs.get(fuel_id, 0.0)
    #         self.country_cost_by_fuel.emissions_costs[fuel_id] = prev_val + emiss

    #         # 3) También sumamos al total nacional
    #         self.country_emissions_costs += emiss

    def _assing_social_costs(self):
        """ Saves the social costs in the FinancialAggParams.
        """
        try: 
            self.financial_agg_params.aggregated_social_costs = AggregatedSocialCosts(
                health_costs=self.country_health_costs,
                gender_costs=self.country_gender_costs, 
                deforestation_costs=self.country_deforestation_costs,
                emissions_costs=self.country_emissions_costs
            )
        except Exception as e:
            self.logger.error("Error assigning social costs: %s", str(e), exc_info=True)
            raise

    # def _assing_average_growth_calculation_appliances(self):
    #     """ Saves the Average Growth Calculation Appliances in the FinancialAggParams.
    #     """
    #     try: 
    #         self.financial_agg_params.average_growth_calculation_appliances = AverageGrowthCalculationAppliances(
    #             appliances=self.appliance_weights_by_fuel
    #         )
    #     except Exception as e:
    #         self.logger.error("Error assigning the Average Growth Calculation Appliances: %s", str(e), exc_info=True)
    #         raise

    


    
           

    def _accumulate_income(self,demand_area_id: int, area_type: str):
        """
        accumulate the income from appliance and fuel tariffs for a specific area and type.
        """
        try:
            # income = self.state.get_region_income(demand_area_id, area_type).get("fuels", {})#self.state.get_income_by_appliance(demand_area_id, area_type)#.get("fuels", {})
            # income_eDemand = self.state.get_region_income(demand_area_id, area_type).get("electric", {})
            # income_eCooking =income.get(self.electricity_fuel_id, 0.0) #Incomes due to cooking and heating Dis electric 
            # income_lpg = income.get(self.lpg_fuel_id, 0.0) #Incomes due to cooking and heating Dis LPG
            inc = self.state.get_region_income(demand_area_id, area_type) or {}
            inc_fuels = inc.get("fuels", {}) or {}
            income_eDemand = float(inc.get("electric", 0.0) or 0.0)
            income_eCooking = float(inc_fuels.get(self.electricity_fuel_id, 0.0) or 0.0)
            income_lpg = float(inc_fuels.get(self.lpg_fuel_id, 0.0) or 0.0)

            #block = E_total, E_cooking, LPG
            block = {
                "E_total": income_eDemand ,#+ income_eCooking,  # Incomes from electricity demand and cooking
                "E_cooking": income_eCooking,
                "LPG": income_lpg
            }
            for fuel_key, value in block.items():
                prev_value = self.financial_agg_params.income_tariff.fuels.get(fuel_key, 0.0)
                self.financial_agg_params.income_tariff.fuels[fuel_key] = prev_value + value
        except Exception as e:
            self.logger.error("Error accumulating income from tariffs in area %s type %s: %s", demand_area_id, area_type, str(e), exc_info=True)
            raise

    

    

    # def _compute_appliance_weights(self, demand_area_id: str, area_type: str):
    #     """
    #     Calculate the income percentages attributable to each appliance within each fuel.
    #     Uses many-to-many mapping Appliance → Fuel and ensures normalization.
    #     """
    #     try:
    #         df_tech = self.df_technologies
    #         income_by_fuel = self.state.get_region_income(demand_area_id, area_type).get("appliance_income_by_fuel", {})
    #         income_by_appliance = self.state.get_region_income(demand_area_id, area_type).get("appliance_income_by_appliance", {})

    #         # Validaciones
    #         if not isinstance(income_by_appliance, dict):
    #             self.logger.warning(f"[{demand_area_id}-{area_type}] 'appliance_income_by_appliance' is not a dict.")
    #             income_by_appliance = {}
    #         if not isinstance(income_by_fuel, dict):
    #             self.logger.warning(f"[{demand_area_id}-{area_type}] 'appliance_income_by_fuel' is not a dict.")
    #             income_by_fuel = {}

    #         # Construir mapeo Appliance_id → lista de Fuel_ids (muchos a muchos)
    #         app_to_fuels = defaultdict(set)
    #         for _, row in df_tech.iterrows():
    #             app_to_fuels[row["Appliance_id"]].add(row["Fuel_id"])

    #         # Inicializar acumulador
    #         fuel_to_appliances = defaultdict(dict)

    #         # Repartir el income_appliance entre sus fuels asociados
    #         for appliance_id, income_appliance in income_by_appliance.items():
    #             fuels = app_to_fuels.get(appliance_id)
    #             if not fuels:
    #                 self.logger.warning(f"[{demand_area_id}-{area_type}] Appliance_id {appliance_id} sin Fuel asociado.")
    #                 continue

    #             share_per_fuel = income_appliance / len(fuels)
    #             for fuel_id in fuels:
    #                 fuel_to_appliances[fuel_id][appliance_id] = share_per_fuel

    #         # Calcular pesos normalizados por fuel
    #         self.appliance_weights_by_fuel = {}
    #         for fuel_id, appliances in fuel_to_appliances.items():
    #             total_income = sum(appliances.values())
    #             if total_income == 0:
    #                 self.logger.warning(f"[{demand_area_id}-{area_type}] Fuel_id {fuel_id} tiene ingreso total 0.")
    #                 continue

    #             weights = {a_id: inc / total_income for a_id, inc in appliances.items()}
    #             self.appliance_weights_by_fuel[fuel_id] = weights

    #             # Verificación suma
    #             sum_weights = sum(weights.values())
    #             if sum_weights > 1.01:
    #                 self.logger.warning(f"[{demand_area_id}-{area_type}] Pesos > 1 para fuel_id={fuel_id}: {sum_weights:.3f}")

    #         # Guardar
    #         self.financial_agg_params.average_growth_calculation_appliances.appliances = self.appliance_weights_by_fuel

    #     except Exception as e:
    #         self.logger.error(f"Error en _compute_appliance_weights para área {demand_area_id} tipo {area_type}: {str(e)}", exc_info=True)
    #         raise
    # def _compute_appliance_weights(self, demand_area_id: str, area_type: str):
    #     """
    #     Acumula, para todo el país, el ingreso atribuible a cada appliance dentro de cada fuel.
    #     Luego, en finalize_and_store_appliance_weights, se normaliza a pesos.
    #     """
    #     try:
    #         df_tech = self.df_technologies
    #         income_region = self.state.get_region_income(demand_area_id, area_type) or {}

    #         income_by_fuel = income_region.get("appliance_income_by_fuel", {}) or {}
    #         income_by_appliance = income_region.get("appliance_income_by_appliance", {}) or {}

    #         # Validaciones
    #         if not isinstance(income_by_appliance, dict):
    #             self.logger.warning(f"[{demand_area_id}-{area_type}] 'appliance_income_by_appliance' is not a dict.")
    #             income_by_appliance = {}
    #         if not isinstance(income_by_fuel, dict):
    #             self.logger.warning(f"[{demand_area_id}-{area_type}] 'appliance_income_by_fuel' is not a dict.")
    #             income_by_fuel = {}

    #         # Construir mapeo Appliance_id → lista de Fuel_ids (muchos a muchos)
    #         app_to_fuels = defaultdict(set)
    #         for _, row in df_tech.iterrows():
    #             app_to_fuels[int(row["Appliance_id"])].add(int(row["Fuel_id"]))

    #         # Repartir el income_appliance entre sus fuels asociados y ACUMULAR a nivel país
    #         for appliance_id, income_appliance in income_by_appliance.items():
    #             appliance_id = int(appliance_id)
    #             income_appliance = float(income_appliance or 0.0)

    #             fuels = app_to_fuels.get(appliance_id)
    #             if not fuels:
    #                 self.logger.warning(f"[{demand_area_id}-{area_type}] Appliance_id {appliance_id} sin Fuel asociado.")
    #                 continue

    #             share_per_fuel = income_appliance / len(fuels)
    #             for fuel_id in fuels:
    #                 fuel_id = int(fuel_id)
    #                 # Acumulamos ingreso asociado a (fuel, appliance) para TODO el país
    #                 self._appliance_income_by_fuel_appliance[fuel_id][appliance_id] += share_per_fuel
                    


    #     except Exception as e:
    #         self.logger.error(
    #             f"Error en _compute_appliance_weights para área {demand_area_id} tipo {area_type}: {str(e)}",
    #             exc_info=True
    #         )
    #         raise
    def _compute_appliance_weights(self, demand_area_id: int, area_type: str):
        """
        Acumula, para todo el país, el ingreso de cada appliance dentro de cada fuel.
        """
        try:
            income_region = self.state.get_region_income(demand_area_id, area_type) or {}
            by_fuel_and_appl = income_region.get("appliance_income_by_fuel_and_appliance", {}) or {}

            for fuel_id, app_map in by_fuel_and_appl.items():
                for app_id, inc in app_map.items():
                    self._country_appliance_income_by_fuel[int(fuel_id)][int(app_id)] += float(inc or 0.0)

        except Exception as e:
            self.logger.error(
                f"Error en _compute_appliance_weights para área {demand_area_id} tipo {area_type}: {str(e)}",
                exc_info=True
            )
            raise


            
    # def _accumulate_all_appliances_incomes(self, area_id, area_type):
    #     "Method to accumulate the total income and expenditure of the country, separated between rural and urban"
    #     "It can be saved into class variables and the assigned to the state at the end of the method"
    #     "needs to be called for each area and area_type" 
    #     "It can be 3 types of area: rural, urban or all (both) with the area_types as None, 'rural' or 'urban'"


    #     try: 
    #         # Bloques completos (rural y urban)
    #         all_blocks = self.state.get_base_price(area_id)

    #         if area_type is None:
    #             keys = ["rural", "urban"]
    #         elif area_type in ("rural", "urban"):
    #             keys = [area_type]
    #         else:
    #             raise ValueError("area_type debe ser None, 'rural' o 'urban'")

    #         for key in keys:
    #             area_block = all_blocks.get(key, {})
    #             if not area_block:
    #                 # nada guardado para esa área, continúa
    #                 continue

    #             total = float(area_block.get("total", 0.0) or 0.0)
    #             total_times_CH = float(area_block.get("total_times_CH", 0.0) or 0.0)
    #             #per_tech = area_block.get("per_tech", {}) or {}

    #             acc = self._country_base_price_acc[key]
    #             acc["sum_total"] += total
    #             acc["sum_total_times_CH"] += total_times_CH # $/year
    #             acc["areas_count"] += 1 

               

    #     except Exception as e:
    #         self.logger.error(f"Error acumulando ingresos y gastos de appliances en área {area_id} tipo {area_type}: {str(e)}", exc_info=True)
    #         raise

    # def finalize_and_store_country_appliance_incomes(self):
    #     """
    #     Constructs the country appliance/base-price income summary (rural/urban and total)
    #     from the accumulator _country_base_price_acc and saves it in the State with a single set.

    #     Estructura resultante:
    #     {
    #         "rural": {
    #             "sum_total": ...,
    #             "sum_total_times_CH": ...,
    #             "areas_count": ...,
    #             "avg_total": ...,
    #         },
    #         "urban": { ... },
    #         "all":   { ... }
    #     }
    #     """
    #     try:
    #         acc_all = getattr(self, "_country_base_price_acc", None)
    #         if not acc_all:
    #             self.logger.warning(
    #                 "[COUNTRY APPL INCOME] _country_base_price_acc vacío o no inicializado."
    #             )
    #             acc_all = {
    #                 "rural": {"sum_total": 0.0, "sum_total_times_CH": 0.0, "areas_count": 0},
    #                 "urban": {"sum_total": 0.0, "sum_total_times_CH": 0.0, "areas_count": 0},
    #             }

    #         out = {}

    #         for key in ("rural", "urban"):
    #             acc = acc_all.get(key, {}) or {}
    #             sum_total = float(acc.get("sum_total", 0.0) or 0.0)
    #             sum_total_times_CH = float(acc.get("sum_total_times_CH", 0.0) or 0.0)
    #             areas_count = int(acc.get("areas_count", 0) or 0)

    #             # media simple por área (si no hay áreas, evitamos div/0)
    #             denom = max(areas_count, 1)
    #             avg_total = sum_total / denom

    #             out[key] = {
    #                 "sum_total": sum_total,
    #                 "sum_total_times_CH": sum_total_times_CH,
    #                 "areas_count": areas_count,
    #                 "avg_total": avg_total,  # ≈ $/cook medio en esa categoría
    #             }

    #         # Agregado "all" (ponderado por nº de áreas)
    #         all_sum_total = out["rural"]["sum_total"] + out["urban"]["sum_total"]
    #         all_sum_total_times_CH = (
    #             out["rural"]["sum_total_times_CH"] + out["urban"]["sum_total_times_CH"]
    #         )
    #         all_areas = out["rural"]["areas_count"] + out["urban"]["areas_count"]

    #         if all_areas > 0:
    #             all_avg_total = all_sum_total / all_areas
    #         else:
    #             all_avg_total = 0.0

    #         out["all"] = {
    #             "sum_total": all_sum_total,
    #             "sum_total_times_CH": all_sum_total_times_CH,
    #             "areas_count": all_areas,
    #             "avg_total": all_avg_total,
    #         }

    #         # Guarda en State con un único set
    #         if hasattr(self.state, "set_country_base_price"):
    #             self.state.set_country_base_price(out)
    #         else:
    #             self.logger.warning(
    #                 "State no tiene método set_country_base_price; resumen país no guardado."
    #             )

    #         self.logger.info("[COUNTRY APPL INCOME] Resumen país guardado: %s", out)

    #     except Exception as e:
    #         self.logger.error(
    #             "Error en finalize_and_store_country_appliance_incomes: %s",
    #             str(e),
    #             exc_info=True,
    #         )
    #         raise
    def _accumulate_all_appliances_incomes(self, area_id, area_type):
        """
        Method to accumulate the total income and expenditure of the country,
        separated between rural and urban.

        It must be called for each area and area_type.
        area_type can be: None (both), 'rural' or 'urban'.
        """
        try:
            # Full blocks (rural and urban) for this demand area
            all_blocks = self.state.get_base_price(area_id)

            if area_type is None:
                keys = ["rural", "urban"]
            elif area_type in ("rural", "urban"):
                keys = [area_type]
            else:
                raise ValueError("area_type must be None, 'rural' or 'urban'")

            for key in keys:
                area_block = all_blocks.get(key, {})
                if not area_block:
                    # Nothing stored for this area_type in this area, continue
                    continue

                # Average price per cook in this area_type [$ / cook]
                total = float(area_block.get("total", 0.0) or 0.0)

                # Annual expenditure / income for this area_type [$ / year]
                total_times_CH = float(area_block.get("total_times_CH", 0.0) or 0.0)

                acc = self._country_base_price_acc[key]

                # 1) Accumulate annual cost / income [$ / year]
                acc["sum_total_times_CH"] += total_times_CH

                # 2) Recover CH_Demand for this area_type and accumulate [cooks / year]
                if total > 0.0:
                    ch_demand = total_times_CH / total  # cooks/year
                else:
                    ch_demand = 0.0

                acc.setdefault("sum_CH", 0.0)
                acc["sum_CH"] += ch_demand

                # 3) Optionally keep these if you still want them (not needed for av income per cook)
                acc.setdefault("sum_total", 0.0)
                acc["sum_total"] += total
                acc.setdefault("areas_count", 0)
                acc["areas_count"] += 1

        except Exception as e:
            self.logger.error(
                f"Error accumulating appliance incomes and expenditures "
                f"in area {area_id} type {area_type}: {str(e)}",
                exc_info=True
            )
            raise

    def finalize_and_store_country_appliance_incomes(self):
        """
        Constructs the country appliance/base-price income summary (rural/urban and total)
        from the accumulator _country_base_price_acc and saves it in the State with a single set.

        Resulting structure (example):

        {
            "rural": {
                "annual_income": float,          # $/year
                "sum_CH": float,                 # cooks/year
                "av_income_per_cook": float,     # $/cook (demand-weighted)
            },
            "urban": {
                ...
            },
            "all": {
                "annual_income": float,          # $/year
                "sum_CH": float,                 # cooks/year
                "av_income_per_cook": float,     # $/cook
            }
        }
        """
        try:
            acc_all = getattr(self, "_country_base_price_acc", None)
            if not acc_all:
                self.logger.warning(
                    "[COUNTRY APPL INCOME] _country_base_price_acc is empty or not initialized."
                )
                acc_all = {
                    "rural": {
                        "sum_total_times_CH": 0.0,
                        "sum_CH": 0.0,
                    },
                    "urban": {
                        "sum_total_times_CH": 0.0,
                        "sum_CH": 0.0,
                    },
                }

            out = {}

            # --- Rural & Urban ---
            for key in ("rural", "urban"):
                acc = acc_all.get(key, {}) or {}

                annual_income = float(acc.get("sum_total_times_CH", 0.0) or 0.0)  # $/year
                sum_CH = float(acc.get("sum_CH", 0.0) or 0.0)                      # cooks/year

                if sum_CH > 0.0:
                    av_income_per_cook = annual_income / sum_CH                    # $/cook
                else:
                    av_income_per_cook = 0.0

                out[key] = {
                    "annual_income": annual_income,
                    "sum_CH": sum_CH,
                    "av_income_per_cook": av_income_per_cook,
                }

            # --- All (rural + urban) ---
            annual_income_all = out["rural"]["annual_income"] + out["urban"]["annual_income"]
            sum_CH_all = out["rural"]["sum_CH"] + out["urban"]["sum_CH"]

            if sum_CH_all > 0.0:
                av_income_per_cook_all = annual_income_all / sum_CH_all
            else:
                av_income_per_cook_all = 0.0

            out["all"] = {
                "annual_income": annual_income_all,
                "sum_CH": sum_CH_all,
                "av_income_per_cook": av_income_per_cook_all,
            }

            # Save in State with a single setter
            if hasattr(self.state, "set_country_base_price"):
                self.state.set_country_base_price(out)
            else:
                self.logger.warning(
                    "State does not have method set_country_base_price; country summary not stored."
                )

            self.logger.info("[COUNTRY APPL INCOME] Country summary stored: %s", out)

        except Exception as e:
            self.logger.error(
                "Error in finalize_and_store_country_appliance_incomes: %s",
                str(e),
                exc_info=True,
            )
            raise


    







        

    def _store_in_state(self):
        try: 
            self.state.set_financial_results(self.financial_agg_params)
        except Exception as e:
            self.logger.error("Error saving financial results in state: %s", str(e), exc_info=True)
            raise
        
    def compute_and_store_economic_results(self, subs_accumulator: AggregatedRestSubsidiesOrTaxesOpex) -> None:
        """
        Calculates the economic result of the state and saves it in self.state.
        FFormulas:
        Electricity (E_total): income_E_total - (fix_grid_gen + rest + var_grid_gen + var_offgrid)
        LPG:                    income_LPG     - (fix_upstream + fix_local + var_upstream + var_local + import)
        Total: net_electric + net_lpg + (taxes_subsidies_appliances + taxes_subsidies_fuels)
        """
        try:
            # ---- Ingresos ----
            incomes = getattr(self.financial_agg_params, "income_tariff", None)
            income_map = incomes.fuels if incomes and hasattr(incomes, "fuels") else {}
            income_e_total = float(income_map.get("E_total", 0.0))
            income_lpg     = float(income_map.get("LPG", 0.0))

            # ---- Costes Electricidad (bloque ElecTotal) ----
            el_block = self.country_aggregated_electricity_costs.get("ElecTotal", {})
            fix_grid_gen = float(el_block.get("final_fix_grid_gen", 0.0))
            rest         = float(el_block.get("rest", 0.0))
            var_grid_gen = float(el_block.get("var_grid_gen", 0.0))
            var_offgrid  = float(el_block.get("var_offgrid", 0.0))
            total_el_costs = fix_grid_gen + rest + var_grid_gen + var_offgrid

            # ---- Costes LPG ----
            lpg_costs = self.country_aggregated_lpg_costs
            fix_upstream = float(lpg_costs.get("fix_costs_upstream", 0.0))
            fix_local    = float(lpg_costs.get("fix_costs_local", 0.0))
            var_upstream = float(lpg_costs.get("var_costs_upstream", 0.0))
            var_local    = float(lpg_costs.get("var_costs_local", 0.0))
            var_import   = float(lpg_costs.get("var_costs_import", 0.0))
            total_lpg_costs = fix_upstream + fix_local + var_upstream + var_local + var_import

            # ---- Taxes/Subsidies (appliances + fuels) ----
            # El acumulador guarda por fuel_id; sumamos todo.
            tot_appliances = sum(float(v) for v in getattr(subs_accumulator, "appliances", {}).values())
            tot_fuels      = sum(float(v) for v in getattr(subs_accumulator, "fuels", {}).values())
            taxes_subsidies_total = tot_appliances + tot_fuels

            # ---- Netos y total ----
            net_electric = income_e_total - total_el_costs
            net_lpg      = income_lpg     - total_lpg_costs
            grand_total  = net_electric + net_lpg + taxes_subsidies_total

            result = EconomicResult(
                net_electric_total=net_electric,
                net_lpg_total=net_lpg,
                taxes_subsidies_total=taxes_subsidies_total,
                grand_total=grand_total
            )
            # Guardar en State
            self.state.set_economic_result(result)

            # (Opcional) Log de resumen
            self.logger.info(
                "[ECON] net_electric=%.3f, net_lpg=%.3f, taxes_subsidies=%.3f, TOTAL=%.3f",
                net_electric, net_lpg, taxes_subsidies_total, grand_total
            )

        except Exception as e:
            self.logger.error("Error calculando resultado económico del estado: %s", str(e), exc_info=True)
            raise



    def _init_country_adoption_accumulators(self) -> None:
        # Denominadores (suma CH por ámbito) y contribuciones ∑(adopción_area_tech * CH_area)
        self._adopt_country = {
            "denom": {"rural": 0.0, "urban": 0.0},
            "initial":   {"rural": defaultdict(float), "urban": defaultdict(float)},
            "potential": {"rural": defaultdict(float), "urban": defaultdict(float)},
        }


    def _init_country_appliance_weight_accumulators(self) -> None:
        """
        Acumulador país: para cada fuel_id, suma el income atribuido a cada appliance.
        Luego se normaliza en finalize_and_store_appliance_weights().
        """
        # dict[fuel_id][appliance_id] = ingreso_acumulado_atribuido
        self._country_appliance_income_by_fuel = defaultdict(lambda: defaultdict(float))
        #self._appliance_income_by_fuel_appliance = defaultdict(lambda: defaultdict(float))

    def _to_float(self, x, default=0.0) -> float:
        try:
            return float(x)
        except Exception:
            return default

    def _get_ch(self, demand_area_id: int, area_type: str) -> float:
        ch = self.state.get_CH_consumption(demand_area_id, area_type)
        if isinstance(ch, dict):
            return self._to_float(ch.get(area_type, 0.0), 0.0)
        return self._to_float(ch, 0.0)
    

    def _accumulate_country_adoption_contrib(self, area_id: int, area_type: str) -> None:
        """
        Adds contributions by technology: contrib += adopción_area_tech * CH_area.
        Not normalized. This is done in the 'finalize' method.
        Requires that _init_country_adoption_accumulators() has been called first.
        """
        ch_val = self._get_ch(area_id, area_type)
        if ch_val <= 0:
            return

        init_dict = self.state.get_initial_adoption(area_id, area_type) or {}
        pot_dict  = self.state.get_potential_adoption(area_id, area_type) or {}

        self._adopt_country["denom"][area_type] += ch_val

        tech_ids = set(init_dict.keys()) | set(pot_dict.keys())
        for tid in tech_ids:
            tid_i = int(tid)
            self._adopt_country["initial"][area_type][tid_i] += self._to_float(init_dict.get(tid, 0.0)) * ch_val
            self._adopt_country["potential"][area_type][tid_i] += self._to_float(pot_dict.get(tid, 0.0)) * ch_val

    def _finalize_and_store_country_adoption_shares(self) -> None:
        """
        Normalizes contributions by the CH denominators and saves them in State.
        """
        acc = getattr(self, "_adopt_country", None)
        if not acc:
            # Nothing accumulated
            self.state.set_country_adoption_shares({}, {}, {}, {}, {}, {})
            return

        def normalize(contrib: dict, denom: float) -> dict:
            if denom <= 0:
                return {}
            return {tid: (val / denom) for tid, val in contrib.items()}

        # Normalización por ámbito
        init_r = normalize(acc["initial"]["rural"], acc["denom"]["rural"])
        init_u = normalize(acc["initial"]["urban"], acc["denom"]["urban"])
        pot_r  = normalize(acc["potential"]["rural"], acc["denom"]["rural"])
        pot_u  = normalize(acc["potential"]["urban"], acc["denom"]["urban"])

        # Totales país (suma contribuciones rurales + urbanas y normaliza por denom_total)
        total_denom = acc["denom"]["rural"] + acc["denom"]["urban"]

        from collections import defaultdict as dd
        def sumdicts(a: dict, b: dict) -> dict:
            out = dd(float)
            for d in (a, b):
                for k, v in d.items():
                    out[int(k)] += float(v)
            return dict(out)

        init_total_contrib = sumdicts(acc["initial"]["rural"], acc["initial"]["urban"])
        pot_total_contrib  = sumdicts(acc["potential"]["rural"], acc["potential"]["urban"])

        init_t = normalize(init_total_contrib, total_denom)
        pot_t  = normalize(pot_total_contrib,  total_denom)

        self.state.set_country_adoption_shares(
            initial_rural=init_r, initial_urban=init_u, initial_total=init_t,
            potential_rural=pot_r, potential_urban=pot_u, potential_total=pot_t,
        )


    # def finalize_and_store_appliance_weights(self) -> None:
    #     """
    #     A partir de self._appliance_income_by_fuel_appliance (acumulado en todo el país),
    #     calcula pesos normalizados por fuel y los guarda en financial_agg_params.
    #     """
    #     try:
    #         weights_by_fuel = {}

    #         for fuel_id, appliances in self._appliance_income_by_fuel_appliance.items():
    #             total_income = sum(float(v or 0.0) for v in appliances.values())
    #             if total_income <= 0:
    #                 self.logger.warning(f"[APPL WEIGHTS] Fuel_id {fuel_id} tiene ingreso total 0; se ignora.")
    #                 continue

    #             weights = {a_id: (float(inc) / total_income) for a_id, inc in appliances.items()}
    #             weights_by_fuel[int(fuel_id)] = weights

    #             sum_weights = sum(weights.values())
    #             if sum_weights > 1.01:
    #                 self.logger.warning(
    #                     f"[APPL WEIGHTS] Pesos > 1 para fuel_id={fuel_id}: suma={sum_weights:.3f}"
    #                 )

    #         # Guardar en financial_agg_params
    #         self.financial_agg_params.average_growth_calculation_appliances.appliances = weights_by_fuel

    #         # DEBUG fuerte en WARNING para que lo veas sí o sí en logs
    #         self.logger.warning(f"[APPL WEIGHTS] Pesos finales por fuel: {weights_by_fuel}")

    #     except Exception as e:
    #         self.logger.error("Error en finalize_and_store_appliance_weights: %s", str(e), exc_info=True)
    #         raise
    def finalize_and_store_appliance_weights(self) -> None:
        """
        A partir de self._country_appliance_income_by_fuel (acumulado en todo el país),
        calcula pesos normalizados por fuel y los guarda en financial_agg_params.
        """
        try:
            weights_by_fuel = {}

            for fuel_id, appl_map in self._country_appliance_income_by_fuel.items():
                # income total por fuel (usamos abs por si hay ingresos negativos)
                total_income = sum(abs(float(v or 0.0)) for v in appl_map.values())

                if total_income <= 0:
                    self.logger.warning(
                        f"[APPL WEIGHTS] Fuel_id {fuel_id} tiene income total 0; se ignora."
                    )
                    continue

                weights = {
                    int(app_id): (abs(float(inc)) / total_income)
                    for app_id, inc in appl_map.items()
                }
                weights_by_fuel[int(fuel_id)] = weights

                sum_weights = sum(weights.values())
                if not (0.99 <= sum_weights <= 1.01):
                    self.logger.warning(
                        f"[APPL WEIGHTS] Suma de pesos para fuel_id={fuel_id} = {sum_weights:.4f}"
                    )

            # Guardar en FinancialAggParams
            self.financial_agg_params.average_growth_calculation_appliances.appliances = weights_by_fuel

            self.logger.warning(f"[APPL WEIGHTS] Pesos finales por fuel: {weights_by_fuel}")

        except Exception as e:
            self.logger.error("Error en finalize_and_store_appliance_weights: %s", str(e), exc_info=True)
            raise




