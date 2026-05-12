from typing import Dict
import numpy as np
import pandas as pd
import logging
from collections import defaultdict

class IncomeModel2_0:
    """
    IncomeModel 2.0: Optimized vectorized computations for incomes and demands
    analogous to AdoptionModel2_0 structure.
    """
    def __init__(self, state, demand_area, data_manager, adoption_model):
        self.state = state
        self.demand_area = demand_area
        self.data_manager = data_manager
        self.adoption_model = adoption_model

        # --- Technologies: sin copiar, usar índice como Tech_id ---
        self.tech_df = adoption_model.technologies   # NO .copy()
        self.tech_df = self.tech_df.assign(Tech_id=self.tech_df.index.astype("int32"))
        # usa este array donde necesites Tech_id
        self._tech_id = self.tech_df.index.to_numpy(copy=False)

        # en __init__




        # Adoption potentials: DataFrame con columnas ['rural','urban']
        # (si ya viene como dict area->Series por Tech_id, esto no hace copia grande)
        self.adopt_df = pd.DataFrame(adoption_model.potential_adoption)

        # Price plans / mappings (referencias)
        self.price_plans_fuels = adoption_model.price_plans_fuels
        self.price_plans_appl  = adoption_model.price_plans_appl
        self.fuel_id_to_name   = adoption_model.fuel_id_to_name
        self.appl_id_to_name   = getattr(adoption_model, "appl_id_to_name", {})

        # Catálogos estáticos (una vez) + dtypes compactos
        self.cook_appl = data_manager.get_dataframe("Cooking_appliances").set_index('Appliance_id')
        self.cook_fuel = data_manager.get_dataframe("Cooking_fuels").set_index('Fuel_id')
        plan_df = data_manager.get_dataframe("Plan_depFuels")
        self.deploy_fuels = set(plan_df["Fuel_id"].astype("int32").to_numpy())

        # Tipos compactos por si no vienen así:
        for col in ("Fuel_id", "Appliance_id"):
            if col in self.tech_df:
                try:
                    self.tech_df[col] = self.tech_df[col].astype("int32")
                except Exception:
                    pass

        # Estructuras de salida
        self.fuel_factor = {"rural": {}, "urban": {}}
        self.fuel_income_factor = {"rural": {}, "urban": {}}
        self.appliance_income_factor = {"rural": {}, "urban": {}}
        self.total_appliance_income = {"rural": 0.0, "urban": 0.0}
        self.electric_demand = {"rural": 0.0, "urban": 0.0}
        self.CH_demand = {"rural": 0.0, "urban": 0.0}
        self.total_fuel_consumption = {"rural": {}, "urban": {}}
        self.region_incomes_appliances = {"rural": 0.0, "urban": 0.0}
        self.region_incomes_fuel = {"rural": {}, "urban": {}}
        self.region_incomes_eDemand = {"rural": 0.0, "urban": 0.0}
        self.absolute_income_adoption = {"rural": {}, "urban": {}}
        self.appl_inc_by_fuel = {"rural": {}, "urban": {}}
        self.appl_inc_by_appliance = {"rural": {}, "urban": {}}
        self.region_incomes_appliance_by_id = {"rural": {}, "urban": {}}
        self.region_incomes_appliance_by_fuel = {"rural": {}, "urban": {}}
        self.appl_inc_by_fuel_and_appliance = {"rural": defaultdict(lambda: defaultdict(float)),
                                               "urban": defaultdict(lambda: defaultdict(float))}
        self.region_incomes_appliance_by_fuel_and_appliance = {"rural": {}, "urban": {}}
        self.base_price_per_tech = {"rural": {}, "urban": {}}
        self.base_price_total = {"rural": 0.0, "urban": 0.0}
        self.base_price_total_times_CH = {"rural": 0.0, "urban": 0.0}

        # --- Cachés de lookups (rápidos) ---
        self._eff_by_appl  = self.cook_appl["Efficiency"].to_dict()   # Appliance_id -> eff
        self._fuel_price   = self.cook_fuel["Price"].to_dict()        # Fuel_id -> price

        def _first_hit_dict(lst):
            out = {}
            for d in lst or []:
                for k, v in d.items():
                    if k not in out:
                        out[k] = v
            return out

        self._appl_plan_mult = _first_hit_dict(self.price_plans_appl)   # name -> mult
        self._fuel_plan_mult = _first_hit_dict(self.price_plans_fuels)  # name -> mult

        bm_loc = self.demand_area.data.get("biomass_multipliers", {}).get("loc_price", {})
        self._fuel_local_mult_by_area = {name: area_map for name, area_map in bm_loc.items()}


        
    @property
    def area_types(self):
        """
        RReturns ['rural'] or ['urban'] if self.demand_area.area_type is defined,
        or both ['rural', 'urban'] if not defined (None).
        """
        return [self.demand_area.area_type] if self.demand_area.area_type else ['rural', 'urban']

    def run_simulation(self):
        """Main execution loop for income calculations across rural and urban areas."""
        try:
            logging.info("Starting IncomeModel2_0 simulation for area %s", self.demand_area.id)
            for area in self.area_types: #['rural','urban']:
                base_cook = self.demand_area.data.get('demand_census_rur_urb', {}).get(area, {}).get('cooking', 0)
                if base_cook == 0:
                    self.electric_demand[area] = 0.0
                    self.CH_demand[area] = 0.0
                    self.fuel_factor[area] = {}
                    self.fuel_income_factor[area] = {}
                    self.appliance_income_factor[area] = {}
                    self.total_appliance_income[area] = 0.0
                    self.total_fuel_consumption[area] = {}
                    self.region_incomes_appliances[area] = 0.0
                    self.region_incomes_fuel[area] = {}
                    self.region_incomes_eDemand[area] = {}
                    self.absolute_income_adoption[area] = {tid: 0.0 for tid in self.tech_df.index}
                    continue
                self._calc_fuel_appliance_base(area)
                self._adjust_demands(area)
                self._calc_total_fuel_consumption(area)
                self._calc_region_incomes(area)
                self._calc_absolute_adoption_income(area)
                self.calc_base_prices(area)
            self.save_to_state()
            return True
        except Exception as e:
            logging.error("Error during simulation: %s", e, exc_info=True)
            return False
        
    def _calc_fuel_appliance_base(self, area):
        """Calculate base values for fuels and appliances including income and efficiency factors."""
        try:
            # -------- 0) inputs alineados sin pandas pesados -------------------
            # pot: potencial por Tech_id (como dict → array alineado con el index de tech_df)
            pot_series = self.adopt_df[area].fillna(0.0)
            pot_dict = pot_series.to_dict()  # {Tech_id: potencial}

            df_tech = self.tech_df  # asumimos index=Tech_id
            tech_ids = df_tech.index.to_numpy(copy=False)

            # potencial alineado con tech_ids sin reindex:
            potential = np.array([pot_dict.get(tid, 0.0) for tid in tech_ids], dtype=np.float64)

            # arrays base
            appl_id = df_tech["Appliance_id"].to_numpy(copy=False)
            fuel_id = df_tech["Fuel_id"].to_numpy(copy=False)
            appl_price = df_tech["AppliancePrice"].to_numpy(copy=False, dtype=np.float64)

            # eficiencia por appliance (lookup dict -> array)
            eff = np.fromiter((self._eff_by_appl.get(int(a), np.nan) for a in appl_id),
                            dtype=np.float64, count=len(appl_id))
            eff = np.where(np.isfinite(eff) & (eff > 0.0), eff, 1.0)  # evita div/0
            # Falta a esta eff del appliance multiplicarla por el cal_value de cada fuel asociado a cada tecnología (Calorific_value)
            cal_value_by_fuel = self.cook_fuel["Calorific_value"].to_dict()
            cal_value = np.fromiter(
                (cal_value_by_fuel.get(int(f), np.nan) for f in fuel_id),
                dtype=np.float64,
                count=len(fuel_id)
            )
            eff = eff * cal_value  # eficiencia ajustada por valor calorífico del fuel


            # -------- 1) fuel_factor por fila y agregado por Fuel_id ----------
            fuel_factor_i = potential / eff  # por tecnología

            uniq_fuels, inv_fuels = np.unique(fuel_id.astype(np.int64), return_inverse=True)
            fuel_factor_sum = np.bincount(inv_fuels, weights=fuel_factor_i)

            self.fuel_factor[area] = {int(fid): float(val)
                                    for fid, val in zip(uniq_fuels, fuel_factor_sum)}

            # -------- 2) ingreso por appliance --------------------------------
            # nombre de appliance por id (sin .map)
            # self.adoption_model.appl_id_to_name: dict {id -> nombre}
            appl_names = [self.adoption_model.appl_id_to_name.get(int(a), None) for a in appl_id]

            # multiplicador de appliance por nombre:
            # - si self._appl_plan_mult es dict: get(name, 1.0)
            # - si es callable: self._appl_plan_mult(name) o 1.0 si None
            if callable(self._appl_plan_mult):
                appl_mult = np.array([self._appl_plan_mult(n) if n is not None else 1.0
                                    for n in appl_names], dtype=np.float64)
            else:
                # dict {nombre -> factor}
                appl_mult = np.array([self._appl_plan_mult.get(n, 1.0) if n is not None else 1.0
                                    for n in appl_names], dtype=np.float64)

            # ingreso por appliance a nivel de tecnología
            app_income_i = appl_price * potential * (appl_mult - 1.0)
            # --- NUEVO: ingreso por (Fuel_id, Appliance_id) a nivel de factor ---
            # arrays base:
            appl_id_int = appl_id.astype(np.int64)
            fuel_id_int = fuel_id.astype(np.int64)

            by_fuel_app = self.appl_inc_by_fuel_and_appliance[area]
            for fid, aid, inc_row in zip(fuel_id_int, appl_id_int, app_income_i):
                by_fuel_app[int(fid)][int(aid)] += float(inc_row)


            # agregado por Appliance_id
            uniq_appl, inv_appl = np.unique(appl_id.astype(np.int64), return_inverse=True)
            app_income_sum_by_appl = np.bincount(inv_appl, weights=app_income_i)

            self.appliance_income_factor[area] = {
                int(aid): float(val) for aid, val in zip(uniq_appl, app_income_sum_by_appl)
            }
            self.total_appliance_income[area] = float(app_income_i.sum())

            # y por Fuel_id (sin groupby)
            app_income_sum_by_fuel = np.bincount(inv_fuels, weights=app_income_i)
            self.appl_inc_by_fuel[area] = {
                int(fid): float(val) for fid, val in zip(uniq_fuels, app_income_sum_by_fuel)
            }

            # -------- 3) fuel_income_factor -----------------------------------
            # precio "raw" por fuel (dict {fuel_id -> precio})
            raw_price = np.fromiter((self._fuel_price.get(int(fid), 0.0) for fid in uniq_fuels),
                                    dtype=np.float64, count=len(uniq_fuels))

            # nombre de fuel por id (usa dict ya existente; sin .map)
            # self.adoption_model.fuel_id_to_name: dict {id -> nombre}
            fuel_names = [self.adoption_model.fuel_id_to_name.get(int(fid), "") for fid in uniq_fuels]

            # multiplicador de plan por nombre de fuel
            # self._fuel_plan_mult: dict {nombre -> factor} o callable
            if callable(self._fuel_plan_mult):
                fuel_plan_mult = np.array([self._fuel_plan_mult(n) if n else 1.0
                                        for n in fuel_names], dtype=np.float64)
            else:
                fuel_plan_mult = np.array([self._fuel_plan_mult.get(n, 1.0) if n else 1.0
                                        for n in fuel_names], dtype=np.float64)

            # opcional: limitar a deploy_fuels (manteniendo tu semántica)
            if getattr(self, "deploy_fuels", None) is not None:
                deploy = set(int(x) for x in self.deploy_fuels)
                mask_deploy = np.fromiter(((int(fid) in deploy) for fid in uniq_fuels),
                                        dtype=bool, count=len(uniq_fuels))
                fuel_plan_mult = np.where(mask_deploy, fuel_plan_mult, fuel_plan_mult - 1.0)

            # multiplicador local por área (si existe): dict {nombre -> {area: mult}}
            fuel_local_mult = np.fromiter(
                (self._fuel_local_mult_by_area.get(n, {}).get(area, 1.0) for n in fuel_names),
                dtype=np.float64, count=len(uniq_fuels)
            )

            # ingreso por fuel (si quieres aplicar local, multiplícalo también)
            # Si el fuel es fuel deploy entonces no se aplica el plan_mult - 1 sino el plan_mult directamente, si no es fuel deploy se aplica el plan_mult - 1
            income_fuel = fuel_factor_sum * raw_price * (fuel_plan_mult)  # * fuel_local_mult
            self.fuel_income_factor[area] = {
                int(fid): float(val) for fid, val in zip(uniq_fuels, income_fuel)
            }
            

        except Exception as e:
            logging.error("Error calculating fuel and appliance base for area %s: %s", area, e, exc_info=True)
            raise



    # def _calc_fuel_appliance_base(self, area):
    #     """Calculate base values for fuels and appliances including income and efficiency factors."""
    #     try:
    #         pot = self.adopt_df[area].fillna(0)
    #         df = self.tech_df.join(pot.rename('potential'), on='Tech_id').copy()
    #         df['Efficiency'] = df['Appliance_id'].map(self.cook_appl['Efficiency'])
    #         df['AppliancePrice'] = df['AppliancePrice']

    #         # Income per tech row (technology = Appliance + Fuel)
    #         df['fuel_factor_i'] = df['potential'] / df['Efficiency']
    #         self.fuel_factor[area] = df.groupby('Fuel_id')['fuel_factor_i'].sum().to_dict()

    #         df['appl_mult'] = df['Appliance_id'].map(lambda a: self.price_plans_appl[0].get(self.adoption_model.appl_id_to_name[a], 1))
    #         df['app_income_i'] = df['AppliancePrice'] * df['potential'] * (df['appl_mult'] - 1)

    #         # Ingreso total por appliance (como antes)
    #         self.appliance_income_factor[area] = df.groupby('Appliance_id')['app_income_i'].sum().to_dict()
    #         self.total_appliance_income[area] = df['app_income_i'].sum()

            
    #         self.appl_inc_by_fuel[area] = df.groupby('Fuel_id')['app_income_i'].sum().to_dict()
            



    #         ### El resto igual: fuel_income_factor, etc.
    #         df_fuel = df.groupby('Fuel_id').agg({'fuel_factor_i': 'sum'}).rename(columns={'fuel_factor_i': 'fuel_factor'})
    #         df_fuel['raw_price'] = self.cook_fuel['Price']
    #         plan0 = self.price_plans_fuels[0]
    #         df_fuel['plan_mult'] = [plan0.get(self.adoption_model.fuel_id_to_name[f], 1) for f in df_fuel.index]
    #         df_fuel['plan_mult'] = np.where(df_fuel.index.isin(self.deploy_fuels), df_fuel['plan_mult'], df_fuel['plan_mult'] - 1)

    #         loc_mult = self.demand_area.data.get('biomass_multipliers', {}).get('loc_price', {})
    #         df_fuel['local_mult'] = [loc_mult.get(self.adoption_model.fuel_id_to_name[f], {'rural': 1, 'urban': 1}).get(area, 1) for f in df_fuel.index]

    #         df_fuel['income_fuel'] = (df_fuel['fuel_factor'] * df_fuel['raw_price'] * df_fuel['plan_mult'])  # opcional * local_mult
    #         self.fuel_income_factor[area] = df_fuel['income_fuel'].to_dict()

    #     except Exception as e:
    #         logging.error("Error calculating fuel and appliance base for area %s: %s", area, e, exc_info=True)
    #         raise


    

    def _adjust_demands(self, area):
        """Adjust electricity and cooking/heating demands with elasticity and growth multipliers."""
        try:
            da = self.demand_area.data['demand_census_rur_urb'][area]
            params = self.demand_area.data['aggregated_clusters'][area]['params']
            base_e = da['electricity']
            dem_mult_e = params['DemandMult']['Electricity']
            elast_e = params['e_elast_demand']
            price_mult_e = self.price_plans_fuels[0].get('Electricity')
            pop = params['Population']
            self.electric_demand[area] = (base_e * dem_mult_e * (1 - elast_e*(price_mult_e-1)) * pop) * 1e-6
            base_ch = da['cooking'] * params['DemandMult']['Cooking'] + da['heating'] * params['DemandMult']['Heating']
            self.CH_demand[area] = base_ch * pop * 1e-6
        except Exception as e:
            logging.error("Error adjusting demands for area %s: %s", area, e, exc_info=True)
            raise

    def _calc_total_fuel_consumption(self, area):
        """Calculate total cooking and heating fuel consumption."""
        try:
            ch = self.CH_demand[area]
            self.total_fuel_consumption[area] = {f: ch * v for f,v in self.fuel_factor[area].items()}
        except Exception as e:
            logging.error("Error calculating total fuel consumption for area %s: %s", area, e, exc_info=True)
            raise

    def _calc_region_incomes(self, area):
        """
        Compute absolute regional income from fuels, appliances, and electricity demand.
        Multiplies relative income factors by CH demand or electric demand to obtain totals.
        """
        try:
            ch = self.CH_demand[area]              # Cooking/heating demand
            e = self.electric_demand[area]         # Electric-only demand

            # Total appliance income (all appliances combined)
            self.region_incomes_appliances[area] = self.total_appliance_income[area] * ch

            # Appliance income disaggregated by Appliance ID
            self.region_incomes_appliance_by_id[area] = {
                a_id: inc * ch for a_id, inc in self.appliance_income_factor.get(area, {}).items()
            }

            # Appliance income grouped by Fuel ID
            self.region_incomes_appliance_by_fuel[area] = {
                f_id: inc * ch for f_id, inc in self.appl_inc_by_fuel.get(area, {}).items()
            }
                        # --- NUEVO: ingreso por (Fuel_id, Appliance_id) a nivel de factor ---
                       # Appliance income grouped by Fuel ID (ya lo tienes)
            

            # --- NUEVO: ingresos por Fuel y Appliance (ya en $/año) ---
            self.region_incomes_appliance_by_fuel_and_appliance[area] = {
                int(fid): {
                    int(aid): float(inc_factor * ch)
                    for aid, inc_factor in app_map.items()
                }
                for fid, app_map in self.appl_inc_by_fuel_and_appliance[area].items()
            }

            # Income from fuels (based on fuel_income_factor, already grouped by Fuel ID)
            self.region_incomes_fuel[area] = {
                f_id: inc * ch for f_id, inc in self.fuel_income_factor.get(area, {}).items()
            }

            # Income from electricity (eDemand)
            raw_price = self.cook_fuel.at[1, 'Price'] if 1 in self.cook_fuel.index and 'Price' in self.cook_fuel.columns else 1.0
            pmult = self.price_plans_fuels[0].get('Electricity', 1.0) if self.price_plans_fuels else 1.0
            self.region_incomes_eDemand[area] = e * raw_price * pmult

        except Exception as e:
            logging.error("Error calculating regional incomes for area %s: %s", area, e, exc_info=True)
            raise

    

    

    def _calc_absolute_adoption_income(self, area):
        """Calculate absolute adoption by multiplying potential with demand."""
        try:
            pot = self.adopt_df[area].fillna(0)
            ch = self.CH_demand[area]
            self.absolute_income_adoption[area] = (pot * ch).to_dict()
        except Exception as e:
            logging.error("Error calculating absolute adoption income for area %s: %s", area, e, exc_info=True)
            raise
    
    def _calc_base_prices_for_area(self, area: str):
        try:
            df = self.tech_df  # NO copy
            tech_ids = df.index

            # 1) adopción alineada
            pot = self.adopt_df[area].reindex(tech_ids).fillna(0.0).to_numpy(copy=False)

            # 2) ids como arrays
            fuel_id_arr = df["Fuel_id"].to_numpy(copy=False)
            appl_id_arr = df["Appliance_id"].to_numpy(copy=False)

            # 3) dicts id->name (desde adoption_model)
            id2fuelname = self.adoption_model.fuel_id_to_name     # {fid: "name"}
            id2applname = self.adoption_model.appl_id_to_name     # {aid: "name"}

            # 4) planes (name->mult) para esta ejecución
            plan_fuels = self.price_plans_fuels[0] if self.price_plans_fuels else {}
            plan_appls = self.price_plans_appl[0]  if self.price_plans_appl  else {}

            # 5) fuel multipliers (NumPy, sin Series.map)
            uniq_fuel, inv_fuel = np.unique(fuel_id_arr, return_inverse=True)
            fuel_mult_uniq = np.array(
                [float(plan_fuels.get(id2fuelname.get(int(fid), ""), 1.0)) for fid in uniq_fuel],
                dtype=np.float64
            )

            # regla deploy_fuels sobre los únicos y luego se expande
            # if hasattr(self, "deploy_fuels") and isinstance(self.deploy_fuels, set):
            #     not_deployed_uniq = np.array([int(fid) not in self.deploy_fuels for fid in uniq_fuel], dtype=bool)
            #     fuel_mult_uniq = np.where(not_deployed_uniq, 1.0, fuel_mult_uniq)

            fuel_mult = fuel_mult_uniq[inv_fuel]

            # 6) appliance multipliers (NumPy, sin Series.map)
            uniq_appl, inv_appl = np.unique(appl_id_arr, return_inverse=True)
            appl_mult_uniq = np.array(
                [float(plan_appls.get(id2applname.get(int(aid), ""), 1.0)) for aid in uniq_appl],
                dtype=np.float64
            )
            appl_mult = appl_mult_uniq[inv_appl]

            # 7) precios base (arrays)
            fuel_price = df["FuelPrice"].to_numpy(copy=False).astype(np.float64, copy=False)
            appl_price = df["AppliancePrice"].to_numpy(copy=False).astype(np.float64, copy=False)

            base_raw = (appl_price * appl_mult) + (fuel_price * fuel_mult)
            base_weighted = base_raw * pot

            # 8) salida sin setitem
            self.base_price_per_tech[area] = dict(zip(tech_ids.to_numpy(), base_weighted))
            total = float(base_weighted.sum())
            self.base_price_total[area] = total
            ch = float(self.CH_demand[area]) #Already in MCook/yr
            #price per cook 
            self.base_price_total_times_CH[area] = (total * ch)#/ 1e6

            logging.info("[%s] Base price total=%.6f | Base price * CH=%.6f", area, total, total * ch)

        except Exception as e:
            logging.error("Error in _calc_base_prices_for_area(%s): %s", area, e, exc_info=True)
            raise





    # def _calc_base_prices_for_area(self, area: str):
    #     """
    #     Calculate the base price per technology by applying appliance and fuel multipliers
    #     and weighting it by the area's adoption. Stores results in:
    #     - base_price_per_tech[area][Tech_id] = (ApPrice*appl_mult + FuelPrice*fuel_mult) * adoption
    #     - base_price_total[area] = summary per technology
    #     - base_price_total_times_CH[area] = base_price_total[area] * CH_demand[area]
    #     """
    #     try:
    #         # 1) Datos base
    #         pot = self.adopt_df[area].fillna(0)  # Series index=Tech_id, values=adoption
    #         df = self.tech_df.copy()

    #         # Asegura columnas requeridas
    #         required_cols = {"Tech_id", "Fuel_id", "Appliance_id", "FuelPrice", "AppliancePrice"}
    #         missing = required_cols - set(df.columns)
    #         if missing:
    #             raise KeyError(f"tech_df no contiene columnas requeridas: {missing}")

    #         # 2) Multiplicadores por nombre
    #         plan_fuels = self.price_plans_fuels[0] if self.price_plans_fuels else {}
    #         plan_appls = self.price_plans_appl[0] if self.price_plans_appl else {}

    #         # Mapear IDs -> nombres (presentes en los plan_*)
    #         def fuel_mult_from_id(fid: int) -> float:
    #             name = self.adoption_model.fuel_id_to_name.get(fid, None)
    #             if name is None:
    #                 logging.warning(f"[{area}] Fuel_id {fid} sin nombre en fuel_id_to_name; mult=1")
    #                 return 1.0
    #             return float(plan_fuels.get(name, 1.0))

    #         def appl_mult_from_id(aid: int) -> float:
    #             name = self.adoption_model.appl_id_to_name.get(aid, None)
    #             if name is None:
    #                 logging.warning(f"[{area}] Appliance_id {aid} sin nombre en appl_id_to_name; mult=1")
    #                 return 1.0
    #             return float(plan_appls.get(name, 1.0))

    #         df["fuel_mult"] = df["Fuel_id"].map(fuel_mult_from_id).astype(float)
    #         df["appl_mult"] = df["Appliance_id"].map(appl_mult_from_id).astype(float)

    #         # (Opcional) Si quieres aplicar la regla de deploy_fuels como en tu lógica previa:
    #         #   - Si el fuel NO está en deploy_fuels, ajusta el multiplicador (ejemplo: mult-1)
    #         if hasattr(self, "deploy_fuels") and isinstance(self.deploy_fuels, set):
    #             mask_not_deployed = ~df["Fuel_id"].isin(self.deploy_fuels)
    #             # Ajuste conservador: si no desplegado, no hay incremento de precio (mult->1.0)
    #             # Cambia esta línea por tu política exacta (p.ej., mult-1) si lo necesitas.
    #             df.loc[mask_not_deployed, "fuel_mult"] = 1.0

    #         # 3) Precio base por tecnología (sin adopción)
    #         #    BasePriceTech = AppliancePrice * appl_mult + FuelPrice * fuel_mult
    #         df["BasePriceTech_raw"] = (
    #             df["AppliancePrice"].astype(float) * df["appl_mult"] +
    #             df["FuelPrice"].astype(float) * df["fuel_mult"]
    #         )

    #         # 4) Aplicar adopción del área (join por Tech_id)
    #         df = df.set_index("Tech_id")
    #         # Asegurar que pot está indexado por Tech_id
    #         pot = pot.reindex(df.index).fillna(0.0)
    #         df["BasePriceTech_weighted"] = df["BasePriceTech_raw"] * pot

    #         # 5) Guardar vector por tecnología y suma total
    #         self.base_price_per_tech[area] = df["BasePriceTech_weighted"].to_dict()
    #         total = float(df["BasePriceTech_weighted"].sum())
    #         self.base_price_total[area] = total

    #         # 6) Multiplicar por consumo CH del área
    #         ch = float(self.CH_demand[area])
    #         self.base_price_total_times_CH[area] = total * ch

    #         logging.info(
    #             "[%s] Base price total=%.6f | Base price * CH=%.6f",
    #             area, self.base_price_total[area], self.base_price_total_times_CH[area]
    #         )

    #     except Exception as e:
    #         logging.error("Error in  _calc_base_prices_for_area(%s): %s", area, e, exc_info=True)
    #         raise


    def calc_base_prices(self, area):
        """
        Calculates the base prices for all defined areas (rural/urban) and leaves results in:
        - self.base_price_per_tech[area]
        - self.base_price_total[area]
        - self.base_price_total_times_CH[area]
        """
        # Initialize containers if they don't exist
        if not hasattr(self, "base_price_per_tech"):
            self.base_price_per_tech = {"rural": {}, "urban": {}}
        if not hasattr(self, "base_price_total"):
            self.base_price_total = {"rural": 0.0, "urban": 0.0}
        if not hasattr(self, "base_price_total_times_CH"):
            self.base_price_total_times_CH = {"rural": 0.0, "urban": 0.0}

        #for area in self.area_types:
        self._calc_base_prices_for_area(area)






    def save_to_state(self):
        """Save all calculated values to the State object."""
        try:
            da_id = self.demand_area.id
            for area in self.area_types: #["rural", "urban"]:
                if hasattr(self.state, 'set_electric_consumption'):
                    self.state.set_electric_consumption(da_id, area, {area: self.electric_demand[area]})
                if hasattr(self.state, 'set_CH_consumption'):
                    self.state.set_CH_consumption(da_id, area, {area: self.CH_demand[area]})
                if hasattr(self.state, 'set_total_fuel_consumption'):
                    self.state.set_total_fuel_consumption(da_id, area, self.total_fuel_consumption[area])
                if hasattr(self.state, 'set_region_income'):
                  self.state.set_region_income(da_id, area, {
                        'appliances': self.region_incomes_appliances[area],
                        'fuels': self.region_incomes_fuel[area],
                        'electric': self.region_incomes_eDemand[area], 
                        'appliance_income_by_fuel': self.region_incomes_appliance_by_fuel[area],
                        'appliance_income_by_appliance': self.region_incomes_appliance_by_id[area],
                        # Nuevo:  ingros por cada appliance de cada fuel
                        'appliance_income_by_fuel_and_appliance': self.region_incomes_appliance_by_fuel_and_appliance[area]
                    })
                if hasattr(self.state, 'set_absolute_income_adoption'):
                    self.state.set_absolute_income_adoption(da_id, area, self.absolute_income_adoption[area])
                # Save income by appliance
                # if hasattr(self.state, 'set_income_by_appliance'):
                #     self.state.set_income_by_appliance(da_id, area, self.income_by_appliance_id.get(area, {}))
                # Dentro de save_to_state()
                if hasattr(self.state, 'set_base_price'):
                    # per-tech (ponderado por adopción), total y total*CH
                    self.state.set_base_price(
                        da_id, area,
                        {
                            'per_tech': self.base_price_per_tech[area],                  # dict {Tech_id: value}
                            'total': self.base_price_total[area],                        # float # Av.Price $/Cook 
                            'total_times_CH': self.base_price_total_times_CH[area],      # float # Expenditure $/Year 
                        }
                    )


            logging.info("All results successfully saved to state for Demand Area %s", da_id)
        except Exception as e:
            logging.error("Error saving results to state for Demand Area %s: %s", self.demand_area.id, e, exc_info=True)
            raise

    #GETTERS
    def get_region_dependent_income(self, fuelID, area_type):
        """
        Returns the regional income for a specific fuel and area type.
        """
        return self.region_incomes_fuel[area_type].get(fuelID)


    def get_total_fuel_consumption(self, fuelID, area_type):
        """
        Returns the total fuel consumption for a specific area type.
        """
        return self.total_fuel_consumption[area_type].get(fuelID, 0.0)
    
