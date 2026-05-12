# Input Data Structure

ICCPT mixes configuration tables, catalog tables, country inputs, and plan/scenario inputs.

## Main input areas

The repository currently contains these major input groups under `data`:

- `data/inputs`
- `data/offline_data_files`
- `data/Co0_general_config.tsv`
- `data/Co0_routes_config.tsv`

## `data/inputs`

This folder stores scenario and country data consumed by the main run.

Observed subfolders include:

- `Country`
- `Catalogs`
- `Plan`

Examples found in the repository:

- country demand and multiplier files
- technology and fuel catalogs
- plan files for electricity and LPG
- cost breakdown tables

From the folder names, the intended separation appears to be:

- `Country`: country-specific demand, calibration, and socioeconomic inputs
- `Catalogs`: reusable technology, appliance, fuel, and supply-chain definitions
- `Plan`: deployment, price, cap, and scenario controls

## `data/offline_data_files`

This folder stores preprocess outputs used in interactive mode.

Examples in the repository include:

- aggregated clusters
- config snapshots
- demand census and social cluster files
- initial adoptions
- technology enrichment tables

These files are loaded directly by `DataManager.load_preprocessed_files()` when interactive mode is selected and files are available.

## Relationship between input layers

At a high level:

1. `config.yaml` points to the general and route configuration tables.
2. `Co0_routes_config.tsv` resolves the logical list of files to load.
3. `DataManager` loads those files as pandas DataFrames.
4. `PreprocessDataManager` calculates derived technology data and demand areas.
5. Offline artifacts are written to `data/offline_data_files` and can later be reused.

## Format assumptions

The codebase strongly suggests tabular input files are expected to be TSV-oriented.

Evidence:

- file extensions are primarily `.tsv`
- loader classes split rows by tab characters
- export functions also write TSV files

## Editing caution

Manual edits are possible, but validation is limited and distributed across loaders and consistency checks.

If you edit input files manually:

- keep the original headers intact
- preserve identifier columns used to relate tables
- avoid changing folder names or logical route entries without updating `Co0_routes_config.tsv`


