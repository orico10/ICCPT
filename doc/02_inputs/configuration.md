# Configuration and Modes

This document explains the runtime configuration files that control ICCPT.

## Main configuration file

The runtime configuration is loaded from the repository-level `config.yaml`.

The package import in `src/__init__.py` resolves `config.yaml` relative to the executable or repository root, so the application expects that file to be present next to the deployed project structure.

Key fields currently used by `main.py` include:

- `interactive_mode`
- `simulation_planCombined`
- `simulation_growthScenario`
- `base_scenario`
- `path.*`
- `logs.*`

## `interactive_mode`

The main execution branch is controlled by `interactive_mode`:

- `true`: load existing preprocessed files from `data/offline_data_files` when available
- `false`: rebuild preprocess artifacts before running the simulation

Behavior implemented in `main.py`:

- in interactive mode, the program checks whether preprocessed files exist and loads them into memory
- if the expected preprocess artifacts are missing, preprocessing is run anyway
- in offline mode, preprocessing is always executed

This means interactive mode is a fast-path, not a separate application.

## Simulation selectors

Two identifiers are read from `config.yaml` to choose the scenario to run:

- `simulation_planCombined`
- `simulation_growthScenario`

Those IDs are resolved after preprocessing when the code builds:

- a `CombinedPlanManager`
- a `GrowthScenarioManager`

If either ID is missing from the loaded data, the run logs an error.

## Base scenario

`base_scenario` contains the baseline values used to initialize mixed states. The current config file includes:

- `PricePlan_id`
- `DepPlan_id`
- `year`
- `state_id`

These values are passed into `MixedStateGenerator` through the preprocessing and simulation pipeline.

## Paths

The `path` section defines where ICCPT reads inputs and writes outputs. The currently referenced paths include:

- `./data/Co0_general_config.tsv`
- `./data/Co0_routes_config.tsv`
- `./data/inputs`
- `./data/outputs`
- `./data/summary_results`
- `./data/offline_data_files`
- `./logs`
- `./reports/report.html`

Important detail:

- `main.py` reads the general and routes TSVs first
- `RouteConfigurationLoader` resolves the actual file locations for the remaining inputs
- outputs and reports are created during or after simulation

## Configuration files read during startup

The startup flow uses three configuration layers:

1. `config.yaml`
2. `data/Co0_general_config.tsv`
3. `data/Co0_routes_config.tsv`

### `Co0_general_config.tsv`

Loaded by `MainConfigurationLoader`.

Expected columns:

- `Name`
- `Value`
- `Units`

The loader converts selected fields into numeric values and stores them as a processed dictionary.

### `Co0_routes_config.tsv`

Loaded by `RouteConfigurationLoader`.

Expected columns:

- `Description`
- `Folder`
- `File`

This file maps logical dataset names to actual input files on disk.

## Practical guidance

Use `interactive_mode: true` when:

- you are re-running the model with already prepared preprocess artifacts
- you are adjusting scenario settings without changing structural geography or base prepared data

Use `interactive_mode: false` when:

- you changed structural inputs used to generate demand areas or technology enrichments
- you want to rebuild preprocess outputs from source inputs


