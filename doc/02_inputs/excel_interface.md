# ICCPT for Excel  
## User Handbook  
### 2026  
**MIT-IIT Universal Energy Access Lab**

---

## Introduction

### Tool Overview

This Excel-based application streamlines the early-stage design and assessment of a case study, from defining the structure of multiple what-if scenarios to visualizing the results. It is intended to replace manual spreadsheet tinkering with a structured, menu-driven workflow that keeps input data, assumptions, and outputs in sync.

#### Core capabilities

The tool walks you through a seamless chain of tasks. It starts with a Console page that lays out the case-study structure and lets you add, remove, rename, or rearrange items in each list. From this same page you can generate the folder hierarchy and the text files the model reads, then launch the model itself, defining the case study by combining your chosen pricing strategy, deployment plan, and growth scenario, and finally save the case.

Next, the Preprocess page lets you set the parameters that will generate a list of buildings and their attributes by pulling data directly from a public building database. The Configuration (`Co`) and Spatial Dimension (`Tp`), and Scenarios (`Pl` and `De5`) pages then capture country-specific inputs and let you spin off as many what-if variants as you need. Each one clones the baseline but can be tweaked independently, so paths like “Optimistic Growth,” “Price-Constrained,” or “Deployment-Constrained” remain clearly separated.

Dedicated input pages let you enter the model’s core data: energy demand by building type (`De1E`, `De1C`, `De1H`, and `De2`), social-cluster traits that drive technology adoption (`De4`), the catalog of cooking technologies (`Ck1`), the initial technology adoption per social cluster (`Ck2`), and location-specific fuel prices and social-cost factors (`Bm1`). In addition, the reference plan pages capture all the parameters that shape each electricity (`El1`) and LPG (`LPG1`) deployment. The LPG definition also includes a built-in logistic-growth model (`LPGin` and `LPGmodel`) to forecast adoption over time. After you run the scenarios, the output pages (`cost`, `adoption`, `social-impact`, and `socioeconomic`) convert the raw calculations into ready-made charts and tables, making it easy to explore and compare results.

#### Typical workflow

A complete study typically flows through the tool in the sequence outlined below:

1. Start a new case study in the **Console** tab by specifying the project path and adjusting the default item structure.
2. Generate the building dataset in `De3` files. Use the preprocessing Python script, configured in the **Preprocess** tab, to download raw data from the OpenStreetMap website and create the list of buildings with their attributes.
3. Complete the core configuration by filling in the **Configuration (`Co`)** and **Spatial Dimension (`Tp`)** tabs.
4. Define scenarios in the pricing-and-deployment tab, **Pl**, and the growth tab, **De5**.
5. Size the system in tabs `De1`, `De2`, `De4`, `Ck1`, `Ck2`, and `Bm1`.
6. Build reference plans outside the tool and enter their parameters in `El1` for electricity, and `LPG1` for LPG. The tool includes an embedded logistic model, `LPGin` and `LPGmodel`, for internal calculations.
7. Select the combined plan and growth scenario, then run the case, either the first pass or iterative variations, using interactive mode.
8. Review outputs in the results tabs and refine the case by revisiting scenario assumptions as needed.
9. Save the case by specifying the desired case name and path to cases. This will copy all input data and output results from the data folder to the desired location.

### Key Benefits

The tool enforces consistency by keeping every scenario, plan, and dataset tied to a single source of inputs, so changes ripple automatically instead of spawning version-control headaches. Its color-coded sheets, audit columns, and ready-made charts deliver transparency, letting users trace any result back to the exact assumptions that produced it. Because new items can be added without rewriting formulas, the workbook offers real scalability as projects expand. Finally, built-in rules, drop-down lists, and cross-sheet checks apply rigorous data validation, catching entry errors before they can distort results.

### Intended Audience

This guide is written for energy-sector professionals who need to model and compare large sets of what-if deployment strategies. Primary users include utility and government planners sizing future electricity and LPG sectors, consultants and development-finance analysts evaluating technology-adoption pathways, and academic researchers studying the equity and cost impacts of clean-cooking or electrification programs. Because the tool combines detailed load modeling with scenario management and automated reporting, it also serves decision makers who may not build models themselves but still rely on transparent, side-by-side results to steer policy or investment choices.

---

## System Requirements and Installation

### Prerequisites

| Component | Minimum | Recommended | Notes |
|---|---|---|---|
| Operating system | Windows 10 (64-bit) | Windows 11 (64-bit) | macOS is possible via Excel 365, but VBA performance may vary |
| Microsoft Excel | Excel 2016 (16.0) | Microsoft 365 | 64-bit Excel avoids memory caps |
| Python | Refer to README file | Refer to README file | Required for preprocessing software |

### Enabling Macros

The workbook relies on VBA and COM calls to launch Python and push results back to Excel.

1. Right-click the file in Windows Explorer → **Properties** → if you see a “Security: This file came from another computer” message, check **Unblock**, then click **Apply**.  
   **Disclaimer:** Always unblock only files received from trusted sources, such as the project owner.
2. Open Excel → **File** → **Options** → **Trust Center** → **Trust Center Settings** → **Macro Settings**.
3. Select **Disable VBA macros with notification**. This is the safest setting for most users, as it blocks macros by default but prompts you to enable them when you open a trusted workbook.
4. Add the tool’s root folder to **Trusted Locations** for seamless file I/O: **Trust Center** → **Trusted Locations** → **Add new location**.

If your IT policy blocks unsigned macros, request a signed copy from the project owner.

### First-Time Checklist

Before you begin modeling, run through the one-time checks below to confirm the workbook and permissions are all set up correctly.

