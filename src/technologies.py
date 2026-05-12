import logging
import pandas as pd
from src import config  # Configuración cargada desde el YAML
import os 



class Technologies:
    def __init__(self, data_manager):
        self.data_manager = data_manager
        self.technologies_df = self.data_manager.get_dataframe("Cooking_technologies")
        self.fuels_df = self.data_manager.get_dataframe("Cooking_fuels")
        self.appliances_df = self.data_manager.get_dataframe("Cooking_appliances")
        self.raw_materials_df = self.data_manager.get_dataframe("Cooking_rawMaterials")
        self.supply_chains_df = self.data_manager.get_dataframe("Cooking_supplyChains")
        self.general_config = self.data_manager.get_config()  # Accede a la configuración general
        self.local_distance = self.general_config.get("Last_mile_distance") # Distancia de la última milla
    def calculate_all(self):
        """
        Perform all necessary calculations for the technologies.
        """
        logging.info("Iniciando cálculos de tecnologías.")

        # Iterar sobre cada fila del DataFrame de tecnologías
        for index, technology in self.technologies_df.iterrows():
            try:
                # Obtener Fuel y Appliance relacionados
                fuel = self.fuels_df[self.fuels_df["Fuel_id"] == technology["Fuel_id"]]
                appliance = self.appliances_df[self.appliances_df["Appliance_id"] == technology["Appliance_id"]]

                # Verificar si hay datos disponibles para Fuel y Appliance
                if fuel.empty or appliance.empty:
                    logging.warning(f"Faltan datos para Fuel o Appliance en la tecnología {technology['Tech_name']}.")
                    continue

                fuel = fuel.iloc[0]  # Acceso directo a la fila
                appliance = appliance.iloc[0]

                # Calcular atributos y asignarlos al DataFrame de tecnologías
                self.technologies_df.at[index, "FuelPrice"] = self.calculate_fuel_price(fuel, appliance)
                self.technologies_df.at[index, "AppliancePrice"] = self.calculate_appliance_price(appliance)
                self.technologies_df.at[index, "Health"] = self.calculate_health_impact(appliance)
                self.technologies_df.at[index, "FuelTimeGen"], self.technologies_df.at[index, "ApplianceTimeGen"] = self.calculate_time_generation(fuel, appliance)
                self.technologies_df.at[index, "Emissions"] = self.calculate_emissions(technology)
                self.technologies_df.at[index, "Deforestation"] = self.calculate_deforestation(technology)

            except Exception as e:
                logging.error(f"Error al procesar la tecnología {technology['Tech_name']} (ID: {technology['Technologies_id']}): {e}", exc_info=True)

        # Actualizar el DataFrame enriquecido en DataManager
        self.data_manager.update_dataframe("Cooking_technologies", self.technologies_df)

        # Guardar el DataFrame enriquecido en un archivo CSV
        self.save_to_tsv()

        logging.info("Technology calculations completed, updated in DataManager and saved to a CSV file.")

    def calculate_fuel_price(self, fuel, appliance):
        """
        Calculating the fuel price by multiplying by DemMult_C from general_config.
        """
        try:
            # Obtener valores necesarios
            calorific_value = fuel["Calorific_value"]
            efficiency = appliance["Efficiency"]
            fuel_price = fuel["Price"]

            # Obtener DemMult_C del general_config
            general_data = self.general_config.get_general_data()
            dem_mult_c = general_data.get("DemMult_C")
            if dem_mult_c is None:
                logging.warning("DemMult_C no está definido en la configuración general. Usando valor predeterminado de 1.")
                dem_mult_c = 1

            # Calcular FuelPrice
            result = fuel_price * dem_mult_c / (calorific_value * efficiency)
            logging.debug(f"FuelPrice calculado: {result} (Fuel ID: {fuel['Fuel_id']}, Appliance ID: {appliance['Appliance_id']}, DemMult_C: {dem_mult_c})")
            return result
        except Exception as e:
            logging.error(f"Error al calcular FuelPrice: {e}", exc_info=True)
            return None


    def calculate_appliance_price(self, appliance):
        """
        Calculating the appliance price.
        """
        try:
            lifetime = appliance["Lifetime"]
            appliance_price = appliance["Retail_price"]
            result = appliance_price / lifetime
            logging.debug(f"AppliancePrice calculado: {result} (Appliance ID: {appliance['Appliance_id']})")
            return result
        except Exception as e:
            logging.error(f"Error al calcular AppliancePrice: {e}", exc_info=True)
            return None

    def calculate_health_impact(self, appliance):
        """
        Calculating the health impact.
        """
        try:
            result = appliance["Health"]
            logging.debug(f"HealthImpact calculado: {result} (Appliance ID: {appliance['Appliance_id']})")
            return result
        except Exception as e:
            logging.error(f"Error al calcular HealthImpact: {e}", exc_info=True)
            return None

    def calculate_time_generation(self, fuel, appliance):
        """
        Calculating the time generation for the fuel and appliance.
        """
        try:
            calorific_value = fuel["Calorific_value"]
            efficiency = appliance["Efficiency"]
            fuel_time_gen = fuel["Time_gender"] / (calorific_value * efficiency)
            appliance_time_gen = appliance["Time_gender"]
            logging.debug(f"FuelTimeGen: {fuel_time_gen}, ApplianceTimeGen: {appliance_time_gen} (Fuel ID: {fuel['Fuel_id']}, Appliance ID: {appliance['Appliance_id']})")
            return fuel_time_gen, appliance_time_gen
        except Exception as e:
            logging.error(f"Error al calcular TimeGeneration: {e}", exc_info=True)
            return None, None

    def calculate_emissions(self, technology):
        """
        Calculating total emissions of supply chain.
        Added normalization to percentages of supply chain that owns to the same fuel in order to sum 100%.
        """
        try:
            # Filtrar todas las cadenas de suministro correspondientes al Fuel_id
            fuel_id = technology["Fuel_id"]
            supply_chains = self.supply_chains_df[self.supply_chains_df["Fuel_id"] == fuel_id]
            
            if supply_chains.empty:
                logging.warning(f"No supply chain found for Fuel_id: {fuel_id}")
                return 0

            # Depuración inicial de las cadenas de suministro
            #logging.debug(f"Cadenas de suministro encontradas para Fuel_id {fuel_id}: {supply_chains}")

            # Calcular la suma total de Fuel_percentage
            total_fuel_percentage = supply_chains["Fuel_percentage"].sum()
            if total_fuel_percentage <= 0:
                logging.warning(f"Fuel_percentage not valid or zero for Fuel_id: {fuel_id}")
                return 0

            # Normalizar los porcentajes si no suman exactamente 100%
            if total_fuel_percentage != 1.0:
                #logging.info(f"Normalizando Fuel_percentage para Fuel_id: {fuel_id} (suma actual: {total_fuel_percentage})")
                #supply_chains["Fuel_percentage"] /= total_fuel_percentage
                supply_chains.loc[:, "Fuel_percentage"] /= total_fuel_percentage


            # Calcular emisiones de transporte para cada cadena de suministro
            transport_emissions = 0
            for _, row in supply_chains.iterrows():
                emissions = (
                    row["Emissions_transportation"] * 
                    row["FuelTransp_distance"] * 
                    row["Fuel_percentage"]
                )
                transport_emissions += emissions
               #logging.debug(f"Emisiones calculadas para Supply Chain {row['SupplyChain_id']}: {emissions}")

            # Obtener las emisiones de procesamiento
            process_emissions = supply_chains["Emissions_processing"].sum()
            #logging.debug(f"Emisiones de procesamiento totales para Fuel_id {fuel_id}: {process_emissions}")

            # Calcular el total de emisiones
            total_emissions = process_emissions + transport_emissions
            #logging.info(f"Emisiones totales calculadas para Fuel_id {fuel_id}: {total_emissions}")

            return total_emissions

        except KeyError as e:
            logging.error(f"Missing column in Supply Chain: {e}")
            raise

    def calculate_emissions(self, technology):
        """
        Complete emissions calculation for a technology.
        Form:
        Emisiones = Emisiones_appliance + (Emisiones_transporte + Emisiones_proceso) / eficiencia + (emisiones_raw / fuelraw / eficiencia)
        """
        try:
            fuel_id = technology["Fuel_id"]
            appliance_id = technology["Appliance_id"]

            # 1. Obtener Supply Chains asociados al fuel
            supply_chains = self.supply_chains_df[self.supply_chains_df["Fuel_id"] == fuel_id]
            if supply_chains.empty:
                logging.warning(f"No se encontró Supply Chain para Fuel_id: {fuel_id}")
                return 0

            # 2. Normalizar Fuel_percentage
            total_fuel_percentage = supply_chains["Fuel_percentage"].sum()
            if total_fuel_percentage <= 0:
                logging.warning(f"Fuel_percentage not valid or zero for Fuel_id: {fuel_id}")
                return 0
            if total_fuel_percentage != 1.0:
                supply_chains.loc[:, "Fuel_percentage"] /= total_fuel_percentage

            # 3. Transporte
            transport_emissions = sum(
                row["Emissions_transportation"] * row["FuelTransp_distance"] * row["Fuel_percentage"]
                for _, row in supply_chains.iterrows()
            )

            # 4. Procesamiento
            process_emissions = supply_chains["Emissions_processing"].sum()

            # 5. Eficiencia: cal_value * appliance_efficiency
            fuel_row = self.fuels_df[self.fuels_df["Fuel_id"] == fuel_id]
            if fuel_row.empty:
                logging.warning(f"No fuel found for Fuel_id: {fuel_id}")
                return 0
            calorific_value = fuel_row.iloc[0]["Calorific_value"]

            appliance_row = self.appliances_df[self.appliances_df["Appliance_id"] == appliance_id]
            if appliance_row.empty:
                logging.warning(f"No appliance found for Appliance_id: {appliance_id}")
                return 0
            appliance_efficiency = appliance_row.iloc[0]["Efficiency"]

            efficiency = calorific_value * appliance_efficiency
            if efficiency == 0:
                logging.warning(f"Null efficiency for Fuel_id {fuel_id} and Appliance_id {appliance_id}")
                return 0

            # 6. Emisiones de entrada del Appliance
            appliance_entry_emissions = appliance_row.iloc[0].get("Emissions", 0)

            # 7. Emisiones por materia prima
            raw_ids = supply_chains["RawMat_id"].unique()
            raw_data = self.raw_materials_df[self.raw_materials_df["RawMat_id"].isin(raw_ids)]
            raw_emissions = raw_data["Emissions"].sum() if not raw_data.empty else 0

            # 8. Eficiencia del combustible crudo (fuelraw) desde supply chain
            fuel_raw_efficiency = supply_chains["Efficiency"].mean()  # o el valor de la primera fila si prefieres

            # 9. Cálculo total
            total_emissions = (
                appliance_entry_emissions +
                (transport_emissions + process_emissions) / efficiency +
                (raw_emissions / fuel_raw_efficiency / efficiency)
            )

            return total_emissions

        except KeyError as e:
            logging.error(f"Missing column in data: {e}")
            return 0
        except Exception as e:
            logging.error(f"Error calculating emissions for technology {technology.get('Tech_name', 'unknown')}: {e}", exc_info=True)
            return 0




    def calculate_deforestation(self, technology):
        """
        Calculate the deforestation caused by the use of wood as fuel.
        """
        try:
            # Obtener los IDs de madera desde la configuración general
            general_data = self.general_config.get_general_data()
            wood_ids = general_data.get("WoodRawMaterial_Id", [])
            if not isinstance(wood_ids, list):
                wood_ids = [wood_ids]

            logging.debug(f"IDs de madera obtenidos de la configuración: {wood_ids}")

            # Relacionar el Fuel_id de la tecnología con Supply Chains
            fuel_id = technology["Fuel_id"]
            supply_chain = self.supply_chains_df[self.supply_chains_df["Fuel_id"] == fuel_id]

            if supply_chain.empty:
                logging.warning(f"No se encontró Supply Chain para Fuel_id: {fuel_id}")
                return 0

            # Filtrar Supply Chains cuyos RawMat_id correspondan a IDs de madera
            supply_chain = supply_chain[supply_chain["RawMat_id"].isin(wood_ids)]

            if supply_chain.empty:
                logging.info(f"There is no RawMat_id in Supply Chain corresponding to wood for Fuel_id: {fuel_id}")
                return 0

            # Obtener la eficiencia del combustible desde Supply Chain
            fuel_raw_efficiency = supply_chain.iloc[0]["Efficiency"]
            logging.debug(f"Efficiency of fuel (Supply Chain): {fuel_raw_efficiency}")

            # Calcular la eficiencia de la tecnología: Calorific Value * Appliance Efficiency
            fuel = self.fuels_df[self.fuels_df["Fuel_id"] == fuel_id]
            if fuel.empty:
                logging.warning(f"No fuel information found for Fuel_id: {fuel_id}")
                return 0

            calorific_value = fuel.iloc[0]["Calorific_value"]

            appliance = self.appliances_df[self.appliances_df["Appliance_id"] == technology["Appliance_id"]]
            if appliance.empty:
                logging.warning(f"No appliance information found for Appliance_id: {technology['Appliance_id']}")
                return 0

            appliance_efficiency = appliance.iloc[0]["Efficiency"]

            technology_efficiency = calorific_value * appliance_efficiency
            logging.debug(f"Efficiency of technology calculated: {technology_efficiency}")

            # Calcular la deforestación
            deforestation_value = 1 / fuel_raw_efficiency / technology_efficiency
            logging.debug(f"Deforestation calculated: {deforestation_value}")

            return deforestation_value

        except KeyError as e:
            logging.error(f"Missing column in some DataFrame: {e}")
            return 0

        except Exception as e:
            logging.error(f"Error calculating deforestation: {e}")
            return 0




    def save_to_tsv(self):
        """
        Saves the enriched technologies DataFrame to a TSV file with tab separator and '.' as decimal separator
        at the path defined in the configuration file.
        """
        try:
            # Obtener la ruta de salida desde el archivo de configuración
            output_dir = config["path"]["offline_data_files"]
            output_path = os.path.join(output_dir, "enriched_technologies.tsv")
            

            # Crear la carpeta si no existe
            os.makedirs(output_dir, exist_ok=True)

            # Guardar el DataFrame
            self.technologies_df.to_csv(output_path, sep="\t", decimal=".", index=False)

            #register dataframe in data_manager for offile process use
            self.data_manager.register_dataframe("enriched_technologies", self.technologies_df)

            logging.info(f"DataFrame of enriched technologies saved to: {output_path}")
        except KeyError as e:
            logging.error(f"The key 'path.preprocess' is not defined in the configuration file: {e}")
        except Exception as e:
            logging.error(f"Error saving the enriched technologies DataFrame: {e}")

    def enriched_technologies_without_electricity(data_manager):
        """
        Returns the enriched technologies DataFrame without the technologies that use electricity as fuel.
        """
        df_technologies_without_electricity = data_manager.get_dataframe("enriched_technologies")
        return df_technologies_without_electricity[df_technologies_without_electricity["Fuel_id"] != 1]
    
    def enriched_tecnologies_without_gas(data_manager):
        """
        Returns the enriched technologies DataFrame without the technologies that use gas as fuel.
        """
        df_technologies_without_gas = data_manager.get_dataframe("enriched_technologies")
        return df_technologies_without_gas[df_technologies_without_gas["Fuel_id"] != 2]
    
    def enriched_technologies_without_electricity_and_gas(data_manager):
        """
        Returns the enriched technologies DataFrame without the technologies that use electricity and gas as fuel.
        """
        df_technologies_without_electricity_and_gas = data_manager.get_dataframe("enriched_technologies")
        return df_technologies_without_electricity_and_gas[
            (df_technologies_without_electricity_and_gas["Fuel_id"] != 1) & 
            (df_technologies_without_electricity_and_gas["Fuel_id"] != 2)
        ]
    