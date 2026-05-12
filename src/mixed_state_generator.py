import copy
import logging
from src.state import State
# Class to generate mixed states from a CombinedPlan and a GrowthScenario
class MixedStateGenerator:
    def __init__(self, combined_plan, growth_scenario, base_scenario):
        """
        Initializes the MixedStateGenerator.
        
        :param combined_plan: CombinedPlan object containing the list of states.
        :param growth_scenario: GrowthScenario object containing growth parameters (including growth_id).
        """
        try:
            self.combined_plan = combined_plan
            self.growth_scenario = growth_scenario
            self.base_scenario = base_scenario 
            
            
        except Exception as e:
            logging.error("Error initializing MixedStateGenerator: %s", e, exc_info=True)
            raise

    
   
    def generate_mixed_states(self):
        """
        Generate mixed states using explicit deployment-plan and price-plan rules.

        Rules:
        - 00:
            parent = base_state
            deployment_plan = base_state.deployment_plan
            price_plan = base_state.price_plan

        - 01:
            parent = e0
            deployment_plan = e0.deployment_plan
            price_plan = e1.price_plan (if e1 exists, otherwise e0.price_plan)

        - For event ei, i >= 1:
            * i0:
                parent = ei
                year = ei.year
                deployment_plan = ei.deployment_plan
                price_plan = ei.price_plan

            * i1:
                parent = ei
                year = ei.year
                deployment_plan = ei.deployment_plan
                price_plan = e(i+1).price_plan
                only created if e(i+1) exists

        - The last event only creates i0.
        """
        try:
            states = list(self.combined_plan.states)
            if not states:
                return []

            base_dep_id = self.base_scenario.get("DepPlan_id")
            base_price_id = self.base_scenario.get("PricePlan_id")
            base_year = self.base_scenario.get("year")

            if base_year is None:
                base_year = min(st.year for st in states)

            if hasattr(self, "growth_scenario"):
                self.growth_scenario.base_year = base_year

            base_state = None
            for st in states:
                current_dep_id = getattr(getattr(st, "deployment_plan", None), "id", None)
                current_price_id = getattr(getattr(st, "price_plan", None), "id", None)

                if st.year == base_year and current_dep_id == base_dep_id and current_price_id == base_price_id:
                    base_state = st
                    break

            if base_state is None:
                base_year_states = [st for st in states if st.year == base_year]
                if base_year_states:
                    base_state = base_year_states[0]
                else:
                    base_state = min(states, key=lambda state: state.year)

            events = [st for st in states if st is not base_state]
            events.sort(key=lambda state: (state.year, state.stage_id))

            mixed_states = []

            # Case with no policy events
            if not events:
                state_00 = State.from_parent(
                    base_state,
                    stage_id=0,
                    semester="first"
                )
                state_00.year = base_year
                state_00.deployment_plan = base_state.deployment_plan
                state_00.price_plan = base_state.price_plan
                setattr(state_00, "apply_policy", False)
                mixed_states.append(state_00)
                return mixed_states

            # 00 -> base year, first semester
            state_00 = State.from_parent(
                base_state,
                stage_id=0,
                semester="first"
            )
            state_00.year = base_year
            state_00.deployment_plan = base_state.deployment_plan
            state_00.price_plan = base_state.price_plan
            setattr(state_00, "apply_policy", False)
            mixed_states.append(state_00)

            # 01 -> base year, second semester
            first_event = events[0]
            next_after_first = events[1] if len(events) > 1 else first_event

            state_01 = State.from_parent(
                first_event,
                stage_id=1,
                semester="second"
            )
            state_01.year = base_year
            state_01.deployment_plan = first_event.deployment_plan
            state_01.price_plan = next_after_first.price_plan
            setattr(state_01, "apply_policy", True)
            mixed_states.append(state_01)

            # Remaining event years
            for idx in range(1, len(events)):
                current_event = events[idx]
                next_event = events[idx + 1] if idx + 1 < len(events) else None
                year_index = idx

                # i0 -> first semester of current event year
                state_first = State.from_parent(
                    current_event,
                    stage_id=int(f"{year_index}0"),
                    semester="first"
                )
                state_first.year = current_event.year
                state_first.deployment_plan = current_event.deployment_plan
                state_first.price_plan = current_event.price_plan
                setattr(state_first, "apply_policy", False)
                mixed_states.append(state_first)

                # i1 -> second semester, same parent/deploy, next price plan
                if next_event is not None:
                    state_second = State.from_parent(
                        current_event,
                        stage_id=int(f"{year_index}1"),
                        semester="second"
                    )
                    state_second.year = current_event.year
                    state_second.deployment_plan = current_event.deployment_plan
                    state_second.price_plan = next_event.price_plan
                    setattr(state_second, "apply_policy", True)
                    mixed_states.append(state_second)

            return mixed_states

        except Exception as e:
            import logging
            logging.error("Error generating mixed states: %s", e, exc_info=True)
            raise



#GETTERS
    def get_base_year_first_semester_state(self, year, semester):
        """
        Returns the state corresponding to the first semester of the base year.
        """
        for state in self.combined_plan.states:
            if state.year == year and state.semester == semester:
                return state
        return None
        