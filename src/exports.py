# src/exports.py
import csv
import os
from typing import List
import pandas as pd
import logging

from src.country_financial_aggregator import AggregatedLpgCosts, AggregatedRestSubsidiesOrTaxesOpex, AggregatedSocialCosts, AverageGrowthCalculationAppliances, FinancialAggParams, IncomeTariff
from src.el_cost_params import CostParameters
from src.financial_agg_params import AggregatedElectricityCosts

# def export_summary_reports(states, output_dir):
#     """
#     Export summary TSV reports in output_dir.
#     """
#     os.makedirs(output_dir, exist_ok=True)
#     # ... tu lógica actual ...

def export_social_params_to_tsv(data_records, output_file_path): # ELIminar método  del diseño final  ------------------
    """
    Exports updated social cluster parameters collected during simulation to a TSV file.

    :param data_records: List of dictionaries containing social parameters per state and demand area.
    :param output_file_path: Path to the output TSV file.
    """
    try:
        with open(output_file_path, mode='w', newline='', encoding='utf-8') as file:
            tsv_writer = csv.writer(file, delimiter='\t')

            # Write header
            tsv_writer.writerow([
                "State_Stage_ID", "Year", "Semester", "DemandArea_ID",
                "Area_Type", "Electricity_DemandMult", "Cooking_DemandMult", "Heating_DemandMult",
                "Elasticity", "Population", "WillPay", "InvestCap",
                "ChangeFact", "BetterFact", "WorseFact", "SocialWeight",
                "Health", "TimeGender", "Emissions", "Deforestation"
            ])

            # Write data rows
            for record in data_records:
                tsv_writer.writerow([
                    record["State_Stage_ID"], record["Year"], record["Semester"], record["DemandArea_ID"],
                    record["Area_Type"], record["Electricity_DemandMult"], record["Cooking_DemandMult"],
                    record["Heating_DemandMult"], record["Elasticity"], record["Population"],
                    record["WillPay"], record["InvestCap"], record["ChangeFact"],
                    record["BetterFact"], record["WorseFact"], record["SocialWeight"],
                    record["Health"], record["TimeGender"], record["Emissions"], record["Deforestation"]
                ])

        logging.info("Social parameters successfully exported to TSV at %s", output_file_path)
    except Exception as e:
        logging.error("Failed to export social parameters to TSV: %s", str(e), exc_info=True)
        raise

def export_potential_adoption_to_tsv(mixed_states, demand_areas, data_manager, output_file_path):
    """
    Exports both initial and potential adoption per technology, demand area, and area type (rural/urban) to a TSV file,
    aligning state data horizontally and including electric and CH consumption.
    """
    try:
        # Crear un diccionario para mapear nombres de tecnologías a sus IDs
        enriched_technologies = data_manager.get_dataframe("enriched_technologies")
        tech_name_to_id = {
            row["Tech_name"]: row["Technologies_id"]
            for _, row in enriched_technologies.iterrows()
        }

        # Preparar la cabecera del TSV
        common_columns = ["DemandArea_ID", "Area_Type", "Technology_ID"]
        state_columns = []

        for state in mixed_states:
            state_columns.extend([
                f"State_{state.stage_id}_Year",                                  # Año (adimensional)
                f"State_{state.stage_id}_Semester",                              # Semestre (adimensional)
                f"State_{state.stage_id}_Initial_Adoption [-]",                  # Porcentaje o fracción
                f"State_{state.stage_id}_Total_Initial_Adoption [-]",
                f"State_{state.stage_id}_Potential_Adoption [-]",
                f"State_{state.stage_id}_Total_Potential_Adoption [-]",
                f"State_{state.stage_id}_Electric_Consumption [GWh/year]",
                f"State_{state.stage_id}_CH_Consumption [MCook/year]"
            ])


        header = common_columns + state_columns

        # Recopilar datos organizados por (DemandArea_ID, Area_Type, Technology_ID)
        data_dict = {}

        for state in mixed_states:
            for demand_area in demand_areas:
                for area_type in ["rural", "urban"]:
                    # Obtener datos de adopción potencial e inicial para el área específica
                    area_potential = state.get_potential_adoption(demand_area.id, area_type)
                    area_initial = state.get_initial_adoption(demand_area.id, area_type)

                    # Obtener consumos eléctricos y de cocinado para el área y tipo de área
                    # electric_consumption = state.get_electric_consumption(demand_area.id, area_type)
                    # ch_consumption = state.get_CH_consumption(demand_area.id, area_type)
                    electric_dict = state.get_electric_consumption(demand_area.id, area_type)
                    ch_dict = state.get_CH_consumption(demand_area.id, area_type)

                    # Get numeric value (defaults to 0.0 if not found or malformed)
                    electric_consumption = electric_dict.get(area_type, 0.0) if isinstance(electric_dict, dict) else electric_dict
                    ch_consumption = ch_dict.get(area_type, 0.0) if isinstance(ch_dict, dict) else ch_dict


                    # Calcular totales
                    total_potential_adoption = sum(area_potential.values()) #if isinstance(area_potential, dict) else 0
                    total_initial_adoption = sum(area_initial.values()) #if isinstance(area_initial, dict) else 0
                    # Ignorar áreas sin demanda de cocinado
                    if ch_consumption == 0.0:
                        continue
                     # Como los datos ya vienen indexados por Technology_ID, iteramos directamente sobre ellos.
                    for tech_id, potential_value in area_potential.items():
                        # Obtener el valor inicial directamente usando el tech id
                        initial_value = area_initial.get(tech_id)

                        # Crear una clave única para la combinación de demand area, tipo de área y tecnología
                        key = (demand_area.id, area_type, tech_id)
                        if key not in data_dict:
                            data_dict[key] = []

                        # Extender los datos con la información del state actual
                        data_dict[key].extend([
                            state.year,
                            state.semester,
                            initial_value,
                            total_initial_adoption,
                            potential_value,
                            total_potential_adoption,
                            electric_consumption,
                            ch_consumption
                        ])

        # Escribir los datos en el archivo TSV
        with open(output_file_path, mode='w', newline='', encoding='utf-8') as file:
            tsv_writer = csv.writer(file, delimiter='\t')
            tsv_writer.writerow(header)

            for key, values_list in data_dict.items():
                demand_area_id, area_type, tech_id = key
                row = [demand_area_id, area_type, tech_id] + values_list
                tsv_writer.writerow(row)

        logging.info("Adopción potencial e inicial, junto con consumos eléctricos y de cocinado, "
                     "exportados correctamente al archivo TSV: %s", output_file_path)

    except Exception as e:
        logging.error("Error al exportar datos de adopción a TSV: %s", str(e), exc_info=True)
        raise


