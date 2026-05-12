import logging
#from src.report_generator import ReportGenerator
import os
from src import config


class ConsistencyCheck:
    def __init__(self, routes_config_loader, log: logging, report):
        self.routes_config_loader = routes_config_loader
        self.log = log
        self.report = report
        inputs_path = config["path"]["inputs"]

        self.required_files = {
            'Electric_load': f'{inputs_path}/Catalogs/De1/De1-Electric.tsv',
            'E-Cooking_load': f'{inputs_path}/Catalogs/De1/De1-Cooking.tsv',
            'E-Heating_load': f'{inputs_path}/Catalogs/De1/De1-Heating.tsv',
            'BuildTypes_config': f'{inputs_path}/Catalogs/De2/De2-Config.tsv',
            'BuildTypes_electric': f'{inputs_path}/Catalogs/De2/De2-Electric.tsv',
            'BuildTypes_cooking': f'{inputs_path}/Catalogs/De2/De2-Cooking.tsv',
            'BuildTypes_heating': f'{inputs_path}/Catalogs/De2/De2-Heating.tsv',
            'Cooking_technologies': f'{inputs_path}/Catalogs/Ck1/Ck1-Technologies.tsv',
            'Cooking_appliances': f'{inputs_path}/Catalogs/Ck1/Ck1-Appliances.tsv',
            'Cooking_fuels': f'{inputs_path}/Catalogs/Ck1/Ck1-Fuels.tsv',
            'Cooking_rawMaterials': f'{inputs_path}/Catalogs/Ck1/Ck1-RawMaterials.tsv',
            'Cooking_supplyChains': f'{inputs_path}/Catalogs/Ck1/Ck1-SupChains.tsv',
            'Social_clusters': f'{inputs_path}/Country/De4/De4.tsv',
            'Territory_partition': f'{inputs_path}/Country/Tp1/Tp1-Rwanda.tsv',
            'LocBio_priceMult': f'{inputs_path}/Country/Bm1/Bm1-LocalPriceMult.tsv',
            'LocBio_timeGenMult': f'{inputs_path}/Country/Bm1/Bm1-LocalTimeGenMult.tsv',
            'ScenGrow_config': f'{inputs_path}/Country/De5/De5-Config.tsv',
            'ScenGrow_appRetPrice': f'{inputs_path}/Country/De5/De5-AppliancesRetPrice.tsv',
            'ScenGrow_demElast': f'{inputs_path}/Country/De5/De5-DemandElast.tsv',
            'ScenGrow_demMult': f'{inputs_path}/Country/De5/De5-DemandMult.tsv',
            'ScenGrow_depFuelCostVar': f'{inputs_path}/Country/De5/De5-DepFuelsCostVariation.tsv',
            'ScenGrow_fuelRetPrice': f'{inputs_path}/Country/De5/De5-FuelsRetPrice.tsv',
            'ScenGrow_socClus': f'{inputs_path}/Country/De5/De5-SocClustPar.tsv',
            'Initial_adoption_mix': f'{inputs_path}/Country/Ck2/Ck2.tsv',
            'Electricity_areas': f'{inputs_path}/Plan/El1/El1.tsv',
            'LPG_areas': f'{inputs_path}/Plan/Lpg1/LPG1.tsv',
            'Electricity_costBreakdown': f'{inputs_path}/Plan/El1/El1-CostBreakdown.tsv',
            'LPG_costBreakdown': f'{inputs_path}/Plan/Lpg1/LPG1-CostBreakdown.tsv',
            'Plan_config': f'{inputs_path}/Plan/Pl0/Pl0-Config.tsv',
            'Plan_appMaxCap': f'{inputs_path}/Plan/Pl0/Pl0-ApplianceMaxCap.tsv',
            'Plan_appPriceMult': f'{inputs_path}/Plan/Pl0/Pl0-AppliancePriceMult.tsv',
            'Plan_depFuelsTarg': f'{inputs_path}/Plan/Pl0/Pl0-DepFuelsTarget.tsv',
            'Plan_depFuels': f'{inputs_path}/Plan/Pl0/Pl0-DeployFuels.tsv',
            'Plan_fuelMaxCap': f'{inputs_path}/Plan/Pl0/Pl0-FuelMaxCap.tsv',
            'Plan_fuelPriceMult': f'{inputs_path}/Plan/Pl0/Pl0-FuelPriceMult.tsv',
        }

        # self.required_files = {
        #     'Electric_load': './data/inputs/Catalogs/De1/De1-Electric.tsv',
        #     'E-Cooking_load': './data/inputs/Catalogs/De1/De1-Cooking.tsv',
        #     'E-Heating_load': './data/inputs/Catalogs/De1/De1-Heating.tsv',
        #     'BuildTypes_config': './data/inputs/Catalogs/De2/De2-Config.tsv',
        #     'BuildTypes_electric': './data/inputs/Catalogs/De2/De2-Electric.tsv',
        #     'BuildTypes_cooking': './data/inputs/Catalogs/De2/De2-Cooking.tsv',
        #     'BuildTypes_heating': './data/inputs/Catalogs/De2/De2-Heating.tsv',
        #     'Cooking_technologies': './data/inputs/Catalogs/Ck1/Ck1-Technologies.tsv',
        #     'Cooking_appliances': './data/inputs/Catalogs/Ck1/Ck1-Appliances.tsv',
        #     'Cooking_fuels': './data/inputs/Catalogs/Ck1/Ck1-Fuels.tsv',
        #     'Cooking_rawMaterials': './data/inputs/Catalogs/Ck1/Ck1-RawMaterials.tsv',
        #     'Cooking_supplyChains': './data/inputs/Catalogs/Ck1/Ck1-SupChains.tsv',
        #     'Social_clusters': './data/inputs/Country/De4/De4.tsv',
        #     'Territory_partition': './data/inputs/Country/Tp1/Tp1-Rwanda.tsv',
        #     'LocBio_priceMult': './data/inputs/Country/Bm1/Bm1-LocalPriceMult.tsv',
        #     'LocBio_timeGenMult': './data/inputs/Country/Bm1/Bm1-LocalTimeGenMult.tsv',
        #     'ScenGrow_config': './data/inputs/Country/De5/De5-Config.tsv',
        #     'ScenGrow_appRetPrice': './data/inputs/Country/De5/De5-AppliancesRetPrice.tsv',
        #     'ScenGrow_demElast': './data/inputs/Country/De5/De5-DemandElast.tsv',
        #     'ScenGrow_demMult': './data/inputs/Country/De5/De5-DemandMult.tsv',
        #     'ScenGrow_depFuelCostVar': './data/inputs/Country/De5/De5-DepFuelsCostVariation.tsv',
        #     'ScenGrow_fuelRetPrice': './data/inputs/Country/De5/De5-FuelsRetPrice.tsv',
        #     'ScenGrow_socClus': './data/inputs/Country/De5/De5-SocClustPar.tsv',
        #     'Initial_adoption_mix': './data/inputs/Country/Ck2/Ck2.tsv',
        #     'Electricity_areas': './data/inputs/Plan/El1/El1.tsv',
        #     'LPG_areas': './data/inputs/Plan/Lpg1/LPG1.tsv',
        #     'Electricity_costBreakdown': './data/inputs/Plan/El1/El1-CostBreakdown.tsv',
        #     'LPG_costBreakdown': './data/inputs/Plan/Lpg1/LPG1-CostBreakdown.tsv',
        #     'Plan_config': './data/inputs/Plan/Pl0/Pl0-Config.tsv',
        #     'Plan_appMaxCap': './data/inputs/Plan/Pl0/Pl0-ApplianceMaxCap.tsv',
        #     'Plan_appPriceMult': './data/inputs/Plan/Pl0/Pl0-AppliancePriceMult.tsv',
        #     'Plan_depFuelsTarg': './data/inputs/Plan/Pl0/Pl0-DepFuelsTarget.tsv',
        #     'Plan_depFuels': './data/inputs/Plan/Pl0/Pl0-DeployFuels.tsv',
        #     'Plan_fuelMaxCap': './data/inputs/Plan/Pl0/Pl0-FuelMaxCap.tsv',
        #     'Plan_fuelPriceMult': './data/inputs/Plan/Pl0/Pl0-FuelPriceMult.tsv'
        # }

        self.expected_relations = {
            ('Cooking_technologies', 'Cooking_appliances'): ['Appliance_id'],
            ('Cooking_technologies', 'Cooking_fuels'): ['Fuel_id'],
            ('Cooking_fuels', 'Cooking_supplyChains'): ['Fuel_id'],
            ('Cooking_rawMaterials', 'Cooking_supplyChains'): ['RawMat_id'],
        }

        self.required_files_processed = [
            "das_config.tsv",
            "das_demand_census_soc_cluster.tsv",
            "das_biomass_patterns.tsv",
            "das_biomass_multipliers_loc_price.tsv",
            "das_biomass_multipliers_time_gen.tsv",
            "das_time_gen_modified.tsv",
            "das_initial_adoptions.tsv",
            "das_aggregated_clusters.tsv",
            "enriched_technologies.tsv"
        ]

    def check_files_existence(self):
        """Checks if all required files are defined and exist."""
        self.validate_routes()
        missing_files = [file for file in self.required_files.values() if file not in self.routes_config_loader.resolved_files.values()]

        if missing_files:
            for file in missing_files:
                error_msg = f"Archivo requerido no definido: {file}"
                self.log.error(error_msg)
                self.report.add_warning(error_msg)
            raise FileNotFoundError(f"Faltan archivos requeridos: {missing_files}")

        self.log.info("Todos los archivos requeridos están definidos.")


    def check_relations(self, data_manager):
        """ Validates the relationships detected by DataManager."""
        
        self.log.info("Verificando relaciones detectadas.")
        for relation, keys in data_manager.get_relations().items():
            self.log.info(f"Relation not detected between {relation[0]} and {relation[1]} using keys: {keys}")
            for key in keys:
                data_manager._validate_relationship(relation[0], relation[1], key)
        self.log.info("Verificación de relaciones completada.")

    def validate_routes(self):
        """Validates that all defined routes are valid text strings."""
        for key, path in self.routes_config_loader.resolved_files.items():
            if not isinstance(path, str):
                error_msg = f"Invalid path for {key}: {path} (type: {type(path)})"
                self.log.error(error_msg)
                raise ValueError(error_msg)
        for key, path in self.required_files.items():
            if not isinstance(path, str):
                error_msg = f"Invalid required file for {key}: {path} (type: {type(path)})"
                self.log.error(error_msg)
                raise ValueError(error_msg)


    def check_expected_relations(self, detected_relations):
        """Checks if the detected relationships match the expected ones."""
        summary = []
        for expected_relation, keys in self.expected_relations.items():
            if expected_relation in detected_relations:
                detected_keys = detected_relations[expected_relation]
                missing_keys = [key for key in keys if key not in detected_keys]

                if missing_keys:
                    message = f"Relation detected between {expected_relation} but missing keys: {missing_keys}"
                    self.log.warning(message)
                    self.report.add_warning(message)
                    summary.append(f"<b>Error:</b> {message}")
                else:
                    message = f"Correct relation between {expected_relation} using keys: {keys}"
                    self.log.info(message)
                    summary.append(f"<b>Correct:</b> {message}")

    def check_preprocessed_files(self, demandAreas_path):
        """
        Checks and returns the list of preprocessed files that exist in the specified directory.

        :param demandAreas_path: Path to the directory where the preprocessed files are located.
        :return: List of available .tsv files in the directory.
        """
        available_files = []
        for file in self.required_files_processed:
            file_path = os.path.join(demandAreas_path, file)
            if os.path.exists(file_path):
                available_files.append(file)
        return available_files


    

                    #De momento comentamos la validación de relaciones esperadas para mayor velocidad en la carga de datos
            #else:
                # message = f"Relación esperada no detectada: {expected_relation}"
                # self.log.warning(message)
                # self.report.add_warning(message)
                # summary.append(f"<b>Error:</b> {message}")

        # for detected_relation in detected_relations:
        #     if detected_relation not in self.expected_relations:
        #         message = f"Relación no esperada detectada: {detected_relation}"
        #         self.log.warning(message)
        #         self.report.add_warning(message)
        #         summary.append(f"<b>Warning:</b> {message}")

        # return "<br>".join(summary)
