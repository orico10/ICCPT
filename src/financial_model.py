from collections import defaultdict
import logging
import os
from typing import Dict, Any, List, Tuple
import pandas as pd


class FinancialModel:
    def __init__(self, mixed_states, data_manager, growth_scenario):
        self.mixed_states = mixed_states
        self.data_manager = data_manager
        self.growth_scenario = growth_scenario
        #self.simulation_plan = simulation_plan
        self.growth_info = self.growth_scenario.get_info()
        self.logger = logging.getLogger(__name__)

        self.electric_cost_breakdown = data_manager.get_dataframe("Electricity_costBreakdown")
        self.lpg_cost_breakdown = data_manager.get_dataframe("LPG_costBreakdown")
        self.fuel_id_to_name = dict(zip(
            data_manager.get_dataframe("Cooking_fuels")["Fuel_id"],
            data_manager.get_dataframe("Cooking_fuels")["Fuel_name"]
        ))
    

        self.model_data_by_state: Dict[str, Dict[str, Any]] = {}
        self.capex_semester_output: List[Dict[str, Any]] = []
        self.opex_semester_output: List[Dict[str, Any]] = []
        self.full_semester_structure = {}
        self.semester_checkpoints: List[Tuple[str, int]] = []


    # def build_all(self):

    #     lifetime_el_map = self._extract_lifetime(self.electric_cost_breakdown)
    #     discount_el_map = self._extract_discount(self.electric_cost_breakdown)

    #     lifetime_lpg_transport = self._extract_lpg_lifetime_transport(self.lpg_cost_breakdown)
    #     lifetime_lpg_process = self._extract_lpg_lifetime_process(self.lpg_cost_breakdown)
    #     discount_lpg_map = self._extract_lpg_discount(self.lpg_cost_breakdown)

    #     years_el_map = self._extract_years(self.electric_cost_breakdown)
    #     years_lpg_map = self._extract_years(self.lpg_cost_breakdown)
       

    #     #for ms in self.mixed_states:
    #     for i, ms in enumerate(self.mixed_states):
    #         # Solo hay previo si i > 0
    #         prev_state = self.mixed_states[i-1] if i > 0 else None  
    #         #self.generate_complete_semester_structure(self.growth_scenario)
    #         state_name = ms.stage_id   #ms["state_name"]
    #         year = ms.year      #ms["year"]
    #         print(f"Processing mixed state: {ms.stage_id}")

    #         # for state in self.simulation_plan.states:
    #         #     print(f"State ID: {state.stage_id}")



    #         # state_obj = next((s for s in self.simulation_plan.states if s.stage_id == state_name), None)
    #         # state_obj = next(
    #         #     (s for s in self.simulation_plan.states
    #         #     if s.deployment_plan is not None
    #         #     and s.deployment_plan.plan_id == int(state_name)),
    #         #     None
    #         # )
    #         # target_plan_id = int(getattr(getattr(ms, "deployment_plan", None), "plan_id", -1))
    #         # target_stage_id = int(getattr(ms, "stage_id", -1))

    #         # state_obj = next(
    #         #     (s for s in self.simulation_plan.states
    #         #     if int(getattr(getattr(s, "deployment_plan", None), "plan_id", -2)) == target_plan_id
    #         #     and int(getattr(s, "stage_id", -3)) == target_stage_id),
    #         #     None
    #         # )



    #         # if state_obj is None:
    #         #     self.logger.warning(f"State '{state_name}' not found in simulation plan.")
    #         #     continue
    #         # print(f"Match found for state {state_name}: {state_obj}")

    #         financial_params = ms.get_financial_results() #state_obj.get_financial_results() if state_obj else ms.get_financial_results()
    #         fuel_id_el = 1  # o el que corresponda a electricidad
    #         fuel_id_lpg = 2  # o el que corresponda a LPG

    #         dep_cost_variation_el = ms.get_dep_cost_variation(fuel_id_el)
    #         dep_cost_variation_lpg = ms.get_dep_cost_variation(fuel_id_lpg)

    #         # Extraer crecimiento para electricidad
    #         growth_el_generation = dep_cost_variation_el.get("Process", 0.0)
    #         growth_el_distribution = dep_cost_variation_el.get("Transport", 0.0)

    #         # Extraer crecimiento para LPG
    #         growth_lpg_process = dep_cost_variation_lpg.get("Process", 0.0)
    #         growth_lpg_transport = dep_cost_variation_lpg.get("Transport", 0.0)
    #         growth_lpg_molecule = dep_cost_variation_lpg.get("Molecule", 0.0)


    #         result = {}
    #         #prev_state_obj = self.simulation_plan.get_previous_state(state_obj)
    #         #prev_state_obj = self.simulation_plan.get_previous_state(ms)
    #         prev_state_obj = prev_state

    #         result['Electricity'] = self._project_block(
    #             ms, financial_params.aggregated_electricity_costs,
    #             years_el_map, lifetime_el_map, discount_el_map, 
    #             process_growth=growth_el_generation,
    #             transport_growth=growth_el_distribution, 
    #             prev_state=prev_state_obj
    #         )
            
    #         # result['EDemand'] = self._project_block(
    #         #     ms, financial_params.aggregated_edemand_costs,
    #         #     years_el_map, lifetime_el_map, discount_el_map
    #         # )
    #         result['LPG'] = self._project_block(
    #             ms,
    #             financial_params.aggregated_lpg_costs,
    #             years_lpg_map, lifetime_lpg_process, discount_lpg_map,
    #             is_lpg=True,
    #             lifetime_process_map=lifetime_lpg_process,
    #             lifetime_transport_map=lifetime_lpg_transport,
    #             process_growth=growth_lpg_process,
    #             transport_growth=growth_lpg_transport,
    #             molecule_growth=growth_lpg_molecule, 
    #             prev_state=prev_state_obj
    #         )

    #         result['Subsidies_Taxes'] = {
    #             'Appliances': financial_params.aggregated_rest_subsidies_or_taxes_opex.appliances,
    #             'Fuels': financial_params.aggregated_rest_subsidies_or_taxes_opex.fuels
    #         }

    #         soc = financial_params.aggregated_social_costs
    #         result['Social_Costs'] = {
    #             'Health': soc.health_costs,
    #             'Gender': soc.gender_costs,
    #             'Deforestation': soc.deforestation_costs,
    #             'Emissions': soc.emissions_costs
    #         }

    #         result['Price_Growth'] = {
    #             'Appliances': self.growth_info.get('App_Retail_Price'),
    #             'Fuels': self.growth_info.get('Fuel_Retail_Price'),
    #             'Dep_Fuel_Cost_Variation': self.growth_info.get('Dep_Fuel_Cost_Variation')
    #         }

    #         result['Income_Tariff'] = financial_params.income_tariff.fuels

    #         # Obtener todos los appliance IDs presentes en el plan
    #         appliance_growth_dict = financial_params.average_growth_calculation_appliances.appliances
            
    #         # Expandir a todos los appliances y estados (0, 1, 2)
    #         appliance_growth_full = {}
    #         # appliance_growth_dict debe tener la forma: { fuel_id: { appliance_id: weight } }
    #         for fuel_id, appliance_map in appliance_growth_dict.items():
    #             appliance_growth_full[fuel_id] = dict(appliance_map)  # copia directa

    #         result['Appliance_Growth'] = appliance_growth_full
    #         self.model_data_by_state[state_name] = result
                        


    #         #self.model_data_by_state[state_name] = result
    def build_all(self):

        # --- 0) Inicializar estructura por estado ---
        self.model_data_by_state = {}

        # --- 1) Extraer parámetros generales de costes / años / discount ---
        lifetime_el_map      = self._extract_lifetime(self.electric_cost_breakdown)
        discount_el_map      = self._extract_discount(self.electric_cost_breakdown)

        lifetime_lpg_transport = self._extract_lpg_lifetime_transport(self.lpg_cost_breakdown)
        lifetime_lpg_process   = self._extract_lpg_lifetime_process(self.lpg_cost_breakdown)
        discount_lpg_map       = self._extract_lpg_discount(self.lpg_cost_breakdown)

        years_el_map  = self._extract_years(self.electric_cost_breakdown)
        years_lpg_map = self._extract_years(self.lpg_cost_breakdown)


        #Acumulador de pesos globales de incomes appliance/fuel en base a todos los estados
        global_appliance_weights = self._compute_global_appliance_weights() 

        # --- 2) Recorrer mixed_states en orden, con acceso al estado previo ---
        for i, ms in enumerate(self.mixed_states):
            prev_state = self.mixed_states[i - 1] if i > 0 else None

            state_name = str(ms.stage_id)  # importante: string para que case con la col "State" en los DF
            year = ms.year
            self.logger.info(f"[BUILD_ALL] Processing mixed state: {state_name} (year={year})")

            # 2.1) Resultados financieros agregados del estado
            financial_params = ms.get_financial_results()
            if financial_params is None:
                self.logger.warning(f"[BUILD_ALL] State '{state_name}' sin financial_results. Se omite.")
                continue

            # IDs de fuel (ajusta si en tu modelo son otros)
            fuel_id_el  = 1  # electricidad
            fuel_id_lpg = 2  # LPG

            # 2.2) Variación de costes dependiente del plan (growth por fuel)
            dep_cost_variation_el  = ms.get_dep_cost_variation(fuel_id_el)  or {}
            dep_cost_variation_lpg = ms.get_dep_cost_variation(fuel_id_lpg) or {}

            # Electricidad: growth en generación y distribución
            growth_el_generation  = dep_cost_variation_el.get("Process",   0.0)
            growth_el_distribution = dep_cost_variation_el.get("Transport", 0.0)

            # LPG: growth en process, transport y molecule
            growth_lpg_process   = dep_cost_variation_lpg.get("Process",   0.0)
            growth_lpg_transport = dep_cost_variation_lpg.get("Transport", 0.0)
            growth_lpg_molecule  = dep_cost_variation_lpg.get("Molecule",  0.0)

            result = {}

            # --- 3) Proyección de bloques de costes ---

            # 3.1) Electricidad (ElecTotal, EDemand, etc. según lo que lleve aggregated_electricity_costs)
            result["Electricity"] = self._project_block(
                ms,
                financial_params.aggregated_electricity_costs,
                years_el_map,
                lifetime_el_map,
                discount_el_map,
                process_growth=growth_el_generation,
                transport_growth=growth_el_distribution,
                prev_state=prev_state,
            )

            # Si en algún momento quieres proyectar EDemand explícito, descomenta y adapta:
            # result["EDemand"] = self._project_block(
            #     ms,
            #     financial_params.aggregated_edemand_costs,
            #     years_el_map,
            #     lifetime_el_map,
            #     discount_el_map,
            #     prev_state=prev_state,
            # )

            # 3.2) LPG
            result["LPG"] = self._project_block(
                ms,
                financial_params.aggregated_lpg_costs,
                years_lpg_map,
                lifetime_lpg_process,
                discount_lpg_map,
                is_lpg=True,
                lifetime_process_map=lifetime_lpg_process,
                lifetime_transport_map=lifetime_lpg_transport,
                process_growth=growth_lpg_process,
                transport_growth=growth_lpg_transport,
                molecule_growth=growth_lpg_molecule,
                prev_state=prev_state,
            )

            # --- 4) Subsidios / Taxes ---
            agg_subs = financial_params.aggregated_rest_subsidies_or_taxes_opex
            result["Subsidies_Taxes"] = {
                "Appliances": agg_subs.appliances,
                "Fuels": agg_subs.fuels,
            }

            # --- 5) Costes sociales ---
            soc = financial_params.aggregated_social_costs
            result["Social_Costs"] = {
                "Health": soc.health_costs,
                "Gender": soc.gender_costs,
                "Deforestation": soc.deforestation_costs,
                "Emissions": soc.emissions_costs,
            }

            # --- 6) Info de crecimiento de precios desde growth_scenario ---
            result["Price_Growth"] = {
                "Appliances": self.growth_info.get("App_Retail_Price"),
                "Fuels": self.growth_info.get("Fuel_Retail_Price"),
                "Dep_Fuel_Cost_Variation": self.growth_info.get("Dep_Fuel_Cost_Variation"),
            }

            # --- 7) Ingresos por tarifa ---
            result["Income_Tariff"] = financial_params.income_tariff.fuels

            # --- 8) Pesos de crecimiento por appliances (Appliance_Growth) ---
            # financial_params.average_growth_calculation_appliances.appliances
            # debe tener la forma: { fuel_id: { appliance_id: weight } }
            appl_struct = getattr(financial_params, "average_growth_calculation_appliances", None)
            raw_appl = getattr(appl_struct, "appliances", {}) if appl_struct is not None else {}

            # Normalizamos tipos: claves como enteros, valores como float
            appliance_growth_full = {}
            for fuel_id, appliance_map in (raw_appl or {}).items():
                if not appliance_map:
                    continue
                f_id_int = int(fuel_id)
                appliance_growth_full[f_id_int] = {
                    int(app_id): float(w or 0.0)
                    for app_id, w in appliance_map.items()
                }

            result["Appliance_Growth"] = global_appliance_weights#appliance_growth_full

            # Log fuerte para ver qué entra en el modelo
            self.logger.warning(
                f"[BUILD_ALL] State {state_name}: Appliance_Growth = {appliance_growth_full}"
            )

            # --- 9) Guardar en model_data_by_state ---
            self.model_data_by_state[state_name] = result


            
        


    def _project_block(self, ms, costs, years_map, lifetime_map, discount_map,
                       is_lpg=False, lifetime_process_map=None, lifetime_transport_map=None, process_growth=0.0, transport_growth=0.0, molecule_growth=0.0, prev_state=None):
        state_name = ms.stage_id   #ms['state_name']
        year =ms.year   #ms['year']
        base_vals = costs.__dict__
        accumm_capx = {}

        block = {
            'State': state_name,
            'Year': year,
            'Lifetime': lifetime_map,
            'Discount_Rate': discount_map,
            'Data': {}
        }
        base_vals_prev = {}

        if prev_state:
            try:
                prev_costs = prev_state.get_financial_results()
                prev_block = (
                    prev_costs.aggregated_lpg_costs if is_lpg else prev_costs.aggregated_electricity_costs
                )
                base_vals_prev = prev_block.__dict__
            except Exception as e:
                self.logger.warning(f"Error accediendo al estado anterior para {state_name}: {e}")


        for key, capex in base_vals.items():
            tech = self._identify_technology(key)

            if key.upper() == "OFFGRID_PERCENTAGE":
                block['Data'][key] = {
                    'Technology': tech,
                    'Base prices M$/yr': capex,
                    'Inc/Annual M$/yr': "-",
                    'Annuity': "-",
                    'Accumulated': "-",
                    'Growth_p.u': "-",
                    'Price_Mult_App': "-",
                    'Price_Mult_Fuel': "-",
                    'Lifetime': "-",
                    'Discount': "-"
                }
                continue

            # --- Lifetime ---
            if is_lpg:
                if "PROCESS" in key.upper():
                    lifetime = lifetime_process_map.get(tech, 15.0)
                elif "TRANSPORT" in key.upper():
                    lifetime = lifetime_transport_map.get(tech, 10.0)
                else:
                    lifetime = lifetime_map.get(tech, 15.0)
            else:
                if key.upper().startswith("E_COOKING"):
                    p_og = getattr(costs, "OFFGRID_percentage", 0.0)
                    lifetime_og = lifetime_map.get("StAloneS", 25.0)
                    lifetime_grid = lifetime_map.get("Grid", 25.0)
                    lifetime = p_og * lifetime_og + (1 - p_og) * lifetime_grid
                else:
                    lifetime = lifetime_map.get(tech, 25.0)
           

            # --- Discount ---
            if not is_lpg and key.upper().startswith("E_COOKING"):
                p_og = getattr(costs, "OFFGRID_percentage", 0.0)
                d_rate_og = discount_map.get("StAloneS", 0.10)
                d_rate_grid = discount_map.get("Grid", 0.10)
                discount = p_og * d_rate_og + (1 - p_og) * d_rate_grid
            else:
                discount = discount_map.get(tech, 0.10)

            # --- Growth ---
            if is_lpg:
                if "PROCESS" in key.upper():
                    growth_capex = process_growth
                elif "TRANSPORT" in key.upper():
                    growth_capex = transport_growth
                elif "MOLECULE" in key.upper() or "IMPORT" in key.upper():
                    growth_capex = molecule_growth
                else:
                    growth_capex = (process_growth + transport_growth + molecule_growth) / 3.0
            else:
                if "GRID" in key.upper() or "MICROG" in key.upper() or "OFFGRID" in key.upper():
                    growth_capex = transport_growth
                else:
                    growth_capex = process_growth

            # --- Base multipliers ---
            scenario_name = self.growth_scenario.scenario_name
            #price_mult_app = self.growth_info.get('GrowthPat_Name' == scenario_name).get('App_Retail_Price', {})
            #price_mult_fuel = self.growth_info.get('GrowthPat_Name' == scenario_name).get('Fuel_Retail_Price', {})

            capex_structure = self._generate_capex_semester_structure()

            # --- Annuity logic: only CAPEX ---
            if key.upper().endswith("CAPEX"):
                if key in base_vals_prev:
                    # prev_capex = base_vals_prev[key]
                    # inc_annual = (capex - prev_capex) * (1 + growth_capex)
                    # annuity_input = inc_annual
                    capex_base = base_vals_prev[key]
                    prev_accum = accumm_capx.get(key, capex_base)
                    inc_annual = (capex - prev_accum) * (1 + growth_capex)
                    annuity_input = inc_annual 
                    #accum = annuity
                    accumm_capx[key] = prev_accum + inc_annual
                else:
                    inc_annual = "-"
                    annuity_input = capex
                annuity = self._get_annuity(annuity_input, lifetime, discount)
                accum = annuity
                # # ✅ CAPEX por semestre (ya tienes annuity y lifetime)
                # state_base = (year, 1) if ms.semester == 1 else (year, 2)
                # capex_semester_values = self._calculate_capex_per_semester(
                #     key=key,
                #     base_annuity=annuity,
                #     lifetime=lifetime,
                #     state_base=state_base,
                #     tech_type=tech,
                #     offgrid_share=getattr(costs, "OFFGRID_percentage", 0.0)
                # )
            else:
                inc_annual = "-"
                annuity = "-" #self._get_annuity(capex, lifetime, discount)
                accum = "-"

            accum = annuity

            # --- Final assignment ---
            block['Data'][key] = {
                'Technology': tech,
                'Base prices M$/yr': capex,
                'Inc/Annual M$/yr': inc_annual,
                'Annuity': annuity,
                'Accumulated': accum,
                'Growth_p.u': growth_capex,
                #'Price_Mult_App': price_mult_app,
                #'Price_Mult_Fuel': price_mult_fuel,
                'Lifetime': lifetime,
                'Discount': discount
            }
            




        return {
                'Years_Map': years_map,
                'Mixed_State': ms,
                'Block_Data': {year: block}
        }

    def _identify_technology(self, key: str) -> str:
        key = key.upper()
        if "OFFGRID" in key or "STALONES" in key:
            return "StAloneS"
        elif "MICROG" in key:
            return "MicroG"
        elif "UPS" in key or "UPSTREAM" in key:
            return "Upstream"
        elif "LOCAL" in key:
            return "Local"
        elif "GRID" in key:
            return "Grid"
        else:
            return "Cooking"


    
    def _get_annuity(self, capex, lifetime, discount): # Suma de VP de flujos descontados(no es la fórmula clásica de annuities)
        if discount <= 0 or lifetime <= 0:
            return capex / lifetime if lifetime > 0 else 0.0
        r, n = discount, lifetime
        return (capex / r) * (1 - (1 / (1 + r) ** n))


    def _extract_years(self, df: pd.DataFrame) -> Dict[str, int]:
        try:
            row = df[df["Data"] == "Years"].iloc[0]
            return {col: int(row[col]) for col in row.index if col.startswith("Col")}
        except Exception:
            return {}

    def _extract_lifetime(self, df: pd.DataFrame) -> Dict[str, float]:
        row = df[df["Data"] == "Lifetime"]
        if row.empty:
            return {}
        return row.iloc[0, 1:].astype(float).to_dict()

    def _extract_discount(self, df: pd.DataFrame) -> Dict[str, float]:
        row = df[df["Data"] == "Discount_rate"]
        if row.empty:
            return {}
        return row.iloc[0, 1:].astype(float).to_dict()

    def _extract_lpg_lifetime_transport(self, df: pd.DataFrame) -> Dict[str, float]:
        row = df[df["Data"] == "Lifetime_transport"]
        if row.empty:
            return {}
        return row.iloc[0, 1:].astype(float).to_dict()

    def _extract_lpg_lifetime_process(self, df: pd.DataFrame) -> Dict[str, float]:
        row = df[df["Data"] == "Lifetime_process"]
        if row.empty:
            return {}
        return row.iloc[0, 1:].astype(float).to_dict()

    def _extract_lpg_discount(self, df: pd.DataFrame) -> Dict[str, float]:
        row = df[df["Data"] == "Discount_rate"]
        if row.empty:
            return {}
        return row.iloc[0, 1:].astype(float).to_dict()
    
    def export_capex_semester_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.capex_semester_output)
    
    
    def _generate_capex_semester_structure(self) -> pd.DataFrame:
        """
        Generate the CAPEX structure Capex_Past, Capex_P1, ..., Capex_Pn.
        Logic:
        - Capex_Past → from first real state (sem 1) to before the first real state with sem 2.
        - Capex_Pi → from sem 2 of a real state to sem 1 of the next.
        """
        try:
            semester_data = sorted(self.full_semester_structure.items())  # [(year, semester), metadata]

            #real_states = sorted(self.mixed_states, key=lambda s: (s.year, s.semester))
            real_states = sorted(self.mixed_states, key=lambda s: (s.year, self.convert_semester(s.semester)))
            checkpoints = [(s.year, self.convert_semester(s.semester)) for s in real_states]
            #checkpoints = [(s.year, self.convert_semester(s.semester)) for s in real_states]
            real_sem2_states = [s for s in real_states if self.convert_semester(s.semester) == 2]

            capex_ranges = []

            # 1. Capex_Past desde (year, 1) del primer estado real hasta el segundo estado real 
            if len(real_states) >= 1:
                first = real_states[0]
                past_end = (real_states[1].year, self.convert_semester(real_states[1].semester)) if len(real_states) > 1 else (9999, 1)

                capex_ranges.append(("Capex_Past", (first.year, self.convert_semester(first.semester)), past_end))

            # 2. Capex_Pi para cada real con semester == 2
            for i, st in enumerate(real_sem2_states):
                start = (st.year, self.convert_semester(st.semester))  # for sure = 2
                if i + 1 < len(real_sem2_states):
                    next_real = real_sem2_states[i + 1]
                    end = (next_real.year, self.convert_semester(next_real.semester))  # = 2
                else:
                    end = (9999, 1)
                label = f"Capex_P{i + 1}"
                capex_ranges.append((label, start, end))


            # Extraer etiquetas únicas
            period_labels = [label for label, _, _ in capex_ranges]

            # Construcción de filas
            # Construcción de filas
            rows = []
            for (year, semester), metadata in semester_data:
                is_real = (year, semester) in checkpoints
                #state_name = next((s.stage_id for s in real_states if (s.year, s.semester) == (year, semester)), f"no_name_{year}_{semester}")
                state_name = next(
                    (s.stage_id for s in real_states
                    if (s.year, self.convert_semester(s.semester)) == (year, semester)),
                    f"no_name_{year}_{semester}"
                )

                # Determinar PeriodLabel
                period_label = None
                for label, start, end in capex_ranges:
                    if start <= (year, semester) < end:
                        period_label = label
                        break

                row = {
                    "State": state_name,
                    "Year": year,
                    "Semester": semester,
                    "IsReal": is_real,
                    "PeriodLabel": period_label,
                    #"InfraRate": metadata.get("infra_rate", None),
                    #"TimeSinceBase": metadata.get("time_since_base", None),
                    #"Growth": metadata.get("growth", {}),
                    "CAPEX_Semester_M$": None,
                }

                # Marcar como True solo la columna del período actual
                for label, start, end in capex_ranges:
                    row[label] = start <= (year, semester) < end

                rows.append(row)


            #return pd.DataFrame(rows)
            df = pd.DataFrame(rows)

            # Añadir columnas Trail_<label> para cada periodo excepto el último
            #df = pd.DataFrame(rows)

            # Añadir columnas Trail_<label> para cada periodo excepto el último
            for i, (label, start, end) in enumerate(capex_ranges[:-1]):  # ignorar el último
                trail_col = f"Trail_{label}"
                df[trail_col] = False
                for idx, row in df.iterrows():
                    year_sem = (row["Year"], row["Semester"])
                    if year_sem >= end:
                        df.at[idx, trail_col] = True

            return df



        except Exception as e:
            self.logger.error(f"Error generando estructura CAPEX: {e}")
            return pd.DataFrame()



    def _generate_opex_semester_structure(self) -> pd.DataFrame:
        try:
            semester_data = sorted(self.full_semester_structure.items())  # [((y,s), meta)]
            real_states = sorted(self.mixed_states, key=lambda s: (s.year, self.convert_semester(s.semester)))
            checkpoints = [(s.year, self.convert_semester(s.semester)) for s in real_states]

            opex_ranges = []
            if real_states:
                first_y = real_states[0].year

            rows = []
            for (year, semester), meta in semester_data:
                is_real = (year, semester) in checkpoints
                state_name = next(
                    (s.stage_id for s in real_states
                    if (s.year, self.convert_semester(s.semester)) == (year, semester)),
                    f"no_name_{year}_{semester}"
                )

                if year == first_y and semester in (1, 2):
                    period_label = "Opex_Past"
                    flags = {"Opex_Past": True, "Opex_Fut": False}
                else:
                    period_label = "Opex_Fut"
                    flags = {"Opex_Past": False, "Opex_Fut": True}

                row = {
                    "State": state_name, "Year": year, "Semester": semester,
                    "IsReal": is_real, "PeriodLabel": period_label,
                    "OPEX_Semester_M$": None,
                    "Opex_Past": flags["Opex_Past"], "Opex_Fut": flags["Opex_Fut"],
                }
                rows.append(row)

            return pd.DataFrame(rows)

        except Exception as e:
            self.logger.error(f"Error generando estructura OPEX: {e}")
            return pd.DataFrame()


    def convert_semester(self,semester_str):
        if semester_str == 'first':
            return 1
        elif semester_str == 'second':
            return 2
        else:
            raise ValueError(f"Semester desconocido: {semester_str}")

    
        
    def generate_complete_semester_structure(self, simulation_growth_scenario):
        """
        Generate a structure of all semesters (real and intermediate) between states.
        Calculates accumulated growth and infrastructure rate for each.
        """
        try:
            base_year = simulation_growth_scenario.base_year
            scenario_name = simulation_growth_scenario.scenario_name
            dep_fuel_cost_var = simulation_growth_scenario.dep_fuel_cost_var

            fuel_ids = [1, 2]  # 1 = electricidad, 2 = LPG

            # 1. Ordenar los estados reales
            sorted_states = sorted(self.mixed_states, key=lambda s: (s.year, self.convert_semester(s.semester)))

            # 2. Extraer tasas de crecimiento por fuel
            fuel_growth_rates = {}
            for fuel_id in fuel_ids:
                record = next(
                    (r for r in dep_fuel_cost_var
                    if r.get('Fuel_id') == fuel_id and r.get('GrowthPat_Name') == scenario_name),
                    None
                )
                if record is None:
                    fuel_growth_rates[fuel_id] = {'Process': 0.0, 'Transport': 0.0, 'Molecule': 0.0}
                else:
                    fuel_growth_rates[fuel_id] = {
                        'Process': record.get('Process', 0.0),
                        'Transport': record.get('Transport', 0.0),
                        'Molecule': record.get('Molecule', 0.0),
                    }

            # 3. Generar todos los semestres intermedios
            all_semesters = []
            for idx, state in enumerate(sorted_states[:-1]):
                next_state = sorted_states[idx + 1]
                year, semester = state.year, self.convert_semester(state.semester)#state.semester
                end_year, end_semester = next_state.year, self.convert_semester(next_state.semester)#next_state.semester

                # Generar semestres hasta el siguiente estado (inclusive)
                while (year, semester) <= (end_year, end_semester):
                    all_semesters.append((year, semester))
                    # avanzar semestre
                    if semester == 1:
                        semester = 2
                    else:
                        semester = 1
                        year += 1

            # Asegurar que el último estado esté incluido
            #all_semesters.append((sorted_states[-1].year, sorted_states[-1].semester))
            last_year = sorted_states[-1].year
            last_semester = self.convert_semester(sorted_states[-1].semester)
            all_semesters.append((last_year, last_semester))

            all_semesters = sorted(set(all_semesters))

            

            #4. Calcular crecimiento acumulado y tasas de infraestructura
            semester_data = {}
            total_semesters = len(all_semesters)
            first = True
            last_checkpoint_idx = 0
            last_infra_rate = 0.0

            # Prepara lista de checkpoints reales (año, semestre)
            checkpoints = [(s.year, self.convert_semester(s.semester)) for s in sorted_states]
            self.semester_checkpoints = checkpoints

            for idx, (year, semester) in enumerate(all_semesters):
                time_since_base = (year - base_year) + (0 if semester == 1 else 0.5)

                # Calcular crecimiento
                growth = {}
                for fuel_id in fuel_ids:
                    growth[fuel_id] = {}
                    for comp in ['Process', 'Transport', 'Molecule']:
                        r = fuel_growth_rates[fuel_id][comp]
                        growth[fuel_id][comp] = (1 + r)**time_since_base if r != 0 else 1.0

                # Calcular tasa de infraestructura
                
                            
                if first:
                    infra_rate = 0.08
                    first = False
                    last_infra_rate = infra_rate
                else:
                    # Año inicial y final del tramo actual
                    start = checkpoints[last_checkpoint_idx]
                    end = (checkpoints[last_checkpoint_idx + 1]
                        if last_checkpoint_idx + 1 < len(checkpoints)
                        else (year, semester))

                    start_year = start[0]
                    end_year = end[0]


                    if start_year == end_year:
                        # total_between = sum(
                        #     1 for (y, s) in all_semesters
                        #     if start <= (y, s) <= end
                        # )
                        infra_rate = last_infra_rate #1.0 / max(1, total_between)
                    else:
                        total_between = sum(
                            1 for (y, s) in all_semesters
                            if start <= (y, s) <= end
                        )
                        infra_rate = 1.0 / max(1, total_between)
                        last_infra_rate = infra_rate

                #Guardar el semestre actual
                semester_data[(year, semester)] = {
                    #'growth': growth,
                    'infra_rate': infra_rate,
                    'Year': year,
                    'Semester': semester,
                    'time_since_base': time_since_base,
                }

                # 👇 Solo después de guardar, avanzamos al siguiente bloque real si tocaba
                if (
                    last_checkpoint_idx + 1 < len(checkpoints)
                    and (year, semester) == checkpoints[last_checkpoint_idx + 1]
                ):
                    last_checkpoint_idx += 1




            # Almacenar si lo necesitas para cálculos futuros
            self.full_semester_structure = semester_data
            return semester_data
        

        except Exception as e:
            logging.error("Error al generar estructura completa de semestres: %s", str(e))
            raise

    def _generate_structured_cost_df(self) -> pd.DataFrame:
        """
        Transform model_data_by_state into a structured DataFrame of costs by fuel, sector, and technical block.
        """
        rows = []

        for state_name, state_data in self.model_data_by_state.items():
            electricity = state_data.get('Electricity')
            lpg = state_data.get('LPG')
            Subsidies_Taxes = state_data.get('Subsidies_Taxes')
            income_tariff = state_data.get('Income_Tariff')

            if electricity:
                year = electricity['Mixed_State'].year
                #semester = electricity['Mixed_State'].semester
                semester = self.convert_semester(electricity['Mixed_State'].semester)


                fuel_id_el = 1  # Electricity
                fuel_name = self.fuel_id_to_name.get(fuel_id_el, 'Unknown')

                # 1. Income Tariffs
                for key, sector in [('E_total', 'E-TOTAL'), ('E_cooking', 'E-cooking')]:
                    if key in state_data.get("Income_Tariff", {}):
                        rows.append([state_name, year, semester, fuel_id_el, fuel_name, sector, "Tariff", "INCOME",
                                    state_data["Income_Tariff"][key], None, None, None, None])

                # 2. Electricity CAPEX/OPEX
                block_data = electricity["Block_Data"].get(year, {}).get("Data", {})
                for key, values in block_data.items():
                    tech = values.get("Technology", "Unknown")
                    sector_map = {
                        'Grid': 'Grid',
                        'StAloneS': 'Off Grid',
                        'Cooking': 'E-cooking'
                    }
                    sector = sector_map.get(tech, tech)
                    if 'distribution' in key.lower():
                        sub_sector = 'Distribution'
                    elif 'generation' in key.lower():
                        sub_sector = 'Generation'
                    elif 'cooking' in key.lower():
                        sub_sector = 'Fraction of electricity'
                    else:
                        sub_sector = 'percentage'

                    # if 'CAPEX' in key:
                    #     cost_type = 'CAPEX'
                    # elif 'OPEX' in key:
                    #     cost_type = 'OPEX'
                    # else:
                    #     cost_type = 'Other'
                    k = key.lower()
                    if "capex" in k:
                        cost_type = "CAPEX"
                    elif "opex" in k:
                        cost_type = "OPEX"
                    else:
                        cost_type = "Other"


                    rows.append([
                        state_name, year, semester, fuel_id_el, fuel_name, sector, sub_sector, cost_type,
                        values.get('Base prices M$/yr'),
                        values.get('Inc/Annual M$/yr'),
                        values.get('Annuity'),
                        values.get('Lifetime'),
                        values.get('Discount')
                    ])

                # 3. Subsidies for Electricity
                # appl_subs = Subsidies_Taxes.get("Appliances", {})
                # el_appliance_subsidy = appl_subs.get(fuel_id_el)

                # if el_appliance_subsidy is not None:
                #     rows.append([state_name, year, semester, fuel_id_el, fuel_name,
                #                 "Subsides & Taxes", "Appliances", "OPEX",
                #                 el_appliance_subsidy, None, None, None, None])

                    
            if lpg: 
                year = lpg['Mixed_State'].year
                #semester = electricity['Mixed_State'].semester
                semester = self.convert_semester(lpg['Mixed_State'].semester)

                fuel_id_lpg = 2  # LPG
                fuel_name = self.fuel_id_to_name.get(fuel_id_lpg, 'Unknown')

                for key, sector in [('LPG', 'LPG')]:
                    if key in state_data.get("Income_Tariff", {}):
                        rows.append([state_name, year, semester, fuel_id_lpg, fuel_name, sector, "Tariff", "INCOME",
                                    state_data["Income_Tariff"][key], None, None, None, None])
                        # 2. LPG CAPEX/OPEX
                block_data = lpg["Block_Data"].get(year, {}).get("Data", {})
                for key, values in block_data.items():
                    tech = values.get("Technology", "Unknown")
                    sector_map = {
                        'Local': 'Local',
                        'Upstream': 'Upstream',
                    }
                    sector = sector_map.get(tech, tech)
                    if 'processing' in key.lower():
                        sub_sector = 'Processing'
                    elif 'transport' in key.lower():
                        sub_sector = 'Transport'
                    elif 'import' in key.lower():
                        sub_sector = 'Import'
                    else:
                        sub_sector = 'Unknown'

                    if 'CAPEX' in key:
                        cost_type = 'CAPEX'
                    elif 'OPEX' in key:
                        cost_type = 'OPEX'
                    else:
                        cost_type = 'Other'

                    rows.append([
                        state_name, year, semester, fuel_id_lpg, fuel_name, sector, sub_sector, cost_type,
                        values.get('Base prices M$/yr'),
                        values.get('Inc/Annual M$/yr'),
                        values.get('Annuity'),
                        values.get('Lifetime'),
                        values.get('Discount')
                    ])
                    # 3. Subsidies for LPG
                # appl_subs = Subsidies_Taxes.get("Appliances", {})
                # lpg_appliance_subsidy = appl_subs.get(fuel_id_lpg)

                # if lpg_appliance_subsidy is not None:
                #     rows.append([state_name, year, semester, fuel_id_lpg, fuel_name,
                #                 "Subsides & Taxes", "Appliances", "OPEX",
                #                 lpg_appliance_subsidy, None, None, None, None])




            appl_subs = Subsidies_Taxes.get("Appliances", {})
            fuel_subs = Subsidies_Taxes.get("Fuels", {})

            for fid in range(1, len(self.fuel_id_to_name) + 1):
                fname = self.fuel_id_to_name.get(fid, 'Unknown')

                # Income dummy (optional)
                #rows.append([state_name, year, semester, fid, fname, fname, "Tariff", "INCOME", None, None, None, None, None])
                year = electricity['Mixed_State'].year
                #semester = electricity['Mixed_State'].semester
                semester = self.convert_semester(electricity['Mixed_State'].semester)

                

                # Appliance Subsidy
                appliance_subsidy = appl_subs.get(fid)
                rows.append([state_name, year, semester, fid, fname,
                            "Subsides & Taxes", "Appliances", "OPEX",
                            appliance_subsidy, None, None, None, None])
                # Fuel Subsidy
                if fid in (1, 2):  # Saltar electricidad y LPG
                    continue
                fuel_subsidy = fuel_subs.get(fid)
                rows.append([state_name, year, semester, fid, fname,
                            "Subsides & Taxes", "Fuel", "OPEX",
                            fuel_subsidy, None, None, None, None])

            social_costs = state_data.get("Social_Costs", {})

            # Línea para deforestación
            if "Deforestation" in social_costs:
                year = electricity['Mixed_State'].year
                #semester = electricity['Mixed_State'].semester
                semester = self.convert_semester(electricity['Mixed_State'].semester)

                rows.append([
                    state_name, year, semester, 0, "All_Fuels",
                    "Carbon_Economy", "Deforestation", "OPEX",
                    social_costs["Deforestation"], None, None, None, None
                ])

            # Línea para emisiones
            if "Emissions" in social_costs:
                year = electricity['Mixed_State'].year
                #semester = electricity['Mixed_State'].semester
                semester = self.convert_semester(electricity['Mixed_State'].semester)

                rows.append([
                    state_name, year, semester, 0, "All_Fuels",
                    "Carbon_Economy", "Emissions", "OPEX",
                    social_costs["Emissions"], None, None, None, None
                ])

        return pd.DataFrame(rows, columns=[
            "State", "Year", "Semester", "Fuel_Id", "Fuel_name", "Sector", "Sub_sector",
            "OPEX/CAPEX/Income", "Base prices M$/yr", "Inc/Annual M$/yr", "Annuity", "Lifetime", "Discount_rate"
        ])
    
    

    def compute_growth(self, row):
        try:
            # 1. Parámetros base
            simulation_growth_scenario = self.growth_scenario
            base_year = simulation_growth_scenario.base_year
            scenario_name = simulation_growth_scenario.scenario_name
            dep_fuel_cost_var = simulation_growth_scenario.dep_fuel_cost_var
            fuel_ret_price = simulation_growth_scenario.fuel_ret_price
            app_ret_price = simulation_growth_scenario.app_ret_price

            state_name = row["State"]
            year = row["Year"]
            semester = row["Semester"]
            fuel_id = row["Fuel_Id"]
            sub_sector = str(row["Sub_sector"]).lower()

            # 2. Calcular el tiempo desde el año base
            # t = (year - base_year) + (0.5 if semester == 2 else 0.0)
            # Use pre-computed TimeSinceBase if available
            # Use pre-computed TimeSinceBase if available
            t = row.get("TimeSinceBase", None)
            if t is None or pd.isna(t):
                t = (year - base_year) + (0.5 if semester == 2 else 0.0)

            # -------------------------
            # CASO 1: sub_sector = 'fuel'
            # -------------------------
            if sub_sector == "fuel" or (sub_sector == "tariff" and fuel_id in [1, 2]):
                record = next(
                    (r for r in fuel_ret_price
                    if r.get("Fuel_id") == fuel_id and r.get("GrowthPat_Name") == scenario_name),
                    None
                )
                growth_rate = record.get("Retail_price", 0.0) if record else 0.0
                return (1 + growth_rate) ** t if growth_rate != 0 else 1.0
            # if sub_sector == "fuel":
            #     record = next(
            #         (r for r in fuel_ret_price
            #         if r.get("Fuel_id") == fuel_id and r.get("GrowthPat_Name") == scenario_name),
            #         None
            #     )
            #     growth_rate = record.get("Retail_price", 0.0) if record else 0.0
            #     return (1 + growth_rate) ** t if growth_rate != 0 else 1.0

            # -------------------------
            # CASO 2: sub_sector = 'appliances'
            # -------------------------
            # -------------------------
            # elif sub_sector == "appliances":
            #     state_to_use = state_name
            #     if state_name not in self.model_data_by_state:
            #         self.logger.warning(f"No model data found for state {state_name}, searching fallback")
            #         valid_states = [s.get_state_name() for s in reversed(self.simulation_plan.states)
            #                         if s.get_state_name() in self.model_data_by_state]
            #         if valid_states:
            #             state_to_use = valid_states[0]
            #         else:
            #             self.logger.warning("No previous valid state found.")
            #             return 1.0

            #     appliance_growth_all = self.model_data_by_state[state_to_use].get("Appliance_Growth", {})
            #     appliance_weights = appliance_growth_all.get(fuel_id, {})

            #     # fallback: si no hay weights porque solo hay una appliance, usar peso 1.0 si se puede inferir
            #     if not appliance_weights:
            #         # Buscar appliance_id asociado a este fuel en app_ret_price
            #         tech_df = self.data_manager.get_dataframe("Cooking_technologies")
            #         fuel_apps = tech_df[tech_df["Fuel_id"] == fuel_id]["Appliance_id"].unique().tolist()

            #         if len(fuel_apps) == 1:
            #             appliance_id = fuel_apps[0]
            #             record = next(
            #                 (r for r in app_ret_price
            #                 if r.get("Appliance_id") == appliance_id and r.get("GrowthPat_Name") == scenario_name),
            #                 None
            #             )
            #             appliance_growth = record.get("Retail_price", 0.0) if record else 0.0
            #             return (1 + appliance_growth) ** t if appliance_growth != 0 else 1.0
            #         else:
            #             self.logger.warning(f"No weights and multiple or no appliances found for fuel_id {fuel_id}")
            #             return 1.0

            #     # caso normal: usar pesos existentes
            #     total_growth_rate = 0.0
            #     for appliance_id, weight in appliance_weights.items():
            #         record = next(
            #             (r for r in app_ret_price
            #             if r.get("Appliance_id") == appliance_id and r.get("GrowthPat_Name") == scenario_name),
            #             None
            #         )
            #         appliance_growth = record.get("Retail_price", 0.0) if record else 0.0
            #         total_growth_rate += weight * appliance_growth

            #     return (1 + total_growth_rate) ** t if total_growth_rate != 0 else 1.0
            elif sub_sector == "appliances":
                try:
                    # Try to use the current state if present
                    state_name = str(row.get("State", ""))
                    appliance_growth_all = {}

                    if state_name in self.model_data_by_state:
                        appliance_growth_all = self.model_data_by_state[state_name].get("Appliance_Growth", {})

                    # Fallback: search any state that has appliance weights for this fuel
                    if not appliance_growth_all or fuel_id not in appliance_growth_all:
                        for st_name, st_data in reversed(self.model_data_by_state.items()):
                            ag = st_data.get("Appliance_Growth", {})
                            if fuel_id in ag:
                                appliance_growth_all = ag
                                break

                    appliance_weights = appliance_growth_all.get(fuel_id, {})

                    if not appliance_weights:
                        # No weights found → no appliance growth information
                        return 1.0

                    total_growth_rate = 0.0
                    for appliance_id, weight in appliance_weights.items():
                        record = next(
                            (r for r in app_ret_price
                            if r.get("Appliance_id") == appliance_id
                            and r.get("GrowthPat_Name") == scenario_name),
                            None
                        )
                        appliance_growth = record.get("Retail_price", 0.0) if record else 0.0
                        total_growth_rate += weight * appliance_growth

                    return (1 + total_growth_rate) ** t if total_growth_rate != 0 else 1.0

                except Exception as e:
                    self.logger.warning(f"Error computing appliance growth: {e}")
                    return 1.0




            # -------------------------
            # CASO 3: Otros subsectores como electricidad, cooking, etc.
            # -------------------------

            # Construir tasas de crecimiento por componente
            fuel_growth_rates = {}
            for fid in [1, 2]:  # Electricity and LPG
                record = next(
                    (r for r in dep_fuel_cost_var
                    if r.get("Fuel_id") == fid and r.get("GrowthPat_Name") == scenario_name),
                    None
                )
                if record:
                    fuel_growth_rates[fid] = {
                        'Process': record.get('Process', 0.0),
                        'Transport': record.get('Transport', 0.0),
                        'Molecule': record.get('Molecule', 0.0),
                    }
                else:
                    fuel_growth_rates[fid] = {'Process': 0.0, 'Transport': 0.0, 'Molecule': 0.0}

            # Asignar componente según sub_sector
            if fuel_id == 1:  # Electricidad
                if "generat" in sub_sector:
                    component = "Process"
                elif "distrib" in sub_sector:
                    component = "Transport"
                elif "fraction of electricity" in sub_sector:
                    component = "AvgProcessTransport"
                
                else:
                    return 1.0  # no aplica crecimiento

            elif fuel_id == 2:  # LPG
                if "process" in sub_sector:
                    component = "Process"
                elif "transport" in sub_sector:
                    component = "Transport"
                elif "import" in sub_sector or "molecule" in sub_sector:
                    component = "Molecule"
                else:
                    return 1.0  # no aplica crecimiento
            else:
                return 1.0  # otros fuels no crecen aún

            # Calcular crecimiento para componente seleccionado
            if component == "AvgProcessTransport":
                proc = fuel_growth_rates[fuel_id]["Process"]
                trans = fuel_growth_rates[fuel_id]["Transport"]
                growth_rate = (proc + trans) / 2
            else:
                growth_rate = fuel_growth_rates[fuel_id].get(component, 0.0)

            return (1 + growth_rate) ** t if growth_rate != 0 else 1.0

        except Exception as e:
            self.logger.warning(f"Error computing growth: {e}")
            return 1.0




    # def compute_capex_from_annuity(self, final_expanded_structured_costs: pd.DataFrame, capex_structure: pd.DataFrame) -> pd.DataFrame:
    #     "Creates the common DataFrame knowing that they share the columns State, Year, Semester but each row of opex corresponds to many rows in final_expanded_structured_costs"
    #     try: 
    #             capex_structure = capex_structure.rename(columns={"State": "state", "Year": "year", "Semester": "semester"})
    #             final_expanded_structured_costs = final_expanded_structured_costs.rename(columns={"State": "state", "Year": "year", "Semester": "semester"})
    #             common_columns = ["state", "year", "semester"]
    #             merged_df = pd.merge(final_expanded_structured_costs, capex_structure, on=common_columns, how="left")
    #             # merged_df = merged_df.dropna(subset=["opex_annuity"])
    #             # merged_df["opex"] = merged_df["opex_annuity"] * merged_df
    #             # ["annuity_factor"]
    #             # merged_df = merged_df.drop(columns=["opex_annuity", "annuity_factor"])
    #             df = final_expanded_structured_costs
    #             mask_app = df["Sub_sector"].str.lower() == "appliances"
    #             print(df.loc[mask_app, ["state", "year", "semester", "Fuel_Id", "Growth_Factor"]].drop_duplicates())
    #             # Imprimir valores en tsv 
    #             df.loc[mask_app, ["state", "year", "semester", "Fuel_Id", "Growth_Factor"]].drop_duplicates().to_csv("appliances_growth_factors.tsv", sep="\t", index=False)
    #             return merged_df
    #     except Exception as e:
    #             print(f"Error al calcular opex desde annuity: {e}")
    #             return pd.DataFrame()

    def compute_capex_from_annuity(
        self,
        final_expanded_structured_costs: pd.DataFrame,
        capex_structure: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Build the common DataFrame for CAPEX-from-annuity computation.

        It aligns detailed cost rows (per fuel / sector / sub-sector) with
        the CAPEX structure defined per (state, year, semester).
        """
        try:
            # import os

            # debug_dir = "debug_capex"
            # os.makedirs(debug_dir, exist_ok=True)

            # # --- Debug: raw inputs as they enter this method ---
            # final_expanded_structured_costs.to_csv(
            #     os.path.join(debug_dir, "final_expanded_structured_costs_raw.tsv"),
            #     sep="\t",
            #     index=False
            # )
            # capex_structure.to_csv(
            #     os.path.join(debug_dir, "capex_structure_raw.tsv"),
            #     sep="\t",
            #     index=False
            # )

            # --- Normalize column names for merge ---
            capex_structure = capex_structure.rename(
                columns={"State": "state", "Year": "year", "Semester": "semester"}
            )
            final_expanded_structured_costs = final_expanded_structured_costs.rename(
                columns={"State": "state", "Year": "year", "Semester": "semester"}
            )

            # --- IMPORTANT: enforce same dtypes for join keys ---
            for df_ in (final_expanded_structured_costs, capex_structure):
                df_["state"] = df_["state"].astype(str)
                df_["year"] = df_["year"].astype(int)
                df_["semester"] = df_["semester"].astype(int)

            common_columns = ["state", "year", "semester"]

            # --- Merge detailed costs with CAPEX structure ---
            merged_df = pd.merge(
                final_expanded_structured_costs,
                capex_structure,
                on=common_columns,
                how="left"
            )

            # --- Debug: merged view with key columns and annuity info (if any) ---
            # merged_df.to_csv(
            #     os.path.join(debug_dir, "capex_merged_full.tsv"),
            #     sep="\t",
            #     index=False
            # )

            debug_cols = [
                "state", "year", "semester",
                "Fuel_Id", "Fuel_name",
                "Sector", "Sub_sector",
                "OPEX/CAPEX/Income",
                # aquí añade lo que venga de capex_structure, por ejemplo:
                "CAPEX_Ann_M$/yr",
                "Annuity",
                "Lifetime",
                "Discount_rate",
                "Growth_Factor",
                "InfraRate",
            ]
            debug_cols = [c for c in debug_cols if c in merged_df.columns]

            # merged_df[debug_cols].drop_duplicates().sort_values(
            #     ["state", "year", "semester", "Fuel_Id"]
            # ).to_csv(
            #     os.path.join(debug_dir, "capex_merged_overview.tsv"),
            #     sep="\t",
            #     index=False
            # )

            # Optional: keep your appliances debug, adapted to CAPEX
            df = final_expanded_structured_costs
            if "Sub_sector" in df.columns:
                mask_app = df["Sub_sector"].str.lower() == "appliances"
                app_view = df.loc[
                    mask_app,
                    [c for c in ["state", "year", "semester", "Fuel_Id", "Growth_Factor"] if c in df.columns]
                ].drop_duplicates()
                #print(app_view.head(40))
                # app_view.to_csv(
                #     os.path.join(debug_dir, "appliances_growth_factors_capex.tsv"),
                #     sep="\t",
                #     index=False
                # )

            return merged_df

        except Exception as e:
            print(f"Error al calcular CAPEX desde annuity: {e}")
            return pd.DataFrame()

    def _calculate_capex_from_annuity(self, capex_from_annuity: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates CAPEX_Past, Trail_Capex_Past and interpolated CAPEX_Px / Trail_Capex_Px
        according to the flags and defined rules.
        """
        try:
            # -----------------------------
            # 0) Ensure core numeric columns
            # -----------------------------
            capex_from_annuity["Annuity"] = pd.to_numeric(capex_from_annuity["Annuity"], errors="coerce")
            capex_from_annuity["Growth_Factor"] = pd.to_numeric(capex_from_annuity["Growth_Factor"], errors="coerce")
            capex_from_annuity["InfraRate"] = pd.to_numeric(capex_from_annuity["InfraRate"], errors="coerce")
            capex_from_annuity["Lifetime"] = pd.to_numeric(capex_from_annuity["Lifetime"], errors="coerce")

            # Extract year / semester from "state" if not present
            if "year" not in capex_from_annuity.columns or "semester" not in capex_from_annuity.columns:
                capex_from_annuity[["year", "semester"]] = capex_from_annuity["state"].str.extract(r"(\d+)_S(\d+)")
            capex_from_annuity["year"] = pd.to_numeric(capex_from_annuity["year"], errors="coerce")
            capex_from_annuity["semester"] = pd.to_numeric(capex_from_annuity["semester"], errors="coerce")

            # Sort by time per group
            capex_from_annuity.sort_values(
                by=["Fuel_Id", "Fuel_name", "Sector", "Sub_sector", "year", "semester"],
                inplace=True
            )

            # -----------------------------
            # 1) CAPEX_Past
            # -----------------------------
            mask_past = (
                (capex_from_annuity["OPEX/CAPEX/Income"] == "CAPEX") &
                (capex_from_annuity["Capex_Past"] == True)
            )
            capex_from_annuity["Capex_Past"] = capex_from_annuity["Capex_Past"].astype(float)

            capex_from_annuity.loc[mask_past, "Capex_Past"] = (
                (capex_from_annuity.loc[mask_past, "Annuity"] *
                capex_from_annuity.loc[mask_past, "InfraRate"]) /
                capex_from_annuity.loc[mask_past, "Growth_Factor"]
            ) / 2.0

            capex_from_annuity.loc[~mask_past, "Capex_Past"] = 0.0

            # -----------------------------
            # 2) Base state per group
            # -----------------------------
            base_capex = (
                capex_from_annuity
                .dropna(subset=["Annuity", "Lifetime"])
                .groupby(["Fuel_Id", "Fuel_name", "Sector", "Sub_sector"], as_index=False)
                .first()[["Fuel_Id", "Fuel_name", "Sector", "Sub_sector", "state", "Annuity", "Lifetime"]]
            )

            base_capex = base_capex.rename(columns={
                "state": "Base_State",
                "Annuity": "Base_Annuity",
                "Lifetime": "Base_Lifetime",
            })

            capex_from_annuity = capex_from_annuity.merge(
                base_capex,
                on=["Fuel_Id", "Fuel_name", "Sector", "Sub_sector"],
                how="left"
            )

            # -----------------------------
            # 3) Trail_Capex_Past
            # -----------------------------
            mask_trial_past = (
                (capex_from_annuity["OPEX/CAPEX/Income"] == "CAPEX") &
                (capex_from_annuity["Trail_Capex_Past"] == True)
            )

            capex_from_annuity["Trail_Capex_Past"] = capex_from_annuity["Trail_Capex_Past"].astype(float)

            capex_from_annuity.loc[mask_trial_past, "Trail_Capex_Past"] = (
                (capex_from_annuity.loc[mask_trial_past, "Base_Annuity"] /
                capex_from_annuity.loc[mask_trial_past, "Lifetime"]) *
                capex_from_annuity.loc[mask_trial_past, "Growth_Factor"]
            ) / 2.0

            capex_from_annuity.loc[~mask_trial_past, "Trail_Capex_Past"] = 0.0

            # -----------------------------
            # 4) CAPEX_Px interpolation
            # -----------------------------
            df = capex_from_annuity.copy()

            capex_columns = [
                col for col in df.columns
                if col.startswith("Capex_P") and col != "Capex_Past"
            ]
            trail_columns = [
                col for col in df.columns
                if col.startswith("Trail_Capex_P") and col != "Trail_Capex_Past"
            ]

            df["Capex_P_result"] = 0.0

            # Keep original flags (True/False) for Capex_Px and Trail_Capex_Px
            capex_flags = df[capex_columns].astype(bool).copy() if capex_columns else None
            trail_flags = df[trail_columns].astype(bool).copy() if trail_columns else None

            # Convert Capex_Px and Trail_Capex_Px to float and set 0.0
            if capex_columns:
                for col in capex_columns:
                    df[col] = 0.0
                df[capex_columns] = df[capex_columns].astype(float)

            if trail_columns:
                for col in trail_columns:
                    df[col] = 0.0
                df[trail_columns] = df[trail_columns].astype(float)

            # Dict to store base_prev + base_fut per group / Capex_Px
            trail_value_dict = {}

            # --- Main interpolation loop ---
            for idx, row in df.iterrows():
                if row["OPEX/CAPEX/Income"] != "CAPEX":
                    continue

                if not capex_columns or capex_flags is None:
                    continue

                # Is any Capex_Px active for this row?
                active_capex_col = next(
                    (col for col in capex_columns if capex_flags.at[idx, col]),
                    None
                )
                if not active_capex_col:
                    # No active Capex_Px → all remain 0.0
                    continue

                current_year = row["year"]
                current_semester = row["semester"]

                same_group_mask = (
                    (df["Fuel_Id"] == row["Fuel_Id"]) &
                    (df["Fuel_name"] == row["Fuel_name"]) &
                    (df["Sector"] == row["Sector"]) &
                    (df["Sub_sector"] == row["Sub_sector"]) &
                    (df["OPEX/CAPEX/Income"] == "CAPEX")
                )

                group = df[same_group_mask].copy()
                if group.empty:
                    df.at[idx, "Capex_P_result"] = 0.0
                    continue

                group = group.sort_values(by=["year", "semester"])

                # Previous (<= current) real states
                previous = group[
                    (
                        (group["year"] < current_year) |
                        ((group["year"] == current_year) & (group["semester"] <= current_semester))
                    ) &
                    (group["IsReal"].astype(bool) == True)
                ].sort_values(by=["year", "semester"])

                # Future (> current) real states
                future = group[
                    (
                        (group["year"] > current_year) |
                        ((group["year"] == current_year) & (group["semester"] > current_semester))
                    ) &
                    (group["IsReal"].astype(bool) == True)
                ].sort_values(by=["year", "semester"])

                is_current_real = bool(row["IsReal"])
                is_last_real = is_current_real and future.empty

                if is_last_real:
                    # Use strictly previous real as prev, current as fut
                    previous_strict = group[
                        (
                            (group["year"] < current_year) |
                            ((group["year"] == current_year) & (group["semester"] < current_semester))
                        ) &
                        (group["IsReal"].astype(bool) == True)
                    ].sort_values(by=["year", "semester"])

                    if previous_strict.empty:
                        print(f"[SKIPPED - Last real state without previous real] {row['state']}")
                        continue

                    prev_row = previous_strict.iloc[-1]
                    fut_row = row
                else:
                    if previous.empty or future.empty:
                        # Cannot form prev/fut pair
                        continue
                    prev_row = previous.iloc[-1]
                    fut_row = future.iloc[0]

                base_prev = prev_row["Annuity"] / prev_row["Growth_Factor"]
                base_fut = fut_row["Annuity"] / fut_row["Growth_Factor"]

                # Store interpolation for all Capex_Px (only applied where flag is True)
                for capex_col in capex_columns:
                    group_key = (
                        row["Fuel_Id"],
                        row["Fuel_name"],
                        row["Sector"],
                        row["Sub_sector"],
                        capex_col,
                    )
                    interpolated = (base_prev + base_fut) * row["Growth_Factor"] * row["InfraRate"]
                    trail_value_dict[group_key] = (base_prev + base_fut)

                    if capex_flags.at[idx, capex_col]:
                        df.at[idx, capex_col] = float(interpolated)
                    else:
                        df.at[idx, capex_col] = 0.0

            # -----------------------------
            # 5) Trail_Capex_Px using stored base values
            # -----------------------------
            if trail_columns and trail_flags is not None:
                for idx, row in df.iterrows():
                    if row["OPEX/CAPEX/Income"] != "CAPEX":
                        continue

                    for trail_col in trail_columns:
                        if trail_col not in df.columns:
                            continue
                        if not trail_flags.at[idx, trail_col]:
                            continue

                        base_capex_col = trail_col.replace("Trail_", "")
                        group_key = (
                            row["Fuel_Id"],
                            row["Fuel_name"],
                            row["Sector"],
                            row["Sub_sector"],
                            base_capex_col,
                        )
                        base_val = trail_value_dict.get(group_key, 0.0)
                        lifetime = row["Lifetime"]
                        growth = row["Growth_Factor"]

                        if (
                            pd.notnull(base_val) and
                            pd.notnull(lifetime) and
                            pd.notnull(growth) and
                            lifetime > 0
                        ):
                            trail_val = ((base_val / lifetime) * growth) / 2.0
                        else:
                            trail_val = 0.0

                        df.at[idx, trail_col] = float(trail_val)

            # -----------------------------
            # 6) Aggregate CAPEX per semester
            # -----------------------------
            capex_columns = [
                col for col in df.columns
                if col.startswith("Capex_P") and col != "Capex_Past"
            ]
            trail_columns = [
                col for col in df.columns
                if col.startswith("Trail_Capex_P") and col != "Trail_Capex_Past"
            ]

            df["CAPEX_Semester_M$"] = (
                df.get("Capex_Past", 0.0) +
                df.get("Trail_Capex_Past", 0.0) +
                (df[capex_columns].sum(axis=1) if capex_columns else 0.0) +
                (df[trail_columns].sum(axis=1) if trail_columns else 0.0)
            )

            return df

        except Exception as e:
            print(f"Error al calcular CAPEX desde annuity: {e}")
            return pd.DataFrame()

    # def _calculate_capex_from_annuity(self, capex_from_annuity: pd.DataFrame) -> pd.DataFrame:
    #     """
    #     Calculates Opex_Past and Opex_Fut according to the flags and defined rules.
    #     """
    #     try:
    #         # Ensure that the columns are numeric
    #         capex_from_annuity["Annuity"] = pd.to_numeric(capex_from_annuity["Annuity"], errors="coerce")
    #         capex_from_annuity["Growth_Factor"] = pd.to_numeric(capex_from_annuity["Growth_Factor"], errors="coerce")
    #         capex_from_annuity["InfraRate"] = pd.to_numeric(capex_from_annuity["InfraRate"], errors="coerce")
    #         capex_from_annuity["Lifetime"] = pd.to_numeric(capex_from_annuity["Lifetime"], errors="coerce")
    #         # Extraer año y semestre para ordenar temporalmente los estados
    #         capex_from_annuity[["Year", "Semester"]] = capex_from_annuity["state"].str.extract(r"(\d+)_S(\d+)")
    #         capex_from_annuity["Year"] = pd.to_numeric(capex_from_annuity["Year"], errors="coerce")
    #         capex_from_annuity["Semester"] = pd.to_numeric(capex_from_annuity["Semester"], errors="coerce")
    #         # Ordenar por año y semestre
    #         capex_from_annuity.sort_values(by=["Fuel_Id", "Fuel_name", "Sector", "Sub_sector", "Year", "Semester"], inplace=True)



    #         # Paso 1: Calcular Opex_Past
    #         mask_past = (capex_from_annuity["OPEX/CAPEX/Income"] == "CAPEX") & (capex_from_annuity["Capex_Past"] == True)
    #         capex_from_annuity["Capex_Past"] = capex_from_annuity["Capex_Past"].astype(float)
            
            

    #         capex_from_annuity.loc[mask_past, "Capex_Past"] = ((
    #             capex_from_annuity.loc[mask_past, "Annuity"] * capex_from_annuity.loc[mask_past, "InfraRate"]
    #         ) / capex_from_annuity.loc[mask_past, "Growth_Factor"])/ 2

    #         capex_from_annuity.loc[~mask_past, "Capex_Past"] = 0
    #         # Paso 2: Identificar estado base por grupo (el más temprano con Annuity y Lifetime válidos)
    #         base_capex = (
    #             capex_from_annuity
    #             .dropna(subset=["Annuity", "Lifetime"])
    #             .groupby(["Fuel_Id", "Fuel_name", "Sector", "Sub_sector"], as_index=False)
    #             .first()[["Fuel_Id", "Fuel_name", "Sector", "Sub_sector", "state", "Annuity", "Lifetime"]]
    #         )

    #         base_capex = base_capex.rename(columns={
    #             "state": "Base_State",
    #             "Annuity": "Base_Annuity",
    #             "Lifetime": "Base_Lifetime"
    #         })

    #         # Paso 3: Unir con el dataframe original para extender el estado base a todas las filas del mismo grupo
    #         capex_from_annuity = capex_from_annuity.merge(
    #             base_capex,
    #             on=["Fuel_Id", "Fuel_name", "Sector", "Sub_sector"],
    #             how="left"
    #         )

    #         # Paso 4: Calcular Trail_Capex_Past
    #         mask_trial_past = (
    #             (capex_from_annuity["OPEX/CAPEX/Income"] == "CAPEX") &
    #             (capex_from_annuity["Trail_Capex_Past"] == True)
    #         )

    #         capex_from_annuity["Trail_Capex_Past"] = capex_from_annuity["Trail_Capex_Past"].astype(float)

    #         capex_from_annuity.loc[mask_trial_past, "Trail_Capex_Past"] = (
    #             (capex_from_annuity.loc[mask_trial_past, "Base_Annuity"] /
    #             capex_from_annuity.loc[mask_trial_past, "Lifetime"]) *
    #             capex_from_annuity.loc[mask_trial_past, "Growth_Factor"]
    #         ) / 2

    #         capex_from_annuity.loc[~mask_trial_past, "Trail_Capex_Past"] = 0

            

    #         # Paso 2: Calcular los valores de las columnas que empuecen por Capex_P excepto Capex_Past y cuyo valor esté True
    #         capex_columns = [col for col in capex_from_annuity.columns if col.startswith("Capex_P") and col != "Capex_Past"]
    #         df = capex_from_annuity.copy()

    #         trail_columns = [col for col in df.columns if col.startswith("Trail_Capex_P") and col != "Trail_Capex_Past"]

    #         #for col in capex_columns:
    #             #mask = (capex_from_annuity["OPEX/CAPEX/Income"] == "CAPEX") & (capex_from_annuity[col] == True)
    #             # capex_from_annuity.loc[mask, col] = capex_from_annuity.loc[mask, "Annuity"] * capex_from_annuity.loc[mask, "InfraRate"] / capex_from_annuity.loc[mask, "Growth_Factor"]
    #             # capex_from_annuity.loc[~mask, col] = 0

    #         #df = capex_from_annuity.copy()
    #         df["Capex_P_result"] = 0.0

    #         #key_cols = ["state", "Fuel_Id", "Fuel_name", "Sector", "Sub_sector", "OPEX/CAPEX/Income"]
    #         # Inicializar columnas auxiliares para trail values
    #         for col in capex_columns:
    #             df[f"TrailValue_{col}"] = 0.0
    #         trail_value_dict = {}
    #         for idx, row in df.iterrows():
    #             if row["OPEX/CAPEX/Income"] != "CAPEX": #or not row["Opex_Fut"]:
    #                 continue
                
    #             active_capex_col = next((col for col in capex_columns if row[col] == True), None)
    #             if not active_capex_col:
    #                 for col in capex_columns:
    #                     df.at[idx, col] = False #0.0
    #                 continue
    #             # Construir el nombre del trail asociado
    #             trail_col = active_capex_col.replace("Capex_P", "Trail_Capex_P")

                

    #             current_year = row["year"]
    #             current_semester = row["semester"]

    #             # Filtro para misma clave solo con estados reales
    #             same_group = (
    #                 #(df["state"] == row["state"]) &
    #                 (df["Fuel_Id"] == row["Fuel_Id"]) &
    #                 (df["Fuel_name"] == row["Fuel_name"]) &
    #                 (df["Sector"] == row["Sector"]) &
    #                 (df["Sub_sector"] == row["Sub_sector"]) &
    #                 (df["OPEX/CAPEX/Income"] == "CAPEX") #&
    #                 #(df["IsReal"].astype(bool) == True)
    #             ).copy()

    #             group = df[same_group].copy()
    #             if group.empty:
    #                 df.at[idx, "Capex_P_result"] = 0.0
    #                 continue

    #             group = group.sort_values(by=["year", "semester"])
    #             current_year = row["year"]
    #             current_semester = row["semester"]

    #             # Buscar estado real anterior o actual
    #             # (2) Filtrar solo los anteriores que sean reales
    #             previous = group[
    #                 (((group["year"] < current_year) |
    #                 ((group["year"] == current_year) & (group["semester"] <= current_semester))) &
    #                 (group["IsReal"].astype(bool) == True))
    #             ].sort_values(by=["year", "semester"])

    #             # if row["IsReal"]:
    #             #     # Si el estado actual es real, incluirlo como posible anterior o futuro
    #             #     current_as_df = pd.DataFrame([row])
    #             # else:
    #             #     current_as_df = previous.tail(1)#pd.DataFrame()  # vacío
    #             # (3) Lógica para incluir el actual si es real
    #             if row["IsReal"] == True:
    #                 previous_or_current = pd.concat([previous, pd.DataFrame([row])]).sort_values(by=["year", "semester"]).tail(1)
    #             else:
    #                 previous_or_current = previous.tail(1)
    #                 #print(f"\n🟠 Estado NO REAL: {row['state']} {row['year']}S{row['semester']}")
    #                 # print(f"   Actual: {row['state']} - Año: {row['year']} S{row['semester']}")
    #                 # print(f"   Growth_Factor (actual): {row['Growth_Factor']} | InfraRate (actual): {row['InfraRate']}")

    #                 # print(f"   → Anterior real usado: Año {prev_row['year']} S{prev_row['semester']} | Base price: {prev_row['Base prices M$/yr']} | Growth_Factor: {prev_row['Growth_Factor']}")
    #                 # print(f"   → Posterior real usado: Año {fut_row['year']} S{fut_row['semester']} | Base price: {fut_row['Base prices M$/yr']} | Growth_Factor: {fut_row['Growth_Factor']}")
    #                 # print("   -----------------------------")
                    


    #             # Tomar el último anterior o actual real
    #             #previous_or_current = pd.concat([previous, current_as_df]).sort_values(by=["year", "semester"]).tail(1)

    #             # Buscar futuro real (exclusivamente posterior)
    #             # (3) Lógica para incluir el actual si es real
    #             future = group[
    #                 (((group["year"] > current_year) |
    #                 ((group["year"] == current_year) & (group["semester"] > current_semester))) &
    #                 (group["IsReal"].astype(bool) == True))
    #             ].sort_values(by=["year", "semester"])#.head(1)

    #             # if row["IsReal"] and future.empty:
    #             #     future = pd.DataFrame([row])#.head(1)  # Si el actual es real, usarlo como futuro
    #             # Detectar si estoy en el último estado real (sin futuros)
    #             is_last_real = row["IsReal"] and future.empty

    #             if is_last_real:
    #                 # Forzar que prev_row no sea el actual, sino estrictamente anterior
    #                 previous = group[
    #                     (((group["year"] < current_year) |
    #                     ((group["year"] == current_year) & (group["semester"] < current_semester))) &
    #                     (group["IsReal"].astype(bool) == True))
    #                 ].sort_values(by=["year", "semester"])

    #                 if not previous.empty:
    #                     prev_row = previous.iloc[-1]
    #                     fut_row = row  # el actual
    #                 else:
    #                     # No hay previo real → omitir esta fila
    #                     print(f"[OMITIDO - Último estado sin anterior real] {row['state']}")
    #                     continue
    #             else:
    #                 # Lógica normal
    #                 prev_row = previous_or_current.iloc[0]
    #                 fut_row = future.iloc[0]

                
    #             if previous_or_current.empty or future.empty:
    #                 # print(f"[OMITIDO] {row['state']} {row['year']}S{row['semester']}")
    #                 # print(f"  IsReal actual: {row['IsReal']}")
    #                 # print(f"  Tamaño prev_or_current: {previous_or_current.shape[0]}")
    #                 # print(f"  Tamaño future: {future.shape[0]}")
    #                 # print(f"  Grupo completo con mismos identificadores:")
    #                 # print(group[["year", "semester", "IsReal", "Base prices M$/yr"]])
    #                 continue



    #             #print(f"\n🔵 Estado Real Actual: {row['state']} {row['year']}S{row['semester']}")
    #             prev_row = previous_or_current.iloc[0]
    #             #print(f"\n🟢 Estado Real Prev: {prev_row['state']} {prev_row['year']}S{prev_row['semester']}")
    #             fut_row = future.iloc[0]
    #             #print(f"   Estado Real Futuro: {fut_row['state']} - Año: {fut_row['year']} S{fut_row['semester']}")

    #             base_prev = (prev_row["Annuity"]) / prev_row["Growth_Factor"]
    #             base_fut = (fut_row["Annuity"] ) / fut_row["Growth_Factor"]

                
    #             # Guarda interpolación para TODOS los Capex_Px
                
    #             for capex_col in capex_columns:
    #                 group_key = (row["Fuel_Id"], row["Fuel_name"], row["Sector"], row["Sub_sector"], capex_col)
    #                 interpolated = (base_prev + base_fut) * row["Growth_Factor"] * row["InfraRate"]
    #                 trail_value_dict[group_key] = (base_prev + base_fut)
    #                 # Si quieres asignar aquí valores directos a Capex_Px si están activos:
    #                 if bool(row.get(capex_col, False)):
    #                     capex_col = float(capex_col)
    #                     df.at[idx, capex_col] = interpolated
    #                 else:
    #                     capex_col = float(capex_col)
    #                     df.at[idx, capex_col] = 0.0
    #         # Cálculo separado de Trail_Capex_Px
    #         for idx, row in df.iterrows():
    #             if row["OPEX/CAPEX/Income"] != "CAPEX":
    #                 continue

                
    #             for trail_col in trail_columns:
    #                 if trail_col in df.columns and bool(row[trail_col]):
    #                     df[trail_col] = df[trail_col].astype(float)
    #                     base_capex_col = trail_col.replace("Trail_", "")
    #                     group_key = (row["Fuel_Id"], row["Fuel_name"], row["Sector"], row["Sub_sector"], base_capex_col)
    #                     # trail_val = trail_value_dict.get(group_key, 0.0)
    #                     # df.at[idx, trail_col] = trail_val
    #                     base_val = trail_value_dict.get(group_key, 0.0)
    #                     #print(f"🔵 Recuperado {base_val} = {base_val} en {row['state']} {row['year']}S{row['semester']}")

    #                     lifetime = row["Lifetime"]
    #                     growth = row["Growth_Factor"]
    #                     if pd.notnull(base_val) and pd.notnull(lifetime) and pd.notnull(growth) and lifetime > 0:
    #                         trail_val = ((base_val / lifetime) * growth )/ 2
    #                     else:
    #                         trail_val = 0.0
    #                     df.at[idx, trail_col] = trail_val

    #                     #print(f"🔵 Recuperado {trail_val} = {trail_val} en {row['state']} {row['year']}S{row['semester']}")



    #         # df["CAPEX_Semester_M$"] = df["Capex_Past"] + df[capex_columns].sum(axis=1)
    #         # Detectar columnas Capex_Px (sin incluir Capex_Past)
    #         capex_columns = [col for col in df.columns if col.startswith("Capex_P") and col != "Capex_Past"]

    #         # Detectar columnas Trail_Capex_Px (sin incluir Trail_Capex_Past)
    #         trail_columns = [col for col in df.columns if col.startswith("Trail_Capex_P") and col != "Trail_Capex_Past"]

    #         # Calcular la suma total por fila
    #         df["CAPEX_Semester_M$"] = (
    #             df.get("Capex_Past", 0.0)
    #             + df.get("Trail_Capex_Past", 0.0)
    #             + df[capex_columns].sum(axis=1)
    #             + df[trail_columns].sum(axis=1)
    #         )

    #         for idx, row in df.iterrows():
    #             if row["OPEX/CAPEX/Income"] != "CAPEX": #or not row["Opex_Fut"]:
    #                 continue

    #             # active_capex_col = next((col for col in capex_columns if row[col] == True), None)
    #             # if not active_capex_col:
    #             #         continue

                

    #         return df

    #     except Exception as e:
    #         print(f"Error al calcular CAPEX desde annuity: {e}")
    #         return pd.DataFrame()
        
    # def compute_opex_from_annuity(self, final_expanded_structured_costs: pd.DataFrame, opex_structure: pd.DataFrame) -> pd.DataFrame:
    #     "crea el dataframe común sabiendo que tienen en común las columnas State  Year  Semester pero que cada fila de opex se corresponde a muchas filas en final_expanded_structured_costs"
    #     try: 
    #         opex_structure = opex_structure.rename(columns={"State": "state", "Year": "year", "Semester": "semester"})
    #         final_expanded_structured_costs = final_expanded_structured_costs.rename(columns={"State": "state", "Year": "year", "Semester": "semester"})
    #         common_columns = ["state", "year", "semester"]
    #         merged_df = pd.merge(final_expanded_structured_costs, opex_structure, on=common_columns, how="left")
    #         # merged_df = merged_df.dropna(subset=["opex_annuity"])
    #         # merged_df["opex"] = merged_df["opex_annuity"] * merged_df
    #         # ["annuity_factor"]
    #         # merged_df = merged_df.drop(columns=["opex_annuity", "annuity_factor"])
    #         df = final_expanded_structured_costs
    #         mask_app = df["Sub_sector"].str.lower() == "appliances"
    #         print(df.loc[mask_app, ["state", "year", "semester", "Fuel_Id", "Growth_Factor"]].drop_duplicates())
    #         # Imprimir valores en tsv 
    #         df.loc[mask_app, ["state", "year", "semester", "Fuel_Id", "Growth_Factor"]].drop_duplicates().to_csv("appliances_growth_factors_opex.tsv", sep="\t", index=False)
                
    #         return merged_df
    #     except Exception as e:
    #         print(f"Error al calcular opex desde annuity: {e}")
    #         return pd.DataFrame()


    ###JUSt for debugging purposes 
    def compute_opex_from_annuity(
        self,
        final_expanded_structured_costs: pd.DataFrame,
        opex_structure: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Build the common dataframe for OPEX-from-annuity computation.

        It aligns detailed cost rows (per fuel / sector / sub-sector) with
        the OPEX structure defined per (state, year, semester), and exports
        intermediate structures for debugging.
        """
        try:
            import os

            # debug_dir = "debug_opex"
            # os.makedirs(debug_dir, exist_ok=True)

            # # --- Debug: raw inputs ---
            # final_expanded_structured_costs.to_csv(
            #     os.path.join(debug_dir, "final_expanded_structured_costs_raw.tsv"),
            #     sep="\t",
            #     index=False
            # )
            # opex_structure.to_csv(
            #     os.path.join(debug_dir, "opex_structure_raw.tsv"),
            #     sep="\t",
            #     index=False
            # )

            # --- Normalize column names for merge ---
            opex_structure = opex_structure.rename(
                columns={"State": "state", "Year": "year", "Semester": "semester"}
            )
            final_expanded_structured_costs = final_expanded_structured_costs.rename(
                columns={"State": "state", "Year": "year", "Semester": "semester"}
            )

            # --- VERY IMPORTANT: ensure same dtypes for merge keys ---
            for df_ in (final_expanded_structured_costs, opex_structure):
                # Cast to string so that numeric IDs (0, 1, 10, 20) and 'no_name_*'
                # are all handled consistently.
                df_["state"] = df_["state"].astype(str)
                df_["year"] = df_["year"].astype(int)      # both should be numeric
                df_["semester"] = df_["semester"].astype(int)

            common_columns = ["state", "year", "semester"]

            # --- Merge detailed costs with OPEX structure ---
            merged_df = pd.merge(
                final_expanded_structured_costs,
                opex_structure,
                on=common_columns,
                how="left"
            )

            # --- Debug: full merged and flags overview ---
            # merged_df.to_csv(
            #     os.path.join(debug_dir, "opex_merged_full.tsv"),
            #     sep="\t",
            #     index=False
            # )

            debug_cols = [
                "state", "year", "semester",
                "Fuel_Id", "Fuel_name",
                "Sector", "Sub_sector",
                "OPEX/CAPEX/Income",
                "IsReal",
                "Opex_Past", "Opex_Fut",
                "Base prices M$/yr",
                "Growth_Factor",
                "InfraRate",
            ]
            debug_cols = [c for c in debug_cols if c in merged_df.columns]

            # merged_df[debug_cols].drop_duplicates().sort_values(
            #     ["state", "year", "semester", "Fuel_Id"]
            # ).to_csv(
            #     os.path.join(debug_dir, "opex_merged_flags_overview.tsv"),
            #     sep="\t",
            #     index=False
            # )

            return merged_df

        except Exception as e:
            print(f"Error al calcular opex desde annuity: {e}")
            return pd.DataFrame()


        
    # VERSIÖN DECENTE -------
    def _calculate_opex_from_annuity(self, opex_from_annuity: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates Opex_Past and Opex_Fut according to the flags and defined rules.
        - Opex_Past se calcula sólo para los dos primeros semestres del año base,
        usando el precio del año base S1 como referencia para S1 y S2.
        - Opex_Fut se calcula interpolando entre prev y fut, restando siempre el
        BaseCase definido como:
            * En el primer estado real (base year, semestre 1): él mismo
            * En estados S2 (semester == 2): el último REAL con semestre 1 del MISMO año
            * En estados S1 de años posteriores: el último REAL con semestre 1 de un año anterior

        La interpolación usa un alpha temporal basado en la posición de t_curr
        entre t_prev y t_fut:
            t = year + 0.5*(semester-1)
        """
        try:
            import os
            debug_dir = "debug_opex"
            os.makedirs(debug_dir, exist_ok=True)

            # ---------- STEP 1: Opex_Past (solo año base S1 y S2) ----------
            base_year = int(opex_from_annuity["year"].min())

            # Inicializamos columnas numéricas explícitas
            opex_from_annuity["Opex_Past_M$"] = 0.0
            opex_from_annuity["Opex_Fut_M$"] = 0.0  # no la usamos luego pero la dejamos por claridad

            # Sólo filas OPEX o INCOME
            is_opex_or_income = (
                (opex_from_annuity["OPEX/CAPEX/Income"] == "OPEX") |
                (opex_from_annuity["OPEX/CAPEX/Income"] == "INCOME")
            )

            key_cols = ["Fuel_Id", "Fuel_name", "Sector", "Sub_sector", "OPEX/CAPEX/Income"]

            # 1.1. Anchor: año base, semestre 1
            anchor_mask = (
                is_opex_or_income &
                (opex_from_annuity["year"] == base_year) &
                (opex_from_annuity["semester"] == 1)
            )

            anchor_map = {}
            for _, row in opex_from_annuity.loc[anchor_mask, key_cols + ["Base prices M$/yr"]].iterrows():
                key = tuple(row[col] for col in key_cols)
                base_price = float(row["Base prices M$/yr"] or 0.0)
                anchor_map[key] = base_price

            # Debug de anchors
            # pd.DataFrame(
            #     [
            #         {
            #             "Fuel_Id": k[0],
            #             "Fuel_name": k[1],
            #             "Sector": k[2],
            #             "Sub_sector": k[3],
            #             "Type": k[4],
            #             "Base_price_anchor": v,
            #         }
            #         for k, v in anchor_map.items()
            #     ]
            # ).to_csv(
            #     os.path.join(debug_dir, "debug_opex_anchors.tsv"),
            #     sep="\t", index=False
            # )

            # 1.2. Calcular Opex_Past en año base S1 y S2 donde Opex_Past == True
            mask_past_base_two = (
                is_opex_or_income &
                (opex_from_annuity["year"] == base_year) &
                (opex_from_annuity["semester"].isin([1, 2])) &
                (opex_from_annuity["Opex_Past"] == True)
            )

            # Convertimos la columna booleana en numérica para almacenar el valor
            opex_from_annuity["Opex_Past"] = opex_from_annuity["Opex_Past"].astype(float)

            for idx, row in opex_from_annuity.loc[mask_past_base_two].iterrows():
                key = tuple(row[col] for col in key_cols)
                base_price_anchor = anchor_map.get(key, 0.0)

                if base_price_anchor != 0.0:
                    growth = float(row["Growth_Factor"] or 0.0)
                    # año base S1/S2 → precio anual / 2 (semestre) * growth
                    opex_from_annuity.at[idx, "Opex_Past"] = (base_price_anchor / 2.0) * growth
                else:
                    opex_from_annuity.at[idx, "Opex_Past"] = 0.0

            # Debug Opex_Past
            # opex_from_annuity.loc[mask_past_base_two, [
            #     "state", "year", "semester",
            #     "Fuel_Id", "Fuel_name", "Sector", "Sub_sector",
            #     "OPEX/CAPEX/Income", "Base prices M$/yr",
            #     "Growth_Factor", "Opex_Past"
            # ]].sort_values(["Fuel_Id","Sector","Sub_sector","year","semester"])\
            # .to_csv(
            #     os.path.join(debug_dir, "debug_opex_past.tsv"),
            #     sep="\t", index=False
            # )

            # ---------- STEP 2: Opex_Fut con alpha temporal y last_year_BCASE ----------
            df = opex_from_annuity.copy()
            df["Opex_Fut_result"] = 0.0
            debug_rows = []

            def _select_basecase_row(current_row: pd.Series, group: pd.DataFrame, base_year_value: int) -> pd.Series:
                """
                Devuelve la fila 'BaseCase' según la lógica:
                - En baseYear & semestre 1: el propio año base S1.
                - En semestre 2: el S1 real del MISMO año; si no existe, el último S1 real de año anterior.
                - En semestre 1 de años posteriores: el último S1 real de año anterior.
                """
                real_s1 = group[
                    (group["IsReal"].astype(bool) == True) &
                    (group["semester"] == 1)
                ].sort_values(by=["year", "semester"])

                if real_s1.empty:
                    # Fallback: último real cualquiera
                    fallback = group[group["IsReal"].astype(bool) == True].sort_values(by=["year", "semester"])
                    return fallback.iloc[0] if not fallback.empty else current_row

                curr_year = int(current_row["year"])
                curr_sem = int(current_row["semester"])

                # Caso especial: primer estado base (year == base_year, sem == 1)
                if (curr_year == base_year_value) and (curr_sem == 1):
                    same_year = real_s1[real_s1["year"] == curr_year]
                    return same_year.iloc[0] if not same_year.empty else real_s1.iloc[0]

                if curr_sem >= 2:
                    # Estados S2 (o superiores): BaseCase = S1 real del mismo año si existe
                    same_year = real_s1[real_s1["year"] == curr_year]
                    if not same_year.empty:
                        return same_year.iloc[-1]
                    # Si no existe S1 real en este año, coger último S1 real anterior
                    before = real_s1[real_s1["year"] < curr_year]
                    if not before.empty:
                        return before.iloc[-1]
                    return real_s1.iloc[0]

                # curr_sem == 1 y no es el año base:
                # BaseCase = último S1 real de un año anterior
                before = real_s1[real_s1["year"] < curr_year]
                if not before.empty:
                    return before.iloc[-1]

                # Si no hay años anteriores, usar el S1 del propio año (fallback)
                same_year = real_s1[real_s1["year"] == curr_year]
                if not same_year.empty:
                    return same_year.iloc[0]

                return real_s1.iloc[0]

            # Recorremos filas para Opex_Fut
            for idx, row in df.iterrows():
                if row["OPEX/CAPEX/Income"] not in ["OPEX", "INCOME"] or row["Opex_Fut"] is False:
                    continue

                same_group = (
                    (df["Fuel_Id"] == row["Fuel_Id"]) &
                    (df["Fuel_name"] == row["Fuel_name"]) &
                    (df["Sector"] == row["Sector"]) &
                    (df["Sub_sector"] == row["Sub_sector"]) &
                    ((df["OPEX/CAPEX/Income"] == "OPEX") | (df["OPEX/CAPEX/Income"] == "INCOME"))
                )

                group = df[same_group].copy()
                if group.empty:
                    continue

                group = group.sort_values(by=["year", "semester"])
                current_year = row["year"]
                current_semester = row["semester"]

                # --- PREV: último REAL anterior o igual ---
                previous_real = group[
                    (((group["year"] < current_year) |
                    ((group["year"] == current_year) & (group["semester"] <= current_semester))) &
                    (group["IsReal"].astype(bool) == True))
                ].sort_values(by=["year", "semester"])

                if row["IsReal"]:
                    # incluye el propio estado para que si es real, pueda ser ancla
                    previous_or_current = pd.concat(
                        [previous_real, pd.DataFrame([row])]
                    ).sort_values(by=["year", "semester"]).tail(1)
                else:
                    previous_or_current = previous_real.tail(1)

                if previous_or_current.empty:
                    # sin anclaje previo → no interpolamos
                    debug_rows.append({
                        "Fuel_Id": row["Fuel_Id"],
                        "Fuel_name": row["Fuel_name"],
                        "Sector": row["Sector"],
                        "Sub_sector": row["Sub_sector"],
                        "state_current": row["state"],
                        "year_current": row["year"],
                        "semester_current": row["semester"],
                        "reason": "no_prev_real",
                    })
                    continue

                prev_row = previous_or_current.iloc[0]

                # --- FUT: primer REAL futuro ---
                future_real = group[
                    (((group["year"] > current_year) |
                    ((group["year"] == current_year) & (group["semester"] > current_semester))) &
                    (group["IsReal"].astype(bool) == True))
                ].sort_values(by=["year", "semester"])

                # Si el actual es real y no hay futuro, tratamos el propio estado como futuro
                if row["IsReal"] and future_real.empty:
                    future_real = pd.DataFrame([row])

                if future_real.empty:
                    debug_rows.append({
                        "Fuel_Id": row["Fuel_Id"],
                        "Fuel_name": row["Fuel_name"],
                        "Sector": row["Sector"],
                        "Sub_sector": row["Sub_sector"],
                        "state_current": row["state"],
                        "year_current": row["year"],
                        "semester_current": row["semester"],
                        "reason": "no_future_real",
                    })
                    continue

                fut_row = future_real.iloc[0]

                # ---- NUEVA LÓGICA DE BASECASE ----
                basecase_row = _select_basecase_row(row, group, base_year)

                # Proteger Growth_Factor == 0 en las filas usadas
                for r in (basecase_row, prev_row, fut_row):
                    gf = r["Growth_Factor"]
                    if (gf is None) or (gf == 0):
                        r["Growth_Factor"] = 1.0

                # Precios deflactados por Growth_Factor (en términos "por semestre")
                last_year_BCASE = (
                    (basecase_row["Base prices M$/yr"] / 2.0) /
                    basecase_row["Growth_Factor"]
                )
                base_prev = (prev_row["Base prices M$/yr"] / 2.0) / prev_row["Growth_Factor"]
                base_fut = (fut_row["Base prices M$/yr"] / 2.0) / fut_row["Growth_Factor"]

                # ---- Alpha temporal entre prev y fut ----
                t_prev = float(prev_row["year"]) + 0.5 * (int(prev_row["semester"]) - 1)
                t_fut = float(fut_row["year"]) + 0.5 * (int(fut_row["semester"]) - 1)
                t_curr = float(row["year"]) + 0.5 * (int(row["semester"]) - 1)

                if t_fut > t_prev:
                    alpha = (t_curr - t_prev) / (t_fut - t_prev)
                else:
                    alpha = 0.0

                # Clip por seguridad
                alpha = max(0.0, min(1.0, alpha))

                # ---------- Interpolación con last_year_BCASE ----------
                # Versión "BCASE": movemos desde last_year_BCASE hacia base_fut
                # usando alpha temporal, luego volvemos a inflar con Growth e InfraRate
                #sem_deflated = last_year_BCASE + ((base_fut - base_prev) * prev_row["InfraRate"]) * alpha 
                sem_deflated = base_prev + (base_fut - base_prev) * alpha
                growth_curr = float(row.get("Growth_Factor", 1.0) or 1.0)
                infra_curr = float(row.get("InfraRate", 1.0) or 1.0)

                interpolated = sem_deflated * growth_curr #* infra_curr

                df.at[idx, "Opex_Fut_result"] = interpolated

                # ---- DEBUG: guardar info de esta interpolación ----
                debug_rows.append({
                    "state": row["state"],
                    "year": row["year"],
                    "semester": row["semester"],
                    "Fuel_Id": row["Fuel_Id"],
                    "Fuel_name": row["Fuel_name"],
                    "Sector": row["Sector"],
                    "Sub_sector": row["Sub_sector"],
                    "IsReal_current": bool(row["IsReal"]),
                    "BasePrice_current": row["Base prices M$/yr"],
                    "Growth_current": growth_curr,
                    "InfraRate_current": infra_curr,

                    "BaseCase_state": basecase_row["state"],
                    "BaseCase_year": basecase_row["year"],
                    "BaseCase_semester": basecase_row["semester"],
                    "BaseCase_BasePrice": basecase_row["Base prices M$/yr"],
                    "BaseCase_scalar_defl": last_year_BCASE,

                    "Prev_state": prev_row["state"],
                    "Prev_year": prev_row["year"],
                    "Prev_semester": prev_row["semester"],
                    "Prev_BasePrice": prev_row["Base prices M$/yr"],
                    "Base_prev_defl": base_prev,

                    "Fut_state": fut_row["state"],
                    "Fut_year": fut_row["year"],
                    "Fut_semester": fut_row["semester"],
                    "Fut_BasePrice": fut_row["Base prices M$/yr"],
                    "Base_fut_defl": base_fut,

                    "t_prev": t_prev,
                    "t_curr": t_curr,
                    "t_fut": t_fut,
                    "alpha": alpha,
                    "Sem_deflated_interp": sem_deflated,
                    "Opex_Fut_result": interpolated,
                })

            # Volcar debug de interpolaciones
            # if debug_rows:
            #     pd.DataFrame(debug_rows).sort_values(
            #         ["Fuel_Id","Sector","Sub_sector","year","semester"]
            #     ).to_csv(
            #         os.path.join(debug_dir, "debug_opex_interpolation.tsv"),
            #         sep="\t", index=False
            #     )

            # Asignar resultado y sumar Past + Fut
            df["Opex_Fut"] = df["Opex_Fut_result"]
            df = df.drop(columns=["Opex_Fut_result"])

            df["OPEX_Semester_M$"] = df["Opex_Past"] + df["Opex_Fut"]

            return df

        except Exception as e:
            print(f"Error al calcular OPEX desde annuity: {e}")
            return pd.DataFrame()


    # VERSIÖN FINAL 
    


    # def _calculate_opex_from_annuity(self, opex_from_annuity: pd.DataFrame) -> pd.DataFrame:
    #     """
    #     Calculates Opex_Past and Opex_Fut according to the flags and defined rules.
    #     """
    #     try:
    #         # Paso 1: tu lógica de Opex_Past, déjala como la tienes ahora mismo
    #         df = opex_from_annuity.copy()
    #         df["Opex_Fut_result"] = 0.0

    #         key_cols = ["state", "Fuel_Id", "Fuel_name", "Sector", "Sub_sector", "OPEX/CAPEX/Income"]

    #         debug_rows = []  # <-- aquí acumulamos info de depuración

    #         for idx, row in df.iterrows():
    #             if row["OPEX/CAPEX/Income"] not in ["OPEX", "INCOME"] or row["Opex_Fut"] == False:
    #                 continue

    #             same_group = (
    #                 (df["Fuel_Id"] == row["Fuel_Id"]) &
    #                 (df["Fuel_name"] == row["Fuel_name"]) &
    #                 (df["Sector"] == row["Sector"]) &
    #                 (df["Sub_sector"] == row["Sub_sector"]) &
    #                 ((df["OPEX/CAPEX/Income"] == "OPEX") | (df["OPEX/CAPEX/Income"] == "INCOME"))
    #             )

    #             group = df[same_group].copy()
    #             if group.empty:
    #                 continue

    #             group = group.sort_values(by=["year", "semester"])
    #             current_year = row["year"]
    #             current_semester = row["semester"]

    #             previous = group[
    #                 (((group["year"] < current_year) |
    #                 ((group["year"] == current_year) & (group["semester"] <= current_semester))) &
    #                 (group["IsReal"].astype(bool) == True))
    #             ].sort_values(by=["year", "semester"])

    #             if row["IsReal"] == True:
    #                 previous_or_current = pd.concat(
    #                     [previous, pd.DataFrame([row])]
    #                 ).sort_values(by=["year", "semester"]).tail(1)
    #             else:
    #                 previous_or_current = previous.tail(1)

    #             future = group[
    #                 (((group["year"] > current_year) |
    #                 ((group["year"] == current_year) & (group["semester"] > current_semester))) &
    #                 (group["IsReal"].astype(bool) == True))
    #             ].sort_values(by=["year", "semester"])

    #             if row["IsReal"] and future.empty:
    #                 future = pd.DataFrame([row])

    #             if previous_or_current.empty or future.empty:
    #                 # Guardamos también los casos donde *no* encuentra prev/fut, para verlos
    #                 debug_rows.append({
    #                     "state_current": row["state"],
    #                     "year_current": row["year"],
    #                     "semester_current": row["semester"],
    #                     "IsReal_current": bool(row["IsReal"]),
    #                     "Fuel_Id": row["Fuel_Id"],
    #                     "Fuel_name": row["Fuel_name"],
    #                     "Sector": row["Sector"],
    #                     "Sub_sector": row["Sub_sector"],
    #                     "reason": "missing_prev_or_future",
    #                 })
    #                 continue

    #             prev_row = previous_or_current.iloc[0]
    #             fut_row = future.iloc[0]

    #             base_prev = (prev_row["Base prices M$/yr"] / 2) * prev_row["Growth_Factor"]
    #             base_fut = (fut_row["Base prices M$/yr"] / 2) * fut_row["Growth_Factor"]

    #             interpolated = base_prev + (base_fut - base_prev) * row["Growth_Factor"] * row["InfraRate"]

    #             df.at[idx, "Opex_Fut_result"] = interpolated

    #             # ---- DEBUG: qué anclas está usando para este estado ----
    #             debug_rows.append({
    #                 "Fuel_Id": row["Fuel_Id"],
    #                 "Fuel_name": row["Fuel_name"],
    #                 "Sector": row["Sector"],
    #                 "Sub_sector": row["Sub_sector"],
    #                 "state_current": row["state"],
    #                 "year_current": row["year"],
    #                 "semester_current": row["semester"],
    #                 "IsReal_current": bool(row["IsReal"]),
    #                 "Growth_current": row["Growth_Factor"],
    #                 "InfraRate_current": row["InfraRate"],

    #                 "prev_state": prev_row["state"],
    #                 "prev_year": prev_row["year"],
    #                 "prev_semester": prev_row["semester"],
    #                 "IsReal_prev": bool(prev_row["IsReal"]),
    #                 "BasePrev_M$/yr": prev_row["Base prices M$/yr"],
    #                 "Growth_prev": prev_row["Growth_Factor"],
    #                 "BasePrev_sem_M$": base_prev,

    #                 "fut_state": fut_row["state"],
    #                 "fut_year": fut_row["year"],
    #                 "fut_semester": fut_row["semester"],
    #                 "IsReal_fut": bool(fut_row["IsReal"]),
    #                 "BaseFut_M$/yr": fut_row["Base prices M$/yr"],
    #                 "Growth_fut": fut_row["Growth_Factor"],
    #                 "BaseFut_sem_M$": base_fut,

    #                 "Opex_Fut_result": interpolated,
    #             })

    #         # Volcar la tabla de depuración a TSV
    #         if debug_rows:
    #             import os
    #             debug_df = pd.DataFrame(debug_rows)
    #             os.makedirs("debug_opex", exist_ok=True)
    #             debug_df.sort_values(
    #                 ["Fuel_Id", "Fuel_name", "Sector", "Sub_sector", "year_current", "semester_current"],
    #                 inplace=True
    #             )
    #             debug_df.to_csv("debug_opex/opex_prev_future_anchors.tsv", sep="\t", index=False)

    #         df["Opex_Fut"] = df["Opex_Fut_result"]
    #         df = df.drop(columns=["Opex_Fut_result"])

    #         df["OPEX_Semester_M$"] = df["Opex_Past"] + df["Opex_Fut"]

    #         return df

    #     except Exception as e:
    #         print(f"Error al calcular OPEX desde annuity: {e}")
    #         return pd.DataFrame()




   

        

    def merge_opex_capex(self, 
        df_opex: pd.DataFrame, df_capex: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Merges OPEX and CAPEX dataframes on common columns.
        """
        try:
            # Limpieza básica de columnas
            # df_opex.columns = df_opex.columns.str.strip()
            # df_capex.columns = df_capex.columns.str.strip()
            df_opex.columns = [str(c).strip() for c in df_opex.columns]
            df_capex.columns = [str(c).strip() for c in df_capex.columns]


            # Columnas clave para el merge
            merge_keys = [
                "state", "year", "semester", "Fuel_Id", "Fuel_name",
                "Sector", "Sub_sector", "OPEX/CAPEX/Income"
            ]

            # Filtra sólo columnas necesarias
            df_opex_sel = df_opex[merge_keys + ["OPEX_Semester_M$"]]
            df_capex_sel = df_capex[merge_keys + ["CAPEX_Semester_M$"]]

            # Merge por claves comunes
            df_merged = pd.merge(df_opex_sel, df_capex_sel, on=merge_keys, how="outer")

            # Crea columna final con lógica condicional
            def resolve_value(row):
                tipo = row["OPEX/CAPEX/Income"]
                if tipo == "OPEX" or tipo == "INCOME":
                    return row["OPEX_Semester_M$"]
                elif tipo == "CAPEX":
                    return row["CAPEX_Semester_M$"]
                else:
                    return None

            df_merged["M$/yr"] = df_merged.apply(resolve_value, axis=1)

            # Deja solo las columnas finales deseadas
            final_cols = merge_keys + ["M$/yr"]
            return df_merged[final_cols]

        except Exception as e:
            print(f"Error merging OPEX and CAPEX: {e}")
            return pd.DataFrame()
        

    def aggregate_to_yearly(self, df):
        """
        Groups the DataFrame by year and relevant keys, summing the M$/yr values.
        """
        try:
            # Asegúrate de que las columnas estén limpias
            #df.columns = df.columns.str.strip()
            df.columns = [str(c).strip() for c in df.columns]


            # Elimina columnas que ya no se usarán
            df = df.drop(columns=["state", "semester"], errors="ignore")

            # Agrupación por año y claves relevantes
            group_keys = [
                "year", "Fuel_Id", "Fuel_name", "Sector", "Sub_sector", "OPEX/CAPEX/Income"
            ]

            # Agrupación y suma
            df_yearly = df.groupby(group_keys, as_index=False)["M$/yr"].sum()

            return df_yearly

        except Exception as e:
            print(f"Error al agrupar por año: {e}")
            return pd.DataFrame()

    

    def _compute_global_appliance_weights(self) -> Dict[int, Dict[int, float]]:
        """
        Agrega las participaciones de appliances por fuel a lo largo de TODOS los estados
        y devuelve un único mapa global:
            { fuel_id: { appliance_id: peso_medio } }
        """
        sum_weights = defaultdict(lambda: defaultdict(float))  # fuel -> appl -> suma_w
        states_count = defaultdict(int)                       # fuel -> nº estados con datos

        for ms in self.mixed_states:
            financial_params = ms.get_financial_results()

            appl_struct = getattr(financial_params, "average_growth_calculation_appliances", None)
            per_state = getattr(appl_struct, "appliances", {}) if appl_struct is not None else {}

            if not per_state:
                continue

            # per_state: { fuel_id: { appliance_id: weight_en_ese_estado } }
            for fuel_id, app_map in per_state.items():
                if not app_map:
                    continue

                # contamos solo estados donde hay algún peso para ese fuel
                states_count[fuel_id] += 1

                for app_id, w in app_map.items():
                    sum_weights[fuel_id][app_id] += float(w or 0.0)

        # Ahora promediamos por nº de estados y renormalizamos a suma≈1
        global_weights: Dict[int, Dict[int, float]] = {}

        for fuel_id, apps in sum_weights.items():
            n = states_count.get(fuel_id, 0)
            if n <= 0:
                continue

            # media simple de las participaciones a lo largo de los estados donde había datos
            avg_map = {int(app_id): (val / n) for app_id, val in apps.items()}

            total = sum(avg_map.values())
            if total > 0.0:
                avg_map = {aid: v / total for aid, v in avg_map.items()}

            global_weights[int(fuel_id)] = avg_map

        # DEBUG opcional
        self.logger.warning(f"[APPL GLOBAL WEIGHTS] Pesos globales por fuel: {global_weights}")

        return global_weights
 
        
    

    
   

    

