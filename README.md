# ICCPT – Integrated Clean Cooking Planning Tool

ICCPT is an open-source geospatial energy planning model for clean cooking and electrification analysis. It integrates demand, technology adoption, financial costs, and social and environmental impacts to support scenario-based planning in low- and middle-income countries.

This repository keeps a single top-level `README.md` as the main entry point for users and developers. Detailed documentation is organized under `doc/`.

## Overview

ICCPT can be used to:

- model clean cooking and electricity demand at subnational scale
- simulate technology adoption using socioeconomic and geospatial parameters
- estimate CAPEX, OPEX, annuities, and infrastructure requirements
- assess emissions and social impacts such as health, gender, and deforestation
- generate reproducible outputs for planners, researchers, and implementers

## Documentation

The detailed project documentation is available in `doc/`.

### Documentation map

01_overview
- [Introduction](doc/01_overview/introduction.md)
- [Architecture](doc/01_overview/architecture.md)
- [Data flow diagram](doc/01_overview/data_flow_diagram.md)
- [Key concepts](doc/01_overview/key_concepts.md)
- [Project structure](doc/01_overview/project_structure.md)

02_inputs
- [Configuration and modes](doc/02_inputs/configuration.md)
- [Input data structure](doc/02_inputs/input_data.md)
- [Excel interface](doc/02_inputs/excel_interface.md)

03_models
- [Models overview](doc/03_models/models_overview.md)

04_engine
- [Execution flow](doc/04_engine/execution_flow.md)

05_outputs
- [Outputs and reports](doc/05_outputs/outputs.md)
- [Summary outputs](doc/05_outputs/summary_outputs.md)
- [Detailed outputs](doc/05_outputs/detailed_outputs.md)
- [Reports and logs](doc/05_outputs/reports_and_logs.md)

06_developers
- [Code map](doc/06_developers/code_map.md)
- [Building executables](doc/06_developers/build_executables.md)


07_execution
- [User execution](doc/08_execution/user_execution.md)

## Developer Setup

ICCPT requires Python 3.9+.

### macOS

```bash
git clone https://github.com/orico10/CleanCooking_os.git
cd CleanCooking_os
# If the geopandas environment in the repo root exists, activate it.
# Otherwise create a new environment using environment.yml.
conda env create -f environment.yml
conda activate geopandas
pip install -r requirements.txt
```

### Windows

```cmd
git clone https://github.com/orico10/CleanCooking_os.git
cd CleanCooking_os
Use the same requirements.txt as macOS
python -m venv geopandas_venvlocal
geopandas_venvlocal\Scripts\activate
pip install -r requirements.txt
```

### Developers (Windows or macOS)

Use the same base requirements, and then add the developer extras:

```cmd
pip install -r requirements_developer.txt
```

The executable definition is currently stored in `main.spec`.

## License

This project is licensed under the [MIT License](LICENSE).

## Contact

- ICCPT development team
- Email: [orico@comillas.edu](mailto:orico@comillas.edu)
- Project context: Rwanda National Integrated Clean Cooking Plan / Sustainable Energy For All

## How to Cite

If you use ICCPT in academic or policy work, please cite:

> O. Rico Diez, *ICCPT – Integrated Clean Cooking Planning Tool*, 2025. GitHub repository: https://github.com/orico10/CleanCooking_os

A formal citation entry can be added later if the project publishes a paper or adopts `CITATION.cff`.
