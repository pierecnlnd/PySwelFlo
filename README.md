# PySwelFlo

**Python tools for automating SwelFlo geothermal wellbore simulations.**

PySwelFlo is a Python toolkit that helps geothermal reservoir engineers work with [SwelFlo](https://swelflo.com/SwelFlo/Home.html), a steady-state wellbore simulation application. It provides a programmatic interface for preparing and editing SwelFlo input files, organizing simulation cases, launching the SwelFlo engine where supported, and extracting simulation results for downstream engineering workflows.

> **Important:** PySwelFlo does not replace or redistribute SwelFlo. A valid SwelFlo installation and the appropriate executable/license are required to run simulations. This project is an independent Python companion.

## Why PySwelFlo?

Reservoir engineering workflows often involve repeating wellbore calculations for multiple operating conditions, wells, or sensitivity cases. Preparing each case manually can be time-consuming and difficult to reproduce.

PySwelFlo is intended to make these workflows scriptable so engineers can use Python for:

- preparing and modifying `SWFinput.txt` models;
- managing wellhead conditions, casing/liner sections, reservoir temperature points, and feedzones;
- writing SwelFlo input and unit-selection files;
- running supported SwelFlo executable builds or opening a model in the SwelFlo GUI;
- parsing output text and sibling CSV files into pandas DataFrames;
- exporting parsed results to JSON and Excel; and
- plotting casing geometry, wellbore profiles, and wellhead output curves.

## Current capabilities

| Area                   | Capability                                                                                |
| ---------------------- | ----------------------------------------------------------------------------------------- |
| Input processing       | Read and write SwelFlo `SWFinput.txt` files                                             |
| Model components       | Wellhead conditions, casing sections, reservoir temperatures, feedzones                   |
| Model inspection       | Convert selected input sections to dictionaries and pandas DataFrames                     |
| Geometry visualization | Plot casing/liner geometry and optionally feedzone depths                                 |
| Simulation execution   | Silent command-line execution where supported; GUI launch as an alternative               |
| Output processing      | Parse `SWFoutput###.txt` and associated `SWFplot###.csv` / `SWFoutcrv###.csv` files |
| Data export            | Export result tables to JSON and Excel                                                    |
| Result visualization   | Plot output curves and selected wellbore profile variables                                |
| PTS utilities          | Experimental utilities for processing spinner/PTS survey data (`geoPTS`)                |

The `geoPTS` utilities are separate from the core SwelFlo input/output workflow and should be considered experimental until validated for a specific field workflow.

## Repository structure

```text
PySwelFlo/
├── README.md
├── pyproject.toml
├── LICENSE
├── .gitignore
├── src/
│   └── pyswelflo.py
├── docs/
│   ├── user-manual-pyswelflo.md
│   └── user-manual-pyswelflo.pdf
└── examples/
    ├── test-input.py
    ├── test-output.py
    └── test-run-loop.py
```

PySwelFlo currently uses a **single-module layout** (`src/pyswelflo.py`). The `src/pyswelflo/` package directory is not required. The public import remains `import pyswelflo` or `from pyswelflo import SWFinput, SWFoutput`.

## Requirements

- Python **3.10 or newer** is declared by the current project metadata. Verify compatibility against the Python version and dependencies used in your environment.
- A SwelFlo installation is required for simulation execution.
- The Python dependencies used by the current source include NumPy, pandas, Matplotlib, Plotly, and pyXSteam.

Install the package and dependencies in editable mode from the repository root:

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

If you prefer to install dependencies separately:

```bash
python -m pip install numpy pandas matplotlib plotly pyXSteam
```

## Quick start

The examples assume you have a valid SwelFlo input model and output files. Set paths to your own files; do not use confidential well data in public examples.

### 1. Read and inspect an existing input model

```python
from pathlib import Path
from pyswelflo import SWFinput

input_file = Path(r"C:\SwelFlo\Projects\Well_A\SWFinput.txt")

model = SWFinput(str(input_file))
model.read()

print(model)
tables = model.to_dataframe()

print(tables["wellhead_conditions"])
print(tables["casing_sections"])
print(tables["feedzones"])
```

### 2. Write a working copy

```python
from pathlib import Path

output_dir = Path("work") / "Well_A_case_01"
model.write(str(output_dir))

# Writes SWFinput.txt and SWFunitsChoices.txt to output_dir.
```

### 3. Read simulation results

```python
from pathlib import Path
from pyswelflo import SWFoutput

result_file = Path(r"C:\SwelFlo\Projects\Well_A\SWFoutput001.txt")
result = SWFoutput(str(result_file))

print(result)
print(result.dataframes.keys())
print(result.dataframes["wellbore_profile"].head())

result.to_excel("Well_A_results.xlsx")
```

See the [User Manual](docs/user-manual-pyswelflo.md) and runnable-script templates in [`examples/`](examples/).

## SwelFlo execution compatibility

The current source exposes two execution methods:

- `SWFinput.run(swelflo_path, output_dir=None)` invokes the executable in silent mode using `-s -f ... -p ...`. Use only with a SwelFlo build that has been verified to support silent execution.
- `SWFinput.run_gui(swelflo_path, output_dir=None)` launches the GUI with the prepared input and returns immediately, allowing the user to run the calculation interactively.

The source comments document a known behavior in the tested environments: the older 2017 executable supports silent execution, while the newer V9.105 build can crash in silent mode and should be opened through the GUI. This is version/build-specific behavior; verify it with your own licensed installation.

## Important notes

1. **Validate before production use.** Compare PySwelFlo-generated input files and parsed outputs against the SwelFlo GUI and known benchmark cases.
2. **Keep original files.** Work on copies of `SWFinput.txt` and associated project files.
3. **Check units and field meanings.** The source stores several SwelFlo fields using compact names (for example `P`, `Q`, `H`, `X`). Confirm their meaning and unit convention against the SwelFlo input specification and your model before changing values programmatically.
4. **Engine availability.** PySwelFlo does not include `swelflo.exe`, license files, or proprietary SwelFlo assets.
5. **No guarantee of numerical validity.** PySwelFlo automates file handling and workflow orchestration; engineering review remains necessary.

## Development

Clone the repository:

```bash
git clone https://github.com/pierecnlnd/PySwelFlo.git
cd PySwelFlo
python -m pip install -e .
```

Run the examples after setting their file paths or environment variables. The examples are intentionally based on user-supplied SwelFlo files because valid input/output files are installation- and project-specific.

## How to cite PySwelFlo

**If PySwelFlo contributes to your research, technical report, publication, software, or engineering workflow, please cite this GitHub repository.** Citation helps others identify the version of the tool used and gives credit to its developer.

Suggested reference:

> Canilandi, M. P. (2026). *PySwelFlo: Python tools for automating SwelFlo geothermal wellbore simulations* (Version 0.1.0) [Computer software]. GitHub. https://github.com/pierecnlnd/PySwelFlo

BibTeX:

```bibtex
@software{canilandi2026pyswelflo,
  author  = {Canilandi, Mesias Piere},
  title   = {PySwelFlo: Python tools for automating SwelFlo geothermal wellbore simulations},
  year    = {2026},
  version = {0.1.0},
  url     = {https://github.com/pierecnlnd/PySwelFlo},
  note    = {GitHub repository}
}
```

For reproducibility, cite the **specific release tag or commit** you used, where possible. Update the version and year in the citation as appropriate. A permanent DOI can be added later if a release is archived through a service such as Zenodo.

**Citation and licensing:** Citation is strongly requested for all uses, especially publications and reports. The MIT License governs legal permissions and does not independently require scholarly citation. If you want a legally enforceable attribution condition beyond MIT, the licensing approach needs separate consideration.

## License

This project is distributed under the MIT License. See [LICENSE](LICENSE).

SwelFlo is a separate product. Its name and associated software remain the property of their respective owner. This repository does not grant rights to use or redistribute SwelFl

# PySwelFlo

**Python tools for automating SwelFlo geothermal wellbore simulations.**

PySwelFlo is a Python toolkit that helps geothermal reservoir engineers work with [SwelFlo](https://swelflo.com/SwelFlo/Home.html), a steady-state wellbore simulation application. It provides a programmatic interface for preparing and editing SwelFlo input files, organizing simulation cases, launching the SwelFlo engine where supported, and extracting simulation results for downstream engineering workflows.

> **Important:** PySwelFlo does not replace or redistribute SwelFlo. A valid SwelFlo installation and the appropriate executable/license are required to run simulations. This project is an independent Python companion.

## Why PySwelFlo?

Reservoir engineering workflows often involve repeating wellbore calculations for multiple operating conditions, wells, or sensitivity cases. Preparing each case manually can be time-consuming and difficult to reproduce.

PySwelFlo is intended to make these workflows scriptable so engineers can use Python for:

- preparing and modifying `SWFinput.txt` models;
- managing wellhead conditions, casing/liner sections, reservoir temperature points, and feedzones;
- writing SwelFlo input and unit-selection files;
- running supported SwelFlo executable builds or opening a model in the SwelFlo GUI;
- parsing output text and sibling CSV files into pandas DataFrames;
- exporting parsed results to JSON and Excel; and
- plotting casing geometry, wellbore profiles, and wellhead output curves.

## Current capabilities

| Area                   | Capability                                                                                |
| ---------------------- | ----------------------------------------------------------------------------------------- |
| Input processing       | Read and write SwelFlo `SWFinput.txt` files                                             |
| Model components       | Wellhead conditions, casing sections, reservoir temperatures, feedzones                   |
| Model inspection       | Convert selected input sections to dictionaries and pandas DataFrames                     |
| Geometry visualization | Plot casing/liner geometry and optionally feedzone depths                                 |
| Simulation execution   | Silent command-line execution where supported; GUI launch as an alternative               |
| Output processing      | Parse `SWFoutput###.txt` and associated `SWFplot###.csv` / `SWFoutcrv###.csv` files |
| Data export            | Export result tables to JSON and Excel                                                    |
| Result visualization   | Plot output curves and selected wellbore profile variables                                |
| PTS utilities          | Experimental utilities for processing spinner/PTS survey data (`geoPTS`)                |

The `geoPTS` utilities are separate from the core SwelFlo input/output workflow and should be considered experimental until validated for a specific field workflow.

## Repository structure

```text
PySwelFlo/
├── README.md
├── pyproject.toml
├── LICENSE
├── .gitignore
├── src/
│   └── pyswelflo/
│       ├── __init__.py
│       └── core.py
├── docs/
│   ├── user-manual-pyswelflo.md
│   └── user-manual-pyswelflo.pdf
└── examples/
    ├── test-input.py
    ├── test-output.py
    └── test-run-loop.py
```

The package layout above follows the existing `src/pyswelflo` directory in this repository. If you intentionally want a single module at `src/utils/pyswelflo.py`, the import paths and package metadata should be adjusted consistently; do not keep two competing package layouts.

## Requirements

- Python **3.10 or newer** is declared by the current project metadata. Verify compatibility against the Python version and dependencies used in your environment.
- A SwelFlo installation is required for simulation execution.
- The Python dependencies used by the current source include NumPy, pandas, Matplotlib, Plotly, and pyXSteam.

Install the package and dependencies in editable mode from the repository root:

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

If you prefer to install dependencies separately:

```bash
python -m pip install numpy pandas matplotlib plotly pyXSteam
```

## Quick start

The examples assume you have a valid SwelFlo input model and output files. Set paths to your own files; do not use confidential well data in public examples.

### 1. Read and inspect an existing input model

```python
from pathlib import Path
from pyswelflo import SWFinput

input_file = Path(r"C:\SwelFlo\Projects\Well_A\SWFinput.txt")

model = SWFinput(str(input_file))
model.read()

print(model)
tables = model.to_dataframe()

print(tables["wellhead_conditions"])
print(tables["casing_sections"])
print(tables["feedzones"])
```

### 2. Write a working copy

```python
from pathlib import Path

output_dir = Path("work") / "Well_A_case_01"
model.write(str(output_dir))

# Writes SWFinput.txt and SWFunitsChoices.txt to output_dir.
```

### 3. Read simulation results

```python
from pathlib import Path
from pyswelflo import SWFoutput

result_file = Path(r"C:\SwelFlo\Projects\Well_A\SWFoutput001.txt")
result = SWFoutput(str(result_file))

print(result)
print(result.dataframes.keys())
print(result.dataframes["wellbore_profile"].head())

result.to_excel("Well_A_results.xlsx")
```

See the [User Manual](docs/user-manual-pyswelflo.md) and runnable-script templates in [`examples/`](examples/).

## SwelFlo execution compatibility

The current source exposes two execution methods:

- `SWFinput.run(swelflo_path, output_dir=None)` invokes the executable in silent mode using `-s -f ... -p ...`. Use only with a SwelFlo build that has been verified to support silent execution.
- `SWFinput.run_gui(swelflo_path, output_dir=None)` launches the GUI with the prepared input and returns immediately, allowing the user to run the calculation interactively.

The source comments document a known behavior in the tested environments: the older 2017 executable supports silent execution, while the newer V9.105 build can crash in silent mode and should be opened through the GUI. This is version/build-specific behavior; verify it with your own licensed installation.

## Important notes

1. **Validate before production use.** Compare PySwelFlo-generated input files and parsed outputs against the SwelFlo GUI and known benchmark cases.
2. **Keep original files.** Work on copies of `SWFinput.txt` and associated project files.
3. **Check units and field meanings.** The source stores several SwelFlo fields using compact names (for example `P`, `Q`, `H`, `X`). Confirm their meaning and unit convention against the SwelFlo input specification and your model before changing values programmatically.
4. **Engine availability.** PySwelFlo does not include `swelflo.exe`, license files, or proprietary SwelFlo assets.
5. **No guarantee of numerical validity.** PySwelFlo automates file handling and workflow orchestration; engineering review remains necessary.

## Development

Clone the repository:

```bash
git clone https://github.com/pierecnlnd/PySwelFlo.git
cd PySwelFlo
python -m pip install -e .
```

Run the examples after setting their file paths or environment variables. The examples are intentionally based on user-supplied SwelFlo files because valid input/output files are installation- and project-specific.

## License

This project is distributed under the MIT License. See [LICENSE](LICENSE).

SwelFlo is a separate product. Its name and associated software remain the property of their respective owner. This repository does not grant rights to use or redistribute SwelFlo.