def export_income_model_to_tsv(mixed_states, output_file_path):
    """
    Export income model values to a TSV file, with one row per combination of demand area, area type,
    and fuel/appliance/technology ID. All IDs appear as separate columns, not embedded in column names.
    """
    try:
        header = [
            "Stage_ID", "Year", "DemandArea_ID", "Area_Type",
            "Electric_Demand [GWh/year]", "CH_Demand [MCook/year]",
            "Region_Income_Appliances [M$/year]", 
            "Region_Income_EDemand [M$/year]" , 
            "Fuel_ID", "Fuel_Consumption [GWh/year or Kton/year]", "Fuel_Income [M$/year]",
            "Technology_ID", "Absolute_Income_Adoption [MCook/year]"
        ]


        with open(output_file_path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file, delimiter='\t')
            writer.writerow(header)

            for state in mixed_states:
                for da_id, _ in state.demand_areas_data.items():
                    for area_type in ["rural", "urban"]:
                        try:
                            electric = state.get_electric_consumption(da_id, area_type)
                            ch = state.get_CH_consumption(da_id, area_type)
                            electric_value = electric.get(area_type, 0.0) if isinstance(electric, dict) else electric
                            ch_value = ch.get(area_type, 0.0) if isinstance(ch, dict) else ch

                            region_income = state.get_region_income(da_id, area_type)
                            appliances_income = region_income.get("appliances", 0.0)
                            edemand_income = region_income.get("electric", 0.0)
                            if isinstance(edemand_income, dict):
                                edemand_income = list(edemand_income.values())[0] if edemand_income else 0.0

                            fuel_cons = state.get_total_fuel_consumption(da_id, area_type)
                            fuel_income = region_income.get("fuels", {})
                            adoption = state.get_absolute_income_adoption(da_id, area_type)

                            # Si no hay fuels ni adoption, al menos escribir una fila base
                            if not fuel_cons and not adoption:
                                writer.writerow([
                                    state.stage_id, state.year, da_id, area_type,
                                    electric_value, ch_value,
                                    appliances_income, edemand_income,
                                    "", "", "",
                                    "", ""
                                ])
                            else:
                                # Una fila por cada fuel
                                for fuel_id in set(fuel_cons.keys()).union(fuel_income.keys()):
                                    writer.writerow([
                                        state.stage_id, state.year, da_id, area_type,
                                        electric_value, ch_value,
                                        appliances_income, edemand_income,
                                        fuel_id,
                                        fuel_cons.get(fuel_id, 0.0),
                                        fuel_income.get(fuel_id, 0.0),
                                        "", ""  # sin tecnología en esta fila
                                    ])
                                # Una fila por cada tecnología
                                for tech_id in adoption.keys():
                                    writer.writerow([
                                        state.stage_id, state.year, da_id, area_type,
                                        electric_value, ch_value,
                                        appliances_income, edemand_income,
                                        "", "", "",
                                        tech_id,
                                        adoption.get(tech_id, 0.0)
                                    ])

                        except Exception as e:
                            writer.writerow([state.stage_id, state.year, da_id, area_type, "ERROR", str(e)])

        logging.info("Income model data with explicit Fuel_ID and Technology_ID exported to TSV: %s", output_file_path)

    except Exception as e:
        logging.error("Error exporting income model with explicit IDs: %s", str(e), exc_info=True)
        raise



def export_electricity_costs_to_tsv(states, output_file_path):
    try:
        header = [
            "State_ID", "Year", "Semester",  # NUEVOS CAMPOS TEMPORALES
            "DemandArea_ID", "Area_Type", "Block", 
            "FIX_Grid_Gen [M$/year]", "Rest [M$/year]", "VAR_Grid_Gen [M$/year]", "VAR_OffGrid [M$/year]",
            "FINAL_FIX_Grid_Gen [M$/year]", "FINAL_Rest [M$/year]", 
            "FINAL_VAR_Grid_Gen [M$/year]", "FINAL_VAR_OffGrid [M$/year]",
            "Ratio [-]", 
            "EDemand [GWh/year]",
            "ETotal [GWh/year]"
        ]

        with open(output_file_path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file, delimiter='\t')
            writer.writerow(header)

            for state in states:
                if not hasattr(state, "electricity_cost_results"):
                    continue

                for area_id, data in state.electricity_cost_results.items():
                    cp = data["cost_parameters"]
                    ratios = data["ratios"]

                    for area_type in ["rural", "urban"]:
                        for block in ["ElecTotal", "EDemand"]:
                            area_cp = getattr(cp[block], area_type)

                            # EDemand
                            consumption = state.get_electric_consumption(area_id, area_type)
                            edemand_value = consumption.get(area_type, 0.0) if isinstance(consumption, dict) else consumption

                            # ETotal
                            etotal_value = 0.0
                            if hasattr(state, "total_current_demand"):
                                etotal_value = state.total_current_demand.get(area_type, 0.0)

                            writer.writerow([
                                state.stage_id,        # Nuevo: ID de estado
                                state.year,            # Nuevo: año
                                state.semester,        # Nuevo: semestre
                                area_id,
                                area_type,
                                block,
                                area_cp.costs.FIX_Grid_Gen,
                                area_cp.costs.Rest,
                                area_cp.costs.VAR_Grid_Gen,
                                area_cp.costs.VAR_OffGrid,
                                area_cp.costs.FINAL_FIX_Grid_Gen,
                                area_cp.costs.FINAL_Rest,
                                area_cp.costs.FINAL_VAR_Grid_Gen,
                                area_cp.costs.FINAL_VAR_OffGrid,
                                ratios.get(area_type, None),
                                edemand_value,
                                etotal_value
                            ])

        logging.info("Electricity cost and ratios exported to TSV (with State metadata): %s", output_file_path)

    except Exception as e:
        logging.error("Error exporting electricity costs to TSV: %s", str(e), exc_info=True)
        raise


