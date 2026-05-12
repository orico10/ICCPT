from src.state import State


class CombinedPlan:
    def __init__(self, combined_plan_id, combined_plan_name):
        self.combined_plan_id = combined_plan_id
        self.combined_plan_name = combined_plan_name
        self.states = []  # Lista de objetos State

    def add_state(self, state: State):
        self.states.append(state)

    def get_info(self):
        return {
            'combined_plan_id': self.combined_plan_id,
            'combined_plan_name': self.combined_plan_name,
            'states': [state.get_info() for state in self.states]
        }
    
    def get_previous_state(self, current_state: State):
        """
        Gets the previous state before the current state.   
        :param current_state: The current state from which to get the previous one.
        :return: The previous state or None if it doesn't exist.
        """
        if not self.states:
            return None
        
        current_index = self.states.index(current_state)
        if current_index > 0:
            return self.states[current_index - 1]
        
        return None
