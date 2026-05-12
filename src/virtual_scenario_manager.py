

import logging
import pandas as pd

class VirtualScenarioManager:
    def __init__(self, data_manager):
        # Se trabaja sobre el DF "enriched_technologies" (y otros datos si fuera necesario)
        self.data_manager = data_manager
        self.enriched_tech = self.data_manager.get_dataframe("enriched_technologies")
        self.backup_fuels = {}      # clave: Fuel_id, valor: backup de las filas eliminadas
        self.backup_areas = {}      # clave: area.id, valor: backup del área (o simplemente se marca como "conectada")
    
    def remove_fuel_and_areas(self, fuel_id, connected_area_ids):
        """
        Remove the associated rows from the enriched DF working version for the fuel
        and mark (or delete) the connected areas (for example, storing them in backup to exclude them)
        """
        try:
            # Backup y eliminación de tecnologías asociadas al fuel:
            backup = self.enriched_tech[self.enriched_tech["Fuel_id"] == fuel_id].copy()
            self.backup_fuels[fuel_id] = backup
            self.enriched_tech = self.enriched_tech[self.enriched_tech["Fuel_id"] != fuel_id].copy()
            logging.info(f"Fuel {fuel_id} eliminado del escenario virtual (backup almacenado).")
            # Para las demand areas, se podría simplemente marcar las que ya se conectaron.
            for area_id in connected_area_ids:
                self.backup_areas[area_id] = True  # se marca que ya se conectó
            # Actualizar el data_manager si es necesario:
            self.data_manager.update_dataframe("enriched_technologies", self.enriched_tech)
        except Exception as e:
            logging.error(f"Error in remove_fuel_and_areas for Fuel {fuel_id}: {e}", exc_info=True)
    
    def recover_full_scenario(self):
        """
        Recover the deleted data, restoring the original scenario.
        """
        try:
            # Se recuperan los fuels eliminados:
            for fuel_id, backup in self.backup_fuels.items():
                self.enriched_tech = pd.concat([self.enriched_tech, backup], ignore_index=True)
            # Limpiar backups:
            self.backup_fuels.clear()
            self.backup_areas.clear()
            self.data_manager.update_dataframe("enriched_technologies", self.enriched_tech)
            logging.info("Virtual scenario restored to the full version.")
        except Exception as e:
            logging.error(f"Error recovering virtual scenario: {e}", exc_info=True)
