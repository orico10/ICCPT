from dataclasses import dataclass, field

# -------------------------------
# Parámetros generales de costes LPG (para todo el sistema LPG)
# -------------------------------
@dataclass
class LPGGeneralCosts:
    FIX_Cost: float = 0.0            # Costo fijo agregado (M$/yr) para LPG
    VAR_Cost: float = 0.0            # Costo variable agregado (M$/yr) para LPG
    Local_Distance: float = 0.0      # Distancia local (Km) para ajustes de LPG
    Ups_FIX_Cost: float = 0.0        # Costo fijo UPS (M$/yr) para LPG
    Ups_VAR_Cost: float = 0.0        # Costo variable UPS (M$/yr) para LPG
    FIX_local_overcost_factor: float = 0.0  # Factor de sobrecosto fijo local para LPG p.u 
    VAR_local_overcost_factor: float = 0.0  # Factor de sobrecosto variable local para LPG p.u
   
# -------------------------------
# Parámetros generales de consumo LPG (para todo el sistema LPG)
# -------------------------------
@dataclass
class LPGGeneralConsumption:
    Demand: float = 0.0  # Demanda total (MCooks/year) para LPG
    Reference_Demand: float = 0.0    # Demanda de referencia (MCooks/year) para LPG
    Adjusted_Capacity: float = 0.0   # Capacidad ajustada (MCooks/year) según margen LPG
    Adjusted_Adoption: float = 0.0   # Adopción ajustada (MCooks/year) para LPG

# -------------------------------
# Parámetros de costes específicos por área LPG (diferenciando rural y urbano)
# -------------------------------
@dataclass
class LPGAreaSpecificCosts:
    # Costes agrupados por área de suministro LPG
    FIX_local_overcost_r: float = 0.0  # Costo fijo de sobrecosto local para el segmento rural (M$/yr)
    FIX_local_overcost_u: float = 0.0  # Costo variable de sobrecosto local para el segmento rural (M$/yr)
    VAR_local_overcost_r: float = 0.0  # Costo fijo de sobrecosto local para el segmento urbano (M$/yr)
    VAR_local_overcost_u: float = 0.0  # Costo variable de sobrecosto local para el segmento urbano (M$/yr)
    FIX_Ups_Cost_r: float = 0.0      # Costo fijo para el segmento rural (M$/yr)
    FIX_Ups_Cost_u: float = 0.0      # Costo fijo para el segmento urbano (M$/yr)
    VAR_Ups_Cost_r: float = 0.0      # Costo variable para el segmento rural (M$/yr)
    VAR_Ups_Cost_u: float = 0.0      # Costo variable para el segmento urbano (M$/yr)
    # Costes FInales por área de suministro LPG
    FINAL_FIX_Cost_Upstream: float = 0.0          # Costo fijo rural y urban (M$/yr)
    FINAL_FIX_Cost_Local: float = 0.0          # Costo fijo rural y urban (M$/yr)
    FINAL_VAR_Cost_Upstream: float = 0.0          # Costo variable rural y urban (M$/yr)
    FINAL_VAR_Cost_Local: float = 0.0          # Costo variable rural y urban (M$/yr)
    FINAL_VAR_Cost_Import: float = 0.0          # Costo variable de importación (M$/yr)

# -------------------------------
# Agrupación de parámetros generales (costes y consumo) para LPG
# -------------------------------
@dataclass
class LPGGeneralParameters:
    costs: LPGGeneralCosts = field(default_factory=LPGGeneralCosts)
    consumption: LPGGeneralConsumption = field(default_factory=LPGGeneralConsumption)

# -------------------------------
# Agrupación de parámetros por área (costes y consumo) para LPG
# -------------------------------
@dataclass
class LPGAreaParameters:
    costs: LPGAreaSpecificCosts = field(default_factory=LPGAreaSpecificCosts)
    #consumption: LPGAreaSpecificConsumption = field(default_factory=LPGAreaSpecificConsumption)

# -------------------------------
# Estructura completa de parámetros de costes para LPG
# -------------------------------
@dataclass
class LPGCostParameters:
    general: LPGGeneralParameters = field(default_factory=LPGGeneralParameters)
    rural: LPGAreaParameters = field(default_factory=LPGAreaParameters)
    urban: LPGAreaParameters = field(default_factory=LPGAreaParameters)