def export_potential_adoption_long_format_to_tsv(mixed_states, demand_areas, data_manager, output_file_path):
    """
    Exports initial and potential adoption per technology, demand area, and area type (rural/urban) to a long-format TSV
    with one row per state and technology, including electric and CH consumption and geolocation.
    """
    try:
        # Obtener nombre y mapping de tecnologías
        enriched_technologies = data_manager.get_dataframe("enriched_technologies")
        tech_id_to_name = {
            row["Technologies_id"]: row["Tech_name"]
            for _, row in enriched_technologies.iterrows()
        }
        all_tech_ids = sorted(tech_id_to_name.keys())

        # Cabecera final del archivo largo
        header = [
            "State_ID", "Year", "Semester",
            "Region_Name", "DemandArea_ID", "Area_Type",
            "Technology_ID", "Tech_Name",
            "Initial_Adoption", "Potential_Adoption",
            "Electric_Consumption [GWh/year]", "CH_Consumption [MCook/year]",
            "Latitude", "Longitude"
        ]

        with open(output_file_path, mode='w', newline='', encoding='utf-8') as file:
            tsv_writer = csv.writer(file, delimiter='\t')
            tsv_writer.writerow(header)

            for state in mixed_states:
                state_id = state.stage_id
                for demand_area in demand_areas:
                    area_types = demand_area.area_type if demand_area.area_type else ['rural', 'urban']
                    for area_type in  area_types: #["rural", "urban"]:
                        # Consumos
                        electric_dict = state.get_electric_consumption(demand_area.id, area_type)
                        ch_dict = state.get_CH_consumption(demand_area.id, area_type)
                        electric_consumption = electric_dict.get(area_type, 0.0) if isinstance(electric_dict, dict) else electric_dict
                        ch_consumption = ch_dict.get(area_type, 0.0) if isinstance(ch_dict, dict) else ch_dict

                        # Ignorar áreas sin demanda de cocinado
                        if ch_consumption == 0.0:
                            continue

                        # Obtener adopciones (pueden ser parciales)
                        area_initial = state.get_initial_adoption(demand_area.id, area_type)
                        area_potential = state.get_potential_adoption(demand_area.id, area_type)

                        # Iterar por todas las tecnologías
                        for tech_id in all_tech_ids:
                            initial_value = area_initial.get(tech_id, 0.0) if isinstance(area_initial, dict) else 0.0
                            potential_value = area_potential.get(tech_id, 0.0) if isinstance(area_potential, dict) else 0.0
                            tech_name = tech_id_to_name.get(tech_id, "Unknown")

                            # Obtener coordenadas promedio si existen
                            coords = demand_area.data["aggregated_points"].get(area_type)
                            lat = coords["Lat"] if coords else ""
                            lon = coords["Long"] if coords else ""

                            row = [
                                state_id,
                                state.year,
                                state.semester,
                                demand_area.region_name,
                                demand_area.id,
                                area_type,
                                tech_id,
                                tech_name,
                                initial_value,
                                potential_value,
                                electric_consumption,
                                ch_consumption,
                                lat,
                                lon
                            ]
                            tsv_writer.writerow(row)

        logging.info("Adopción por estado exportada en formato largo correctamente a: %s", output_file_path)

    except Exception as e:
        logging.error("Error al exportar adopciones en formato largo: %s", str(e), exc_info=True)
        raise


def collect_social_params(state, demand_area, data_records):
        """
        Collects social parameters from the demand area data and appends them to the data_records list.
        """
        for area_type in ["rural", "urban"]:
                            params = demand_area.data["aggregated_clusters"].get(area_type, {}).get("params", {})
                            if params:
                                social_balance = params.get("social_balance", {})
                                data_records.append({
                                    "State_Stage_ID": state.stage_id,
                                    "Year": state.year,
                                    "Semester": state.semester,
                                    "DemandArea_ID": demand_area.id,
                                    "Area_Type": area_type,
                                    "Electricity_DemandMult": params.get("DemandMult", {}).get("Electricity", 0.0),
                                    "Cooking_DemandMult": params.get("DemandMult", {}).get("Cooking", 0.0),
                                    "Heating_DemandMult": params.get("DemandMult", {}).get("Heating", 0.0),
                                    "Elasticity": params.get("e_elast_demand", 0.0),
                                    "Population": params.get("Population", 0.0),
                                    "WillPay": params.get("will_pay", 0.0),
                                    "InvestCap": params.get("invest_cap", 0.0),
                                    "ChangeFact": params.get("change_fact", 0.0),
                                    "BetterFact": params.get("better_fact", 0.0),
                                    "WorseFact": params.get("worse_fact", 0.0),
                                    "SocialWeight": params.get("social_weight", 0.0),
                                    "Health": social_balance.get("health", 0.0),
                                    "TimeGender": social_balance.get("time_gender", 0.0),
                                    "Emissions": social_balance.get("emissions", 0.0),
                                    "Deforestation": social_balance.get("deforestation", 0.0)
                                }) ## hasta aquí ----------------- BOrrar del diseño final

