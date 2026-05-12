from dataclasses import dataclass, field
# This module defines data structures for managing electricity cost parameters
# in a structured and organized manner.
# General cost parameters (for the entire system)
@dataclass
class GeneralCosts:
    FIX_Cost: float = 0.0            # (M$/yr)
    OG_G_VAR: float = 0.0            # ($/kWh)
    VAR_OGgen: float = 0.0           # (M$/yr)
    #Ratios for the cost of generation
    OG_G_Diesel_rate: float = 0.0    # (p.u.) -- NO, EN EL NUEVO MODELO ENTRA COMO KgCO2/kWh
    GrCap_pu: float = 0.0            # (p.u., between 0 and 1)
    GrCapU_pu: float = 0.0           # (p.u., between 0 and 1) - Urban
   

# General consumption parameters (for the entire system)
@dataclass
class GeneralConsumption:
    GC: float = 0.0    # G Cost (GWh/year)
    OG: float = 0.0    # OG Cost (GWh/year)

# Area-specific cost parameters
@dataclass
class AreaSpecificCosts:
    VAR_OGgen_r: float = 0.0         # Rural: VAR_OGgen (M$/yr)
    VAR_OGgen_u: float = 0.0         # Urban: VAR_OGgen (M$/yr)
    FIX_Cost_exceptGGen_r: float = 0.0  # Rural: FIX_Cost excluding generation (M$/yr)
    FIX_Cost_exceptGGen_u: float = 0.0  # Urban: FIX_Cost excluding generation (M$/yr)

    #Variables finales para costes E-TOTAL adjusted for both E-Total and Edemand: 
    # Nuevas variables para los costes finales ETOTAL:
    FIX_Grid_Gen: float = 0.0      # Rural & Urban: FIX Grid Gen (M$/yr)
    Rest: float = 0.0              # Rural & Urban: Resto del coste fijo (M$/yr)
    VAR_Grid_Gen: float = 0.0      # Rural & Urban: VAR Grid Gen (M$/yr)
    VAR_OffGrid: float = 0.0       # Rural & Urban: VAR OffGrid (M$/yr)
   

    # Final cost variables for E-DEMAND AND E-Total:
    FINAL_FIX_Grid_Gen: float = 0.0      # Rural & Urban: FIX Grid Gen (M$/yr)
    FINAL_Rest: float = 0.0              # Rural & Urban: Resto del coste fijo (M$/yr)
    FINAL_VAR_Grid_Gen: float = 0.0      # Rural & Urban: VAR Grid Gen (M$/yr)
    FINAL_VAR_OffGrid: float = 0.0       # Rural & Urban: VAR OffGrid (M$/yr)
    


# Area-specific consumption parameters
@dataclass
class AreaSpecificConsumption:
    GCu: float = 0.0   # Urban: GCu (GWh/year)
    OGu: float = 0.0   # Urban: OGu (GWh/year)
    GCr: float = 0.0   # Rural: GCr (GWh/year)
    OGr: float = 0.0   # Rural: OGr (GWh/year)
    gcu: float = 0.0   # Urban adjustment (GWh/year)
    ogu: float = 0.0   # Urban adjustment (GWh/year)
    grc: float = 0.0   # Rural adjustment (GWh/year)
    ogr: float = 0.0   # Rural adjustment (GWh/year)

# Grouping general parameters (both costs and consumption)
@dataclass
class GeneralParameters:
    costs: GeneralCosts = field(default_factory=GeneralCosts)
    consumption: GeneralConsumption = field(default_factory=GeneralConsumption)

# Grouping area-specific parameters (both costs and consumption)
@dataclass
class AreaParameters:
    costs: AreaSpecificCosts = field(default_factory=AreaSpecificCosts)
    consumption: AreaSpecificConsumption = field(default_factory=AreaSpecificConsumption)

# Complete cost parameters structure
@dataclass
class CostParameters:
    general: GeneralParameters = field(default_factory=GeneralParameters)
    rural: AreaParameters = field(default_factory=AreaParameters)
    urban: AreaParameters = field(default_factory=AreaParameters)

