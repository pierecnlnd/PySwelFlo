"""
Parse a SwelFlo output file and export its tables.

Set PYSWELFLO_OUTPUT to a SWFoutput###.txt file. Keep its sibling CSV files
(SWFplot###.csv and SWFoutcrv###.csv) in the same directory if available.
"""
import os
from pathlib import Path

from pyswelflo import SWFoutput

output_path = os.environ.get("PYSWELFLO_OUTPUT")
if not output_path:
    raise RuntimeError("Set PYSWELFLO_OUTPUT to the full path of SWFoutput###.txt")

result = SWFoutput(output_path)

print(result)
print("\nSections:", list(result.sections))
print("Tables:", list(result.dataframes))

for name, frame in result.dataframes.items():
    print(f"\n--- {name} ---")
    print(frame.head())

output_dir = Path("work") / "parsed_results"
output_dir.mkdir(parents=True, exist_ok=True)

result.to_excel(str(output_dir / "swelflo_results.xlsx"))

import json
with (output_dir / "swelflo_results.json").open("w", encoding="utf-8") as stream:
    json.dump(result.to_json(), stream, indent=2, default=str)

# Plot methods use the data parsed from the output file.
result.plot_output_curve()
profile_fig = result.plot_profile_value(
    column="Press (Bara)",
    title="Simulated Wellbore Pressure"
)
profile_fig.show()