- [ ] Enable content when Excel prompts: **Security Warning – Macros have been disabled**.
- [ ] Set the project path in the **Console** tab so relative links resolve correctly.
- [ ] Confirm tab availability. Make sure every required worksheet is present and correctly named before you begin: `Console`, `Preprocess`, `Co`, `Tp`, `Pl`, `De1E`, `De1C`, `De1H`, `De2`, `De4`, `De5`, `Ck1`, `Ck2`, `Bm1`, `El1`, `LPGin`, `LPGmodel`, `LPG1`, `cost`, `adoption`, `social-impact`, and `socioeconomic`.
- [ ] Click **Write Files** in the **Console** tab and confirm that the expected folder hierarchy and text files are created in your project directory.
- [ ] Click **Run Model** and confirm the engine launches. Even if the first pass ends with validation errors, the goal is simply to verify that the calculation process starts and the run log appears.

---

## Interface and Navigation

### Console Features

The **Console** tab is your launchpad. From here you can:

1. Set the project path.
2. Write input files.
3. Choose run parameters.
4. Launch the model, with the option to run in interactive mode.
5. Review the case-study structure.
6. Add structure entries.
7. Delete structure entries.
8. Rename structure entries.
9. Reorder structure entries.
10. Save a case.
11. Load a case.
12. Hide or unhide groups of sheets to facilitate navigation.

### Sheets Overview

The workbook uses consistent color language for individual cells so you can spot input types inside each sheet immediately:

| Color | Meaning |
|---|---|
| Light yellow | Required user input; optionally, leave the cell blank |
| Light green | Required choice from a drop-down list |
| Light blue | User-entered value that has passed validation checks |
| Gray | Locked formula cell (read-only) |
| Pale brown | Table-dimension settings that control the number of rows or columns |

Below is a one-line description of every sheet in the order you will typically use them:

| Sheet | Description |
|---|---|
| Console | Central dashboard: set project path, write files, run model, and manage structure |
| Preprocess | Configure download of public building data and set parameters |
| Co | Country-level constants (currency, labor cost, electrical system, and file names) |
| Tp | Spatial dimension: territory administrative division and building file names |
| Pl | Pricing and deployment plan parameters |
| De5 | Growth-scenario assumptions |
| De1 | Basic hourly profiles for electricity, cooking, and heating demand |
| De2 | Multipliers to define demands of building types |
| De4 | Adoption settings of social clusters |
| Ck1 | Catalog of cooking technologies: raw materials, fuels, supply chains, appliances |
| Ck2 | Initial technology adoption of social clusters |
| Bm1 | Local disparities of fuel price and social costs due to main land use |
| El1 | Reference-plan inputs for electricity rollout |
| LPGin | Embedded LPG logistic model: inputs |
| LPGmodel | Embedded LPG logistic model: scenario definition |
| LPG1 | Reference-plan inputs for LPG rollout |
| cost | Chart to observe the cost and expenditure evolution in urban/rural context |
| adoption | Chart to observe the adoption of each technology in urban/rural context |
| social-impact | Chart to observe the social impact of clean cooking per unit |
| socioeconomic | Chart to observe the absolute value of the social factors |

---

## Core Workflows

### Edit Structure

The Console list-management controls let you shape the study’s master hierarchy, demand profiles, building types, social clusters, raw materials, fuels, supply chains, appliances, and technologies, without diving into individual sheets or formulas.

#### 1. Add item

Select the target list from the left-hand pane, enter a unique name and identifier, choose the spot where it should appear (after the currently chosen entry), and click **Add item**. The tool inserts the row or column and copies the new item name and identifier into all related input sheets, `De1`, `De2`, `De4`, `Ck1`, `Ck2`, and `Bm1`, so it is ready for data entry everywhere it is needed.

#### 2. Remove item

Highlight the target list in the left pane, select the entry you want to delete, and click **Remove item**. The tool wipes that row or column from every linked input sheet, `De1`, `De2`, `De4`, `Ck1`, `Ck2`, and `Bm1`, and then sequences the remaining items. Deletions are permanent, so back up or export your data before you proceed.

#### 3. Rename item

Highlight the target list in the left pane, select the entry you wish to rename, type the new label, and click **Rename item**. The revised name instantly propagates to every linked input sheet, `De1`, `De2`, `De4`, `Ck1`, `Ck2`, and `Bm1`, keeping all references consistent.

#### 4. Rearrange item

Highlight the target list in the left pane, select the two entries you wish to swap positions, and click **Rearrange items**. The updated order is applied instantly across all linked sheets, `De1`, `De2`, `De4`, `Ck1`, `Ck2`, and `Bm1`, ensuring every reference stays in sync.

After a batch of edits and revising the data, click **Write Files** to regenerate the text files and keep the external model aligned with your revised structure.

### Plan and Scenario Definition

Defining scenarios is a two-step exercise done on the `Pl` and `De5` sheets. In both cases, you start by telling the workbook how many tables you need; the macro behind **Update Tables** then builds or trims those tables so the sheet always matches your count. The content that goes inside the tables, rates, prices, stage dates, and so on, is covered later. Here we focus only on the mechanics of adding, removing, and structuring scenarios.

#### Deployment and pricing plans

The `Pl` sheet manages two plan families that later combine into the run list.

1. Enter the desired number of deployment, pricing, and combined plans. Each must be at least 2.
2. Set the number of stages, the time intervals across which each plan’s conditions apply, also at least 2.
3. Click **Update Tables**. This adds or removes blocks of tables for **Deployments**, **Pricings**, and **Combined Plans** to match your counts, and adds or trims stage rows within the Combined Plans table to align with the stage count. Each block carries its own header, input rows, and validation rules.