def export_financial_aggregation_tabular_for_tableau(states: List, output_path: str):
        """
        Exports the aggregated financial data in tabular format by state, ready for Tableau.
        This takes the FinancialAggParams stored in each state (via set_financial_results)
        and breaks them down into rows with columns for:
            State_ID, Year, Semester,
            Sector, SubSector, CostType, EconType,
            Lifetime, DiscountRate, Value_M$/year,
            GrowthRate, Notes
        """
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            header = [
                "State_ID", "Year", "Semester",
                "Sector", "SubSector", "CostType", "EconType",
                "Lifetime", "DiscountRate", "Value_M$/year",
                "GrowthRate", "Notes"
            ]

            lifetime_defaults = {
                "GRID": 35,
                "OG": 25,
                "LPG_Local": 15,
                "LPG_Ups": 15,
                "E_Cooking": 25
            }
            discount_rate = 10.0  # general default, puede refinarse por caso

            with open(output_path, mode="a", newline="", encoding="utf-8") as file:
                writer = csv.writer(file, delimiter="\t")
                writer.writerow(header)

                for state in states:
                    fid = state.stage_id
                    year = state.year
                    semester = getattr(state, "semester", 1)

                    # Obtener FinancialAggParams del estado
                    fr: FinancialAggParams = state.get_financial_results()

                    # 1) Electricidad - ETotal (agregado_electricity_costs)
                    el_etotal: AggregatedElectricityCosts = fr.aggregated_electricity_costs
                    oof_grid_share = float(state.get_country_off_grid_percentage() or 0.0) * 100.0
                    def row_elec_etotal(sector, sub, cost_type, econ_type, value, life_key, notes=""):
                        lifetime = lifetime_defaults.get(life_key, "")
                        writer.writerow([
                            fid, year, semester,
                            sector, sub, cost_type, econ_type,
                            lifetime, f"{discount_rate}%", round(value, 3),
                            "-1%", notes
                        ])

                    row_elec_etotal("Electricity_ETotal", "OffGrid_percentage", "NONE", "Tariff",
                                    oof_grid_share, "OG", notes="OffGrid percentage share")
                    
                    row_elec_etotal("Electricity_ETotal", "Grid_Distribution", "CAPEX", "Tariff",
                                    el_etotal.GRID_distribution_CAPEX, "GRID")
                    row_elec_etotal("Electricity_ETotal", "Grid_Distribution", "OPEX", "Tariff",
                                    el_etotal.GRID_distribution_OPEX, "GRID")
                    row_elec_etotal("Electricity_ETotal", "Grid_Generation", "CAPEX", "Tariff",
                                    el_etotal.GRID_generation_CAPEX, "GRID")
                    row_elec_etotal("Electricity_ETotal", "Grid_Generation", "OPEX", "Tariff",
                                    el_etotal.GRID_generation_OPEX, "GRID")
                    row_elec_etotal("Electricity_ETotal", "OffGrid_Distribution", "CAPEX", "Tariff",
                                    el_etotal.OFFGRID_distribution_CAPEX, "OG")
                    row_elec_etotal("Electricity_ETotal", "OffGrid_Distribution", "OPEX", "Tariff",
                                    el_etotal.OFFGRID_distribution_OPEX, "OG")
                    row_elec_etotal("Electricity_ETotal", "OffGrid_Generation", "CAPEX", "Tariff",
                                    el_etotal.OFFGRID_generation_CAPEX, "OG")
                    row_elec_etotal("Electricity_ETotal", "OffGrid_Generation", "OPEX", "Tariff",
                                    el_etotal.OFFGRID_generation_OPEX, "OG")
                    row_elec_etotal("Electricity_ETotal", "E-Cooking", "CAPEX", "Tariff",
                                    el_etotal.E_Cooking_CAPEX, "E_Cooking", notes="E-cooking share")
                    row_elec_etotal("Electricity_ETotal", "E-Cooking", "OPEX", "Tariff",
                                    el_etotal.E_Cooking_OPEX, "E_Cooking", notes="E-cooking share")

                    # # 2) Electricidad - EDemand (agregado_edemand_costs)
                    # el_edemand: AggregatedElectricityCosts = fr.aggregated_edemand_costs
                    # def row_elec_edemand(sector, sub, cost_type, econ_type, value, life_key, notes=""):
                    #     lifetime = lifetime_defaults.get(life_key, "")
                    #     writer.writerow([
                    #         fid, year, semester,
                    #         sector, sub, cost_type, econ_type,
                    #         lifetime, f"{discount_rate}%", round(value, 3),
                    #         "-1%", notes
                    #     ])

                    # row_elec_edemand("Electricity_EDemand", "Grid_Distribution", "CAPEX", "Tariff",
                    #                 el_edemand.GRID_distribution_CAPEX, "GRID")
                    # row_elec_edemand("Electricity_EDemand", "Grid_Distribution", "OPEX", "Tariff",
                    #                 el_edemand.GRID_distribution_OPEX, "GRID")
                    # row_elec_edemand("Electricity_EDemand", "Grid_Generation", "CAPEX", "Tariff",
                    #                 el_edemand.GRID_generation_CAPEX, "GRID")
                    # row_elec_edemand("Electricity_EDemand", "Grid_Generation", "OPEX", "Tariff",
                    #                 el_edemand.GRID_generation_OPEX, "GRID")
                    # row_elec_edemand("Electricity_EDemand", "OffGrid_Distribution", "CAPEX", "Tariff",
                    #                 el_edemand.OFFGRID_distribution_CAPEX, "OG")
                    # row_elec_edemand("Electricity_EDemand", "OffGrid_Distribution", "OPEX", "Tariff",
                    #                 el_edemand.OFFGRID_distribution_OPEX, "OG")
                    # row_elec_edemand("Electricity_EDemand", "OffGrid_Generation", "CAPEX", "Tariff",
                    #                 el_edemand.OFFGRID_generation_CAPEX, "OG")
                    # row_elec_edemand("Electricity_EDemand", "OffGrid_Generation", "OPEX", "Tariff",
                    #                 el_edemand.OFFGRID_generation_OPEX, "OG")
                    # row_elec_edemand("Electricity_EDemand", "E-Cooking", "CAPEX", "Tariff",
                    #                 el_edemand.E_Cooking_CAPEX, "E_Cooking", notes="E-cooking share")
                    # row_elec_edemand("Electricity_EDemand", "E-Cooking", "OPEX", "Tariff",
                    #                 el_edemand.E_Cooking_OPEX, "E_Cooking", notes="E-cooking share")

                    # 3) LPG (agregado_lpg_costs)
                    lpg: AggregatedLpgCosts = fr.aggregated_lpg_costs
                    def row_lpg(sector, sub, cost_type, econ_type, value, life_key, notes=""):
                        lifetime = lifetime_defaults.get(life_key, "")
                        writer.writerow([
                            fid, year, semester,
                            sector, sub, cost_type, econ_type,
                            lifetime, f"{discount_rate}%", round(value, 3),
                            "-1%", notes
                        ])

                    row_lpg("LPG", "Local_Processing", "CAPEX", "Tariff",
                            lpg.LOCAL_processing_CAPEX, "LPG_Local")
                    row_lpg("LPG", "Local_Processing", "OPEX", "Tariff",
                            lpg.LOCAL_processing_OPEX, "LPG_Local")
                    row_lpg("LPG", "Local_Transport", "CAPEX", "Tariff",
                            lpg.LOCAL_transport_CAPEX, "LPG_Local")
                    row_lpg("LPG", "Local_Transport", "OPEX", "Tariff",
                            lpg.LOCAL_transport_OPEX, "LPG_Local")
                    row_lpg("LPG", "Upstream_Processing", "CAPEX", "Tariff",
                            lpg.UPS_processing_CAPEX, "LPG_Ups")
                    row_lpg("LPG", "Upstream_Processing", "OPEX", "Tariff",
                            lpg.UPS_processing_OPEX, "LPG_Ups")
                    row_lpg("LPG", "Upstream_Transport", "CAPEX", "Tariff",
                            lpg.UPS_transport_CAPEX, "LPG_Ups")
                    row_lpg("LPG", "Upstream_Transport", "OPEX", "Tariff",
                            lpg.UPS_transport_OPEX, "LPG_Ups")
                    row_lpg("LPG", "Upstream_Import", "OPEX", "Tariff",
                            lpg.UPS_import_OPEX, "LPG_Ups")

                    # 4) Subsidies (agregado_rest_subsidies_or_taxes_opex)
                    subs: AggregatedRestSubsidiesOrTaxesOpex = fr.aggregated_rest_subsidies_or_taxes_opex
                    for fuel_app_id, val in subs.appliances.items():
                        writer.writerow([
                            fid, year, semester,
                            "Rest_subsidies", f"Appliances_fuel_id_{fuel_app_id}", "OPEX", "Subsidy",
                            "", "", round(val, 3), "", ""
                        ])
                    for fuel_id, val in subs.fuels.items():
                        writer.writerow([
                            fid, year, semester,
                            "Rest_subsidies", f"Fuel_{fuel_id}", "OPEX", "Subsidy",
                            "", "", round(val, 3), "", ""
                        ])

                    # 5) Social Costs (agregado_social_costs)
                    social: AggregatedSocialCosts = fr.aggregated_social_costs
                    # health_costs, gender_costs, emissions_costs, deforestation_costs
                    writer.writerow([
                        fid, year, semester,
                        "SocialCosts", "Health", "Cost", "", "",
                        "", "", round(social.health_costs, 3),
                        "", ""
                    ])
                    writer.writerow([
                        fid, year, semester,
                        "SocialCosts", "Gender", "Cost", "", "",
                        "", "", round(social.gender_costs, 3),
                        "", ""
                    ])
                    writer.writerow([
                        fid, year, semester,
                        "SocialCosts", "Emissions", "Cost", "", "",
                        "", "", round(social.emissions_costs, 3),
                        "", ""
                    ])
                    writer.writerow([
                        fid, year, semester,
                        "SocialCosts", "Deforestation", "Cost", "", "",
                        "", "", round(social.deforestation_costs, 3),
                        "", ""
                    ])

                    # 6) Average Growth Calculation Appliances
                    avg_growth: AverageGrowthCalculationAppliances = fr.average_growth_calculation_appliances
                    for fuel_id, appliances_dict in avg_growth.appliances.items():
                        for appl_id, growth_val in appliances_dict.items():
                            writer.writerow([
                                fid, year, semester,
                                "ApplianceGrowth",
                                f"Fuel_{fuel_id}_Appliance_{appl_id}",  # Combinas fuel y appliance para identificación
                                "GrowthRate",
                                "",
                                "", "", "", "",
                                round(growth_val, 3)
                            ])


                    # 7) Income Tariff (ingresos por fuel)
                    income_tariff: IncomeTariff = fr.income_tariff
                    for fuel_id, inc_val in income_tariff.fuels.items():
                        writer.writerow([
                            fid, year, semester,
                            "IncomeTariff", f"Fuel_{fuel_id}", "Income", "",
                            "", "", round(inc_val, 3), "", ""
                        ])

            logging.info(
                "Financial export for Tableau completed in  : %s",
                output_path
            )

        except Exception as e:
            logging.error(
                "Error exporting financial tabular data for Tableau: %s",
                str(e), exc_info=True
            )
            raise



