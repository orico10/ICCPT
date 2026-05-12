# Code Map

This page is a fast orientation guide for developers entering the repository.

## Entry points

- `main.py`: application entry point and top-level orchestration
- `main.spec`: PyInstaller specification for packaging
- `src/__init__.py`: package bootstrap and config loading

## Main runtime modules

### Configuration and loading

- `src/main_configuration_loader.py`
- `src/route_configuration_loader.py`
- `src/base_file_loader.py`
- `src/data_manager.py`
- `src/consistency_check.py`

### Preprocess and structures

- `src/preprocess_manager.py`
- `src/demand_area_manager.py`
- `src/demand_area.py`
- `src/technologies.py`
- `src/combined_plan.py`
- `src/combinedPlans_manager.py`
- `src/growth_scenario.py`
- `src/growth_scenarios_manager.py`
- `src/mixed_state_generator.py`

### Simulation

- `src/simulation_runner.py`
- `src/state.py`
- `src/adoption_model_2_0.py`
- `src/income_mode_2_0.py`
- `src/electricity_cost_model.py`
- `src/electricity_deployment.py`
- `src/lpg_cost_model.py`
- `src/lpg_deploy_model.py`
- `src/non_deploy_fuel_cost_model.py`
- `src/non_deploy_emissions_model.py`
- `src/social_cost_model.py`

### Outputs and reporting

- `src/output_writer.py`
- `src/exports.py`
- `src/report_generator.py`
- `src/summary_report.py`

## Data flow in code terms

At a high level:

1. loaders produce pandas DataFrames
2. managers transform them into structured domain objects
3. simulation mutates per-state results
4. exporters serialize state and country summaries back to TSV/HTML

## Packaging and environments

The repository includes:

- `requirements.txt`
- `requirements_developer.txt`
- `environment.yml`
- `main.spec`

This suggests two practical ways of working:

- a lighter Python environment for runtime or Windows packaging
- a broader conda environment for geospatial or research workflows

## Observed codebase quirks

- some modules appear to exist in older and newer variants, such as `adoption_model.py` and `adoption_model_2_0.py`
- there are mixed naming conventions, for example `income_mode_2_0.py` instead of `income_model_2_0.py`
- some exported helper functions exist but are not currently wired into the active run path
- several comments in the source code are exploratory or debug-oriented

None of these are blockers, but they are worth knowing before refactoring.

## Good first files to read

For a new contributor, the best order is:

1. `main.py`
2. `src/simulation_runner.py`
3. `src/preprocess_manager.py`
4. `src/data_manager.py`
5. `src/output_writer.py`
6. `src/exports.py`

After that, drill into the specific model family you want to modify.
