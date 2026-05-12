import pandas as pd
import logging
import os

class NonDeployEmissionsModel:
    def __init__(self, state, data_manager, demand_area, adoption_model, income_model, tech_without_el_and_gas):
        """
        Constructor for NonDeployEmissionsModel.

        :param state: Current state.
        :param data_manager: Object that manages data access.
        :param demand_area: Identifier or information for the demand area.
        :param adoption_model: Instance of the adoption model.
        :param income_model: Instance of the income model, which contains the 'absolute_income_adoption'
                             dictionary with keys "rural" and "urban".
        :param tech_without_el_and_gas: DataFrame with technology data (excluding electricity and gas) 
                                        with at least columns: 'techID' and 'tech_emissions'.
        """
        self.state = state
        self.data_manager = data_manager
        self.demand_area = demand_area
        #self.area_type = demand_area.area_type
        self.adoption_model = adoption_model
        self.income_model = income_model
        self.tech_without_el_and_gas = tech_without_el_and_gas

        # Initialize the final emissions dictionary for each demand area and area type.
        self.final_tech_emissions = {}

    @property
    def area_types(self):
        """
        Returns ['rural'] or ['urban'] if self.demand_area.area_type is defined,
        or both ['rural', 'urban'] if it is not defined (None).
        """
        return [self.demand_area.area_type] if self.demand_area.area_type else ['rural', 'urban']

    def run_simulation(self):
        """
        Executes the simulation to calculate the final emissions for each technology for both area types.
        
        The formula applied for each technology is:
        
            final_emission = absolute_demand_adoption * tech_emissions / 1000
        
        where:
          - tech_emissions is retrieved from the tech_without_el_and_gas DataFrame (column "tech_emissions").
          - absolute_demand_adoption is obtained from income_model.absolute_income_adoption[area_type][techID].
        
        All errors are logged and re-raised.
        """
        try:
            logging.info("Starting NonDeployEmissionsModel simulation for demand area: %s", self.demand_area)
            # Iterate over each area type: rural and urban
            #for area_type in ["rural", "urban"]:
                # Iterate over each technology in the DataFrame
            # Paso 1: ignorar áreas con demanda de cocina cero
            for area_type in self.area_types:
                base_cook = self.demand_area.data.get("demand_census_rur_urb", {}).get(area_type, {}).get("cooking", 0)
                if base_cook == 0:
                    logging.warning("Demanda de cocina cero para área %s (%s), se ignora el cálculo de emisiones.", self.demand_area.id, area_type)
                    self.final_tech_emissions[area_type] = {}
                    return self.final_tech_emissions

                for idx, tech in self.tech_without_el_and_gas.iterrows():
                    try:
                        tech_id = tech['Technologies_id']
                        tech_emissions = float(tech['Emissions'])  # Assuming tech_emissions is a float in the DataFrame
                        
                        #float(self.tech_without_el_and_gas.loc[tech_id, "Emissions"].iloc[0])
                        
                        
                        # Retrieve the absolute demand adoption for this technology and area type
                        #absolute_demand = self.income_model.absolute_income_adoption.get(self.area_type, {}).get(tech_id, 0.0)
                        absolute_demand = self.state.get_absolute_income_adoption(self.demand_area.id, area_type).get(tech_id, 0.0)
                        # Calculate the final emissions using the provided formula
                        final_emission = absolute_demand * tech_emissions / 1000.0
                        # Save the result under the corresponding area type
                        self.final_tech_emissions[tech_id] = final_emission
                
                    except Exception as inner_e:
                        logging.error("Error processing technology %s for area %s: %s", tech.get('techID', 'unknown'), area_type, inner_e, exc_info=True)
                
                        # Optionally, continue processing the remaining technologies
                logging.info("Completed processing for area type: %s",area_type)
                logging.info("Final emissions calculated: %s", self.final_tech_emissions)
                # Save into state
                self.state.save_non_deploy_emissions(self.demand_area.id, area_type,  self.final_tech_emissions)

                
            return self.final_tech_emissions
        except Exception as e:
            logging.error("Error in run_simulation of NonDeployEmissionsModel: %s", e, exc_info=True)
            raise



    def export_rest_emissions_debug_info(self, output_path, state_id):
        """
        Exports the final emissions results for technologies in tabular format.
        Added append mode to avoid overwriting the file if it already exists.

        Columnas:
        - DemandArea_ID
        - State_ID
        - AreaType
        - Technology_ID
        - FinalEmissions_kg
        """
        try:
           
            for area_type in self.area_types: 
                if not self.final_tech_emissions.get(area_type):
                    logging.warning("No hay emisiones calculadas para área %s (%s), se omite la exportación.", self.demand_area.id, area_type)
                    return

                rows = []
                for tech_id, emission in self.final_tech_emissions[area_type].items():
                    rows.append({
                        "DemandArea_ID": self.demand_area.id,
                        "State_ID": state_id,
                        "AreaType": area_type,
                        "Technology_ID": tech_id,
                        "FinalEmissions_kg": emission
                    })

                df = pd.DataFrame(rows)

                # Crear directorio si es necesario
                dir_path = os.path.dirname(output_path)
                if dir_path:
                    os.makedirs(dir_path, exist_ok=True)

                # Determinar si se escribe encabezado (solo si el archivo no existe o está vacío)
                write_header = not os.path.exists(output_path) or os.stat(output_path).st_size == 0

                # Escribir en modo append
                df.to_csv(output_path, sep="\t", index=False, mode='a', header=write_header)
                logging.info(f"NonDeployEmissionsModel appended to {output_path} ({len(df)} filas)")
            
        except Exception as e:
            logging.error("Error exporting emissions debug info: %s", e, exc_info=True)
            raise