The tool preserves any data that still fits inside the new layout, but cells that disappear are permanently deleted. After the table structure refreshes, name and complete each plan, and enter the number of contiguous years that every stage interval covers.

#### Growth scenarios

The `De5` sheet manages the growth scenarios.

1. Enter the number of growth scenarios. It must be at least 2.
2. Click **Update Tables**. This inserts or deletes vertical blocks so that exactly the requested number of Growth Scenario tables appears. Each block carries its own header, input rows, and validation rules.

If you reduce the count, the right-most scenarios are deleted first, so export or copy any data you want to keep before shrinking the list. After the table structure is updated, populate the tables with valid information.

### Write Files

Once the project path and the study structure, plans, and scenarios are in place, press **Write Files** on the Console to push everything out to disk. The tool performs three checks in sequence:

1. **Folder audit.** It scans the project path for the required subfolders. Any missing folder is created on the fly; existing ones are left intact.
2. **Overwrite warning.** If text files with the same names already exist, a dialog asks whether to overwrite. Choose **OK** to replace them or **Cancel** to keep the current versions.
3. **File generation.** For each sheet section, the tool exports a tab-separated-value (`TSV`) text file using the current input information.

Write files every time you change items, plans, scenarios, or any other input cells so the external model stays perfectly in sync with the workbook.

### Run Model

Within the **Console** page, use the drop-down menus to pick:

1. the **Combined Plan** — the pricing-and-deployment blend you created in `Pl`, and
2. the **Growth Scenario** from `De5`.

If you are only making minor input tweaks, say, adjusting a price or shifting a stage boundary, check the **Interactive Mode** box. In this mode, `main.exe` reloads the latest text files but skips the heavy preprocessing steps, so the run finishes much faster. Clear the box whenever you have made a structural change, such as added or removed items, plans, or scenarios, because those edits require a full, clean run to ensure every downstream calculation is rebuilt.

With all selections in place, click **Run Model**. Behind the button, Excel shells out to the compiled Python executable `main.exe`, located in your project folder, in a separate window. That window streams real-time progress messages until the run finishes or halts. If everything completes successfully, the window closes automatically; otherwise, leave the window open and inspect the log files.

### Save Case

Once the model has been executed and the results verified, press **Save Case** on the Console to archive the current inputs, configuration, and outputs. The tool performs the following actions in sequence:

1. **File naming.** It verifies that the specified case folder exists within the project directory. If the folder is missing, it is created automatically.
2. **Case export.** It saves all input data, configuration files, and output results under the chosen case-name folder.

Each saved case represents a complete snapshot of the model state at the time of saving, allowing you to reopen or rerun it later without re-entering inputs. It is recommended to save the case after each major change in scenarios, parameters, or results to maintain a clear record of all modeling iterations.

### Load Case

To reopen a previously saved case, press **Load Case** on the Console. This command retrieves the results associated with a stored case using the specified case path and case name. The tool performs the following actions in sequence:

1. **Case identification.** It uses the provided path to case and case name to locate the corresponding case folder within the project directory.
2. **Results import.** It loads the stored output data into the workbook, updating the visualization sheets.

The loaded case populates the four available output views: cost of cooking, technology adoption, social impact of clean cooking, and socioeconomic value of social factors. This allows users to review previously generated results without rerunning the model.

### Show / Hide Sheets

To simplify navigation across the workbook, the Console includes three buttons that allow you to hide or unhide groups of sheets associated with different stages of the workflow. These buttons do not modify any data; they only control the visibility of sheets to keep the interface easier to navigate.

Each button toggles the visibility of a predefined set of worksheets:

1. **Show / Hide Preprocess sheet** – Displays or hides the sheets used to enter preprocessing model inputs, including only `Preprocess`.
2. **Show / Hide Configuration sheets** – Displays or hides the sheets used to define structural settings, including `Co` and `Tp`.
3. **Show / Hide Plan and Output sheets** – Displays or hides the sheets that define plans and scenarios, and present model results and visualizations, including `Pl`, `De5`, `cost`, `adoption`, `social-impact`, and `socioeconomic`.

Using these controls helps reduce the number of visible tabs and allows you to focus on the relevant part of the workflow at each stage of the analysis.

---

## Input Data and Validation

### Preprocess

#### Purpose

`Preprocess` stores the settings used to pull building data from OpenStreetMap and create the `De3` building-list files. Filling out this sheet is optional and can be done independently of running the model. See the preprocessing tool README for further details.

#### Key inputs

- `C3` – web link to OpenStreetMap zip file from `https://download.geofabrik.de/`
- `C4` – code for defined Coordinated Reference System from `https://epsg.io/`
- `C7:C9` – column labels that will appear as header names for administrative divisions in the shapefile and CSV inputs
- `D7:D9` – shapefiles that define the administrative divisions
- `H6` – default building-type code used when a shapefile or CSV input file lacks an explicit tag
- `H7` – default social-cluster code used when a CSV input file lacks an explicit tag
- `H8` – column headers expected in the social-census CSV input file that categorizes households by income level
- `H9` – fuel names that must exactly match the labels used in the fuel-area definition files
- `B13:B` – free-form column for listing all top-level administrative divisions that will regionalize the model
- `E13:E` – free-form column for assigning each building to a numbered social-cluster identifier. Adjacent protected columns `C` and `D` display the building type for quick reference
- `I13:I` – free-form column for listing the land-use raster TIFF filenames (one per row) downloaded from `https://livingatlas.arcgis.com/landcover/`. Adjacent columns `F`, `G`, and `H` display the existing and used land-use codes
- `J11` – select the building-type code that represents aggregated sites such as refugee camps or military bases
- `J13:J` – free-form column for listing the shapefile names that define these aggregated building areas

