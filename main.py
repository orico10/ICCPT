# # --- parche para rastrear deepcopy ---
# import copy, traceback
# from collections import Counter
# _calls = Counter()
# _orig_deepcopy = copy.deepcopy

# def _spy(obj, *a, **k):
#     st = "".join(traceback.format_stack(limit=6)[:-1])  # top 5 frames
#     _calls[st] += 1
#     return _orig_deepcopy(obj, *a, **k)

# copy.deepcopy = _spy
# # al final del run imprime top sitios:
# import atexit
# @atexit.register
# def _report():
#     print("\n== Top deepcopy callers ==")
#     for st, n in _calls.most_common(10):
#         print(f"\n[{n} calls]\n{st}")
# # -------------------------------


from collections import defaultdict
import os
import sys
from typing import List
# main.py (al principio, ANTES de importar tus módulos que usan pandas)
# --- BOOTSTRAP RENDIMIENTO ---
import os   
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

import pandas as pd
# Copy-on-Write (si existe en tu versión)
try:
    pd.options.mode.copy_on_write = True
except Exception:
    pass

# Arrow dtypes (forma robusta)
# try:
#     # Preferimos asignación directa por atributo (evita OptionError de set_option)
#     if hasattr(pd.options.mode, "dtype_backend"):
#         pd.options.mode.dtype_backend = "pyarrow"
#     else:
#         # Fallback silencioso si la opción no existe en esta build
#         pass
# except Exception as e:
#     print("Info: no se pudo activar dtype_backend:", repr(e))
# # --- FIN BOOTSTRAP ---
# print("pandas:", pd.__version__)
# print("has dtype_backend?", hasattr(pd.options.mode, "dtype_backend"))
# if hasattr(pd.options.mode, "dtype_backend"):
#     print("dtype_backend:", pd.options.mode.dtype_backend)



from src.financial_agg_params import AggregatedElectricityCosts, AggregatedLpgCosts, AggregatedRestSubsidiesOrTaxesOpex, AggregatedSocialCosts, AverageGrowthCalculationAppliances, FinancialAggParams, IncomeTariff
from src.output_writer import OutputWriter
from src.simulation_runner import SimulationRunner
from src.summary_report import SummaryReport

# 🔧 Sanea el PATH si estás congelado (PyInstaller) y en Windows
# if getattr(sys, 'frozen', False) and sys.platform == 'win32':
#     meipass = sys._MEIPASS
#     os.environ['PATH'] = ';'.join(p for p in os.environ['PATH'].split(';') if meipass not in p)
if getattr(sys, "frozen", False) and sys.platform == "win32":
    # If you really want to deduplicate PATH, do it without removing MEIPASS
    parts = os.environ.get("PATH", "").split(";")
    seen = set()
    dedup = []
    for p in parts:
        if p and p not in seen:
            seen.add(p)
            dedup.append(p)
    os.environ["PATH"] = ";".join(dedup)


# 🔄 Restaura ruta de búsqueda de DLLs en Windows
# if sys.platform == "win32":
#     import ctypes
#     ctypes.windll.kernel32.SetDllDirectoryW(None)



import csv
import copy 

import os
import time
print(">>> RUNNING main.py")
print(f"PID: {os.getpid()}")
print(f"Current Folder: {os.getcwd()}")
time.sleep(5)  # pausa para ver si al menos arranca


#sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
from src.main_configuration_loader import MainConfigurationLoader
from src.route_configuration_loader import RouteConfigurationLoader
from src.log_handler import LogHandler
from src.report_generator import ReportGenerator
from src.timer import Timer
import logging
#logging.basicConfig(level=logging.ERROR)
#logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')
#logging.basicConfig(level=25)
from src import config
from src.data_manager import DataManager
from src.consistency_check import ConsistencyCheck
from src.technologies import Technologies
#from src.buildings_manager import BuildingsManager
from src.demand_area_manager import DemandAreaManager
from src.preprocess_manager import PreprocessDataManager
#from src.base_file_loader import BaseFileLoader

from src.mixed_state_generator import MixedStateGenerator

