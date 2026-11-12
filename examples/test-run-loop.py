"""
Template for a repeated SwelFlo run workflow.

This example intentionally does not invent the physical meaning or units of
SwelFlo input fields. Confirm which WellheadCond field you intend to vary and
its units against your SwelFlo model/input specification before enabling the
parameter update below.

Set:
  PYSWELFLO_INPUT  - validated SWFinput.txt
  PYSWELFLO_EXE    - full path to swelflo.exe
  PYSWELFLO_RUN_MODE - "silent" or "gui"

Each case is written to its own folder to prevent output overwrites.
"""
import os
from pathlib import Path

from pyswelflo import SWFinput, SWFoutput

input_path = os.environ.get("PYSWELFLO_INPUT")
swelflo_exe = os.environ.get("PYSWELFLO_EXE")
run_mode = os.environ.get("PYSWELFLO_RUN_MODE", "silent").lower()

if not input_path or not swelflo_exe:
    raise RuntimeError("Set PYSWELFLO_INPUT and PYSWELFLO_EXE environment variables")

base_model = SWFinput(input_path)
base_model.read()

# EXAMPLE SENSITIVITY VALUES ONLY.
# Replace with an engineering-approved list and set the correct field name.
# The field below is deliberately left as None to prevent accidental runs.
parameter_name = None  # e.g. "P" only after confirming its meaning and units
parameter_values = []  # e.g. [value_1, value_2, value_3]

if not parameter_name or not parameter_values:
    raise RuntimeError(
        "Configure parameter_name and parameter_values after confirming the "
        "target SwelFlo field and its units. No simulation has been launched."
    )

if not base_model.wellhead_conditions:
    raise RuntimeError("The input model contains no wellhead conditions to modify")

root = Path("work") / "batch_runs"
root.mkdir(parents=True, exist_ok=True)

for case_number, value in enumerate(parameter_values, start=1):
    # Start from a fresh copy of the base model for every realization.
    model = SWFinput(input_path)
    model.read()

    model.update_wellhead_condition(0, **{parameter_name: value})

    case_dir = root / f"case_{case_number:03d}"
    model.write(str(case_dir))

    print(f"Running case {case_number}: {parameter_name}={value}")

    if run_mode == "silent":
        model.run(swelflo_path=swelflo_exe, output_dir=str(case_dir))
    elif run_mode == "gui":
        model.run_gui(swelflo_path=swelflo_exe, output_dir=str(case_dir))
        print("GUI launched. Complete the simulation in SwelFlo before parsing results.")
        continue
    else:
        raise ValueError("PYSWELFLO_RUN_MODE must be 'silent' or 'gui'")

    outputs = sorted(case_dir.glob("SWFoutput*.txt"))
    if not outputs:
        print(f"No output text file found for {case_dir}; skipping parse.")
        continue

    result = SWFoutput(str(outputs[-1]))
    result.to_excel(str(case_dir / "results.xlsx"))
    print(f"Completed: {case_dir}")
