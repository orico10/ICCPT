from dataclasses import dataclass, field
from typing import Dict

@dataclass
class AggregatedElectricityCosts:
    E_Cooking_CAPEX: float = 0.0
    E_Cooking_OPEX: float = 0.0
    GRID_distribution_CAPEX: float = 0.0
    GRID_distribution_OPEX: float = 0.0
    GRID_generation_CAPEX: float = 0.0
    GRID_generation_OPEX: float = 0.0
    OFFGRID_generation_CAPEX: float = 0.0
    OFFGRID_generation_OPEX: float = 0.0
    OFFGRID_distribution_CAPEX: float = 0.0
    OFFGRID_distribution_OPEX: float = 0.0
    OFFGRID_percentage: float = 0.0

@dataclass
class AggregatedLpgCosts:
    LOCAL_processing_CAPEX: float = 0.0
    LOCAL_processing_OPEX: float = 0.0
    LOCAL_transport_CAPEX: float = 0.0
    LOCAL_transport_OPEX: float = 0.0
    UPS_processing_CAPEX: float = 0.0
    UPS_processing_OPEX: float = 0.0
    UPS_transport_CAPEX: float = 0.0
    UPS_transport_OPEX: float = 0.0
    UPS_import_OPEX: float = 0.0

@dataclass
class AggregatedRestSubsidiesOrTaxesOpex:
    """
    Cada diccionario tiene como clave el id (int) del elemento (appliance o fuel)
    y como valor el coste total OPEX de subsidios o taxes.
    """
    appliances: Dict[int, float] = field(default_factory=dict)
    fuels: Dict[int, float] = field(default_factory=dict)

@dataclass
class AggregatedSocialCosts: 
    health_costs: float = 0.0#Dict[int, float] = field(default_factory=dict)
    gender_costs: float = 0.0#Dict[int, float] = field(default_factory=dict)
    emissions_costs: float = 0.0 #Dict[int, float] = field(default_factory=dict) --- Esto pertenece a la carbon economy 
    deforestation_costs: float = 0.0#Dict[int, float] = field(default_factory=dict) --- Esto pertenece a la carbon economy 

@dataclass 
class AverageGrowthCalculationAppliances: 
    """
    Cada diccionario tiene como clave el id (int) del fuel y como valor otro diccionario:
    clave: id del appliance
    valor: peso relativo o coste medio de crecimiento anual.
    """
    appliances: Dict[int, Dict[int, float]] = field(default_factory=dict)


 

@dataclass # Puede que ya los extraiga con el total de las aplpiances y fuels, pero lo dejamos por si acaso
class IncomeTariff: # Incomes due to Cooking and Heating
    """
    Clase para almacenar los ingresos por tarifas debidos a CH de cada fuel
    """
    fuels: Dict[str, float] = field(default_factory=dict)  # Dict[int, float] para almacenar ingresos por fuel    


@dataclass 
class FinancialAggParams:
    aggregated_electricity_costs: AggregatedElectricityCosts = field(default_factory=AggregatedElectricityCosts)
    aggregated_edemand_costs: AggregatedElectricityCosts = field(default_factory=AggregatedElectricityCosts)  # NUEVO
    aggregated_lpg_costs: AggregatedLpgCosts = field(default_factory=AggregatedLpgCosts)
    aggregated_rest_subsidies_or_taxes_opex: AggregatedRestSubsidiesOrTaxesOpex = field(default_factory=lambda: AggregatedRestSubsidiesOrTaxesOpex({}, {}))
    aggregated_social_costs: AggregatedSocialCosts = field(default_factory=AggregatedSocialCosts)
    average_growth_calculation_appliances: AverageGrowthCalculationAppliances = field(default_factory=AverageGrowthCalculationAppliances)
    income_tariff: IncomeTariff = field(default_factory=IncomeTariff)
