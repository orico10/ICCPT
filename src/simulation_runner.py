# src/simulation_runner.py
import os, copy, logging
from collections import defaultdict

from src import config
from src.mixed_state_generator import MixedStateGenerator
from src.demand_area_manager import DemandAreaManager
from src.technologies import Technologies
from src.adoption_model_2_0 import AdoptionModel2_0
from src.income_mode_2_0 import IncomeModel2_0
from src.electricity_cost_model import ElectricityCostModel
from src.electricity_deployment import DeployElectricity
from src.lpg_cost_model import LPGCostModel
from src.lpg_deploy_model import LPGDeployModel
from src.lpg_emissions_model import EmissionsLPG
from src.electricity_emissions_model import EmissionsElectricity
from src.non_deploy_emissions_model import NonDeployEmissionsModel
from src.non_deploy_fuel_cost_model import ApplFuelCostModel
from src.social_cost_model import SocialCostModel
from src.country_financial_aggregator import CountryFinancialAggregator
from src.financial_model import FinancialModel

class ResultCache:
    """Cache for (AdoptionModel, IncomeModel) by (state_id, area_id, area_type, tech_profile)."""
    def __init__(self):
        self._adopt = {}
        self._income = {}

    @staticmethod
    def _key(state, da, tech_key: str):
        return (state.stage_id, da.id, da.area_type, tech_key)

    def get_or_build(self, state, prev_state, growth, data_manager, demand_area, tech_df):
        tech_key = getattr(tech_df, "_cache_key", None) or f"k_{id(tech_df)}"
        k = self._key(state, demand_area, tech_key)
        if k not in self._adopt:
            adopt = AdoptionModel2_0(state, prev_state, growth, demand_area, data_manager, tech_df)
            adopt.run_simulation()
            income = IncomeModel2_0(state, demand_area, data_manager, adopt)
            income.run_simulation()
            self._adopt[k] = adopt
            self._income[k] = income
        return self._adopt[k], self._income[k]