from src.electricity_cost_model import ElectricityCostModel
from src.electricity_deployment import DeployElectricity
from src.lpg_cost_model import LPGCostModel
from src.lpg_deploy_model import LPGDeployModel
from src.non_deploy_fuel_cost_model import ApplFuelCostModel
from src.lpg_emissions_model import EmissionsLPG
from src.electricity_emissions_model import EmissionsElectricity
from src.non_deploy_emissions_model import NonDeployEmissionsModel
from src.social_cost_model import SocialCostModel
from src.country_financial_aggregator import CountryFinancialAggregator
from src.financial_model import FinancialModel

from src.adoption_model_2_0 import AdoptionModel2_0
from src.income_mode_2_0 import IncomeModel2_0





def main():
    LogHandler.configure_logs()
    logging.info("Start of the program")
    logger = logging.getLogger(__name__)
    errors = []  # Lista para capturar errores 
    #configuración leer ruta de salida
    inputs_path = config["path"]["inputs"]
    output_path = config["path"]["output"]
    preprocess_path = config["path"]["offline_data_files"]
    base_scenario = config["base_scenario"]
    general_timer = Timer()
    # report = SummaryReport(data)
    # report.generate()
    

    try:
        
        general_timer.start()
        elapsed_time = 0  # Inicializar la variable para evitar errores

        # Cargar configuración general
        general_config_loader = MainConfigurationLoader(config["path"]["general_config"])
        general_config_loader.load_file()
        general_config_loader.process_file()

        # Cargar configuración de rutas
        routes_config_loader = RouteConfigurationLoader(config["path"]["routes_config"])
        routes_config_loader.load_file()
        routes_config_loader.process_file()

        # Ejemplo: Acceso a datos procesados
        # Validar archivos definidos en las rutas
        for name, path in routes_config_loader.resolved_files.items():
            if not os.path.exists(path):
                error_msg = f"Missing File: {name} in {path}"
                logging.error(error_msg)
                errors.append(error_msg)

        # Crear instancia de ConsistencyCheck
        consistency_check = ConsistencyCheck(routes_config_loader, logging, ReportGenerator())

       

        # Verificar existencia de archivos
        missing_files = consistency_check.check_files_existence()
        if missing_files:
            raise FileNotFoundError(f"Required Files: {missing_files}")

        

        # Inicializar DataManager y cargar DataFrames con la configuración cargada 
        data_manager = DataManager(routes_config_loader, general_config_loader)
        data_manager.load_files()

        # Detectar relaciones automáticamente
        data_manager.detect_relations()

         # Validar relaciones detectadas
        logger.user("Validating input data consistency...")
        detected_relations = data_manager.get_relations()
        consistency_check.check_expected_relations(detected_relations)

        # Mostrar relaciones detectadas
        print("Detected relations between files:", data_manager.get_relations())

        # Verificar modo de operación ( Preprocesamiento o Interactividad)

        #preprocess_manager = PreprocessDataManager(data_manager, output_path, demandAreas_path)

        # Preprocesar datos
        #preprocess_manager.preprocess()

        # Procesar o cargar datos según el modo de operación
        logger.user("Processing or loading data according to the operation mode...")
        preprocess_manager = PreprocessDataManager(data_manager, output_path, preprocess_path, base_scenario)
        process_or_load_data(preprocess_manager, data_manager, output_path, preprocess_path, consistency_check, logger)
        # Build simulation structures (CombinedPlan and GrowthScenario) and select the simulation plan
        logger.user("Building simulation structures and selecting simulation plan...")
        simulation_plan, simulation_growth_scenario = build_simulation_structures(preprocess_manager, config)

        # Start the adoption model simulation with the selected structures
        logger.user("Starting adoption model simulation...")
        #start_incremental_loop(simulation_plan, simulation_growth_scenario, data_manager)
        # ... loaders, consistency, DataManager, preprocess ...
        #simulation_plan, simulation_growth_scenario = build_simulation_structures(preprocess_manager, config)

        writer = OutputWriter()
        runner = SimulationRunner(
            simulation_plan=simulation_plan,
            growth=simulation_growth_scenario,
            data_manager=data_manager,
            base_scenario=base_scenario,
            output_writer=writer,
            logger=logger,
            debug_exports=False  # actívalo cuando quieras
        )
        runner.run()

        # Finalizar temporizador
        elapsed_time = general_timer.stop()
        logging.info(f"Total execution time: {elapsed_time:.2f} seconds")


    except Exception as e:
        error_msg = f"Critical error: {str(e)}"
        logging.critical(error_msg)
        errors.append(error_msg)


    finally:
        # Generar reporte HTML
        ReportGenerator.generate_html_report(
            headers=["Description", "File"],
            data=[[k, v] for k, v in routes_config_loader.resolved_files.items()],
            errors=errors,
            total_execution_time=elapsed_time, 
            building_load_time=None  # Set to None as already logged in BuildingsManager
        )
        logging.info("HTML report generated successfully.")
        


