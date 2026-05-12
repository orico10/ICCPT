# Execution Flow

This page describes the runtime flow implemented by `main.py` and `src/simulation_runner.py`.

## High-level sequence

The application entry point is `main.py`.

At startup it:

1. configures logging
2. loads and processes the general configuration TSV
3. loads and processes the routes configuration TSV
4. validates the existence of routed files
5. loads input tables into `DataManager`
6. detects cross-table relations
7. preprocesses or loads cached preprocess outputs depending on `interactive_mode`
8. builds the combined plan and growth scenario structures
9. runs the state-by-state simulation
10. exports reports and output TSVs
11. writes an HTML report even if execution fails

## Startup pipeline

### Configuration loading

`src/__init__.py` loads `config.yaml` into the package-level `config`.

`main.py` then creates:

- `MainConfigurationLoader`
- `RouteConfigurationLoader`

Both are processed before the simulation begins.

### Input validation

The route configuration is resolved into actual file paths. `ConsistencyCheck` is then used to validate that required files exist and that expected relations across tables are present.

## Preprocess phase

`PreprocessDataManager` is responsible for the preparation layer.

Its implemented responsibilities are:

- calculate derived technology data through `Technologies.calculate_all()`
- create demand areas through `DemandAreaManager.process_demand_areas()`
- build scenario/state structures through `CombinedPlanManager` and `GrowthScenarioManager`

## Simulation phase

The main orchestration class is `SimulationRunner`.

### Preparation

Before looping through states, the runner:

- generates mixed states with `MixedStateGenerator`
- loads demand areas from config/output sources
- assigns preprocessed data to those demand areas

### Per-state processing order

For each state, the runner performs these phases:

1. electricity ratios and electricity deployment
2. LPG flow for non-electrified areas
3. post-deployment processing for LPG-deployed areas
4. electricity final costs and emissions for electrified areas
5. remaining fuels and social-cost processing for non-LPG areas
6. financial aggregation at state level

After each state:

- the current state is snapshotted and becomes the previous state reference
- optional progress rendering can be triggered through `OutputWriter.render_progress()`

## Export phase

After all states are processed, the runner:

- exports summary reports and TSV outputs
- builds the annualized financial model
- writes `merged_opex_capex_yearly.tsv`

## Error handling

`main.py` wraps the run in `try/except/finally`.

Observed behavior:

- critical runtime errors are logged and appended to the report error list
- the HTML report is still generated in `finally`

This is useful for operational troubleshooting because the run can leave a report even when the scenario does not complete successfully.

## Practical mental model

It is useful to think about the engine in three layers:

1. load tables and validate them
2. transform tables into demand areas, plans, and states
3. iterate through states and compute deployments, costs, emissions, and exports