def export_summary_reports(states, output_dir):
    """
    Export Four summary TSV files in output_dir.

    1) SocialImpact.tsv
       Columns: State_ID, Year, Semester, Health, Ti_gender, Emissions, Deforestation
       Values: ratios vs base (base row = 1.0). Redondeo a 3 decimales.

    2) SocialImpact_Absolute.tsv
       Columns: State_ID, Year, Semester, Health, Ti_gender, Emissions, Deforestation, Economic
       Valores absolutos de cada estado (+ un parámetro económico si está disponible). Redondeo a 3 decimales.

    3) SocialImpact_Diff.tsv
       Columns: State_ID, Year, Semester, Health_Diff, Ti_gender_Diff, Emissions_Diff, Deforestation_Diff
       Diferencias absolutas (valor - base). Redondeo a 3 decimales.
    """
    try:
        # --- Prep output directory
        os.makedirs(output_dir, exist_ok=True)

        # --- Helper: semester getter robusto
        def semester_num(s):
            return getattr(s, "semester", 1) or 1

        # --- Selección de estado base
        def is_base_state(s):
            return getattr(s, "stage_id", None) == 0 and getattr(s, "semester", "").lower() == "first"

        base_candidates = [s for s in states if is_base_state(s)]
        if base_candidates:
            base_state = base_candidates[0]
        else:
            raise ValueError("No se encontró un estado base con stage_id=0 y semester='first'")

        # --- Extraer costes sociales del estado base
        base_fr = base_state.get_financial_results()
        base_social = getattr(base_fr, "aggregated_social_costs", None)
        if base_social is None:
            raise ValueError("El estado base no contiene 'aggregated_social_costs' en sus resultados financieros.")

        def get_float(obj, attr, default=0.0):
            return float(getattr(obj, attr, default) or default)

        base_vals = {
            "health":        get_float(base_social, "health_costs", 0.0),
            "gender":        get_float(base_social, "gender_costs", 0.0),
            "emissions":     get_float(base_social, "emissions_costs", 0.0),
            "deforestation": get_float(base_social, "deforestation_costs", 0.0),
        }

        # --- Evitar división por cero
        def safe_ratio(val, base):
            if base is None or base == 0:
                return 0.0
            return float(val) / float(base)
        
        def percent_change(curr, prev):
            if prev is None or prev == 0:
                return 0.0
            return (float(curr) - float(prev)) / float(prev) * 100.0

        # --- Extractor flexible para "Economic"
        warned_missing_econ = False
        econ_attr_candidates = [
            "economic_indicator", "economy", "economic_costs", "economic_value",
            "gdp", "income", "net_benefit", "npv_total", "total_income"
        ]
        def extract_economic_value(fin_results):
            nonlocal warned_missing_econ
            for name in econ_attr_candidates:
                if hasattr(fin_results, name):
                    try:
                        return float(getattr(fin_results, name) or 0.0)
                    except Exception:
                        continue
            # intentar agregado tipo 'aggregated_economics'
            agg_econ = getattr(fin_results, "aggregated_economics", None)
            if agg_econ is not None:
                for name in econ_attr_candidates:
                    if hasattr(agg_econ, name):
                        try:
                            return float(getattr(agg_econ, name) or 0.0)
                        except Exception:
                            continue
            if not warned_missing_econ:
                logging.warning(
                    "[SocialImpact_Absolute] No se encontró un atributo económico conocido en financial_results. "
                    "Se usará 0.0. Puedes indicar el nombre exacto y lo añadimos."
                )
                warned_missing_econ = True
            return 0.0

        # --- 1) SocialImpact.tsv (ratios)
        social_path = os.path.join(output_dir, "SocialImpact.tsv")
        with open(social_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerow(["State_ID", "Year", "Health", "Ti_gender", "Emissions", "Deforestation", "Semester"])

            for state in states:
                fid = getattr(state, "stage_id", "")
                year = getattr(state, "year", "")
                semester = semester_num(state)

                fr = state.get_financial_results()
                social = getattr(fr, "aggregated_social_costs", None)
                if social is None:
                    logging.warning(f"[SocialImpact] Estado {fid}: sin 'aggregated_social_costs'. Se registran ceros.")
                    health = gender = emissions = deforestation = 0.0
                else:
                    health        = get_float(social, "health_costs", 0.0)
                    gender        = get_float(social, "gender_costs", 0.0)
                    emissions     = get_float(social, "emissions_costs", 0.0)
                    deforestation = get_float(social, "deforestation_costs", 0.0)

                if state is base_state:
                    r_health = r_gender = r_emissions = r_deforestation = 1.0
                else:
                    r_health        = safe_ratio(health,        base_vals["health"])
                    r_gender        = safe_ratio(gender,        base_vals["gender"])
                    r_emissions     = safe_ratio(emissions,     base_vals["emissions"])
                    r_deforestation = safe_ratio(deforestation, base_vals["deforestation"])

                writer.writerow([
                    fid, year,
                    round(r_health, 3),
                    round(r_gender, 3),
                    round(r_emissions, 3),
                    round(r_deforestation, 3),
                    semester

                ])
        #======================= 2) CountryAdoptionPotentialByTech.tsv 
        # Solo potencial por tecnología, separado en rural y urbano (valores en fracción [-])
        adoption_path = os.path.join(output_dir, "CountryAdoptionPotentialByTech.tsv")
        with open(adoption_path, mode="w", newline="", encoding="utf-8") as f4:
            w4 = csv.writer(f4, delimiter="\t")
            w4.writerow(["State_ID", "Year", "Area", "Technology_ID", "Potential_Adoption [-]", "Semester"])

            # Orden temporal (igual criterio que en otros TSV)
            states_sorted = sorted(
                states,
                key=lambda s: (getattr(s, "year", 0), semester_num(s), getattr(s, "stage_id", 0))
            )

            for state in states_sorted:
                fid = getattr(state, "stage_id", "")
                year = getattr(state, "year", "")
                semn = semester_num(state)

                try:
                    pot_shares = state.get_country_adoption_shares(kind="potential")
                except Exception:
                    logging.warning(f"[AdoptionPotential] Estado {fid}: get_country_adoption_shares no disponible.")
                    pot_shares = {"rural": {}, "urban": {}, "total": {}}

                for area_key in ("rural", "urban"):
                    area_map = pot_shares.get(area_key, {}) or {}
                    # Salida estable: ordena por Technology_ID
                    for tech_id in sorted(area_map.keys()):
                        frac = float(area_map.get(tech_id, 0.0) or 0.0)
                        w4.writerow([fid, year, area_key, int(tech_id), round(frac, 6), semn])

       # ===================== 3) CostOfCooking.tsv =====================
        # Orden temporal para calcular % incremento vs estado anterior (mismo Area)
        states_sorted = sorted(states, key=lambda s: (getattr(s, "year", 0), semester_num(s), getattr(s, "stage_id", 0)))

        costcook_path = os.path.join(output_dir, "CostOfCooking.tsv")
        with open(costcook_path, mode="w", newline="", encoding="utf-8") as f3:
            w3 = csv.writer(f3, delimiter="\t")
            w3.writerow([
                "State_ID", "Year", "Area",
                "Price_per_Cook_USD", "Expenditure_USD/Year",
                "Percent_Increment_vs_Prev", "Semester"
            ])

            prev_exp_by_area = {"rural": None, "urban": None}

            for state in states_sorted:
                fid = getattr(state, "stage_id", "")
                year = getattr(state, "year", "")
                semn = semester_num(state)

                # Resumen país guardado previamente en State
                try:
                    country = state.get_country_base_price()
                except Exception:
                    logging.warning(f"[CostOfCooking] Estado {fid}: get_country_base_price no disponible. Se omite.")
                    continue

                for area_key in ("rural", "urban"):
                    block = country.get(area_key, {})
                    if not block:
                        continue

                    price_per_cook = float(block.get("av_income_per_cook", 0.0) or 0.0)              # $/cook
                    expenditure_million = float(block.get("annual_income", 0.0) or 0.0) # millones USD (crudo)

                    # % incremento vs estado anterior (misma área)
                    if is_base_state(state):
                        pct_inc = 0.0  # <-- base explícitamente 0.0
                    else:
                        prev_val = prev_exp_by_area[area_key]
                        pct_inc = percent_change(expenditure_million, prev_val) if prev_val is not None else 0.0

                    # Actualiza el previo SIEMPRE para la secuencia temporal
                    prev_exp_by_area[area_key] = expenditure_million

                    w3.writerow([
                        fid, year, area_key,
                        round(price_per_cook, 3),
                        round(expenditure_million, 3),
                        round(pct_inc, 2),
                        semn
                    ])

        # ===================== 4) EconomicAndSocial.tsv =====================
        # Contiene: Grand_Total (económico) + costes sociales absolutos por estado (país)
        # econ_path = os.path.join(output_dir, "EconomicAndSocial.tsv")
        # with open(econ_path, mode="w", newline="", encoding="utf-8") as f4:
        #     w4 = csv.writer(f4, delimiter="\t")
        #     w4.writerow(["State_ID", "Year", "Semester", "Grand_Total","BaseEDemand_Total", "Health", "Ti_gender", "Emissions", "Deforestation"])

        #     for state in states:
        #         fid = getattr(state, "stage_id", "")
        #         year = getattr(state, "year", "")
        #         semn = semester_num(state)

        #         # Económico: Grand Total (si no está calculado, 0.0)
        #         econ_res = None
        #         try:
        #             econ_res = state.get_economic_result()
        #         except Exception:
        #             logging.warning(f"[EconomicAndSocial] Estado {fid}: get_economic_result no disponible.")

        #         grand_total = float(getattr(econ_res, "grand_total", 0.0) or 0.0)

        #         # Sociales absolutos (mismo criterio que SocialImpact_Absolute)
        #         fr = state.get_financial_results()
        #         social = getattr(fr, "aggregated_social_costs", None)
        #         if social is None:
        #             health = gender = emissions = deforestation = 0.0
        #         else:
        #             health        = get_float(social, "health_costs", 0.0)
        #             gender        = get_float(social, "gender_costs", 0.0)
        #             emissions     = get_float(social, "emissions_costs", 0.0)
        #             deforestation = get_float(social, "deforestation_costs", 0.0)
        #             # Usamos el valor guardado en el State. Si en estados no-base es None,
        #         # tomamos el del estado base (para que sea constante en toda la serie).
        #         base_country_costs = state.get_country_base_edemand_costs()
        #         if base_country_costs is None:
        #             try:
        #                 base_country_costs = base_state.get_country_base_edemand_costs()
        #             except Exception:
        #                 base_country_costs = None

        #         bed_r = round(float(getattr(base_country_costs, "rural", 0.0) or 0.0), 3) if base_country_costs else 0.0
        #         bed_u = round(float(getattr(base_country_costs, "urban", 0.0) or 0.0), 3) if base_country_costs else 0.0
        #         bed_t = round((bed_r + bed_u), 3) if base_country_costs else 0.0

        #         w4.writerow([
        #             fid, year, semn,
        #             round(grand_total, 3), bed_t, 
        #             round(health, 3), round(gender, 3), round(emissions, 3), round(deforestation, 3),
                    
        #         ])

        # return {
        #     "social_impact": social_path,
        #     "adoption_potential_by_tech": adoption_path,
        #     "cost_of_cooking": costcook_path,
        #     "economic_and_social": econ_path,
        # }


    except Exception as e:
        logging.error("Error exporting summaries: %s", str(e), exc_info=True)
        raise


 

def export_electrified_areas_with_costs(mixed_states, demand_areas, output_file_path: str) -> None:
    """
    Escribe un TSV con SOLO las áreas electrificadas. Por fila:
      - State_ID, Year, Semester, DemandArea_ID, Area_Type
      - FINAL_* del bloque ElecTotal (costes del área)
      - EDemand [GWh/year]
      - E_Cooking [GWh/year] = ETotal - EDemand (si ETotal está disponible)
    """
   

    try:
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)

        header = [
            "State_ID", "Year", "Semester", "DemandArea_ID", "Area_Type",
            "F_FIX_USD/kWh", "F_REST_USD/kWh", "F_VAR_Grid_Gen_USD/kWh", "F_VAR_OffGrid_USD/kWh",
            "EDemand_GWh/year", "ETotal_GWh/year", "E_Cooking_GWh/year"
        ]

        with open(output_file_path, mode="w", newline="", encoding="utf-8") as tsv_file:
            tsv_writer = csv.writer(tsv_file, delimiter="\t")
            tsv_writer.writerow(header)

            for state in mixed_states:
                state_id = getattr(state, "stage_id", "")
                year = getattr(state, "year", "")
                semester = getattr(state, "semester", 1)

                for demand_area in demand_areas:
                    for area_type in ["rural", "urban"]:
                        #area_cp = demand_area.get_cost_parameters(area_type)
                        

                        if not state.is_electrified(demand_area.id, area_type):
                            continue  # No electrificado
                        electricity_costs_blocks = state.get_electricity_cost_parameters(demand_area.id)["cost_parameters"]
                        for block in ['ElecTotal']: #, 'EDemand'):
                            if block in electricity_costs_blocks:
                                cost_params: CostParameters = electricity_costs_blocks[block]
                                area_obj = (cost_params.rural if area_type == 'rural' else cost_params.urban)
                                area_cp = area_obj.costs
                       

                                F_FIX = area_cp.FINAL_FIX_Grid_Gen # float(area_cp.FINAL_FIX_Grid_Gen, 0.0) 
                                F_REST = area_cp.FINAL_Rest # float(area_cp.FINAL_Rest, 0.0)
                                F_VAR_G = area_cp.FINAL_VAR_Grid_Gen # float(area_cp.FINAL_VAR_Grid_Gen, 0.0)
                                F_VAR_OG = area_cp.FINAL_VAR_OffGrid # float(area_cp.FINAL_VAR_OffGrid, 0.0)
                        
                        fuel_id_electric = 1
                                

                        region_income = state.get_region_income(demand_area.id, area_type) or {}
                        edemand_gwh = float(region_income.get("electric", 0.0))
                        fuels_income = region_income.get("fuels", {}) or {}
                        e_cooking_gwh = float(fuels_income.get(fuel_id_electric, 0.0))
                        etotal_gwh = edemand_gwh + e_cooking_gwh



                        # edemand_gwh = state.get_electric_consumption(demand_area.id, area_type)
                        # if isinstance(edemand_gwh, dict):
                        #     edemand_gwh = edemand_gwh.get(area_type, 0.0)
                        # edemand_gwh = float(edemand_gwh or 0.0)

                        # etotal_gwh = state.get_el_total_consumption(demand_area.id, area_type)
                        # if isinstance(etotal_gwh, dict):
                        #     etotal_gwh = etotal_gwh.get(area_type, 0.0)
                        # etotal_gwh = float(etotal_gwh) if etotal_gwh is not None else None

                        # e_cooking_gwh = None
                        # if etotal_gwh is not None:
                        #     e_cooking_gwh = etotal_gwh - edemand_gwh

                        row = [
                            state_id,
                            year,
                            semester,
                            demand_area.id,
                            area_type,
                            round(F_FIX, 3),
                            round(F_REST, 3),
                            round(F_VAR_G, 3),
                            round(F_VAR_OG, 3),
                            round(edemand_gwh, 3),
                            round(etotal_gwh, 3) if etotal_gwh is not None else "",
                            round(e_cooking_gwh, 3) if e_cooking_gwh is not None else ""
                        ]   
                        tsv_writer.writerow(row)
        logging.info(
            "Exported electrified areas with costs to: %s",
            output_file_path
        )
    except Exception as e:
        logging.error("Error exporting electrified areas with costs: %s", str(e), exc_info=True)
        raise