def process_or_load_data(preprocess_manager, data_manager, output_path, preprocess_path, consistency_check, logger):
    """
    Process the data or load preprocessed data according to the operation mode specified in the configuration.
    :param data_manager: Instance of DataManager with loaded data.
    :param output_path: Path where output files will be saved.
    :param demandAreas_path: Path where preprocessed files are located.
    :param consistency_check: Instance of ConsistencyCheck to verify the existence of files.
    """
    mode = config["interactive_mode"]
    if mode == True:
        logging.info("Online mode selected. Verifying preprocessed files.")
        logger.user("Interactive mode selected. Checking for preprocessed files...")
        available_files = consistency_check.check_preprocessed_files(preprocess_path)
        if available_files:
            logging.info("Preprocessed files found. Loading preprocessed data.")
            data_manager.load_preprocessed_files(preprocess_path, available_files)
        else:
            logging.warning("Preprocessed files not found. Performing preprocessing.")
            #preprocess_manager = PreprocessDataManager(data_manager, output_path, preprocess_path)
            preprocess_manager.preprocess()
    elif mode == False:
        logging.info("Offline mode selected. Performing preprocessing.")
        logger.user("Offline mode selected. Preprocessing data...")
        #preprocess_manager = PreprocessDataManager(data_manager, output_path, preprocess_path)
        preprocess_manager.preprocess()
    else:
        raise ValueError(f"Invalid operating mode:: {mode}. Use 'True' o 'False'.")
    

def build_simulation_structures(preprocess_manager, config):
    """
    Creates the simulation structures by generating the CombinedPlan and GrowthScenario
    structures. It returns the selected simulation plan and growth scenario based on the IDs
    provided in the configuration.
    
    :param preprocess_manager: Instance of PreprocessDataManager with loaded data.
    :param config: Dictionary containing configuration parameters.
    :return: (simulation_plan, simulation_growth_scenario)
    """
    try:
        # Create the CombinedPlan (states structure) from the config file
        preprocess_manager.create_state_structure()
        # Create the GrowthScenario structure from the corresponding config file
        preprocess_manager.create_growth_scenario_structure()

        combined_plan_manager = preprocess_manager.combined_plan_manager
        growth_scenario_manager = preprocess_manager.growth_scenario_manager

        sim_plan_id = config.get("simulation_planCombined")
        sim_growth_id = config.get("simulation_growthScenario")

        simulation_plan = combined_plan_manager.get_combined_plan(sim_plan_id)
        if simulation_plan is None:
            logging.error("No combined plan found with id %s.", sim_plan_id)
        else:
            logging.info("Selected combined plan: %s", simulation_plan.get_info())

        simulation_growth_scenario = growth_scenario_manager.get_growth_scenario(sim_growth_id)
        if simulation_growth_scenario is None:
            logging.error("No growth scenario found with id %s.", sim_growth_id)
        else:
            logging.info("Selected growth scenario: %s", simulation_growth_scenario.get_info())

        return simulation_plan, simulation_growth_scenario
    except Exception as e:
        logging.error("Error building simulation structures: %s", e, exc_info=True)
        raise

    

#print(">> Estoy justo antes del if __name__ == '__main__'")
def safe_run():
    print(">>> Calling main()")
    try:
        main()
    except Exception as e:
        print("⚠️ ERROR while main():", e)
        import traceback
        traceback.print_exc()
        input("Press Enter to close...")

# Llamada directa sin condicional
if __name__ == "__main__":
    safe_run()

    