#### Validation rules

The sheet actively validates numeric fields only. File paths and URLs are not checked at this stage, so any typos will surface later when you run the preprocessing script. Keep in mind that everything entered here is simply translated into the YAML configuration file consumed by the preprocessing package.

#### Typical edits

You will touch this sheet mainly when you launch a new study in a different region or country. After consulting the preprocessing package’s README, the usual updates are the OpenStreetMap download path, the coordinate-reference system, the list of administrative divisions, and the filenames for land-use TIFF rasters and aggregated-building shapefiles.

### Configuration

#### Purpose

`Co` stores country-wide settings in four sections: the UTM zone, key economic parameters, electricity-system characteristics, and adoption/capacity-margin targets for both electricity and LPG. A closing block lets you specify the filenames of the input datasets that the Python model will read.

#### Key inputs

- `C3` – enter the Universal Transverse Mercator zone for the study area. If the project straddles multiple zones, pick the dominant zone or subdivide the analysis into smaller areas that fit a single zone. This value must match cell `C4` in `Preprocess` to keep coordinate systems aligned
- `C5` – acronym of local currency
- `C6` – exchange rate local currency to USD
- `C7` – labor cost in USD per hour, being the average for the sector or region, including social contributions and other mandatory costs
- `C8` – diesel cost in USD per liter
- `C10:C13` – voltage levels in electricity system in kV
- `C14` – select frequency from drop-down list in Hz
- `C15` – current electricity system peak load in GW
- `C16` – current annual electricity demand in TWh
- `C17` – percentage of distributed generation that supports the peak load
- `C18` – average annual CO₂ emissions rate of electricity system in kg per kWh
- `C19` – reliability of the main electricity grid
- `C20` – percentage of losses in the electricity system
- `C21` – average vintage of the electricity system in years, used for depreciation and amortization
- `C22:C25` – levelized CAPEX and OPEX for generation, and TOTEX for the transmission and distribution systems, all expressed in USD per kWh
- `C27:C30` – current adoption rates for electricity and LPG, plus the forward-looking capacity margins planned for each fuel
- `C32:C66` – input-file names for every data sheet. Each sheet is internally broken into text-file blocks, but you can rename any file freely. The tool takes care of the underlying partitioning

#### Validation rules

All numerical values are restricted to positive decimals, such as costs, voltages, percentages, and energy values, or whole numbers, such as years.

#### Typical edits

The parameters in the first four blocks are typically updated only when launching a new case study. Once set, they usually stay unchanged for subsequent project runs. File-name entries can remain as they are unless you choose to rename them.

### Territory Partition

#### Purpose

`Tp` specifies the administrative or geographic hierarchy for the case study, from the highest level down to the main division, and links directly to the corresponding `De3` files that list buildings and their attributes. The sheet also lets you enter land-use classifications and define a latitude-longitude bounding box for spatial filtering.

#### Key inputs

- **Column B** – a short, capital-letter identifier for each administrative or geographic division
- **Column C** – name of administrative or geographic division
- **Column D** – assign `0` to bottom-level divisions, then increment by `1` for each nested division above it
- **Column H** – specify the minimum and maximum latitude and longitude that define the bounding box of each division
- **Column I** – for divisions at level `1` and above, enter the count of subordinate divisions under each parent
- **Column J** – enter the code of the immediate parent division
- **Column K** – for level `0` divisions, enter the folder path, relative to the `inputs` directory in the project root, where the `De3` file for that division is stored
- **Columns L:O** – enter the percentage of each selected land-cover category, trees, crops, built-up area, and rangeland, within every division

#### Validation rules

The sheet actively validates numeric fields:

- level is a positive integer
- longitude values must be between `-180` and `180`
- latitude values must be between `-90` and `90`
- number of dependencies must be a positive integer
- land-use percentages must be between `0%` and `100%`

In addition, verify each of the following to avoid runtime failures:

- Every row includes all required fields.
- Dependency counts match the actual number of subdivisions.
- Parent codes correctly reference the immediate higher-level division.
- Input paths for `De3` building files are valid and relative to the input folder.
- Land-use percentages sum to exactly `100%`. You may need to normalize.

#### Typical edits

These settings are configured when you launch a new case study and generally remain fixed. Adjust them only if you change the administrative or geographic division levels to alter the model’s granularity.

### Definition of Plans

#### Purpose

`Pl` lets you define your deployment and pricing plans, and their combinations, for each model run, as well as the number of time stages, or year intervals, over which those plans apply. Start by entering the counts for deployment plans, pricing plans, combined scenarios, and stages.

- **Deployment plans** set targets for electricity and LPG adoption and limit available capacity of fuels and appliances.
- **Pricing plans** apply multipliers to fuel and appliance prices. A value below `1` represents a subsidy or incentive; a value above `1` represents a tax or surcharge.

Each combined scenario then pairs one deployment plan with one pricing plan across the defined stages.

#### Key inputs

- `C13` – number of deployment plans
- `C14` – number of pricing plans
- `C15` – number of combined plans
- `C16` – number of time stages
- `C17` – initial year of simulation run
- **Row 18** – duration of each time stage in years

**Deployment Plans** – a vertical series of subtables, one for each deployment plan:

- 1st row – identifier of deployment plan
- 2nd row – name of deployment plan
- 3rd row – electricity adoption target of deployment plan
- 4th row – LPG adoption target of deployment plan
- 1st subtable – maximum deployed capacity of fuels in rural and urban areas
- 2nd subtable – maximum deployed capacity of appliances in rural and urban areas

**Pricing Plans** – a vertical series of subtables, one for each pricing plan:

