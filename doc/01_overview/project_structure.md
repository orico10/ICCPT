# Project Structure

This page summarizes the main structure of the ICCPT repository.

## Top-level layout

- `config.yaml`: Main configuration file used by ICCPT.
- `main.py`: Python entry point.
- `main.exe`: Windows executable (should be placed here after building).
- `main.spec`: PyInstaller spec used for packaging.
- `geopandas_venvlocal/`: Local environment folder for geopandas (optional, can be ignored by users).
- `src/`: Core source code.
- `data/`: Inputs, outputs, and preprocessed data.
- `doc/`: Documentation.
- `reports/`: Generated HTML reports.
- `logs/`: Execution logs.

## Data folders

- `data/inputs`: Catalogs, plans, growth scenarios, and other inputs.
- `data/offline_data_files`: Preprocessed datasets used in interactive mode.
- `data/summary_results`: Quick validation outputs.
- `data/outputs`: Detailed simulation outputs.

## Documentation folders

- `doc/01_overview`: Conceptual overview and architecture.
- `doc/02_inputs`: Input data and configuration.
- `doc/03_models`: Model descriptions.
- `doc/04_engine`: Execution flow and orchestration.
- `doc/05_outputs`: Output formats and reports.
- `doc/06_developers`: Developer notes and build steps.
- `doc/07_execution`: User execution from the terminal.
