import logging
from src.combined_plan import CombinedPlan
from src.state import State
from src.deployment_plan import DeploymentPlan
from src.pricing_plan import PricePlan

class CombinedPlanManager:
    def __init__(self, data_manager, base_scenario):
        self.data_manager = data_manager
        self.base_scenario = base_scenario
        self.logger = logging.getLogger("CombinedPlanManager")
        self.combined_plans = self._load_combined_plans()

    
    def _load_combined_plans(self):
        """
        Load CombinedPlan objects from Plan_config and create:
        - One fictitious base State per CombinedPlan using base_scenario.
        - One 'policy' State per row in Plan_config (Year, DepPlan, PricePlan).

        These States will later be transformed into mixed semester states
        by generate_mixed_states.
        """
        combined_plans = {}
        try:
            config_df = self.data_manager.get_dataframe("Plan_config")

            if config_df is None or config_df.empty:
                self.logger.warning("Plan_config dataframe is empty. No combined plans created.")
                return {}

            # Ensure deterministic ordering: by CombinedPlan, Year, Stage_id
            config_df = config_df.sort_values(["CombinedPlan_id", "Year", "Stage_id"])

            # --- Base scenario information from config.yaml ---
            base_dep_id = self.base_scenario.get("DepPlan_id")
            base_price_id = self.base_scenario.get("PricePlan_id")
            base_stage_id = self.base_scenario.get("stage_id", 0)

            # If base year is not specified, use the minimum Year from Plan_config
            if "year" in self.base_scenario:
                base_year = int(self.base_scenario["year"])
            else:
                base_year = int(config_df["Year"].min())

            # Try to recover human-readable names for the base plans from Plan_config
            base_dep_name = None
            base_price_name = None

            if base_dep_id is not None:
                dep_rows = config_df[config_df["DepPlan_id"] == base_dep_id]
                if not dep_rows.empty:
                    base_dep_name = str(dep_rows.iloc[0]["DepPlan_Name"])

            if base_price_id is not None:
                price_rows = config_df[config_df["PricePlan_id"] == base_price_id]
                if not price_rows.empty:
                    base_price_name = str(price_rows.iloc[0]["PricePlan_Name"])

            # Fallback names in case they do not appear explicitly in Plan_config
            if base_dep_name is None:
                base_dep_name = f"BaseDepPlan_{base_dep_id}" if base_dep_id is not None else "BaseDepPlan"
            if base_price_name is None:
                base_price_name = f"BasePricePlan_{base_price_id}" if base_price_id is not None else "BasePricePlan"

            # To avoid creating more than one base State per CombinedPlan
            base_created_for_cp = set()

            # --- Build CombinedPlan objects ---
            for _, row in config_df.iterrows():
                cp_id = int(row["CombinedPlan_id"])
                cp_name = str(row["CombinedPlan_Name"])

                if cp_id not in combined_plans:
                    combined_plans[cp_id] = CombinedPlan(cp_id, cp_name)
                cp = combined_plans[cp_id]

                # 1) Create fictitious BASE STATE once per CombinedPlan
                if (
                    cp_id not in base_created_for_cp
                    and base_dep_id is not None
                    and base_price_id is not None
                ):
                    base_state = State(base_stage_id, base_year)

                    dep_plan_base = DeploymentPlan(base_dep_id, base_dep_name)
                    price_plan_base = PricePlan(base_price_id, base_price_name)

                    base_state.set_deployment_plan(dep_plan_base)
                    base_state.set_price_plan(price_plan_base)

                    cp.add_state(base_state)
                    base_created_for_cp.add(cp_id)

                # 2) Create a "policy" State for this Plan_config row
                stage_id = int(row["Stage_id"])
                year = int(row["Year"])

                dep_plan_id = int(row["DepPlan_id"])
                price_plan_id = int(row["PricePlan_id"])

                dep_plan = DeploymentPlan(dep_plan_id, str(row["DepPlan_Name"]))
                price_plan = PricePlan(price_plan_id, str(row["PricePlan_Name"]))

                state = State(stage_id, year)
                state.set_deployment_plan(dep_plan)
                state.set_price_plan(price_plan)

                cp.add_state(state)

        except Exception as e:
            self.logger.critical(f"Error loading combined plans: {e}", exc_info=True)
            raise

        # Enrich with additional plan tables (Plan_depFuels, Plan_fuelPriceMult, etc.)
        self._enrich_plans(combined_plans)
        return combined_plans



    def _enrich_plans(self, combined_plans):
        """Enriches each DeploymentPlan and PricePlan with additional details from other DataFrames."""
        # Ejemplo: obtener DataFrames con detalles y asignarlos a los planes
        dep_fuels_df = self.data_manager.get_dataframe("Plan_depFuels")
        dep_fuels_targ_df = self.data_manager.get_dataframe("Plan_depFuelsTarg")
        fuel_max_cap_df = self.data_manager.get_dataframe("Plan_fuelMaxCap")
        fuel_price_mult_df = self.data_manager.get_dataframe("Plan_fuelPriceMult")
        app_max_cap_df = self.data_manager.get_dataframe("Plan_appMaxCap")
        app_price_mult_df = self.data_manager.get_dataframe("Plan_appPriceMult")
        
        for cp in combined_plans.values():
            for state in cp.states:
                # Enriquecimiento para DeploymentPlan:
                dep_id = state.deployment_plan.plan_id
                deploy_details = {
                    # Fuel reference: se asigna la tabla completa ya que los deploy fuels (con Fuel_id, Ref_capacity y Margin)
                    # son comunes y no dependen de un DepPlan_id (ya que los nombres pueden variar).
                    'fuel_reference': dep_fuels_df.to_dict(orient='records') if dep_fuels_df is not None else None,
                    # Si la tabla de deploy fuels target tiene DepPlan_id, se filtra:
                    'fuels_target': (dep_fuels_targ_df[dep_fuels_targ_df['DepPlan_id'] == dep_id]
                                    .to_dict(orient='records')
                                    if dep_fuels_targ_df is not None and 'DepPlan_id' in dep_fuels_targ_df.columns else None),
                    # Capacidad máxima de fuels según el plan de deploy
                    'fuel_max_cap': (fuel_max_cap_df[fuel_max_cap_df['DepPlan_id'] == dep_id]
                                    .to_dict(orient='records')
                                    if fuel_max_cap_df is not None else None),
                    # Capacidad máxima de appliances según el plan de deploy
                    'appliances_max_cap': (app_max_cap_df[app_max_cap_df['DepPlan_id'] == dep_id]
                                        .to_dict(orient='records')
                                        if app_max_cap_df is not None else None)
                }
                state.deployment_plan.enrich(deploy_details)
                
                # Enriquecimiento para PricePlan:
                price_id = state.price_plan.plan_id
                price_details = {
                    # Precio para fuels (ejemplo: Electricity, LPG, Biogas, etc.)
                    'fuel_price': (fuel_price_mult_df[fuel_price_mult_df['PricePlan_id'] == price_id]
                                .to_dict(orient='records')
                                if fuel_price_mult_df is not None else None),
                    # Precio para appliances (ejemplo: Electric_0, Electric_1, etc.)
                    'app_price': (app_price_mult_df[app_price_mult_df['PricePlan_id'] == price_id]
                                .to_dict(orient='records')
                                if app_price_mult_df is not None else None)
                }
                state.price_plan.enrich(price_details)

    def get_combined_plan(self, cp_id):
        return self.combined_plans.get(cp_id)

    def iterate_combined_plans(self):
        for cp in self.combined_plans.values():
            yield cp