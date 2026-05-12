import logging
from src.el_emissions_params import EmissionELParameters
import csv
import os

class EmissionsElectricity:
    def __init__(self, state, data_manager, demand_area, electricity_model):
        """
        Constructor for EmissionsElectricity.
        
        :param final_costs: Dictionary containing final electricity technology costs.
        :param adjustment_factor: Adjustment factor for emissions calculation.
        """
        self.state = state
        self.data_manager = data_manager
        self.demand_area = demand_area
        self.electricity_model = electricity_model
       

        # Necesito Extraer datos: 
        # Diesel Emissions 
        self.general_cofig = self.data_manager.get_config()
        self.diesel_emission_rate = self.general_cofig.get("Diesel_emissions")
        # Loss pu 
        self.power_losses_factor = self.general_cofig.get("Power_losses_factor") #/100  #Pasamos el porcentaje a decimal
        # Em. rate Emissions_rate
        self.emission_rate = self.general_cofig.get("Emissions_rate")
        # Y de la clase El_CostModel
        # OG_G Diesel rate pu 
        # ogu y ogr 
        # gcr y gru


        self.emissions_parameters = {
            "ElecTotal": EmissionELParameters(),
            "EDemand": EmissionELParameters()
        }

    def calculate_emissions(self):
        """
        Calculates electricity emissions for both ElecTotal and EDemand.
        
        The formulas used are:
        
            OG Emissions Overall:
                ((Loss pu + 1)/2) * (ogu + ogr) * OG_G DieselRate * DieselEmissions / 1000
            
            OG Emissions Rural:
                ((Loss pu + 1)/2) * (ogr) * OG_G DieselRate * DieselEmissions / 1000
            
            OG Emissions Urban:
                ((Loss pu + 1)/2) * (ogu) * OG_G DieselRate * DieselEmissions / 1000
            
            Grid Emissions Rural:
                ((Loss pu + 1)/1000) * (gcr) * Emissions_rate
            
            Grid Emissions Urban:
                ((Loss pu + 1)/1000) * (gru) * Emissions_rate
        
        The cost parameters (OG_G Diesel rate pu, ogu, ogr, gcr, gru) are extracted from the electricity model.
        """
        try:
            # Loop through both blocks: ElecTotal and EDemand
            for block in ["ElecTotal", "EDemand"]:
                cp = self.electricity_model.cost_parameters[block]
                
                # Extract required parameters from cost parameters structure
                og_g_diesel_rate = cp.general.costs.OG_G_Diesel_rate  # OG_G Diesel rate (pu)
                ogu = cp.urban.consumption.ogu  # Urban adjustment (ogu)
                ogr = cp.rural.consumption.ogr  # Rural adjustment (ogr)
                gcr = cp.rural.consumption.GCr  # Rural generation consumption (gcr)
                gru = cp.urban.consumption.GCu  # Urban generation consumption (gru)
                
                # Calculate factors based on power losses
                factor_og = ((self.power_losses_factor + 1) / 2 ) / 1000
                factor_grid = (self.power_losses_factor + 1) / 1000
                
                # Calculate OG emissions 
                og_emiss_overall = factor_og * (ogu + ogr) * og_g_diesel_rate * self.diesel_emission_rate 
                og_emiss_rural   = factor_og * ogr * og_g_diesel_rate * self.diesel_emission_rate 
                og_emiss_urban   = factor_og * ogu * og_g_diesel_rate * self.diesel_emission_rate 
            
                # Calculate Grid emissions
                grid_emiss_rural = factor_grid * gcr * self.emission_rate
                grid_emiss_urban = factor_grid * gru * self.emission_rate
                
                # Assign calculated emissions into the emissions_parameters structure
                ep = self.emissions_parameters[block]
                ep.general.OG_Emiss = og_emiss_overall
                ep.rural.OG_Emiss = og_emiss_rural
                ep.urban.OG_Emiss = og_emiss_urban
                ep.rural.Grid_Emiss = grid_emiss_rural
                ep.urban.Grid_Emiss = grid_emiss_urban
            
            logging.info("Emissions calculated and assigned: %s", self.emissions_parameters)
            return self.emissions_parameters
        except Exception as e:
            logging.error("Error calculating electricity emissions: %s", e, exc_info=True)
            raise

 

    def export_electricity_emissions_debug_info(self, output_path, state_id):
        """
        Exports the calculated electricity emissions for the blocks ElecTotal and EDemand
        in TSV format, including general, rural, and urban emissions by block type.
        """
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            with open(output_path, "a", newline='') as tsvfile:
                writer = csv.writer(tsvfile, delimiter="\t")

                # Escribir encabezado si el archivo está vacío
                if os.stat(output_path).st_size == 0:
                    writer.writerow([
                        "State_ID", "ElectricArea_ID", "Block", "DemandAreaID", "AreaType",
                        "Grid_Emiss", "OG_Emiss"
                    ])

                electric_area_id = self.electricity_model.demand_area_el_id
                demand_area_id = self.demand_area.id

                for block in ["ElecTotal", "EDemand"]:
                    ep = self.emissions_parameters[block]

                    # General (overall emissions — solo OG)
                    writer.writerow([
                        state_id,
                        electric_area_id,
                        block,
                        demand_area_id,
                        "general",
                        "",  # Grid emissions not applicable for general
                        round(ep.general.OG_Emiss, 6)
                    ])

                    # Rural
                    writer.writerow([
                        state_id,
                        electric_area_id,
                        block,
                        demand_area_id,
                        "rural",
                        round(ep.rural.Grid_Emiss, 6),
                        round(ep.rural.OG_Emiss, 6)
                    ])

                    # Urban
                    writer.writerow([
                        state_id,
                        electric_area_id,
                        block,
                        demand_area_id,
                        "urban",
                        round(ep.urban.Grid_Emiss, 6),
                        round(ep.urban.OG_Emiss, 6)
                    ])

            logging.info("Electricity emissions debug info exported to %s", output_path)
        except Exception as e:
            logging.error("Error exporting electricity emissions debug info: %s", str(e), exc_info=True)
            raise
