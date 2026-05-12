from dataclasses import dataclass, field

# General emissions parameters for the entire system
@dataclass
class GeneralEmissions:
    OG_Emiss: float = 0.0  # Overall OG emissions (e.g., MTonCO2/Year)

# Area-specific emissions parameters
@dataclass
class AreaSpecificEmissions:
    OG_Emiss: float = 0.0    # OG emissions for the specific area (e.g., MTonCO2/Year)
    Grid_Emiss: float = 0.0  # Grid emissions for the specific area (e.g., MTonCO2/Year)

# Grouping emissions parameters (both general and area-specific)
@dataclass
class EmissionELParameters:
    general: GeneralEmissions = field(default_factory=GeneralEmissions)
    rural: AreaSpecificEmissions = field(default_factory=AreaSpecificEmissions)
    urban: AreaSpecificEmissions = field(default_factory=AreaSpecificEmissions)

# Complete emissions model parameters structure for both Etotal and EDemand
@dataclass
class EmissionsModelParameters:
    Etotal: EmissionELParameters = field(default_factory=EmissionELParameters)
    EDemand: EmissionELParameters = field(default_factory=EmissionELParameters)
