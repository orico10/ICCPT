import pandas as pd
import logging

from src.state import State


class StatesManager:
    def __init__(self, data_manager):
        self.data_manager = data_manager
        self.states = self._load_states()
        self.logger = logging.getLogger("StateManager")

    def _load_states(self):
        states = {}
        try:
            config_plan_df = self.data_manager.get_dataframe('Plan_config')
            for _, row in config_plan_df.iterrows():
                state_name = row['State']
                if state_name not in states:
                    states[state_name] = State(state_name)

                state = states[state_name]
                state.set_year(row['Year'])

                if state.plan_start_year is None or row['Year'] < state.plan_start_year:
                    state.set_plan_start_year(row['Year'])

                if state.plan_duration is None:
                    state.set_plan_duration(1)
                else:
                    state.set_plan_duration(row['Year'] - state.plan_start_year + 1)

                state.add_deployment_plan(row['DepPlan_id'], row['DepPlan_Name'])
                state.add_price_plan(row['PricePlan_id'], row['PricePlan_Name'])
                state.add_combined_plan(row['CombinedPlan_id'], row['CombinedPlan_Name'])
        except Exception as e:
            self.logger.critical(f"Error loading states: {e}", exc_info=True)
            raise
        return states

    def get_state(self, state_name):
        """
        Obtain a specific state.

        :param state_name
        :return: State Object or None if not found
        """
        return self.states.get(state_name)
    
    
    
    def iterate_states(self):
        """
        Iterate over all states.

        :yield: State Object
        """
        for state in self.states.values():
            yield state