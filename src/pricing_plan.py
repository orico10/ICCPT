

class PricePlan:
    def __init__(self, plan_id, plan_name):
        self.plan_id = plan_id
        self.plan_name = plan_name
        self.details = {}  # Se enriquecerá con los datos de precio (por ejemplo, multiplicadores, capacidades, etc.)

    def enrich(self, details):
        self.details = details

    def get_info(self):
        return {'id': self.plan_id, 'name': self.plan_name, 'details': self.details}