- 1st row – identifier of pricing plan
- 2nd row – name of pricing plan
- 1st subtable – price multipliers of fuels in rural and urban areas
- 2nd subtable – price multipliers of appliances in rural and urban areas

**Combined Plans** – a vertical series of subtables, one for each combined plan:

- 1st row – identifier of combined plan
- 2nd row – name of combined plan
- subtable – select a combination of deployment and pricing plans for the start year of each stage. By default, the first stage uses the first deployment plan and the first pricing plan, and those cells are locked to preserve the initial configuration

#### Validation rules

Counts and years must be positive integers. Percentages must lie between `0%` and `100%`. Multipliers must be positive numbers. All required fields in each table must be completed before running the model. Clicking **Update Tables** with a smaller count will permanently delete the excess tables or columns, and their data, so back up any work you need to keep.

#### Typical edits

You may define an unlimited number of deployment and pricing plans without degrading tool performance. When you are ready to execute specific combinations, select the desired pairing in the **Console** tab, and maintain an external log of each run’s configuration for reproducibility.

### Definition of Growth Scenarios

#### Purpose

`De5` enables you to specify how key variables evolve over the entire study horizon, including demand, household income, population, technology learning, social indicators, fuel costs, and retail price multipliers. Each growth scenario you define on this sheet applies uniformly from the first to the final year of the model.

#### Key inputs

- `C13` – number of growth scenarios
- 1st row – identifier of growth scenario
- 2nd row – name of growth scenario
- 1st subtable – variation of the demand multipliers for electricity, cooking, and heating in rural and urban areas
- 2nd subtable – variation of the elasticity for electricity demand in rural and urban areas
- 3rd subtable – variation of household income, population, and technology learning rate in rural and urban areas
- 4th subtable – variation of the relative social weight versus economic value, along with independent social-factor parameters, health, gender equity, emissions, deforestation. These values do not need to sum to `1`
- 5th subtable – variation of the costs of electricity and LPG procurement, transportation, and molecule, LPG only
- 6th subtable – variation of the retail price of fuels
- 7th subtable – variation of the retail price of appliances

#### Validation rules

Counts must be positive integers. Percentages must lie between `-100%` and `100%`. Elasticities must be positive numbers. Clicking **Update Tables** with a smaller count will permanently delete the excess tables or columns, and their data, so back up any work you need to keep.

#### Typical edits

You may define an unlimited number of scenarios without degrading tool performance. When you are ready to execute, select the desired scenario in the **Console** tab, and maintain an external log of each run’s configuration for reproducibility.

### Hourly Profiles of Demand

#### Purpose

`De1` stores the foundational 24-hour load profiles for electricity (`De1E`), cooking (`De1C`), and heating (`De1H`). These baseline demand curves are then combined in `De2` to generate detailed load profiles for each defined building type. If you need to extend the model beyond 24 hours, please contact the developer.

#### Key inputs

- **Rows** – basic demand profiles
- **Columns** – hours
- **Content** – demand in kW

#### Validation rules

All values must be greater than or equal to zero.

#### Typical edits

These values are configured when you initiate a new case study and can be retained if the new study area exhibits similar characteristics.

### Demand Multipliers

#### Purpose

`De2` lets you enter demand multipliers that scale the basic load profiles to each building type. For every building type, electricity, cooking, and heating demands are computed by multiplying the respective 24-hour base profile by its size parameter. This sheet also records the nominal voltage level for each building type.

#### Key inputs

- **Rows** – building types
- **Column C** – select a voltage level from the list
- **Column D** – size parameter to scale the linear combination of basic load profiles
- **Subtable electricity demand** – insert multipliers of basic load profiles
- **Subtable cooking demand** – insert multipliers of basic load profiles
- **Subtable heating demand** – insert multipliers of basic load profiles

Each building’s demand profile is computed by linearly combining the base load profiles with the specified multipliers and then scaling the result by the size parameter.

#### Validation rules

All numerical values must be greater than or equal to zero.

#### Typical edits

These values are configured when you initiate a new case study and can be retained if the new study area exhibits similar characteristics.

### Characteristics of Social Clusters

#### Purpose

`De4` stores the parameters for each social cluster that drive technology-adoption modeling. These include adoption elasticity, budget constraint, willingness to pay, adoption penalty, switching sensitivity, and social-cost weight. Additionally, social-impact factors, health, gender equity, emissions, and deforestation, are entered as percentages of the total social weight and must sum to `100%`.

#### Key inputs

- **Rows** – social clusters
- **Column C** – select from the list whether it is a rural or urban social cluster
- **Column D** – adoption elasticity, responsiveness to changes in costs or incentives
- **Column E** – budget constraint, maximum spending capacity for adopting technologies in USD
- **Column F** – willingness to pay, economic preference level for upgrading in USD per unit
- **Column G** – adoption penalty, negative factor reducing adoption desirability
- **Columns H:I** – switching sensitivity, propensity to move to better or worse technologies than the one currently used
- **Column J** – social-cost weight, relative percentage of social versus economic costs when evaluating a new technology
- **Columns K:N** – social-impact factors, health, gender equity, emissions, and deforestation, which comprise the social-cost weight and must sum to `100%`

#### Validation rules

All numerical values must be greater than or equal to zero. All percentages must be between `0%` and `100%`. Ensure that the social-impact factors sum to exactly `100%`, as indicated in the protected check column.

#### Typical edits

These values are configured when you initiate a new case study and can be retained if the new study area exhibits similar characteristics.

### Catalog of Cooking Technologies

#### Purpose

`Ck1` organizes cooking-technology data in a bottom-up workflow: raw materials, fuels, supply chains, appliances, and technologies. Attributes of each link are captured in dedicated tables.

