# Models Overview

ICCPT is organized as a set of domain models coordinated by the simulation engine.

This page summarizes the model groups that are directly visible in the current codebase.

## Core model families

### Adoption and income

These modules estimate how areas adopt technologies and what income constraints or spending patterns shape that adoption.


The active execution path in `src/simulation_runner.py` primarily uses:

- `AdoptionModel2_0`
- `IncomeModel2_0`

## Electricity

Electricity-related logic is split into cost, deployment, and emissions components.

Relevant modules:

- `src/electricity_cost_model.py`
- `src/electricity_deployment.py`
- `src/electricity_emissions_model.py`
- `src/el_cost_params.py`
- `src/el_emissions_params.py`

In the current runner, electricity is processed before LPG deployment. Area ratios are computed first and then passed into `DeployElectricity`.

## LPG

LPG logic follows a similar pattern.

Relevant modules:

- `src/lpg_cost_model.py`
- `src/lpg_deploy_model.py`
- `src/lpg_emissions_model.py`
- `src/lpg_cost_params.py`
- `src/lpg_emissions_params.py`

The runner groups non-electrified areas by LPG area, computes area ratios, deploys LPG, and then calculates emissions for deployed areas.

## Non-deployed fuels

The model also keeps track of fuels that are neither electricity nor LPG.

Relevant modules:

- `src/non_deploy_fuel_cost_model.py`
- `src/non_deploy_emissions_model.py`
- `src/non_deployable_fuel_cost_model.py`

Naming note:

- both `non_deploy_fuel_cost_model.py` and `non_deployable_fuel_cost_model.py` exist in the repository
- the active import in `main.py` and `simulation_runner.py` points to `non_deploy_fuel_cost_model.py`
- the second file should be reviewed to determine whether it is legacy or still needed

## Social and financial aggregation

Relevant modules:

- `src/social_cost_model.py`
- `src/country_financial_aggregator.py`
- `src/financial_model.py`
- `src/financial_agg_params.py`

These modules transform area-level results into state-level and yearly financial outputs, including the final annualized CAPEX/OPEX export.

## State and scenario structures

Relevant modules:

- `src/state.py`
- `src/states_manager.py`
- `src/combined_plan.py`
- `src/combinedPlans_manager.py`
- `src/growth_scenario.py`
- `src/growth_scenarios_manager.py`
- `src/mixed_state_generator.py`

These classes define the time-sequenced states that the runner processes.

## Technology and territory support

Relevant modules:

- `src/technologies.py`
- `src/demand_area.py`
- `src/demand_area_manager.py`
- `src/deployment_plan.py`
- `src/pricing_plan.py`

These provide the structured objects that the simulation uses as its working units.

## Important implementation note

The current execution path is not a fully independent set of modules. The models share state through:

- the active `state`
- the previous state snapshot
- the `DataManager`
- cached adoption and income results

That means module-level documentation should eventually explain both the conceptual equations and the object interactions.


