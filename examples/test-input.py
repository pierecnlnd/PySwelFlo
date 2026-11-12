"""
Inspect an existing SwelFlo input deck and write a separate working copy.

Set PYSWELFLO_INPUT to a validated SWFinput.txt file before running.
"""
import os
from pathlib import Path

from pyswelflo import SWFinput

input_path = os.environ.get("PYSWELFLO_INPUT")
if not input_path:
    raise RuntimeError("Set PYSWELFLO_INPUT to the full path of a validated SWFinput.txt")

model = SWFinput(input_path)
model.read()

print(model)
for name, frame in model.to_dataframe().items():
    print(f"\n--- {name} ---")
    print(frame.head())

# Optional: visualize the casing and feedzone positions.
figure = model.plot_casing(show_feedzone=True)
figure.show()

# Always write to a new directory; do not overwrite the source project.
output_dir = Path("work") / "input_inspection_copy"
model.write(str(output_dir))
print(f"Working copy written to: {output_dir.resolve()}")