def summarize_country_electric_demand(mixed_states, output_file_path: str) -> None:
    """
    Escribe un TSV resumiendo la demanda eléctrica total por país y año.
    Columnas:
      - State_ID, Year, Semester
      - ETotalDemand_Total_GWh/year
      - Grid_Electricity_Share [%]
    """
    try:
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)

        header = [
            "State_ID", "Year", "Semester",
            "ETotalDemand_Total_GWh/year", 
            "Off_Grid_Electricity_Share [%]", 
        ]

        with open(output_file_path, mode="w", newline="", encoding="utf-8") as tsv_file:
            tsv_writer = csv.writer(tsv_file, delimiter="\t")
            tsv_writer.writerow(header)

            for state in mixed_states:
                state_id = getattr(state, "stage_id", "")
                year = getattr(state, "year", "")
                semester = getattr(state, "semester", 1)

                country_demand = float(state.get_total_country_el_demand()) or 0.0
                grid_share = float(state.get_country_off_grid_percentage() or 0.0) * 100.0

                row = [
                    state_id,
                    year,
                    semester,
                    round(country_demand, 3),
                    round(grid_share, 2),
                ]
                tsv_writer.writerow(row)

                

        logging.info(
            "Exported country electric demand summary to: %s",
            output_file_path
        )
    except Exception as e:
        logging.error("Error exporting country electric demand summary: %s", str(e), exc_info=True)
        raise
    