#### Key inputs

- `C15` – CO₂ emissions of diesel fuel for transportation in kg per liter
- `C16` – typical transportation distance from logistic centers to retail stores
- `C17` – typical transportation distance from retail stores to end consumer

**1st table – raw materials**

- **Column C** – procurement cost in USD per kg, kWh, or liter
- **Column D** – CO₂ emissions in kg per kg, kWh, or liter

**2nd table – fuels**

- **Column C** – retail price in USD per kg, kWh, or liter
- **Column D** – calorific value in kWh per kg, kWh, or liter
- **Column E** – gender-social cost in units per kg or liter. This reflects the time women and children spend collecting fuel

**3rd table – supply chains**

- **Columns C:D** – select combination of raw material and fuel that defines the supply chain
- **Column E** – efficiency of conversion from raw material to fuel
- **Column F** – cost of processing in USD per kg or liter
- **Column G** – cost of transportation in USD per kg or liter, per kilometer
- **Column H** – CO₂ emissions from processing in kg per kg or liter
- **Column I** – CO₂ emissions from transportation in kg per kg or liter
- **Column J** – percentage of fuel weight in chain to adjust costs
- **Column K** – average transportation distance of raw material to conversion facility in km

**4th table – appliances**

- **Column C** – cost of the appliance in USD
- **Column D** – cost of transportation in USD per km
- **Column E** – CO₂ emissions of transportation in kg per km
- **Column F** – retail price in USD
- **Column G** – lifetime in cooking units
- **Column H** – efficiency in cooking units per kWh
- **Column I** – health-social cost in units per cooking unit
- **Column J** – gender-social cost in units per cooking unit
- **Column K** – CO₂ emissions in kg per cooking unit

**5th table – technologies**

- **Columns C:D** – pair fuel with appliance

#### Validation rules

All numerical values must be greater than or equal to zero. Percentages must be between `0%` and `100%`.

#### Typical edits

These values are configured when you initiate a new case study and can be retained if the new study area exhibits similar characteristics.

### Initial Technology Adoption

#### Purpose

`Ck2` stores the initial technology adoption per social cluster.

#### Key inputs

- **Rows** – social clusters
- **Column C** – select from the list whether it is a rural or urban social cluster
- **Column D onward** – enter the adoption percentage of each technology for each cluster

#### Validation rules

Percentages must be between `0%` and `100%`. Ensure that the total adoption sums to exactly `100%`, as indicated in the protected check column.

#### Typical edits

These values are configured when you initiate a new case study and are expected to change from case to case.

### Local Differences

#### Purpose

`Bm1` lets you specify multipliers that adjust fuel retail prices and gender-related social costs according to the predominant land use around each building, increasing or decreasing procurement and social-cost values based on local geographic context.

For example, the fuel price of commercial firewood is input in sheet `Ck1`. This price, however, may differ between land areas. It could be higher in urban areas, where it is less accessible, than in forestry areas, where it may be sold inexpensively. These geographic price variations can be controlled using these multipliers.

#### Key inputs

**1st table – local multiplier of fuel retail price**

- **Rows** – land use and rural or urban area
- **Column D onward** – multiplier per fuel

**2nd table – local multiplier of fuel gender-related social cost**

- **Rows** – land use and rural or urban area
- **Column D onward** – multiplier per fuel

#### Validation rules

All numerical values must be greater than or equal to zero.

#### Typical edits

These values are configured when you initiate a new case study and can be retained if the new study area exhibits similar characteristics.

---

## Advanced Features

### Electricity Plan

Because detailed electrification planning involves geospatial analyses, network-sizing algorithms, and techno-economic assumptions that vary widely by case study, this work is delegated to specialized electrification models rather than re-implemented in Excel. By importing a precomputed reference plan, you leverage rigorous, context-specific cost and capacity forecasts, built with up-to-date grid-extension or mini-grid algorithms, without duplicating effort.

This modular approach keeps Excel focused on scenario and adoption modeling and result visualization, while allowing you to swap in new or improved electrification pathways as they become available. It also ensures consistency: every project run uses the same baseline trajectories, so comparative analyses remain valid even as the external reference model evolves.

#### Purpose

`El1` captures the Electricity Reference Plan, detailing the CAPEX, OPEX, and other relevant attributes required to build out the electricity system up to a target access capacity. You must supply four sequential states:

- **State 1** – business as usual without clean cooking access, or minimal access
- **State 2** – clean cooking access in urban areas only
- **State 3** – clean cooking access in rural areas only
- **State 4** – clean cooking access in both urban and rural areas

These inputs come from an external electrification model and feed into cost estimates for e-cooking deployment under different coverage scenarios.

#### Key inputs

- `C13` – reference capacity of electrification plan
- `C14` – number of electric areas

**1st table – common characteristics of each electrification mode**

Rows correspond to electrification modes: grid extension, microgrid, and standalone system.

- **Column C** – fraction of fixed OPEX on total OPEX
- **Column D** – typical lifetime of equipment for depreciation and amortization in years
- **Column E** – discount rate

**2nd table – specifications for each state of electrification plan**

- **Column B** – identifier of electric area
- **Column C** – name of electric area

For each of the four states, the subtable includes:

- 1st column – CAPEX in million USD per year
- 2nd column – OPEX of microgrid systems in USD per kWh
- 3rd column – CO₂ emissions of microgrid systems in kg per kWh
- 4th column – fraction of total demand connected to the main grid in %
- 5th column – fraction of total urban demand connected to the main grid in %

#### Validation rules

All numerical values must be greater than or equal to zero. Percentages must be between `0%` and `100%`.

#### Typical edits

