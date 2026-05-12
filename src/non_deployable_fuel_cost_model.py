import logging


class NonDeployableFuelCostModel:
    def __init__(self, state, fuel, data_manager):
        self.state = state
        self.fuel = fuel
        self.data_manager = data_manager
        self.cost = 0.0

    def run_simulation(self):
        try:
            self.calculate_costs()
            logging.info("Coste para fuel no deployable (Fuel ID %s): %f", self.fuel["Fuel_id"], self.cost)
            return self.cost
        except Exception as e:
            logging.error("Error en NonDeployableFuelCostModel para Fuel ID %s: %s", self.fuel["Fuel_id"], e, exc_info=True)
            raise

    def calculate_costs(self):
        base = self.get_base_cost()
        penalty = self.get_non_deploy_penalty()
        self.cost = base + penalty

    def get_base_cost(self):
        return self.fuel.get("Ref_capacity", 1) * 100

    def get_non_deploy_penalty(self):
        return 30
