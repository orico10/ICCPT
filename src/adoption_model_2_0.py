import numpy as np
import pandas as pd
from scipy.optimize import linprog
import logging
import copy


class AdoptionModel2_0:
    """
    AdoptionModel 2.0: implements improvements in vectorization, discrete choice (logit),
    convex optimization (LP), and checking for areas without consumption.
    """
    def __init__(
        self,
        state,
        prev_state,
        growth_scenario,
        #simulation_plan,
        demand_area,
        data_manager,
        tech_df
    ):
        # Datos de entrada
        self.state = state
        self.prev_state = prev_state
        self.growth = growth_scenario
        #self.sim_plan = simulation_plan
        self.demand_area = demand_area
        # Tecnologías como DataFrame
        self.data_manager = data_manager
        
        self.technologies = tech_df.copy().set_index('Technologies_id')
        enriched_technologies_df = data_manager.get_dataframe("enriched_technologies")
        self.all_technologies = enriched_technologies_df.set_index("Technologies_id")  # universo completo
        # Parámetros logit (sensibilidades)
        self.lambda_cost = getattr(growth_scenario, 'logit_lambda', 1.0)
        self.mu_social = getattr(growth_scenario, 'logit_mu', 1.0)
        # Capacidades por área y tecnología (vectorizar después)
        # Relación fuel y appliance con nombre
        self.fuel_id_to_name = dict(zip(
            data_manager.get_dataframe("Cooking_fuels")["Fuel_id"],
            data_manager.get_dataframe("Cooking_fuels")["Fuel_name"]
        ))
        self.appl_id_to_name = dict(zip(
            data_manager.get_dataframe("Cooking_appliances")["Appliance_id"],
            data_manager.get_dataframe("Cooking_appliances")["Appl_name"]
        ))
        # Relación fuel y appliance con nombre
        self.fuel_id_to_name = dict(zip(
            data_manager.get_dataframe("Cooking_fuels")["Fuel_id"],
            data_manager.get_dataframe("Cooking_fuels")["Fuel_name"]
        ))
        appl_df = data_manager.get_dataframe("Cooking_appliances")

        self.appl_retail_price = dict(zip(appl_df["Appliance_id"], appl_df["Retail_price"]))

        # Planes de precio y despliegue
        #price_plan_details = state.price_plan.details
        self.price_plans_fuels = {} #price_plan_details.get("fuel_price", [])
        self.price_plans_appl = {} #price_plan_details.get("app_price", [])
        # Reserva para adopción potencial
        #deployment_plan_details = state.deployment_plan.details 
        self.deployment_plan_appliances_max_cap = {} #deployment_plan_details.get("appliances_max_cap", [])
        self.deployment_plan_fuels_max_cap = {} #deployment_plan_details.get("fuel_max_cap", [])
        self.potential_adoption = {}

    def _prep_growth_cache(self):
        # Convierte list[dict] / dict en: {0: {...}, 1: {...}} usando Is_Urban como clave
        def by_u(rows):
            out = {0: {}, 1: {}}
            if isinstance(rows, dict):
                # si ya viene como dict, normalizamos a lista
                rows = [rows]
            for r in rows:
                u = int(r.get("Is_Urban", 0))
                for k, v in r.items():
                    if k != "Is_Urban":
                        try:
                            out[u][k] = float(v)
                        except (TypeError, ValueError):
                            out[u][k] = v
            return out

        self._g_dem_mult  = by_u(self.growth.dem_mult)   # {0:{Electricity,...}, 1:{...}}
        self._g_dem_elast = by_u(self.growth.dem_elast)  # {0:{Electricity:...}, 1:{...}}
        self._g_soc_clus  = by_u(self.growth.soc_clus)   # {0:{Population_growth,...}, 1:{...}}


    @property
    def area_types(self):
        """
       Returns ['rural'] or ['urban'] if self.demand_area.area_type is defined,
        or both ['rural', 'urban'] if not defined (None).
        """
        return [self.demand_area.area_type] if self.demand_area.area_type else ['rural', 'urban']


    

    def run_simulation(self):
        """Main execution loop for income calculations across rural and urban areas."""
        try:
            results = {}
            self.simulate_state()

            for area in self.area_types: #['rural', 'urban']:
                base_cook = self.demand_area.data.get('demand_census_rur_urb', {}).get(area, {}).get('cooking', 0)

                if base_cook == 0:
                    init_zero = {t: 0.0 for t in self.technologies['Tech_name']}
                    init_zero_by_id = {tid: 0.0 for tid in self.technologies.index}
                    self.demand_area.data['initial_adoptions'][area] = init_zero
                    self.state.set_initial_adoption(self.demand_area.id, area, init_zero_by_id)
                    results[area] = pd.Series(init_zero_by_id)
                    continue

                if not self.demand_area.data['initial_adoptions'].get(area):
                    default_init = {t: 0.0 for t in self.technologies['Tech_name']}
                    self.demand_area.data['initial_adoptions'][area] = default_init
                    self.state.set_initial_adoption(
                        self.demand_area.id,
                        area,
                        {tid: default_init[self.technologies.at[tid, 'Tech_name']] for tid in self.technologies.index}
                    )

                params = self._update_social_params(area)
                df = self._compute_indicators(area, params)
                init_cand = self._compute_init_candidates(df, area)
                pot_lp = self._adoption_lp(init_cand, area)
                results[area] = pot_lp

            self.potential_adoption = results
            self.save_results_to_state()
            return results
        except Exception as e:
            logging.error("Error en la simulación de adopción: %s", str(e), exc_info=True)
            raise

    def simulate_state(self):
        """ Simulate the state of the demand area. Adjusts the initial adoptions based on the previous state. """
        try: 
            self.demand_area.data.setdefault('initial_adoptions', {'rural': {}, 'urban': {}})
            base_year = self.growth.base_year
            year = self.state.year
            semester = self.state.semester

            if (year > base_year) or (year == base_year and semester == "second"):
                self.updateInitAdoption(self.prev_state)

            self.save_results_init_to_state()

            
            current_price_plan = self.state.price_plan.details
            self.price_plans_fuels = current_price_plan.get("fuel_price", [])
            self.price_plans_appl = current_price_plan.get("app_price", [])
            current_deployment_plan = self.state.deployment_plan.details
            self.deployment_plan_appliances_max_cap = current_deployment_plan.get("appliances_max_cap", [])
            self.deployment_plan_fuels_max_cap = current_deployment_plan.get("fuel_max_cap", [])
        except Exception as e:
            logging.error("Error en la simulación del estado: %s", str(e), exc_info=True)
            raise
    
    

  
    def updateInitAdoption(self, prev_state):
        """ Update initial adoptions from the previous state. """
        try:
            tech_id_to_name = self.all_technologies["Tech_name"].to_dict()  # <- usar todas
            for area_type in self.area_types:
                prev_potential = prev_state.get_potential_adoption(self.demand_area.id, area_type)
                if not isinstance(prev_potential, dict):
                    continue
                self.demand_area.data['initial_adoptions'].setdefault(area_type, {})
                for tech_id, value in prev_potential.items():
                    tech_name = tech_id_to_name.get(tech_id)
                    if tech_name:
                        self.demand_area.data['initial_adoptions'][area_type][tech_name] = value
        except Exception as e:
            logging.error("Error actualizando adopciones iniciales: %s", e, exc_info=True)
            raise


    def save_results_init_to_state(self):
        """ Save initial adoptions to the state. """
        try:
            for area_type in self.area_types:
                adoptions = self.demand_area.data['initial_adoptions'].get(area_type, {})
                full_tech_ids = self.all_technologies.index.tolist()
                full_tech_names = self.all_technologies["Tech_name"]

                values_by_id = {
                    tid: adoptions.get(full_tech_names[tid], 0.0)
                    for tid in full_tech_ids
                }

                self.state.set_initial_adoption(self.demand_area.id, area_type, values_by_id)
        except Exception as e:
            logging.error("Error guardando adopciones iniciales: %s", e, exc_info=True)
            raise


    def _update_social_params(self, area):
        """Actualiza los parámetros sociales para el área dada (sin pandas)."""
        try:
            if not hasattr(self, "_g_dem_mult"):
                self._prep_growth_cache()

            u = 1 if area == "urban" else 0
            year_diff = self.state.year - self.growth.base_year

            gm = self._g_dem_mult[u]
            ge = self._g_dem_elast[u]
            gs = self._g_soc_clus[u]

            aggr = self.demand_area.data['aggregated_clusters'][area]

            # base_params snapshot superficial (una vez)
            base = aggr.get('base_params')
            if base is None:
                base = aggr['base_params'] = dict(aggr['params'])

            # Partimos de base (shallow) para no acumular factores en cada llamada
            params = dict(base)

            # Demand multipliers (Electricity/Cooking/Heating)
            dm0 = params.get('DemandMult', {})
            params['DemandMult'] = {
                'Electricity': float(dm0.get('Electricity', 1.0)) * (1.0 + float(gm.get('Electricity', 0.0))) ** year_diff,
                'Cooking':    float(dm0.get('Cooking',    1.0)) * (1.0 + float(gm.get('Cooking',    0.0))) ** year_diff,
                'Heating':    float(dm0.get('Heating',    1.0)) * (1.0 + float(gm.get('Heating',    0.0))) ** year_diff,
            }

            # Elasticidad electricidad
            base_elast = float(params.get('e_elast_demand', 1.0))
            params['e_elast_demand'] = base_elast * (1.0 - float(ge.get('Electricity', 0.0))) ** year_diff

            # Población (si quieres multiplicativo sobre base, cambia la fórmula)
            params['Population'] = (1.0 + float(gs.get('Population_growth', 0.0))) ** year_diff

            inc_growth = float(gs.get('Income_growth', 0.0))
            params['will_pay']   = float(params.get('will_pay',   1.0)) * (1.0 + inc_growth) ** year_diff
            params['invest_cap'] = float(params.get('invest_cap', 1.0)) * (1.0 + inc_growth) ** year_diff

            # Tecnología (change/better/worse bounded)
            tech_prog = (1.0 + float(gs.get('Technology_progress', 0.0))) ** year_diff
            params['change_fact'] = min(1.0, float(params.get('change_fact', 1.0)) * tech_prog)
            params['better_fact'] = float(params.get('better_fact', 1.0)) * tech_prog
            params['worse_fact']  = float(params.get('worse_fact',  1.0)) * tech_prog

            # Social weight acotado a [0,1]
            params['social_weight'] = min(
                1.0,
                float(params.get('social_weight', 1.0)) * (1.0 + float(gs.get('Social_weight', 0.0))) ** year_diff
            )

            # Social balance re-normalizado
            sb = params.get('social_balance', {})
            new_sb = {}
            total = 0.0
            for key, gkey in (('health','Health'), ('time_gender','Time_gen'), ('emissions','Emissions')):
                val = float(sb.get(key, 0.0)) * (1.0 + float(gs.get(gkey, 0.0))) ** year_diff
                new_sb[key] = val
                total += val

            # Completa deforestation y normaliza si hay masa
            new_sb['deforestation'] = max(1.0 - total, 0.0)
            s = sum(new_sb.values())
            if s > 0.0:
                for k in new_sb:
                    new_sb[k] = new_sb[k] / s
            params['social_balance'] = new_sb

            # Persistir en el objeto
            aggr['params'] = params
            return params

        except Exception as e:
            logging.error("Error actualizando parámetros sociales: %s", e, exc_info=True)
            raise


   

    def _compute_indicators(self, area, soc_params):
        """Calculate indicators for the given area and compute projection weights."""
        try:
            tech = self.technologies           # NO copy
            idx  = tech.index

            # --- columnas a arrays (sin copia) ---
            tech_names = tech["Tech_name"].to_numpy(copy=False)

            health = tech["Health"].to_numpy(copy=False)
            emis   = tech["Emissions"].to_numpy(copy=False)
            defor  = tech["Deforestation"].to_numpy(copy=False)
            t_fuel = tech["FuelTimeGen"].to_numpy(copy=False)
            t_appl = tech["ApplianceTimeGen"].to_numpy(copy=False)

            p_fuel_base = tech["FuelPrice"].to_numpy(copy=False)
            p_appl_base = tech["AppliancePrice"].to_numpy(copy=False)
            

            fuel_id_arr = tech["Fuel_id"].to_numpy(copy=False)
            appl_id_arr = tech["Appliance_id"].to_numpy(copy=False)

            # --- 1) init y time_vec sin pandas ---
            init_dict = self.demand_area.data['initial_adoptions'][area]  # {tech_name: val}
            init = np.fromiter((init_dict.get(name, 0.0) for name in tech_names),
                            dtype=np.float64, count=tech_names.size)

            # tgm_by_area = self.demand_area.data.get("time_gen_modified", {}).get(area, {})
            # # tgm_by_area puede ser dict o Serie; lo normalizamos a dict {tech_name: mult}
            # if hasattr(tgm_by_area, "to_dict"):
            #     tgm_by_area = tgm_by_area.to_dict()
            # time_vec = np.fromiter((tgm_by_area.get(name, 1.0) for name in tech_names),
            #                     dtype=np.float64, count=tech_names.size)
            tgm_root = self.demand_area.data.get("time_gen_modified", {}) or {}
            # tgm_root: {tech_name: {area: value}}

            time_vec = np.fromiter(
                (float((tgm_root.get(name, {}) or {}).get(area, 1.0)) for name in tech_names),
                dtype=np.float64,
                count=tech_names.size
            )



            # --- 2) referencias para normalizar S ---
            ref_h = max(float(np.dot(init, health)), 1e-12)
            ref_t = max(float(np.dot(init, time_vec)), 1e-12)
            ref_e = max(float(np.dot(init, emis)),   1e-12)
            ref_d = max(float(np.dot(init, defor)),  1e-12)

            # --- 3) S: score social (todo en arrays) ---
            w = soc_params['social_balance']
            S = (health / ref_h) * w['health'] \
            #+ ((t_fuel + t_appl) / ref_t) * w['time_gender'] \
            + ((time_vec) / ref_t) * w['time_gender']
            + (emis   / ref_e) * w['emissions'] \
            + (defor  / ref_d) * w['deforestation']

            # --- 4) multiplicadores de precio sin Series.map ---
            #   Preparamos diccionarios:
            fuel_id_to_name = self.fuel_id_to_name          # {fid: name}
            appl_id_to_name = self.appl_id_to_name          # {aid: name}

            def first_hit_dict(lst):
                out = {}
                for d in lst or []:
                    for k, v in d.items():
                        if k not in out:
                            out[k] = v
                return out

            plan_fuels = first_hit_dict(getattr(self, "price_plans_fuels", []))  # {name: mult}
            plan_appls = first_hit_dict(getattr(self, "price_plans_appl", []))   # {name: mult}

            # Local multipliers por área (por nombre de fuel)
            bm_loc = self.demand_area.data.get("biomass_multipliers", {}).get("loc_price", {})
            # dict name->mult (para este area)
            fuel_loc_mult_by_name = {name: area_map.get(area, 1.0) for name, area_map in bm_loc.items()}

            #   a) Fuel: calculamos sobre IDs únicos y expandimos
            uniq_fuel, inv_fuel = np.unique(fuel_id_arr, return_inverse=True)
            fuel_mult_uniq = np.empty_like(uniq_fuel, dtype=np.float64)
            for i, fid in enumerate(uniq_fuel):
                name = fuel_id_to_name.get(int(fid), "")
                plan_mult = plan_fuels.get(name, 1.0)
                loc_mult  = fuel_loc_mult_by_name.get(name, 1.0)
                fuel_mult_uniq[i] = float(plan_mult) * float(loc_mult)

            fuel_mult = fuel_mult_uniq[inv_fuel]

            #   b) Appliance: IDs únicos → plan_appls por nombre → expandir
            uniq_appl, inv_appl = np.unique(appl_id_arr, return_inverse=True)
            appl_mult_uniq = np.empty_like(uniq_appl, dtype=np.float64)
            for i, aid in enumerate(uniq_appl):
                name = appl_id_to_name.get(int(aid), "")
                appl_mult_uniq[i] = float(plan_appls.get(name, 1.0))
            appl_plan_mult = appl_mult_uniq[inv_appl]

            # --- 5) precios absolutos y relativos ---
            p_fuel = p_fuel_base * fuel_mult
            p_appl = p_appl_base * appl_plan_mult

            p_time = float(soc_params.get('social_weight', 1.0)) * float(soc_params.get('will_pay', 1.0)) * time_vec
            C = p_fuel + p_appl + p_time

            C_rel_factor = max(float(np.dot(C, init) + float(soc_params.get('will_pay', 0.0))) / 2.0, 0.01)
            C_rel = C / C_rel_factor

            # --- 6) proyección ---
            soc_weight  = float(soc_params.get("social_weight", 1.0))
            better_fact = float(soc_params.get("better_fact", 1.0))
            worse_fact  = float(soc_params.get("worse_fact", 1.0))

            soc_econ_rep = soc_weight * S + (1.0 - soc_weight) * C_rel
            max_soc_econ_rep = np.clip(soc_econ_rep, 0.001, None)

            projection_weights = np.where(
                soc_econ_rep <= 1.0,
                1.0 + better_fact * (1.0 / max_soc_econ_rep - 1.0),
                1.0 / (1.0 + worse_fact * (soc_econ_rep - 1.0))
            )

            # --- 7) Resultado (crea el DF solo si lo necesitas) ---
            df = pd.DataFrame({"C": C, "S": S, "W": projection_weights}, index=idx)

            if not hasattr(self, "projection_weights"):
                self.projection_weights = {}
            self.projection_weights[area] = pd.Series(projection_weights, index=idx)

            return df

        except Exception as e:
            logging.error("Error calculando indicadores: %s", e, exc_info=True)
            raise



    

    def _compute_init_candidates(self, df, area):
        """
        Compute initial adoption candidates with appliance price penalty and projection weights.
        Reescrita sin pd.Series ni .map: puro numpy + dicts.
        """
        try:
            tech = self.technologies  # DataFrame
            tech_names = tech["Tech_name"].to_numpy()
            appl_ids   = tech["Appliance_id"].to_numpy()
            base_appl_price = tech["AppliancePrice"].to_numpy(dtype=float)

            # init0: dict -> array alineada con tech_names (sin Series)
            init_dict = self.demand_area.data['initial_adoptions'][area]
            init0 = np.array([init_dict.get(name, 0.0) for name in tech_names], dtype=float)

            # parámetros
            change = self.demand_area.data['aggregated_clusters'][area]['params']['change_fact']
            #tau = max(1, (2 * (self.state.year - self.growth.base_year)) ** 2)
            if self.prev_state is not None:
                tau = max(1, (2*(self.state.year - self.prev_state.year)) ** 2)
            else:   tau = max(1, (2 * (self.state.year - self.growth.base_year)) ** 2)            
            invest_cap = float(self.demand_area.data['aggregated_clusters'][area]['params'].get('invest_cap', 1.0))

            # --- (1) Retail price por Appliance_id, sin .map
            # self.appl_retail_price: dict {appliance_id -> retail_price}
            # Clip inferior 0.01
            retail_price = np.array([self.appl_retail_price.get(aid, 1.0) for aid in appl_ids], dtype=float)
            retail_price = np.maximum(retail_price, 0.01)

            # --- (2) Multiplicador del plan por nombre de appliance, sin .map
            # self.appl_id_to_name: dict {appliance_id -> appliance_name}
            appl_names = np.array([self.appl_id_to_name.get(aid, None) for aid in appl_ids], dtype=object)

            # Compose un único lookup {appliance_name -> factor}, equivalente a:
            # next((p.get(name, 1.0) for p in self.price_plans_appl), 1.0)
            # (si hay varios planes, respeta prioridad por orden en self.price_plans_appl)
            plan_lookup = {}
            for name in set(appl_names):
                if name is None:
                    continue
                val = 1.0
                for plan in self.price_plans_appl:
                    x = plan.get(name)
                    if x is not None:
                        val = x
                        break
                plan_lookup[name] = val

            plan_factor = np.array([plan_lookup.get(n, 1.0) if n is not None else 1.0 for n in appl_names], dtype=float)

            # --- (3) Precio final de compra de appliance
            final_appl_purchase_prices = retail_price * plan_factor  # (equivalente a tu línea)

            # --- (4) Reducción por precio (clip & ramas)
            # red_factor_appl_price:
            # if p < 0.01 -> 0.01
            # elif p < invest_cap -> min(0.5*sqrt(invest_cap/p), 1.0)
            # else -> 0.5*(invest_cap/p)**2
            p = final_appl_purchase_prices
            red_factor_appl_price = np.empty_like(p, dtype=float)

            # rama 1 (p < 0.01) -> 0.01
            mask1 = p < 0.01
            red_factor_appl_price[mask1] = 1.0 #0.01

            # rama 2 (0.01 <= p < invest_cap) -> min(0.5*sqrt(invest_cap/p), 1.0)
            mask2 = (~mask1) & (p < invest_cap)
            tmp = 0.5 * np.sqrt(invest_cap / np.clip(p[mask2], 1e-12, None))
            red_factor_appl_price[mask2] = np.minimum(tmp, 1.0)

            # rama 3 (p >= invest_cap) -> 0.5*(invest_cap/p)**2
            mask3 = (~mask1) & (~mask2)
            red_factor_appl_price[mask3] = 0.5 * (invest_cap / np.clip(p[mask3], 1e-12, None)) ** 2

            # --- (5) Proyección por pesos W (W ya viene en df; extrae como numpy)
            W = df["W"].to_numpy(dtype=float)
            reduced_value_appl_price = red_factor_appl_price * W
            s = reduced_value_appl_price.sum()
            if s > 1e-12:
                reduced_value_appl_price_normalized = reduced_value_appl_price / s
            else:
                # evita división por 0; conserva estructura
                reduced_value_appl_price_normalized = reduced_value_appl_price

            # --- (6) Mezcla con init0 (f_new y n_normalized)
            f_new = np.where(init0 < 0.05, change + 20.0 * (1.0 - change) * init0, 1.0)
            n = init0 + (reduced_value_appl_price_normalized - init0) * f_new
            tot = n.sum()
            n_normalized = n / tot if tot > 1e-9 else n

            # --- (7) Candidatos iniciales
            init_cand = (10.0 * init0 + n_normalized * tau) / (10.0 + tau)
            return init_cand

        except Exception as e:
            logging.error("Error calculando candidatos iniciales: %s", e, exc_info=True)
            raise




    
    
    def _adoption_lp(self, init_cand, area):
        """
         Iterative alternative inspired by the heuristic model.
            Distributes adoption by avoiding concentration on a single technology.
            Distributes surplus evenly if there are no candidates.  
        """
        try:
            tech_ids = list(self.technologies.index)
            appl_ids = self.technologies['Appliance_id']
            fuel_ids = self.technologies['Fuel_id']
            is_urban = (area == "urban")

            appl_cap = next((d for d in self.deployment_plan_appliances_max_cap if d.get("Is_Urban") == is_urban), {})
            fuel_cap = next((d for d in self.deployment_plan_fuels_max_cap if d.get("Is_Urban") == is_urban), {})

            # 1. Inicialización y normalización
            initial = {tid: max(0.0, v) for tid, v in zip(tech_ids, init_cand)}
            total0 = sum(initial.values())
            if total0 > 0:
                initial = {tid: val/total0 for tid, val in initial.items()}
                
            # 👇 AÑADE ESTO AQUÍ (antes del bucle)
            candidate_prev = {tid: initial.get(tid, 0.0) for tid in tech_ids}

            # Iterar hasta converger
            for _ in range(50):
                # 2. Recorte por appliance
                reduced_appl = {
                    tid: min(initial[tid], appl_cap.get(aid, 1.0))
                    for tid, _, aid in zip(tech_ids, fuel_ids, appl_ids)
                }
                sum_appl = sum(reduced_appl.values())
                if sum_appl > 0:
                    reduced_appl = {tid: val/sum_appl for tid, val in reduced_appl.items()}

                # 3. Recorte por fuel
                fuel_group_sum = {}
                for tid, fid in zip(tech_ids, fuel_ids):
                    fuel_group_sum[fid] = fuel_group_sum.get(fid, 0.0) + reduced_appl[tid]

                reduced_fuel = {}
                for tid, fid in zip(tech_ids, fuel_ids):
                    ra = reduced_appl[tid]
                    group = fuel_group_sum.get(fid, 0.0)
                    if group > 0:
                        reduced_fuel[tid] = min(ra, ra * fuel_cap.get(fid, 1.0) / group)
                    else:
                        reduced_fuel[tid] = 0.0
                sum_rf = sum(reduced_fuel.values())
                if sum_rf > 0:
                    reduced_fuel = {tid: val/sum_rf for tid, val in reduced_fuel.items()}

                # # 4. Exceso
                # excess = {tid: initial[tid] - reduced_fuel.get(tid, 0.0) for tid in tech_ids}
                # total_excess = sum(excess.values())
                # if total_excess <= 1e-9:
                #     break

                excess = {tid: max(initial[tid] - reduced_fuel.get(tid, 0.0), 0.0) for tid in tech_ids}
                total_excess = sum(excess.values())
                if total_excess <= 1e-9:
                    break


                candidate = {
                    tid: reduced_fuel.get(tid, 0.0)
                    if (reduced_fuel.get(tid, 0.0) >= initial[tid] and candidate_prev.get(tid, 0.0) > 1e-9)
                    else 0.0
                    for tid in tech_ids
                }

                total_candidate = sum(candidate.values())


                # 6. Redistribución del exceso
                new_initial = {}
                n = len(tech_ids)
                for tid in tech_ids:
                    rf = reduced_fuel.get(tid, 0.0)
                    if total_candidate > 1e-9:
                        delta = candidate.get(tid, 0.0) * total_excess / total_candidate
                    else:
                        # distribuido uniformemente si no hay candidatos
                        delta = 0 #total_excess / n
                    new_initial[tid] = max(0.0, rf + delta)

                # Normalizar initial para la siguiente iteración
                total_new = sum(new_initial.values())
                if total_new > 0:
                    initial = new_initial#{tid: val/total_new for tid, val in new_initial.items()}
                else:
                    break

                candidate_prev = candidate

            # 7. Resultado final
            result = pd.Series(initial)
            return result

        except Exception as e:
            logging.error("Error en la adopción LP: %s", e, exc_info=True)
            raise



    def save_results_to_state(self):
        """
        Saves the calculated potential adoption in the state object.
        Includes ALL technologies in the universe, with 0.0 if they are not active.
        """
        try:
            if not hasattr(self, 'state') or self.state is None:
                logging.error("No state object associated with the current instance.")
                return
            if not hasattr(self, 'potential_adoption') or not self.potential_adoption:
                logging.warning("Potential adoption results are empty or not calculated.")
                return

            full_tech_ids = self.all_technologies.index.tolist()

            for area in self.area_types:
                result_series = self.potential_adoption.get(area, pd.Series(dtype=float))
                active_ids = self.technologies.index.tolist()

                # Si hay valores para tecnologías activas, los copiamos. El resto se pone a 0.0
                full_result = {
                    tid: result_series.get(tid, 0.0) if tid in active_ids else 0.0
                    for tid in full_tech_ids
                }

                self.state.set_potential_adoption(self.demand_area.id, area, full_result)

            logging.info(
                "Potential adoption results successfully saved to state %s",
                self.state.stage_id
            )
        except Exception as e:
            logging.error("Error saving potential adoption results to state: %s", str(e), exc_info=True)
            raise




    
        