class SimulationRunner:
    def __init__(self, simulation_plan, growth, data_manager, base_scenario, output_writer, logger=None, debug_exports=False):
        self.plan = simulation_plan
        self.growth = growth
        self.dm = data_manager
        self.base_scenario = base_scenario
        self.out = output_writer
        self.debug = debug_exports
        self.log = logger or logging.getLogger(__name__)
        self.cache = ResultCache()

    # ---------- API pública ----------
    def run(self):
        mixed_states, dam, demand_areas = self._prepare_inputs()
        prev_state = None

        for state in mixed_states:
            self.log.user("Processing state %s (Y=%s, S=%s)", state.stage_id, state.year, state.semester)
            state.calculate_cost_dep_variation(self.growth)

            # 1) Fase EL: ratios y despliegue
            el_ratios, total_el = self._phase_el_compute_ratios(state, prev_state, mixed_states, demand_areas)
            self._phase_el_deploy(state, prev_state, el_ratios, total_el, dam)

            # 2) Fase LPG: preparar no-electrificadas, ratios, despliegue + emisiones
            grouped_lpg = self._phase_lpg_flow(state, prev_state, mixed_states, dam)
            # 2.b)NUEVO: procesar áreas con LPG desplegado (resto fuels + social)
            self._phase_rest_for_lpg_deployed(state, prev_state, dam)

            # 3) Fase EL (post-deploy): costes/emisiones finales para electrificadas + resto fuels
            self._phase_el_finalize_costs_emissions(state, prev_state, mixed_states, dam)

            # 4) Fase resto fuels/social en no-LPG
            self._phase_rest_fuels_and_social(state, prev_state, dam)

            # 5) Agregado financiero por estado
            self._aggregate_financials_state(state, demand_areas)

            #prev_state = copy.deepcopy(state)
            prev_state = state.snapshot()

            

            # (Opcional) snapshot incremental del reporte
            self.out.render_progress(mixed_state=state)

        # 6) Exports finales y modelo financiero anualizado
        self._final_exports_and_financial(mixed_states, demand_areas)

    # ---------- Preparación ----------
    def _prepare_inputs(self):
        " Prepares mixed states and demand areas. "
        gen = MixedStateGenerator(self.plan, self.growth, self.base_scenario)
        mixed_states = gen.generate_mixed_states()
        self.log.user("Mixed states generated.")

        dam = DemandAreaManager(self.dm, base_path=config["path"]["output"], demandAreas_path=None)
        demand_areas = dam.load_demand_areas_from_config()
        demand_areas = dam.assign_preprocessed_data()
        self.log.user("Demand areas preprocessed and assigned.")
        return mixed_states, dam, demand_areas

    # ---------- Fase EL (pre-deploy) ----------
    def _phase_el_compute_ratios(self, state, prev_state, mixed_states, demand_areas):
        " Computes electricity area ratios for deployment. "
        tech_all = self.dm.get_dataframe("enriched_technologies")
        ratios, total = [], 0.0
        for da in demand_areas:
            state.initialize_demand_area(da.id)
            adopt, income = self.cache.get_or_build(state, prev_state, self.growth, self.dm, da, tech_all)
            el_model = ElectricityCostModel(state, prev_state, mixed_states, self.dm, da, adopt)
            el_model.run_simulation()
            ratios.extend(el_model.get_sorted_area_ratios())
        total += sum(a["demand"] for a in ratios)
        return ratios, total

    def _phase_el_deploy(self, state, prev_state, ratios, total_demand, dam):
        " Deploys electricity based on computed ratios. "
        sorted_areas = sorted(ratios, key=lambda x: x["ratio"])
        deploy = DeployElectricity(prev_state, state, self.growth, self.dm, sorted_areas, total_demand, dam)
        deploy.run_deployment()

    # ---------- Fase LPG ----------
    def _phase_lpg_flow(self, state, prev_state, mixed_states, dam):
        " Full LPG flow: prepare non-electrified, compute ratios, deploy, emissions. "
        non_el = state.get_not_electrified_areas()
        non_el_das = []
        tech_wo_el = Technologies.enriched_technologies_without_electricity(self.dm)

        for area_id, area_type in non_el:
            da = dam.get_demand_area_by_id_and_type(area_id, area_type)
            adopt, income = self.cache.get_or_build(state, prev_state, self.growth, self.dm, da, tech_wo_el)
            #adopt = AdoptionModel2_0(state, prev_state, self.growth, self.plan, da, self.dm, tech_wo_el); adopt.run_simulation()
            #income = IncomeModel2_0(state, da, self.dm, adopt); income.run_simulation()
            non_el_das.append(da)

        grouped = dam.group_areas_by_lpg_area(non_el_das)

        all_ratios, total = [], 0.0
        for lpg_area_id, area_types in grouped.items():
            areas = area_types["rural"] + area_types["urban"]
            lpg_model = LPGCostModel(state, prev_state, mixed_states, self.dm, lpg_area_id, areas, self.growth)
            lpg_model.run_simulation()
            if self.debug: self.out.debug_lpg_costs(lpg_model, state)
            all_ratios.extend(lpg_model.get_sorted_area_ratios())

        total += sum(a["demand"] for a in all_ratios)
        sorted_areas_lpg = sorted(all_ratios, key=lambda x: x["ratio"])
        deploy = LPGDeployModel(prev_state, state, self.growth, self.dm, sorted_areas_lpg, total)
        deploy.run_deployment()

        # Ajustes finales & emisiones por área desplegada
        for (lpg_area_id, area_type), _area in state.get_lpg_deployed_areas().items():
            cost_data = state.get_lpg_cost_parameters(lpg_area_id)
            cost_params, ratios = cost_data["cost_parameters"], cost_data["ratios"]
            #LPGCostModel.adjust_final_cost_lpg_from_parameters(cost_params, area_type, lpg_area_id)
            lpg_model.adjust_final_cost_lpg_from_parameters(cost_params, area_type, lpg_area_id)
            state.store_lpg_cost_parameters(lpg_area_id, cost_params, ratios)
            em = EmissionsLPG(state, self.dm, lpg_area_id, area_type, lpg_model); em.calculate_emissions()
            state.set_lpg_emissions(lpg_area_id, em)

        return grouped

    def _phase_rest_for_lpg_deployed(self, state, prev_state, dam):
        """Processes areas with LPG deployed: runs adoption/income, emissions, costs for non-electricity/gas fuels, and social cost."""
        
        deployed_lpg_areas = state.get_lpg_deployed_areas()  # dict { (lpg_area_id, area_type): area_obj } o similar
        if not deployed_lpg_areas:
            return

        # Desagrupar a DemandAreas individuales
        lpg_areas_ungrouped = dam.ungroup_areas_by_lpg_area(deployed_lpg_areas)

        tech_without_el_and_gas = Technologies.enriched_technologies_without_electricity_and_gas(self.dm)
        tech_wo_el = Technologies.enriched_technologies_without_electricity(self.dm)

        for da in lpg_areas_ungrouped:
            # Para el “resto” trabajamos con adopción/ingresos bajo perfil sin electricidad ni gas
            adopt, income = self.cache.get_or_build(state, prev_state, self.growth, self.dm, da, tech_wo_el)
            # adopt = AdoptionModel2_0(state, prev_state, self.growth, self.plan, da, self.dm, tech_without_electricity)
            # adopt.run_simulation()
            # income = IncomeModel2_0(state, da, self.dm, adopt)
            # income.run_simulation()

            # Emisiones de resto de fuels (sin EL ni GAS)
            rest_em = NonDeployEmissionsModel(state, self.dm, da, adopt, income, tech_without_el_and_gas)
            rest_em.run_simulation()

            # Costes de fuel/appliance para resto de fuels (sin electricidad)
            # (en tu código original aquí usabas tecnologies_without_electricity)
            rest_cost = ApplFuelCostModel(state, self.dm, da, adopt, income, tech_without_el_and_gas)
            rest_cost.run_simulation()

            # Coste social de esa área
            SocialCostModel(state, self.dm, da).run_simulation()


    # ---------- Fase EL (post-deploy): costes/emisiones + resto fuels ----------
    def _phase_el_finalize_costs_emissions(self, state, prev_state, mixed_states, dam):
        """ Finalizes electricity costs and emissions for electrified areas, and processes non-electricity/gas fuels. """
        electrified = state.get_electrified_areas()
        tech_wo_lpg = Technologies.enriched_tecnologies_without_gas(self.dm)

        # 1) adoption/income por parte electrificada (perfil: sin LPG)
        adopt_map, income_map, by_id = {}, {}, defaultdict(dict)
        for area_id, area_type in electrified:
            da = dam.get_demand_area_by_id_and_type(area_id, area_type)
            adopt, income = self.cache.get_or_build(state, prev_state, self.growth, self.dm, da, tech_wo_lpg)
            adopt_map[(da.id, da.area_type)] = adopt
            income_map[(da.id, da.area_type)] = income
            by_id[da.id][da.area_type] = da

        # 2) rural+urban juntos cuando existan ambas partes
        for aid, types in by_id.items():
            if "rural" in types and "urban" in types:
                da_r, da_u = types["rural"], types["urban"]
                joint = da_r.clone_or_merge_with(da_r, da_u)
                adopt, income = self.cache.get_or_build(state, prev_state, self.growth, self.dm, joint, tech_wo_lpg)
                el = ElectricityCostModel(state, prev_state, mixed_states, self.dm, joint, adopt)
                el.run_simulation(); el.adjust_final_cost_electricity()
                state.store_electricity_cost_parameters(joint.id, el.cost_parameters, ratios=el.ratios)
                em = EmissionsElectricity(state, self.dm, joint, el); em.calculate_emissions()
                state.set_electricity_emissions(joint.id, em)

                tech_wo_el_gas = Technologies.enriched_technologies_without_electricity_and_gas(self.dm)
                NonDeployEmissionsModel(state, self.dm, joint, adopt, income, tech_wo_el_gas).run_simulation()
                ApplFuelCostModel(state, self.dm, joint, adopt, income, tech_wo_lpg).run_simulation()
                SocialCostModel(state, self.dm, joint).run_simulation()
            else:
                da = types.get("rural") or types.get("urban")
                adopt = adopt_map[(da.id, da.area_type)]
                income = income_map[(da.id, da.area_type)]
                el = ElectricityCostModel(state, prev_state, mixed_states, self.dm, da, adopt)
                el.run_simulation(); el.adjust_final_cost_electricity()
                da.store_electricity_costs(el.cost_parameters)
                state.store_electricity_cost_parameters(da.id, el.cost_parameters, ratios=el.ratios)
                em = EmissionsElectricity(state, self.dm, da, el); em.calculate_emissions()
                state.set_electricity_emissions(da.id, em)

                tech_wo_el_gas = Technologies.enriched_technologies_without_electricity_and_gas(self.dm)
                NonDeployEmissionsModel(state, self.dm, da, adopt, income, tech_wo_el_gas).run_simulation()
                ApplFuelCostModel(state, self.dm, da, adopt, income, tech_wo_lpg).run_simulation()
                SocialCostModel(state, self.dm, da).run_simulation()

    # ---------- Fase resto fuels + social en no-LPG ----------
    def _phase_rest_fuels_and_social(self, state, prev_state, dam):
        """Processes non-LPG deployed areas: runs adoption/income, emissions, costs for non-electricity/gas fuels, and social cost."""
        non_lpg = state.get_not_lpg_deployed_areas()
        das = dam.ungroup_areas_by_lpg_area(non_lpg)
        tech_wo_el_gas = Technologies.enriched_technologies_without_electricity_and_gas(self.dm)
        tech_wo_lpg = Technologies.enriched_tecnologies_without_gas(self.dm)

        for da in das:
            adopt = AdoptionModel2_0(state, prev_state, self.growth, da, self.dm,tech_wo_el_gas); adopt.run_simulation()
            income = IncomeModel2_0(state, da, self.dm, adopt); income.run_simulation()
            NonDeployEmissionsModel(state, self.dm, da, adopt, income, tech_wo_el_gas).run_simulation()
            ApplFuelCostModel(state, self.dm, da, adopt, income, tech_wo_lpg).run_simulation()
            SocialCostModel(state, self.dm, da).run_simulation()

    # ---------- Agregado financiero por estado ----------
    def _aggregate_financials_state(self, state, demand_areas):
        """Aggregates financial data for the given state across all demand areas."""
        agg = CountryFinancialAggregator(state=state, data_manager=self.dm,
                                         demand_areas=demand_areas,
                                        #  simulation_plan=self.plan,
                                         growth_scenario=self.growth)
        agg.run()

    # ---------- Exports finales + modelo financiero anualizado ----------
    def _final_exports_and_financial(self, mixed_states, demand_areas):
        """Exports final reports and runs the annualized financial model."""
        # Resúmenes/TSV
        self.out.export_post_loop(mixed_states, demand_areas, self.dm)

        # Modelo financiero anualizado (incluye fix de merges)
        self.out.build_and_export_financial_model(mixed_states, self.dm, self.growth, debug=self.debug)
        self.log.user("Simulation completed and all outputs exported.")