These values are configured when you initiate a new case study and are expected to change from case to case.

### LPG Plan

Unlike the electricity reference plan, which is imported from an external electrification model, the LPG Reference Plan is generated entirely within Excel by an embedded logistic model. This self-contained approach reflects two practical considerations. First, there is not a widely adopted, open-source LPG rollout tool equivalent to those used for grid planning. Second, upstream costs, procurement, cylinder refill, transport, and storage, and downstream costs, distribution and retail margin, can be represented with a manageable set of parameters inside a logistic cost model.

Consult the main documentation for full details on the LPG model. Here we outline the input-output workflow. To generate the LPG Reference Plan, work across three sheets: `LPGin`, `LPGmodel`, and `LPG1`.

#### Data Input

##### Purpose

`LPGin` consolidates all LPG sector inputs in one worksheet, organized into two sections. The first section defines each stage’s parameters, production, transport, storage, distribution, and retail, including several specifications. The second section lets you enter the distances between procurement sites, storage facilities, and delivery points.

##### Key inputs

**Tables on the left-hand side**

**1st table – country-level data**

- `C4` – sectorial Weighted Average Cost of Capital (`WACC`)
- `C5` – number of working days during a year

**2nd table – procurement of LPG**

- `C8` – procurement cost in USD per ton
- `C9` – technical or commercial losses in %
- `C10` – license fee for procuring LPG in USD
- `C11` – license validity in years

**3rd table – depots of LPG**

- `C14` – technical or commercial losses in %
- `C15` – lifetime of infrastructure in years
- `C16` – installation fee in USD
- `C17` – operation license fee in USD
- `C18` – operation license validity in years

**4th table – bulk transportation of LPG**

- `C21` – capacity of each vehicle in tons
- `C22` – cost of each vehicle in USD
- `C23` – fuel consumption in liters per 100 km
- `C24` – fixed operation and maintenance cost in USD per year
- `C25` – variable operation and maintenance cost in USD per km
- `C26` – lifetime of vehicle in years
- `C27` – technical or commercial losses in %
- `C28` – license fee in USD
- `C29` – license validity in years
- `C30` – average speed of vehicle when delivering in km per hour

**5th table – bottling station**

- `C33` – overnight cost of a bottling station with 35 kTon capacity in USD
- `C34` – fixed operation and maintenance cost in USD per year
- `C35` – variable operation and maintenance cost in USD per kg
- `C36` – lifetime of infrastructure in years
- `C37` – technical or commercial losses in %
- `C38` – installation fee in USD
- `C39` – operation license fee in USD
- `C40` – operation license validity in years

**6th table – primary transportation of LPG cylinders from bottling stations to warehouses**

- `C43` – capacity of each vehicle in tons
- `C44` – cost of each vehicle in USD
- `C45` – fuel consumption in liters per 100 km
- `C46` – fixed operation and maintenance cost in USD per year
- `C47` – variable operation and maintenance cost in USD per km
- `C48` – lifetime of vehicle in years
- `C49` – technical or commercial losses in %
- `C50` – license fee in USD
- `C51` – license validity in years
- `C52` – average speed of vehicle when delivering in km per hour

**7th table – warehouses for LPG cylinders**

- `C55` – overnight cost of a warehouse in USD
- `C56` – maximum storage capacity of 12-kg cylinders
- `C57` – fixed operation and maintenance cost in USD per year
- `C58` – lifetime of infrastructure in years
- `C59` – technical or commercial losses in %
- `C60` – operation license fee in USD
- `C61` – operation license validity in years

**8th table – secondary transportation of LPG cylinders from warehouses to retailers**

- `C64` – capacity of each vehicle in tons
- `C65` – cost of each vehicle in USD
- `C66` – fuel consumption in liters per 100 km
- `C67` – fixed operation and maintenance cost in USD per year
- `C68` – variable operation and maintenance cost in USD per km
- `C69` – lifetime of vehicle in years
- `C70` – technical or commercial losses in %
- `C71` – license fee in USD
- `C72` – license validity in years
- `C73` – average speed of vehicle when delivering in km per hour

**9th table – cylinders of LPG**

You can add more rows to each of the four blocks to consider additional cylinder sizes.

- `C76` – annual replacement rate of cylinders due to damage, theft, or others, in %
- `C77` – requalification fee for new or expired cylinders in USD
- `C78` – requalification validity in years
- 1st block – size in kg
- 2nd block – share of total in %
- 3rd block – lifetime in years
- 4th block – purchase cost in USD

**Tables on the right-hand side**

**1st table – warehouses to store LPG cylinders**

- **Column F** – name of warehouse
- **Column G** – number of inhabitants covered by warehouse
- **Column H** – annual equivalent LPG consumption per capita in kg
- **Column I** – urban population covered by warehouse in %
- **Column J** – cylinder demand from total LPG demand in %. Protected columns `J:L` display the total LPG cylinder demand in urban and rural areas based on the specified adoption level

**2nd table – bottling stations to fill LPG cylinders**

- **Column O** – name of bottling station
- **Column P** – distance of bottling station to procurement site in km

**3rd table – distance from warehouse to retail points**

- **Rows** – name of warehouse
- **Column S** – average distance from each warehouse to its assigned retail points in urban areas
- **Column T** – average distance from each warehouse to its assigned retail points in rural areas

**4th table – distance matrix from warehouse to bottling station**

- **Rows** – name of warehouse
- **Column V onward** – distance from warehouse to bottling station in km. A protected column displays the name of the closest bottling station to each warehouse

##### Validation rules

All numerical values must be greater than or equal to zero. Days and years must be positive integers. Percentages must lie between `0%` and `100%`. Ensure that cylinder-size share percentages sum to `100%`, and that the total building count matches the sum of entries in the `De3` files.

