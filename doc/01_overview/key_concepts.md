# Key Concepts

This page summarizes the core concepts that structure ICCPT. It is intended as a shared vocabulary for users and developers.

## Areas and Geography

- **Country**: The national boundary that defines the simulation scope.
- **Administrative divisions**: Region, district, and other administrative layers used for aggregation.
- **Demand areas**: The spatial units where demand, adoption, and costs are simulated. They aggregate buildings that owns to the same electricy supply area.

## Buildings and Social Categories

- **Buildings**: The most granular geospatial units used to infer demand and social attributes.
- **Building types**: Residential, health, education, and other categories used for consumption and social impact mapping.
- **Social categories**: Labels that capture social or demographic attributes used in adoption and impact calculations.

## Technologies and Fuels

- **Technologies**: Cooking and electrification technologies evaluated by the model. They are a combination between fuels and appliances. 
- **Fuels**: Energy carriers that power technologies (e.g., electricity, LPG, biomass).
- **Supply chains**: Parameters that determine availability, delivery costs, and constraints by area.

## Plans and Scenarios

- **Plans**: Policy or deployment assumptions, including targets and fuel constraints.
- **Growth scenarios**: Economic or demographic trajectories that influence adoption and demand.
- **Combined plans**: Bundles that select a plan and a growth scenario for a simulation run.

## Adoption and Demand

- **Adoption model**: Rules that determine how households move from one technology/fuel to another over time.
- **States**: The discrete time steps or stages used to represent the evolution of the system.

## Costs, Emissions, and Social Impacts

- **Costs**: CAPEX, OPEX, annuities, and infrastructure investments.
- **Emissions**: Fuel and technology-specific emissions metrics.
- **Social impacts**: Health, gender, deforestation, and other indicators derived from adoption outcomes.


