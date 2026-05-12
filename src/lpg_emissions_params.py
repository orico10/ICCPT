from dataclasses import dataclass, field

# General LPG emissions parameters (for the entire system)
@dataclass
class GeneralLPGEmissions:
    no_trans: float = 0.0   # Emissions without transportation (No trans)
    local: float = 0.0      # Local emissions
    upstream: float = 0.0   # Upstream emissions

# Area-specific LPG emissions parameters
@dataclass
class AreaSpecificLPGEmissions:
    total: float = 0.0         # Total emissions for the area (rural or urban)
    upstream: float = 0.0      # Upstream emissions for the area
    local: float = 0.0         # Local emissions for the area
    usage_import: float = 0.0  # Usage + import emissions for the area

# Complete LPG emissions parameters structure grouping general and area-specific emissions
@dataclass
class LPGEmissionsParameters:
    general: GeneralLPGEmissions = field(default_factory=GeneralLPGEmissions)
    rural: AreaSpecificLPGEmissions = field(default_factory=AreaSpecificLPGEmissions)
    urban: AreaSpecificLPGEmissions = field(default_factory=AreaSpecificLPGEmissions)