##### Typical edits

The values on the left-hand side are configured when you initiate a new case study and can be retained if the new study area exhibits similar characteristics. In contrast, the values on the right-hand side are expected to change from case to case.

#### Logistic Cost Model

##### Purpose

`LPGmodel` performs calculations to estimate LPG deployment costs. The average household demand, total LPG demand for the study area divided by the number of households, and the adoption rate for the selected scenario are entered directly by the user. If you wish to explore an individual case, you can adjust the relevant state and area cells accordingly.

Using these inputs, together with the data from `LPGin`, the model calculates total LPG demand for the specified state and area, the transportation requirements, such as vehicle fleet size, and the number of cylinders needed. These results are then used to derive the cost for each link in the LPG supply chain. For convenience, the sheet also provides a summary of the main outputs.

##### Key inputs

- `B5` – LPG calorific value in kWh per kg
- `B6` – cooking-units energy content in kWh
- `C10` – reference adoption capacity
- `C11` – choose state at reference capacity: `(1)` only urban, `(2)` only rural, `(3)` urban plus rural
- `C12` – numbered position of the warehouse as it appears in the list
- `C35` – number of trucks in bulk fleet, from LPG depots to bottling stations. This cell is used iteratively to adjust the maximum number of working days of drivers in cell `C38`
- `C36` – number of trucks in primary fleet, from bottling stations to warehouses. This cell is used iteratively to adjust the maximum number of working days of drivers in cell `C39`
- `C37` – number of trucks in secondary fleet, from warehouses to retailers. This cell is used iteratively to adjust the maximum number of working days of drivers in cell `C40`

##### Validation rules

All numerical values must be greater than zero. Reference access must be between `0%` and `100%`. Warehouse number cannot exceed the total number of existing warehouses.

##### Typical edits

These values are configured when you initiate a new case study and can be retained if the new study area exhibits similar characteristics.

#### Reference Plan

`LPG1` displays the specifications from the LPG Reference Plan required for the adoption model. It indicates the reference-capacity access and the number of LPG supply areas, listing the name of each area and detailing three states:

- **State 2** – reference access for urban areas
- **State 3** – reference access for rural areas
- **State 4** – reference access for urban and rural areas

**State 1 does not exist**, as it represents `0%` access.

For each state, the sheet provides:

- CAPEX in billion USD per year
- OPEX in billion USD per year
- average local last-mile delivery distance in km

Under **State 4**, the model also reports CAPEX and OPEX for the upstream segment, covering the logistic chain from procurement through transport to the warehouse, in billion USD per year.

Additional distances are given for:

1. procurement site to bottling station
2. bottling station to warehouse
3. warehouse to retailer

Finally, the sheet presents the interpolation parameters:

- fraction of fixed costs within OPEX
- fixed/variable cost fractions for transportation links
- fixed/variable cost fractions for processing links

Each of these is split between the **upstream side** and the **local side**.

The only user input is in **Column B**, where you must enter the identifier of each LPG supply area. This must match the file that assigns buildings to LPG areas.

All values are updated when clicking **Calculate states**, as the macro combines states 2, 3, and 4 with every individual area.

---

## Outputs Visualization

After running the model or loading a previously saved case, results can be explored through four visualization sheets. These sheets present the outputs in both chart form and tabular form to facilitate interpretation and comparison across years, stages, and geographical areas.

Each visualization page contains:

- a chart summarizing the main results
- filters or selectors to explore specific areas or technologies
- a table showing the numerical values used to generate the chart

### Cost of Cooking

The cost-of-cooking visualization presents the evolution of cooking costs over time. Two indicators are displayed:

1. **Price (`$/cook`)** – the estimated cost per cooking event
2. **Expenditure (`$/year`)** – the annual cooking expenditure per household

The chart displays these indicators across years, terms within each year, and geographical area, urban or rural. A selector allows switching between urban and rural areas.

The table below the chart provides the underlying numerical values, including:

- Year
- Stage (term)
- Area
- Price per cook
- Annual expenditure
- Percentage variation relative to the baseline

This visualization helps identify how policy scenarios or adoption pathways influence household cooking costs over time.

### Adoption of Technologies

The adoption-of-technologies visualization shows the projected adoption rate of each cooking technology. The chart displays the percentage of households adopting a given technology over time for a selected area.

Two selectors are available:

1. **Area selector** – urban or rural
2. **Technology selector** – specific cooking technology

The table below the chart provides the detailed data used in the visualization, including:

- Year
- Stage (term)
- Area
- Technology identifier
- Adoption percentage

This view allows users to track how technologies penetrate the market under the defined scenarios and how adoption evolves throughout the simulation horizon.

### Social Impact of Clean Cooking

The social-impact visualization presents the evolution of the main social indicators associated with cooking transitions. The chart shows four indicators:

- Health
- Gender
- Emissions
- Deforestation

Each indicator is normalized relative to the initial year, allowing the chart to illustrate the relative improvement or deterioration over time. The table below the chart contains the corresponding values for each year and stage.

These indicators reflect the social impacts associated with changes in cooking technologies and fuel use.

### Socioeconomic Value of Social Factors

The socioeconomic-value visualization aggregates the social indicators into economic terms. The chart shows the total socioeconomic value of the social impacts resulting from the transition in cooking technologies.

The table provides a breakdown of the components contributing to this value:

- Base economic cost
- Health
- Gender
- Emissions
- Deforestation
- Total (grand) socioeconomic value

Values are reported for each year and stage.

This visualization allows users to assess the combined economic and social benefits associated with different scenario outcomes.
