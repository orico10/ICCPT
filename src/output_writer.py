# src/output_writer.py
import os, logging, pandas as pd
from src import config
from src.summary_report import SummaryReport  # si lo usas
from src.financial_model import FinancialModel
from src.exports import (  # crea este módulo moviendo tus funciones export_* aquí
    export_summary_reports,
    export_social_params_to_tsv,
    export_potential_adoption_to_tsv,
    export_potential_adoption_long_format_to_tsv,
    export_electricity_costs_to_tsv,
    export_income_model_to_tsv,
    
    export_electrified_areas_with_costs,
    summarize_country_electric_demand,

)

class OutputWriter:
    def __init__(self, out_dir=None, summary_dir=None, logger=None):
        self.out_dir = out_dir or config["path"]["output"]
        self.sum_dir = summary_dir or config["path"]["summary_results"]
        self.log = logger or logging.getLogger(__name__)
        os.makedirs(self.out_dir, exist_ok=True)
        os.makedirs(self.sum_dir, exist_ok=True)

    # --- live progress mínimo (opcional) ---
    def render_progress(self, mixed_state):
        # Podrías actualizar un HTML incremental o un JSON “heartbeat”
        pass

    # --- debug helpers ---
    def debug_lpg_costs(self, lpg_model, state):
        path = os.path.join(self.out_dir, "lpg_costs_debug.tsv")
        lpg_model.export_lpg_cost_debug_info(path, state.stage_id)

    # --- post-loop exports ---
    def export_post_loop(self, mixed_states, demand_areas, data_manager):
        " Eports summary reports and various TSV files after processing all states. "
        export_summary_reports(mixed_states, self.sum_dir)

        # export_social_params_to_tsv([], os.path.join(self.out_dir, "social_parameters.tsv"))  # si lo mantienes
        # export_potential_adoption_to_tsv(mixed_states, demand_areas, data_manager,
        #                                  os.path.join(self.out_dir, "potential_adoption_summary.tsv"))
        # export_income_model_to_tsv(mixed_states, os.path.join(self.out_dir, "income_model_summary.tsv"))
        # export_electricity_costs_to_tsv(mixed_states, os.path.join(self.out_dir, "electricity_costs_summary.tsv"))
        export_potential_adoption_long_format_to_tsv(mixed_states, demand_areas, data_manager,
                                                     os.path.join(self.out_dir, "potential_adop_for_visualization.tsv"))
        # summarize_country_electric_demand(mixed_states, os.path.join(self.out_dir, "country_electric_demand_summary.tsv"))
        # export_electrified_areas_with_costs(mixed_states, demand_areas,
        #                                     os.path.join(self.out_dir, "electrified_areas_with_costs.tsv"))
        # summarize_country_electric_demand(mixed_states, os.path.join(self.out_dir, "country_electric_demand_summary.tsv"))  

    # --- bloque financiero anualizado (incluye fix de merges robusto) ---
    def build_and_export_financial_model(self, mixed_states, dm, growth, debug=False):
        """ Builds and exports the annualized financial model (CAPEX/OPEX). 
        If debug is True, exports intermediate dataframes for inspection.
        """
        model = FinancialModel(mixed_states, dm, growth); model.build_all()
        all_sem = model.generate_complete_semester_structure(growth)
        capex_s = model._generate_capex_semester_structure()
        opex_s  = model._generate_opex_semester_structure()
        structured_df = model._generate_structured_cost_df()

        
        def _to_sem_int(x):
            if isinstance(x, str):
                x = x.strip().lower()
                return 1 if x == "first" else 2 if x == "second" else pd.to_numeric(x, errors="coerce")
            return pd.to_numeric(x, errors="coerce")

        # 1) Construye df_sem con claves consistentes
        df_sem = pd.DataFrame([
            {"Year": year,
            "Semester": _to_sem_int(semester),
            "InfraRate": data.get("infra_rate", 0.0),
            "TimeSinceBase": data.get("time_since_base", 0.0)}
            for (year, semester), data in all_sem.items()
        ]).dropna(subset=["Year","Semester"])
        df_sem["Year"] = pd.to_numeric(df_sem["Year"], errors="coerce").astype(int)
        df_sem["Semester"] = df_sem["Semester"].astype(int)

        # 2) Asegura columnas en structured_df y mergea con df_sem
        structured_df["Year"] = pd.to_numeric(structured_df["Year"], errors="coerce")
        structured_df["Semester"] = _to_sem_int(structured_df["Semester"]).astype(int)

        for col in ("InfraRate","TimeSinceBase"):
            if col not in structured_df.columns:
                structured_df[col] = pd.NA

        structured_df = structured_df.merge(
            df_sem[["Year","Semester","InfraRate","TimeSinceBase"]],
            on=["Year","Semester"], how="left", suffixes=("","_m")
        )
        for col in ("InfraRate", "TimeSinceBase"):
            mcol = f"{col}_m"

            structured_df[col] = (
                pd.to_numeric(structured_df[col], errors="coerce")
                .fillna(pd.to_numeric(structured_df[mcol], errors="coerce"))
                .fillna(0.0)
            )

            # Elimina columna temporal si existe
            if mcol in structured_df.columns:
                structured_df.drop(columns=[mcol], inplace=True)



        min_year = int(structured_df["Year"].min())
        min_sem  = int(structured_df.loc[structured_df["Year"]==min_year,"Semester"].min())
        base = structured_df.query("Year == @min_year and Semester == @min_sem").copy()
        if base.empty:
            raise ValueError("No base row for financial finalization")

        all_idx = df_sem[["Year","Semester","InfraRate","TimeSinceBase"]].drop_duplicates()
        existing_idx = structured_df[["Year","Semester"]].drop_duplicates()
        missing = all_idx.merge(existing_idx, on=["Year","Semester"], how="left", indicator=True)
        missing = missing[missing["_merge"]=="left_only"].drop(columns=["_merge"])

        clones = []
        for _, r in missing.iterrows():
            y, s, infra, tsb = int(r["Year"]), int(r["Semester"]), float(r["InfraRate"]), float(r["TimeSinceBase"])
            nr = base.copy()
            nr.loc[:, "Year"] = y; nr.loc[:, "Semester"] = s
            nr.loc[:, "InfraRate"] = infra; nr.loc[:, "TimeSinceBase"] = tsb
            nr.loc[:, "State"] = f"no_name_{y}_{s}"
            clones.append(nr)

        fake_costs = pd.concat(clones, ignore_index=True) if clones else base.head(0).copy()
        final_df = pd.concat([structured_df, fake_costs], ignore_index=True).sort_values(["Year","Semester"]).reset_index(drop=True)

        final_df["Growth_Factor"] = final_df.apply(lambda row: model.compute_growth(row), axis=1)

        capex_from_ann = model.compute_capex_from_annuity(final_df, capex_s)
        capex = model._calculate_capex_from_annuity(capex_from_ann)
        opex_from_ann = model.compute_opex_from_annuity(final_df, opex_s)
        opex = model._calculate_opex_from_annuity(opex_from_ann)

        merged = model.merge_opex_capex(opex, capex)
        yearly = model.aggregate_to_yearly(merged)

        out = os.path.join(self.out_dir, "merged_opex_capex_yearly.tsv")
        yearly.to_csv(out, sep="\t", index=False)
        self.log.info("Anualizado CAPEX/OPEX exportado: %s", out)
