import os
import re
import json
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import pandas as pd
import numpy as np

from typing import List, Tuple, Optional
from dataclasses import dataclass, asdict
from pyXSteam.XSteam import XSteam

xst = XSteam(XSteam.UNIT_SYSTEM_MKS)

def write_json(file_path: str, initial_list: list=np.nan):
    """Create or overwrite a JSON file with a list."""
    if isinstance(initial_list, float) and np.isnan(initial_list):
        initial_list = []
    with open(file_path, "w") as json_file:
        json.dump(initial_list, json_file, indent=4)
    print(f"✅ File saved successfully: {file_path}")

def read_json(file_path: str, message: bool=True):
    """Read and return the list from a JSON file."""
    try:
        with open(file_path, "r") as json_file:
            if message:
                print(f"📂 File loaded successfully: {file_path}")
            return json.load(json_file)
    except FileNotFoundError:
        print(f"⚠️ File not found. Returning empty list: {file_path}")
        return []
    except json.JSONDecodeError:
        print(f"⚠️ Invalid JSON format. Returning empty list: {file_path}")
        return []

_PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Default SwelFlo engine. The 2017 build in swelflo_engine_old/ runs SILENTLY
# (-s -f -p) and produces output; the newer V9.105 build in swelflo_engine/
# segfaults in silent mode (see docs G3) and is only usable via its GUI. The
# project therefore defaults to the old engine for automated/silent runs, falling
# back to the V9.105 folder only if the old one is absent.
_ENGINE_OLD_DIR = os.path.join(_PROJ_ROOT, 'swelflo_engine_old')
_ENGINE_NEW_DIR = os.path.join(_PROJ_ROOT, 'swelflo_engine')
ENGINE_DIR = _ENGINE_OLD_DIR if os.path.exists(os.path.join(_ENGINE_OLD_DIR, 'swelflo.exe')) \
    else _ENGINE_NEW_DIR

# Template input path (used when SWFinput() is created with no path).
DEFAULT_FILEPATH = os.path.join(ENGINE_DIR, 'SWFinput.txt')
# Runnable engine executable.
DEFAULT_EXE = os.path.join(ENGINE_DIR, 'swelflo.exe')

# Unit selections written to SWFunitsChoices.txt next to SWFinput.txt; the engine
# reads this file from the working directory. Golden default: "2 1 2 1 1 1".
DEFAULT_UNITS_CHOICES = ['2', '1', '2', '1', '1', '1']

@dataclass
class WellheadCond:
    P: float; Q: float; T: float; H: float; Ho: float
    X: float; Xo: float; XCO2: float

    def to_dict(self): return asdict(self)

@dataclass
class CasingSection:
    ele: float; secl: float; dev: float; trued: float
    casing_choice: int; rad: float; eps: float; delz: float

    def to_dict(self): return asdict(self)
    def add_length(self, extra_length: float): self.secl += extra_length

@dataclass
class ReservoirTemperature:
    depth: float; temp: float
    def to_dict(self): return asdict(self)

@dataclass
class Feedzone:
    depth: float
    ficode: int
    pressure: float
    temperature: float
    enthalpy: float
    x: float
    xCO2: float
    values: List[float]

    def to_list(self):
        return [self.depth, self.ficode, self.pressure, self.temperature,
                self.enthalpy, self.x, self.xCO2] + self.values

    def to_dict(self):
        return {
            "depth": self.depth,
            "ficode": self.ficode,
            "pressure": self.pressure,
            "temperature": self.temperature,
            "enthalpy": self.enthalpy,
            "x": self.x,
            "xCO2": self.xCO2,
            "values": self.values
        }

class SWFinput:
    def __init__(self, filepath: Optional[str] = None):
        self.filepath = filepath or DEFAULT_FILEPATH
        self.project_dir = os.path.dirname(self.filepath)
        self.comments: List[str] = ['-','-','-']
        self.sim_params = {
            'ANS': '2',
            'VELT': '1',
            'NSIMVALS': '50',
            'WANTOUTC': '1',
            'DOUBLESIM': '0.000000',
            'GWELLFLAG': '0',
            'SIMRANOK': 'T',
            'GOTOUTC': 'T',
            'READYTOPLOT': 'T',
            'GETPROFILE': 'T',
            'ALLOWHFLO': 'F',
            'QMAXOC': '0.000000',
            'QMINOC': '0.000000',
            'NSIMOUTCPTS': '50',
            'SPACNG': '50',
            'DaltonR': '0.000000',
            'DaltonRbutton': '1',
            'HWLBT': '90000.2',
            'XCWLBT': '1.000000E-03',
            'CHFelev': '851.000'
        }
        self.data_files: List[Tuple[str, int]] = []
        self.wellhead_conditions: List[WellheadCond] = []
        self.whp_control = {'WHPTOLERANCE': 0.001, 'PMINSET': 0.0, 'PMAXSET': 0.0}
        self.length = 0.0
        self.thermal_cond = 2.0
        self.rock_density = 2800.0
        self.heat_capacity = 1000.0
        self.time = 604800.0
        self.casing_sections: List[CasingSection] = []
        self.reservoir_temps: List[ReservoirTemperature] = []
        # Raw NUPO lines as read (may have 3 columns); written back verbatim.
        self.reservoir_temps_raw: List[str] = []
        self.feedzones: List[Feedzone] = []
        # Unit selections written to SWFunitsChoices.txt (engine reads it).
        self.units_choices: List[str] = list(DEFAULT_UNITS_CHOICES)
        # Monte-Carlo / Batch trailing block, preserved verbatim across read/write
        # so the engine still parses it (gap G1). Empty for from-scratch inputs.
        self.monte_carlo_raw: List[str] = []
        self.casing_db = {
            'CASING 4"1/2 H 9.5': {'INNERDIAM': 4.0906, 'OUTERDIAM': 4.5, 'ROUGHNESS': 0.0018},
            'CASING 4"1/2 H 10.5': {'INNERDIAM': 4.0512, 'OUTERDIAM': 4.5, 'ROUGHNESS': 0.0018},
            'CASING 4"1/2 K 11.6': {'INNERDIAM': 4.0, 'OUTERDIAM': 4.5, 'ROUGHNESS': 0.0018},
            'CASING 4"1/2 N 13.5': {'INNERDIAM': 3.9213, 'OUTERDIAM': 4.5, 'ROUGHNESS': 0.0018},
            'CASING 5" K 13.0': {'INNERDIAM': 4.4921, 'OUTERDIAM': 5.0, 'ROUGHNESS': 0.0018},
            'CASING 5" K 15.0': {'INNERDIAM': 4.4094, 'OUTERDIAM': 5.0, 'ROUGHNESS': 0.0018},
            'CASING 5" N 18.0': {'INNERDIAM': 4.2756, 'OUTERDIAM': 5.0, 'ROUGHNESS': 0.0018},
            'CASING 5" N 21.4': {'INNERDIAM': 4.126, 'OUTERDIAM': 5.0, 'ROUGHNESS': 0.0018},
            'CASING 5" N 24.1': {'INNERDIAM': 4.0, 'OUTERDIAM': 5.0, 'ROUGHNESS': 0.0018},
            'CASING 5"1/2 H 14.0': {'INNERDIAM': 5.0118, 'OUTERDIAM': 5.5, 'ROUGHNESS': 0.0018},
            'CASING 5"1/2 J 15.5': {'INNERDIAM': 4.9488, 'OUTERDIAM': 5.5, 'ROUGHNESS': 0.0018},
            'CASING 5"1/2 K 17.0': {'INNERDIAM': 4.8937, 'OUTERDIAM': 5.5, 'ROUGHNESS': 0.0018},
            'CASING 5"1/2 N 20.0': {'INNERDIAM': 4.7795, 'OUTERDIAM': 5.5, 'ROUGHNESS': 0.0018},
            'CASING 5"1/2 N 23.0': {'INNERDIAM': 4.6693, 'OUTERDIAM': 5.5, 'ROUGHNESS': 0.0018},
            'CASING 6"5/8 J 20.0': {'INNERDIAM': 6.0512, 'OUTERDIAM': 6.625, 'ROUGHNESS': 0.0018},
            'CASING 6"5/8 K 24.0': {'INNERDIAM': 5.9213, 'OUTERDIAM': 6.625, 'ROUGHNESS': 0.0018},
            'CASING 6"5/8 N 28.0': {'INNERDIAM': 5.7921, 'OUTERDIAM': 6.625, 'ROUGHNESS': 0.0018},
            'CASING 6"5/8 N 32.0': {'INNERDIAM': 5.6772, 'OUTERDIAM': 6.625, 'ROUGHNESS': 0.0018},
            'CASING 7" H 17.0': {'INNERDIAM': 6.5394, 'OUTERDIAM': 7.0, 'ROUGHNESS': 0.0018},
            'CASING 7" J 20.0': {'INNERDIAM': 6.4567, 'OUTERDIAM': 7.0, 'ROUGHNESS': 0.0018},
            'CASING 7" K 23.0': {'INNERDIAM': 6.3661, 'OUTERDIAM': 7.0, 'ROUGHNESS': 0.0018},
            'CASING 7" N 26.0': {'INNERDIAM': 6.2756, 'OUTERDIAM': 7.0, 'ROUGHNESS': 0.0018},
            'CASING 7" N 29.0': {'INNERDIAM': 6.185, 'OUTERDIAM': 7.0, 'ROUGHNESS': 0.0018},
            'CASING 7" N 32.0': {'INNERDIAM': 6.0945, 'OUTERDIAM': 7.0, 'ROUGHNESS': 0.0018},
            'CASING 7" N 35.0': {'INNERDIAM': 6.0039, 'OUTERDIAM': 7.0, 'ROUGHNESS': 0.0018},
            'CASING 7" N 38.0': {'INNERDIAM': 5.9213, 'OUTERDIAM': 7.0, 'ROUGHNESS': 0.0018},
            'CASING 7"5/8 H 24.0': {'INNERDIAM': 7.0276, 'OUTERDIAM': 7.625, 'ROUGHNESS': 0.0018},
            'CASING 7"5/8 K 26.4': {'INNERDIAM': 6.9685, 'OUTERDIAM': 7.625, 'ROUGHNESS': 0.0018},
            'CASING 7"5/8 N 29.7': {'INNERDIAM': 6.878, 'OUTERDIAM': 7.625, 'ROUGHNESS': 0.0018},
            'CASING 7"5/8 N 33.7': {'INNERDIAM': 6.7677, 'OUTERDIAM': 7.625, 'ROUGHNESS': 0.0018},
            'CASING 7"5/8 N 39.0': {'INNERDIAM': 6.626, 'OUTERDIAM': 7.625, 'ROUGHNESS': 0.0018},
            'CASING 7"5/8 N 42.8': {'INNERDIAM': 6.5039, 'OUTERDIAM': 7.625, 'ROUGHNESS': 0.0018},
            'CASING 7"5/8 N 47.1': {'INNERDIAM': 6.378, 'OUTERDIAM': 7.625, 'ROUGHNESS': 0.0018},
            'CASING 8"5/8 H 28.0': {'INNERDIAM': 8.0197, 'OUTERDIAM': 8.625, 'ROUGHNESS': 0.0018},
            'CASING 8"5/8 J 24.0': {'INNERDIAM': 8.0984, 'OUTERDIAM': 8.625, 'ROUGHNESS': 0.0018},
            'CASING 8"5/8 J 32.0': {'INNERDIAM': 7.9213, 'OUTERDIAM': 8.625, 'ROUGHNESS': 0.0018},
            'CASING 8"5/8 K 36.0': {'INNERDIAM': 7.8268, 'OUTERDIAM': 8.625, 'ROUGHNESS': 0.0018},
            'CASING 8"5/8 N 40.0': {'INNERDIAM': 7.7244, 'OUTERDIAM': 8.625, 'ROUGHNESS': 0.0018},
            'CASING 8"5/8 N 44.0': {'INNERDIAM': 7.626, 'OUTERDIAM': 8.625, 'ROUGHNESS': 0.0018},
            'CASING 8"5/8 N 49.0': {'INNERDIAM': 7.5118, 'OUTERDIAM': 8.625, 'ROUGHNESS': 0.0018},
            'CASING 9"5/8 H 32.3': {'INNERDIAM': 9.0039, 'OUTERDIAM': 9.625, 'ROUGHNESS': 0.0018},
            'CASING 9"5/8 J 36.0': {'INNERDIAM': 8.9252, 'OUTERDIAM': 9.625, 'ROUGHNESS': 0.0018},
            'CASING 9"5/8 K 40.0': {'INNERDIAM': 8.8346, 'OUTERDIAM': 9.625, 'ROUGHNESS': 0.0018},
            'CASING 9"5/8 N 43.5': {'INNERDIAM': 8.7559, 'OUTERDIAM': 9.625, 'ROUGHNESS': 0.0018},
            'CASING 9"5/8 N 47.0': {'INNERDIAM': 8.6811, 'OUTERDIAM': 9.625, 'ROUGHNESS': 0.0018},
            'CASING 9"5/8 N 53.5': {'INNERDIAM': 8.5354, 'OUTERDIAM': 9.625, 'ROUGHNESS': 0.0018},
            'CASING 10"3/4 H 32.8': {'INNERDIAM': 10.189, 'OUTERDIAM': 10.75, 'ROUGHNESS': 0.0018},
            'CASING 10"3/4 J 40.5': {'INNERDIAM': 10.0472, 'OUTERDIAM': 10.75, 'ROUGHNESS': 0.0018},
            'CASING 10"3/4 K 45.5': {'INNERDIAM': 9.9488, 'OUTERDIAM': 10.75, 'ROUGHNESS': 0.0018},
            'CASING 10"3/4 N 51.0': {'INNERDIAM': 9.8465, 'OUTERDIAM': 10.75, 'ROUGHNESS': 0.0018},
            'CASING 10"3/4 N 55.5': {'INNERDIAM': 9.7598, 'OUTERDIAM': 10.75, 'ROUGHNESS': 0.0018},
            'CASING 11"3/4 H 42.0': {'INNERDIAM': 11.0827, 'OUTERDIAM': 11.75, 'ROUGHNESS': 0.0018},
            'CASING 11"3/4 J 47.0': {'INNERDIAM': 11.0, 'OUTERDIAM': 11.75, 'ROUGHNESS': 0.0018},
            'CASING 11"3/4 K 54.0': {'INNERDIAM': 10.878, 'OUTERDIAM': 11.75, 'ROUGHNESS': 0.0018},
            'CASING 11"3/4 N 60.0': {'INNERDIAM': 10.7717, 'OUTERDIAM': 11.75, 'ROUGHNESS': 0.0018},
            'CASING 13"3/8 H 48.0': {'INNERDIAM': 12.7126, 'OUTERDIAM': 13.375, 'ROUGHNESS': 0.0018},
            'CASING 13"3/8 J 54.5': {'INNERDIAM': 12.6142, 'OUTERDIAM': 13.375, 'ROUGHNESS': 0.0018},
            'CASING 13"3/8 J 61.0': {'INNERDIAM': 12.5157, 'OUTERDIAM': 13.375, 'ROUGHNESS': 0.0018},
            'CASING 13"3/8 K 68.0': {'INNERDIAM': 12.4134, 'OUTERDIAM': 13.375, 'ROUGHNESS': 0.0018},
            'CASING 13"3/8 N 72.0': {'INNERDIAM': 12.3465, 'OUTERDIAM': 13.375, 'ROUGHNESS': 0.0018},
            'CASING 16" H 65.0': {'INNERDIAM': 15.252, 'OUTERDIAM': 16.0, 'ROUGHNESS': 0.0018},
            'CASING 16" J 75.0': {'INNERDIAM': 15.122, 'OUTERDIAM': 16.0, 'ROUGHNESS': 0.0018},
            'CASING 16" K 84.0': {'INNERDIAM': 15.0118, 'OUTERDIAM': 16.0, 'ROUGHNESS': 0.0018},
            'CASING 18"5/8 J 87.5': {'INNERDIAM': 17.7559, 'OUTERDIAM': 18.625, 'ROUGHNESS': 0.0018},
            'CASING 20" J 94.0': {'INNERDIAM': 19.122, 'OUTERDIAM': 20.0, 'ROUGHNESS': 0.0018},
            'CASING 20" K106.5': {'INNERDIAM': 19.0, 'OUTERDIAM': 20.0, 'ROUGHNESS': 0.0018},
            'CASING 20" K133.0': {'INNERDIAM': 18.7283, 'OUTERDIAM': 20.0, 'ROUGHNESS': 0.0018},
            'CASINGOTHER': {'INNERDIAM': 0.0, 'OUTERDIAM': 0.0, 'ROUGHNESS': 0.0018},
            'LINER 3"1/2 J': {'INNERDIAM': 2.9213, 'OUTERDIAM': 3.5, 'ROUGHNESS': 0.0},
            'LINER 4" J': {'INNERDIAM': 3.4291, 'OUTERDIAM': 4.0, 'ROUGHNESS': 0.0},
            'LINER 4"1/2 H 9.5': {'INNERDIAM': 4.0906, 'OUTERDIAM': 4.5, 'ROUGHNESS': 0.0},
            'LINER 4"1/2 H 10.5': {'INNERDIAM': 4.0512, 'OUTERDIAM': 4.5, 'ROUGHNESS': 0.0},
            'LINER 4"1/2 K 11.6': {'INNERDIAM': 4.0, 'OUTERDIAM': 4.5, 'ROUGHNESS': 0.0},
            'LINER 4"1/2 N 13.5': {'INNERDIAM': 3.9213, 'OUTERDIAM': 4.5, 'ROUGHNESS': 0.0},
            'LINER 5" K 13.0': {'INNERDIAM': 4.4921, 'OUTERDIAM': 5.0, 'ROUGHNESS': 0.0},
            'LINER 5" K 15.0': {'INNERDIAM': 4.4094, 'OUTERDIAM': 5.0, 'ROUGHNESS': 0.0},
            'LINER 5" N 18.0': {'INNERDIAM': 4.2756, 'OUTERDIAM': 5.0, 'ROUGHNESS': 0.0},
            'LINER 5" N 21.4': {'INNERDIAM': 4.126, 'OUTERDIAM': 5.0, 'ROUGHNESS': 0.0},
            'LINER 5" N 24.1': {'INNERDIAM': 4.0, 'OUTERDIAM': 5.0, 'ROUGHNESS': 0.0},
            'LINER 5"1/2 H 14.0': {'INNERDIAM': 5.0118, 'OUTERDIAM': 5.5, 'ROUGHNESS': 0.0},
            'LINER 5"1/2 J 15.5': {'INNERDIAM': 4.9488, 'OUTERDIAM': 5.5, 'ROUGHNESS': 0.0},
            'LINER 5"1/2 K 17.0': {'INNERDIAM': 4.8937, 'OUTERDIAM': 5.5, 'ROUGHNESS': 0.0},
            'LINER 5"1/2 N 20.0': {'INNERDIAM': 4.7795, 'OUTERDIAM': 5.5, 'ROUGHNESS': 0.0},
            'LINER 5"1/2 N 23.0': {'INNERDIAM': 4.6693, 'OUTERDIAM': 5.5, 'ROUGHNESS': 0.0},
            'LINER 6"5/8 J 20.0': {'INNERDIAM': 6.0512, 'OUTERDIAM': 6.625, 'ROUGHNESS': 0.0},
            'LINER 6"5/8 K 24.0': {'INNERDIAM': 5.9213, 'OUTERDIAM': 6.625, 'ROUGHNESS': 0.0},
            'LINER 6"5/8 N 28.0': {'INNERDIAM': 6.2087, 'OUTERDIAM': 6.625, 'ROUGHNESS': 0.0},
            'LINER 6"5/8 N 32.0': {'INNERDIAM': 5.6772, 'OUTERDIAM': 6.625, 'ROUGHNESS': 0.0},
            'LINER 7" H 17.0': {'INNERDIAM': 6.5394, 'OUTERDIAM': 7.0, 'ROUGHNESS': 0.0},
            'LINER 7" J 20.0': {'INNERDIAM': 6.4567, 'OUTERDIAM': 7.0, 'ROUGHNESS': 0.0},
            'LINER 7" K 23.0': {'INNERDIAM': 6.3661, 'OUTERDIAM': 7.0, 'ROUGHNESS': 0.0},
            'LINER 7" N 26.0': {'INNERDIAM': 6.2756, 'OUTERDIAM': 7.0, 'ROUGHNESS': 0.0},
            'LINER 7" N 29.0': {'INNERDIAM': 6.185, 'OUTERDIAM': 7.0, 'ROUGHNESS': 0.0},
            'LINER 7" N 32.0': {'INNERDIAM': 6.0945, 'OUTERDIAM': 7.0, 'ROUGHNESS': 0.0},
            'LINER 7" N 35.0': {'INNERDIAM': 6.0039, 'OUTERDIAM': 7.0, 'ROUGHNESS': 0.0},
            'LINER 7" N 38.0': {'INNERDIAM': 5.9213, 'OUTERDIAM': 7.0, 'ROUGHNESS': 0.0},
            'LINER 7"5/8 H 24.0': {'INNERDIAM': 7.0276, 'OUTERDIAM': 7.625, 'ROUGHNESS': 0.0},
            'LINER 7"5/8 K 26.4': {'INNERDIAM': 6.9685, 'OUTERDIAM': 7.625, 'ROUGHNESS': 0.0},
            'LINER 7"5/8 N 29.7': {'INNERDIAM': 6.878, 'OUTERDIAM': 7.625, 'ROUGHNESS': 0.0},
            'LINER 7"5/8 N 33.7': {'INNERDIAM': 6.7677, 'OUTERDIAM': 7.625, 'ROUGHNESS': 0.0},
            'LINER 7"5/8 N 39.0': {'INNERDIAM': 6.626, 'OUTERDIAM': 7.625, 'ROUGHNESS': 0.0},
            'LINER 7"5/8 N 42.8': {'INNERDIAM': 6.5039, 'OUTERDIAM': 7.625, 'ROUGHNESS': 0.0},
            'LINER 7"5/8 N 47.1': {'INNERDIAM': 6.378, 'OUTERDIAM': 7.625, 'ROUGHNESS': 0.0},
            'LINER 8"5/8 H 28.0': {'INNERDIAM': 8.0197, 'OUTERDIAM': 8.625, 'ROUGHNESS': 0.0},
            'LINER 8"5/8 J 24.0': {'INNERDIAM': 8.0984, 'OUTERDIAM': 8.625, 'ROUGHNESS': 0.0},
            'LINER 8"5/8 J 32.0': {'INNERDIAM': 7.9213, 'OUTERDIAM': 8.625, 'ROUGHNESS': 0.0},
            'LINER 8"5/8 K 36.0': {'INNERDIAM': 7.8268, 'OUTERDIAM': 8.625, 'ROUGHNESS': 0.0},
            'LINER 8"5/8 N 40.0': {'INNERDIAM': 7.7244, 'OUTERDIAM': 8.625, 'ROUGHNESS': 0.0},
            'LINER 8"5/8 N 44.0': {'INNERDIAM': 7.626, 'OUTERDIAM': 8.625, 'ROUGHNESS': 0.0},
            'LINER 8"5/8 N 49.0': {'INNERDIAM': 7.5118, 'OUTERDIAM': 8.625, 'ROUGHNESS': 0.0},
            'LINER 9"5/8 H 32.3': {'INNERDIAM': 9.0039, 'OUTERDIAM': 9.625, 'ROUGHNESS': 0.0},
            'LINER 9"5/8 J 36.0': {'INNERDIAM': 8.9252, 'OUTERDIAM': 9.625, 'ROUGHNESS': 0.0},
            'LINER 9"5/8 K 40.0': {'INNERDIAM': 8.8346, 'OUTERDIAM': 9.625, 'ROUGHNESS': 0.0},
            'LINER 9"5/8 N 43.5': {'INNERDIAM': 8.7559, 'OUTERDIAM': 9.625, 'ROUGHNESS': 0.0},
            'LINER 9"5/8 N 47.0': {'INNERDIAM': 8.6811, 'OUTERDIAM': 9.625, 'ROUGHNESS': 0.0},
            'LINER 9"5/8 N 53.5': {'INNERDIAM': 8.5354, 'OUTERDIAM': 9.625, 'ROUGHNESS': 0.0},
            'LINER 10"3/4 H 32.8': {'INNERDIAM': 10.189, 'OUTERDIAM': 10.75, 'ROUGHNESS': 0.0},
            'LINER 10"3/4 J 40.5': {'INNERDIAM': 10.0472, 'OUTERDIAM': 10.75, 'ROUGHNESS': 0.0},
            'LINER 10"3/4 K 45.5': {'INNERDIAM': 9.9488, 'OUTERDIAM': 10.75, 'ROUGHNESS': 0.0},
            'LINER 10"3/4 N 51.0': {'INNERDIAM': 9.8465, 'OUTERDIAM': 10.75, 'ROUGHNESS': 0.0},
            'LINER 10"3/4 N 55.5': {'INNERDIAM': 9.7598, 'OUTERDIAM': 10.75, 'ROUGHNESS': 0.0},
            'LINER 11"3/4 H 42.0': {'INNERDIAM': 11.0827, 'OUTERDIAM': 11.75, 'ROUGHNESS': 0.0},
            'LINER 11"3/4 J 47.0': {'INNERDIAM': 11.0, 'OUTERDIAM': 11.75, 'ROUGHNESS': 0.0},
            'LINER 11"3/4 K 54.0': {'INNERDIAM': 10.878, 'OUTERDIAM': 11.75, 'ROUGHNESS': 0.0},
            'LINER 11"3/4 N 60.0': {'INNERDIAM': 10.7717, 'OUTERDIAM': 11.75, 'ROUGHNESS': 0.0},
            'LINER 13"3/8 H 48.0': {'INNERDIAM': 12.7126, 'OUTERDIAM': 13.375, 'ROUGHNESS': 0.0},
            'LINER 13"3/8 J 54.5': {'INNERDIAM': 12.6142, 'OUTERDIAM': 13.375, 'ROUGHNESS': 0.0},
            'LINER 13"3/8 J 61.0': {'INNERDIAM': 12.5157, 'OUTERDIAM': 13.375, 'ROUGHNESS': 0.0},
            'LINER 13"3/8 K 68.0': {'INNERDIAM': 12.4134, 'OUTERDIAM': 13.375, 'ROUGHNESS': 0.0},
            'LINER 13"3/8 N 72.0': {'INNERDIAM': 12.3465, 'OUTERDIAM': 13.375, 'ROUGHNESS': 0.0},
            'LINER 16" H 65.0': {'INNERDIAM': 15.252, 'OUTERDIAM': 16.0, 'ROUGHNESS': 0.0},
            'LINER 16" J 75.0': {'INNERDIAM': 15.122, 'OUTERDIAM': 16.0, 'ROUGHNESS': 0.0},
            'LINER 16" K 84.0': {'INNERDIAM': 15.0118, 'OUTERDIAM': 16.0, 'ROUGHNESS': 0.0},
            'LINER 18"5/8 J 87.5': {'INNERDIAM': 17.7559, 'OUTERDIAM': 18.625, 'ROUGHNESS': 0.0},
            'LINER OTHER': {'INNERDIAM': 0.0, 'OUTERDIAM': 0.0, 'ROUGHNESS': 0.0},
            'OPEN HOLE': {'INNERDIAM': 0.0, 'OUTERDIAM': 0.0, 'ROUGHNESS': 0.0018}}

    def calc_length(self):
        l = 0
        for i in range(len(self.casing_sections)):
            l += self.casing_sections[i].secl
        self.length = l

    def read(self):
        with open(self.filepath, 'r') as f:
            lines = [line for line in f]
            # lines = [line.rstrip() for line in f if line.strip()]
        idx = 0
        self.comments = lines[0:3]; idx = 3

        sim_line = lines[idx].split(); idx += 1
        keys = [
            'ANS','VELT','NSIMVALS','WANTOUTC','DOUBLESIM','GWELLFLAG',
            'SIMRANOK','GOTOUTC','READYTOPLOT','GETPROFILE','ALLOWHFLO',
            'QMAXOC','QMINOC','NSIMOUTCPTS','SPACNG','DaltonR','DaltonRbutton',
            'HWLBT','XCWLBT','CHFelev']
        self.sim_params = dict(zip(keys, sim_line))

        ndataf = int(lines[idx]); idx += 1
        for _ in range(ndataf):
            path, typ = lines[idx].rsplit(' ', 1)
            self.data_files.append((path.strip('\"'), int(typ)))
            idx += 1

        notops = int(lines[idx]); idx += 1
        for _ in range(notops):
            vals = list(map(float, lines[idx].split()))
            self.wellhead_conditions.append(WellheadCond(*vals))
            idx += 1

        self.whp_control = dict(zip(['WHPTOLERANCE','PMINSET','PMAXSET'], map(float, lines[idx].split()))); idx += 1
        self.length = float(lines[idx]); idx += 1
        self.thermal_cond = float(lines[idx]); idx += 1
        self.rock_density = float(lines[idx]); idx += 1
        self.heat_capacity = float(lines[idx]); idx += 1
        self.time = float(lines[idx]); idx += 1

        nusec = int(lines[idx]); idx += 1
        for _ in range(nusec):
            parts = lines[idx].split()
            self.casing_sections.append(CasingSection(
                float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3]),
                int(parts[4]), float(parts[5]), float(parts[6]), float(parts[7])
            ))
            idx += 1

        nupo = int(lines[idx]); idx += 1
        for _ in range(nupo):
            toks = lines[idx].split()
            try:
                # Spec format is "DEPTH TEMP"; some files carry a leading index
                # column. Take the last two floats either way.
                depth, temp = float(toks[-2]), float(toks[-1])
                self.reservoir_temps.append(ReservoirTemperature(depth, temp))
            except (ValueError, IndexError):
                pass
            # Keep the raw line: GUI-written files carry 3 columns here and the
            # engine CRASHES in silent mode if the row is rewritten with only
            # 2 (verified on LHD-8, 2026-08-05). write() re-emits these
            # verbatim unless the parsed list was modified programmatically.
            self.reservoir_temps_raw.append(lines[idx].rstrip('\n'))
            idx += 1

        nufeed = int(lines[idx]); idx += 1
        for _ in range(nufeed):
            parts = list(map(float, lines[idx].split()))
            self.feedzones.append(Feedzone(parts[0], int(parts[1]), parts[2], parts[3], parts[4], parts[5], parts[6], parts[7:]))
            idx += 1

        # Everything after the feedzone block is the Monte-Carlo / Batch trailing
        # section. Preserve it verbatim so write() can reproduce it (gap G1).
        self.monte_carlo_raw = [ln.rstrip('\n') for ln in lines[idx:]]

        # Pick up unit selections from a sibling SWFunitsChoices.txt if present.
        units_path = os.path.join(os.path.dirname(os.path.abspath(self.filepath)),
                                  'SWFunitsChoices.txt')
        if os.path.exists(units_path):
            with open(units_path, 'r') as uf:
                toks = uf.read().split()
            if toks:
                self.units_choices = toks

    def add_wellhead_condition(self, P: float, Q: float, T: float, H: float, Ho: float, X: float, Xo: float, XCO2: float):
        self.wellhead_conditions.append(WellheadCond(P, Q, T, H, Ho, X, Xo, XCO2))

    def update_wellhead_condition(self, index: int, **kwargs):
        if 0 <= index < len(self.wellhead_conditions):
            whc = self.wellhead_conditions[index]
            for key, value in kwargs.items():
                if hasattr(whc, key):
                    setattr(whc, key, value)

    def add_casing_section(self, ele: float, secl: float, dev: float, trued: float, casing_choice: int, rad: float, eps: float, delz: float):
        self.casing_sections.append(CasingSection(ele, secl, dev, trued, casing_choice, rad, eps, delz))

    def update_casing_section(self, index: int, **kwargs):
        if 0 <= index < len(self.casing_sections):
            csg = self.casing_sections[index]
            for key, value in kwargs.items():
                if hasattr(csg, key):
                    setattr(csg, key, value)
    
    def add_reservoir_temp(self, depth: float, temp: float):
        self.reservoir_temps.append(ReservoirTemperature(depth, temp))

    def update_reservoir_temp(self, index: int, **kwargs):
        if 0 <= index < len(self.reservoir_temps):
            csg = self.reservoir_temps[index]
            for key, value in kwargs.items():
                if hasattr(csg, key):
                    setattr(csg, key, value)

    def add_feedzone(self, depth: float, ficode: int, pressure: float, temperature: float, enthalpy: float, x: float, xCO2: float, values: List[float]):
        if depth > self.length:
            raise ValueError(f"Feedzone depth {depth} exceeds well length {self.length}")
        self.feedzones.append(Feedzone(depth, ficode, pressure, temperature, enthalpy, x, xCO2, values))

    def update_feedzone(self, index: int, **kwargs):
        if 0 <= index < len(self.feedzones):
            fz = self.feedzones[index]
            for key, value in kwargs.items():
                if hasattr(fz, key):
                    setattr(fz, key, value)
            if hasattr(fz, 'depth') and fz.depth > self.length:
                raise ValueError(f"Feedzone depth {fz.depth} exceeds well length {self.length}")

    def write(self, output_dir: str):
        os.makedirs(output_dir, exist_ok=True)
        self.project_dir = output_dir
        output_file = os.path.join(output_dir, "SWFinput.txt")

        def format_chars(number, n):
            if number <= -1 or number >= 1 or number == 0:
                s = str(number)
                if '.' in s:
                    int_part, dec_part = s.split('.')
                else:
                    int_part = s
                    dec_part = ''
                formatted = f"{int_part}.{dec_part}"
                formatted = formatted[:n].ljust(n, '0')
            else:
                s = str(number).lower()
                
                if 'e' in s:
                    front_part, back_part = s.split('e-')
                    formatted = format_chars(float(front_part), n-5)
                    formatted = formatted+'E-'+back_part[:3].rjust(3, '0')
                else:
                    s = f'{number:.5e}'
                    front_part, back_part = s.split('e-')
                    formatted = format_chars(float(front_part), n-5)
                    formatted = formatted+'E-'+back_part[:3].rjust(3, '0')
            
            return formatted

        def format_positive_scientific(number, n):
            s = f'{number:.5e}'
            front_part, back_part = s.split('e+')
            formatted = format_chars(float(front_part), n-5)
            formatted = formatted+'E+'+back_part[:3].rjust(3, '0')

            return formatted

        def format_value(val):
            if isinstance(val, int):
                return f"{val:<16f}"
            elif isinstance(val, float):
                if abs(val) != 0 and (abs(val) < 1e-3 or abs(val) > 9999):
                    return f"{val: .15E}".replace("e", "E")
                else:
                    return f"{val: .15f}"
            return str(val)

        def format_line_v2(values):
            s = ''
            for i, v in enumerate(values):
                if i == 0:
                    s += v
                else:
                    if v[0] == '-':
                        s += ' '+v
                    else:
                        s += '  '+v 
            # return '   ' + '  '.join(format_value(v) for v in values) + '\n'
            return '   ' + s + '\n'

        def format_line(values):
            return '   ' + '  '.join(format_value(v) for v in values) + '\n'

        with open(output_file, 'w') as f:
            for _ in self.comments:
                # comments read from a file keep their trailing newline; strip it
                # so we don't emit a blank line after each comment.
                f.write(_.rstrip('\n') + '\n')
            f.write('   '+' '.join(self.sim_params.values()) + '\n')
            f.write(f"   {len(self.data_files)}\n")
            for path, typ in self.data_files:
                path = path.replace('"','')
                f.write(f' "{path}"  {typ}\n')
            f.write(f"   {len(self.wellhead_conditions)}\n")
            for cond in self.wellhead_conditions:
                cond_values = [format_chars(_, 17) if _ <= -1 or _ >= 1 or _ == 0 else format_chars(_, 22) for _ in cond.to_dict().values()]
                f.write(format_line_v2(cond_values))
            whp_control_values = [format_chars(_, 17) if _ <= -1 or _ >= 1 or _ == 0 else format_chars(_, 22) for _ in self.whp_control.values()]
            f.write(format_line_v2(whp_control_values))
            f.write(f'   {format_chars(self.length, 16)}' + '\n')
            f.write(f'   {format_chars(self.thermal_cond, 16)}' + '\n')
            f.write(f'   {format_chars(self.rock_density, 16)}' + '\n')
            f.write(f'   {format_chars(self.heat_capacity, 16)}' + '\n')
            f.write(f'   {format_chars(self.time, 16)}' + '\n')
            f.write(f"   {len(self.casing_sections)}\n")
            casing_section_list = []
            for sec in self.casing_sections:
                sec_values = sec.to_dict().values()
                s = '  '
                for i, val in enumerate(sec_values):
                    if i == 0:
                        if val < 0:
                            s += format_chars(val, 9) + '        '
                        else:
                            s += ' '+format_chars(val, 8) + '        '
                    if i == 1:
                        s += format_chars(val, 8) + '       '
                    if i == 2:
                        s += format_positive_scientific(val, 14) + '    '
                    if i == 3:
                        s += format_chars(val, 8)
                    if i == 4:
                        s += f'{val:>10d}' + '   '
                    if i == 5:
                        s += format_chars(val, 13) + '   '
                    if i == 6:
                        s += format_chars(val, 13) + '    '
                    if i == 7:
                        s += format_chars(val, 8)
                casing_section_list.append(s)
            f.write('\n'.join(casing_section_list)+'\n')
            # Reservoir temperatures (NUPO). GUI-written files carry 3 columns
            # per row and the engine crashes in silent mode on a 2-column
            # rewrite (verified on LHD-8, 2026-08-05) — so re-emit the raw
            # lines verbatim when they are still in sync with the parsed list;
            # fall back to "DEPTH TEMP" only for programmatically-built inputs.
            f.write(f"   {len(self.reservoir_temps)}\n")
            if len(self.reservoir_temps_raw) == len(self.reservoir_temps):
                for ln in self.reservoir_temps_raw:
                    f.write(ln + '\n')
            else:
                for t in self.reservoir_temps:
                    f.write(f'   {format_chars(t.depth, 16)}  {format_chars(t.temp, 16)}\n')
            f.write(f"   {len(self.feedzones)}\n")
            fz_list = []
            for fz in self.feedzones:
                fz_values = fz.to_list()
                s = '   '
                for i, val in enumerate(fz_values):
                    if i == 0:
                        s += format_chars(val, 16)
                    elif i == 1:
                        s += f'{val:>3d}' + '  '
                    else:
                        s += format_chars(val, 16) + '  '
                fz_list.append(s)
            f.write('\n'.join(fz_list)+'\n')
            # Monte-Carlo / Batch trailing block (gap G1): reproduce verbatim what
            # read() captured so the engine still parses the whole file.
            for ln in self.monte_carlo_raw:
                f.write(ln + '\n')

        # The engine reads unit selections from SWFunitsChoices.txt in the same
        # directory (gap G4).
        self.write_units(output_dir)

    def write_units(self, output_dir: str):
        """Write SWFunitsChoices.txt (6 integer unit selections) next to the input."""
        os.makedirs(output_dir, exist_ok=True)
        with open(os.path.join(output_dir, "SWFunitsChoices.txt"), 'w') as f:
            f.write(' '.join(str(u) for u in self.units_choices) + '\n')

    def to_dict(self):
        return {
            "comments": self.comments,
            "sim_params": self.sim_params,
            "data_files": self.data_files,
            "wellhead_conditions": [w.to_dict() for w in self.wellhead_conditions],
            "whp_control": self.whp_control,
            "length": self.length,
            "thermal_cond": self.thermal_cond,
            "rock_density": self.rock_density,
            "heat_capacity": self.heat_capacity,
            "time": self.time,
            "casing_sections": [c.to_dict() for c in self.casing_sections],
            "reservoir_temps": [r.to_dict() for r in self.reservoir_temps],
            "feedzones": [f.to_dict() for f in self.feedzones],
        }

    def to_dataframe(self):
        return {
            "wellhead_conditions": pd.DataFrame([w.to_dict() for w in self.wellhead_conditions]),
            "casing_sections": pd.DataFrame([c.to_dict() for c in self.casing_sections]),
            "reservoir_temps": pd.DataFrame([r.to_dict() for r in self.reservoir_temps]),
            "feedzones": pd.DataFrame([f.to_dict() for f in self.feedzones]),
        }

    def __str__(self):
        return f"SWFinput: {self.comments[0]} with {len(self.data_files)} data files, {len(self.casing_sections)} casing sections"

    def __repr__(self):
        return f"<SWFinput file='{self.filepath}' project_dir='{self.project_dir}' with {len(self.casing_sections)} casing sections>"

    def plot_casing(self, max_x=0.0, normalize=False, scale=1.0, fig=None, title='Casing', show_feedzone=False):
        if fig is None:
            fig = go.Figure()
            fig.update_layout(
                title=dict(
                    text=f"<b>{title}</b>",
                    # pad=dict(t=10),
                    x=0.5,
                    y=0.97,
                    font=dict(size=14, color="black", family="Arial Black", weight="bold")
                ),
                xaxis=dict(
                    title=dict(
                        text="Radius (inch)",
                        font=dict(size=12, color="red", family="Arial", weight="bold"),
                        standoff=0
                    ),
                    tickfont=dict(size=10, color="red", family="Arial"),
                    ticks="outside",
                    ticklen=1,
                    range=[max_x-15*4.5, max_x+15*4.5],
                    side="top",
                    showgrid=True,
                    gridcolor="lightgray",
                    gridwidth=1,
                    griddash="dash"
                ),
                yaxis=dict(
                    title=dict(
                        text='Depth (mMD)',
                        font=dict(size=12, color="black", family="Arial", weight="bold"),
                        standoff=5
                    ),
                    tickfont=dict(size=10, color="black", family="Arial"),
                    ticks="outside",
                    ticklen=5,
                    autorange="reversed",
                    showgrid=True,
                    gridcolor="lightgray",
                    gridwidth=1,
                    griddash="dash",
                    # range=[0,1300]
                ),
                legend=dict(
                    title=dict(
                        text="Legend:",
                        font=dict(size=12, color="black", family="Arial", weight="bold"),
                        side="top"
                    ),
                    font=dict(size=10, color="black", family="Arial Narrow"),
                    x=0.55,
                    y=-0.155,
                    xanchor="center",
                    yanchor="top",
                    orientation="h",
                    traceorder="normal",
                    tracegroupgap=0.5,
                    bordercolor="gray",
                    borderwidth=1,
                    itemwidth=30,  # 👈 Controls the width of each legend item to help force line breaks
                ),
                height=850,   #fig, ax1 = plt.subplots(figsize=(8.27, 11.69)
                width=550,
                # height=11.69*81,
                template="plotly_white",
                # margin=dict(l=5, r=5, t=100, b=50),
                paper_bgcolor="white",
                plot_bgcolor="white",
                shapes=[
                    dict(
                        type="rect",
                        xref="paper",
                        yref="paper",
                        x0=0,
                        y0=0,
                        x1=1,
                        y1=1,
                        line=dict(color="grey", width=0.5)
                    )
                ]
            )
        
        y_shoe_value = 10
        x_shoe_value = 2
        center = max_x
        depth = 0.0

        max_rad = -9999
        for i in range(len(self.casing_sections)):
            if self.casing_sections[i].rad/0.0254 > max_rad:
                max_rad = self.casing_sections[i].rad/0.0254

        for i in range(len(self.casing_sections)):
            casing_section = self.casing_sections[i]
            left_loc = center - casing_section.rad/0.0254
            right_loc = center + casing_section.rad/0.0254
            if normalize:
                left_loc = center - casing_section.rad/0.0254/max_rad*scale
                right_loc = center + casing_section.rad/0.0254/max_rad*scale
            start = depth
            end = depth + casing_section.secl
            if casing_section.eps == 0:
                style = 'dash'
                color = 'gray'
                bg_color = 'aliceblue'
                casing_type = 'Liner'
            else:
                style = 'solid'
                color = 'black'
                bg_color = 'lightskyblue'
                casing_type = 'Casing' 
            casing_size = f'{2*casing_section.rad/0.0254:.2f}"'
            # Add fill
            fig.add_trace(
                go.Scatter(
                    x=[left_loc, right_loc, right_loc, left_loc],
                    y=[start, start, end, end],
                    fill="toself",
                    fillcolor=bg_color,
                    line=dict(width=0),  # No border line
                    mode="none",
                    showlegend=False
                )
            )
            # Add left boundary
            fig.add_trace(go.Scatter(
                x=[left_loc, left_loc], y=[start, end],
                mode='lines',
                line=dict(color=color, dash=style, width=1.5),
                name=f"{casing_type} - {casing_size}",
                showlegend=False, xaxis="x"
            ))
            # Add right boundary
            fig.add_trace(go.Scatter(
                x=[right_loc, right_loc], y=[start, end],
                mode='lines',
                line=dict(color=color, dash=style, width=1.5),
                showlegend=False, xaxis="x"
            ))
            # Draw left shoe (triangle)
            fig.add_trace(go.Scatter(
                x=[left_loc, left_loc - x_shoe_value, left_loc],
                y=[end, end, end + y_shoe_value * -1],
                fill='toself', mode='lines',
                line=dict(color=color, width=1),
                fillcolor=color,
                showlegend=False, xaxis="x"
            ))
            # Draw right shoe (triangle)
            fig.add_trace(go.Scatter(
                x=[right_loc, right_loc + x_shoe_value, right_loc],
                y=[end, end, end + y_shoe_value * -1],
                fill='toself', mode='lines',
                line=dict(color=color, width=1),
                fillcolor=color,
                showlegend=False, xaxis="x"
            ))
            # Add casing label in the middle
            fig.add_trace(go.Scatter(
                x=[center], y=[(start + end) / 2],
                mode="text", text=[casing_size],
                textposition="middle center",
                textfont=dict(size=8, color="black", family="Arial Black"),
                showlegend=False, xaxis="x"
            ))

            depth = end
        
        if show_feedzone:
            for i in range(len(self.feedzones)):
                feedzone = self.feedzones[i]
                fig.add_trace(go.Scatter(
                    x=[center],
                    y=[feedzone.depth],
                    mode='lines+markers',
                    marker=dict(
                        symbol='triangle-up',
                        color='red',
                        size=8,
                        line=dict(width=1, color='red'),
                    ),
                    line=dict(color='red', width=5, dash='solid'),
                    opacity=0.5,
                    name=f'FZ #{i+1}',
                    showlegend=False,
                ))
        
        return fig

    def run(self, swelflo_path: str, output_dir: Optional[str] = None):
        """
        Run SwelFlo silently/head-less on this model's SWFinput.txt.

        CLI contract:  swelflo.exe -s -f <SWFinput.txt> -p <output_dir>
        (-s = silent, -f = input file, -p = output/project path). A
        SWFunitsChoices.txt is written next to the input because the engine reads
        unit selections from the working directory.

        Use the 2017 engine (``swelflo_engine_old/swelflo.exe``, the default
        ``DEFAULT_EXE``) for this — it runs silently and writes output. The newer
        V9.105 build (``swelflo_engine/``) SEGFAULTS in silent mode (verified
        2026-06-24, even on its own template), so against that build this method
        detects the failure and raises an actionable error telling the caller to
        use the GUI instead (see run_gui() / docs gap G3).

        Parameters:
            swelflo_path (str): Full path to swelflo.exe.
            output_dir (str, optional): Working/output directory. Defaults to the
                directory the input was last written to (self.project_dir).
        """
        import subprocess

        target_dir = os.path.abspath(output_dir) if output_dir else os.path.abspath(self.project_dir)
        input_file = os.path.join(target_dir, "SWFinput.txt")
        # Ensure the engine finds its unit selections alongside the input.
        self.write_units(target_dir)

        before = {f for f in os.listdir(target_dir) if f.startswith('SWFoutput')} \
            if os.path.isdir(target_dir) else set()

        command = f'"{swelflo_path}" -s -f "{input_file}" -p "{target_dir}"'
        result = subprocess.run(command, shell=True, capture_output=True, text=True)

        after = {f for f in os.listdir(target_dir) if f.startswith('SWFoutput')} \
            if os.path.isdir(target_dir) else set()
        produced_output = bool(after - before)
        crashed = result.returncode != 0 or 'SIGSEGV' in (result.stderr or '') \
            or 'Segmentation' in (result.stderr or '')

        if not produced_output or crashed:
            # Silent mode (-s) segfaults in this V9.105 build; it cannot run
            # head-less. Guide the caller to the GUI (use run_gui() for that).
            detail = f"\n\nEngine output:\n{result.stderr.strip()}" if result.stderr else ""
            raise RuntimeError(
                "SwelFlo could not run head-less: silent mode (-s) crashes in this "
                "V9.105 engine build (no simulation output was produced).\n\n"
                "Run the model through the SwelFlo GUI instead:\n"
                f"  1. SwelFlo opens with this model loaded from:\n       {target_dir}\n"
                "  2. Press RUN in the GUI.\n"
                "  3. Come back to the Calibration tab and load the result.\n"
                "(Use the 'Open in SwelFlo (GUI)' button, which does step 1 for you.)"
                + detail
            )
        return result.stdout

    def run_gui(self, swelflo_path: str, output_dir: Optional[str] = None):
        """Launch the SwelFlo GUI with this model pre-loaded, then return immediately.

        This is the reliable path for V9.105: it uses ``-f <input> -p <output_dir>``
        *without* ``-s`` (silent mode segfaults — see run()). The engine reads the
        input, then opens its window so the user can press RUN; outputs are written
        to ``output_dir``. Non-blocking: the dashboard stays responsive.
        """
        import subprocess

        target_dir = os.path.abspath(output_dir) if output_dir else os.path.abspath(self.project_dir)
        input_file = os.path.join(target_dir, "SWFinput.txt")
        self.write_units(target_dir)
        command = f'"{swelflo_path}" -f "{input_file}" -p "{target_dir}"'
        # Popen, not run(): do not wait for the GUI to be closed.
        subprocess.Popen(command, shell=True)
        return command

class SWFoutput:
    def __init__(self, filename):
        self.filename = filename
        if not os.path.exists(filename):
            raise FileNotFoundError(f"File '{filename}' not found.")

        with open(filename, 'r') as file:
            self.content = file.read()

        if len(self.content.strip()) == 0:
            raise ValueError("The provided SwelFlo result file is empty.")

        self.sections = {}
        self.dataframes = {}

        self._extract_all()

    def __repr__(self):
        return f"SWFoutput(filename='{self.filename}')\nSections extracted: {list(self.sections.keys())}"

    def __str__(self):
        return (
            f"SwelFlo Simulation Result Summary:\n"
            f"- File: {os.path.basename(self.filename)}\n"
            f"- Sections: {len(self.sections)} parsed\n"
            f"- Available data tables: {list(self.dataframes.keys())}"
        )

    def _extract_all(self):
        self.sections['setup_summary'] = self._extract_setup_summary()
        self.sections['downhole_profile'] = self._extract_downhole_profile()
        self.dataframes['casing_geometry'] = self._extract_casing_geometry()
        # self.dataframes['feedpoints'] = self._extract_feedpoint_info()

        blocks = self._extract_all_wellhead_condition_blocks()
        self.dataframes['all_wellhead_blocks'] = blocks
        self.dataframes['wellhead_info_summary'] = self._extract_wellhead_info_from_blocks(blocks)
        self.dataframes['feedzone_results'] = self._extract_feedzone_result_table_per_block(blocks)
        self.dataframes['wellbore_profile'] = self._extract_wellbore_profile_table()
        self.sections['summary_stats'] = self._generate_summary_stats()
        self._load_sibling_csvs()

    def _load_sibling_csvs(self):
        """Load SWFplot###.csv / SWFoutcrv###.csv that sit next to this output file.

        The engine writes clean CSVs alongside SWFoutput###.txt (gap G5); they are
        far more robust to parse than the text profile table.
        """
        d = os.path.dirname(os.path.abspath(self.filename))
        base = os.path.basename(self.filename)
        m = re.search(r'(\d{3})', base)
        num = m.group(1) if m else None
        for key, prefix, reader in (
            ('plot_profile', 'SWFplot', self.read_plot_csv),
            ('output_curve', 'SWFoutcrv', self.read_outcrv_csv),
        ):
            path = os.path.join(d, f"{prefix}{num}.csv") if num else None
            if not path or not os.path.exists(path):
                # fall back to any matching CSV in the directory
                cand = [f for f in os.listdir(d) if f.startswith(prefix) and f.endswith('.csv')]
                path = os.path.join(d, sorted(cand)[-1]) if cand else None
            if path and os.path.exists(path):
                try:
                    self.dataframes[key] = reader(path)
                except Exception:
                    self.dataframes[key] = pd.DataFrame()

    @staticmethod
    def _read_swf_csv(path):
        """Parse a SwelFlo CSV: quoted header row, then numeric rows; ignore any
        trailing non-numeric description lines the engine appends."""
        rows = []
        with open(path, 'r') as f:
            header = f.readline()
            cols = [c.strip().strip('"').strip() for c in header.split(',')]
            ncol = len(cols)
            for line in f:
                parts = [p.strip() for p in line.split(',')]
                if len(parts) < ncol:
                    continue
                try:
                    rows.append([float(p) for p in parts[:ncol]])
                except ValueError:
                    continue
        return pd.DataFrame(rows, columns=cols)

    @staticmethod
    def read_plot_csv(path):
        """SWFplot###.csv -> Depth (mMU), P SIM (bara), T SIM (deg C), V SIM."""
        return SWFoutput._read_swf_csv(path)

    @staticmethod
    def read_outcrv_csv(path):
        """SWFoutcrv###.csv -> Sim Flow (kg/s), WHP (Bara), Sim flowing Enth (kJ/kg)."""
        return SWFoutput._read_swf_csv(path)

    def _extract_setup_summary(self):
        match = re.search(r"SETUP SUMMARY:\s*-+\s*(.*?)\n\s*Orkiszewski correlation", self.content, re.DOTALL)
        return match.group(1).strip() if match else None

    def _extract_downhole_profile(self):
        match = re.search(r"Downhole Profile Information\s*-+\s*(.*?)\n\s*PRODUCTION simulation", self.content, re.DOTALL)
        return match.group(1).strip() if match else None

    def _extract_casing_geometry(self):
        pattern = r"Casing Geometry:\s*-+\s*CHF elevation:\s*(.*?)\n\s*Elevation \(mASL\).*?\n(.*?)(?:\n\s*-{2,}|\Z)"
        match = re.search(pattern, self.content, re.DOTALL)
        if not match:
            return pd.DataFrame()

        rows = [line.split() for line in match.group(2).strip().splitlines() if line.strip()]
        columns = [
            "Elevation (mASL)", "Section length (m)", "Angle (deg)",
            "Vert extent (m)", "Vertical d to end (m)", "Length to end (m)",
            "Casing choice", "Radius (m)", "Roughness (m)", "Subdivision size (m)"
        ]
        df = pd.DataFrame(rows, columns=columns).apply(pd.to_numeric, errors='coerce')
        df['CHF elevation'] = float(match.group(1))
        return df

    def _extract_feedpoint_info(self):
        pattern = r"Feedpoint information:\s*-+\s*Information was provided for.*?feed points\.(.*?)(?:\n\n|\n#|\Z)"
        match = re.search(pattern, self.content, re.DOTALL)
        if not match:
            return pd.DataFrame()

        data = re.findall(r"^\s*(\d+\.\d+.*?)$", match.group(1), re.MULTILINE)
        rows = [re.split(r"\s+", row) for row in data if row.strip()]
        columns = [
            "Depth (m MD)", "Type No.", "Reservoir P (Bara)", "Reservoir T (deg C)",
            "Reservoir H(kJ/kg)", "Reservoir X", "XCO2", "Feed flowrate (kg/s)"
        ]
        return pd.DataFrame(rows, columns=columns).apply(pd.to_numeric, errors='coerce')

    def _extract_all_wellhead_condition_blocks(self):
        pattern = r"(?<=\n)#\s+Wellhead pressure \(Bara\).*?(?=\n#\*{5,}|\Z)"
        blocks = re.findall(pattern, self.content, re.DOTALL)
        return {f"Block_{i+1}": blk.strip() for i, blk in enumerate(blocks)}

    def _extract_wellhead_info_from_blocks(self, blocks):
        patterns = {
            "Wellhead Pressure (Bara)": r"Wellhead pressure \(Bara\)\s*:\s*([\d.]+)",
            "Wellhead Temperature (°C)": r"Wellhead temperature \(oC\)\s*:\s*([\d.]+)",
            "Wellhead Flowing Steam Mass Fraction": r"Wellhead flowing steam mass fraction\s*:\s*([\d.]+)",
            "Static Dryness": r"Static dryness\s*:\s*([\d.]+)",
            "Wellhead Flowing Enthalpy (kJ/kg)": r"Wellhead flowing enthalpy \(kJ/kg\)\s*:\s*([\d.E+]+)",
            "Static Enthalpy (kJ/kg)": r"Static enthalpy\s*:\s*([\d.E+]+)",
            "Wellhead Total Flow (kg/s)": r"Wellhead total flow \(kg/s\)\s*:\s*([\d.]+)",
            "Flash Depth (m MD)": r"Flash depth\s*:\s*([\d.]+) m MD",
            "Wellhead CO2 Total Mass Fraction": r"Wellhead CO2 total mass fraction\s*:\s*([\d.]+)",
            "Wellhead CO2 Fraction in Liquid": r"Wellhead CO2 fraction in liquid\s*:\s*([\d.]+)"
        }
        rows = []
        for block in blocks.values():
            row = {k: float(re.search(p, block).group(1)) if re.search(p, block) else None for k, p in patterns.items()}
            rows.append(row)
        return pd.DataFrame(rows)

    def _extract_feedzone_result_table_per_block(self, blocks):
        all_rows = []
        for i, block in enumerate(blocks.values(), 1):
            lines = block.splitlines()
            start_index = next((idx for idx, line in enumerate(lines) if "Feed no." in line), -1)
            if start_index == -1:
                continue
            for line in lines[start_index + 2:]:
                clean_line = line.strip().lstrip("#").strip()
                if not clean_line or re.match(r"^-{5,}", clean_line):
                    continue
                if re.match(r"^\d", clean_line):
                    row = re.split(r"\s+", clean_line)
                    if len(row) >= 14:
                        all_rows.append([i] + row[:14])

        columns = [
            "Condition Block", "Feed no.", "Depth (m MD)", "Vert Depth (m)", "Flow (kg/s)", "Flowing H(kJ/kg)",
            "Res.T (oC)", "Res.P (Bara)", "Well P (Bara)", "Sat.", "P1 (kg/s/MPa)",
            "Prod.Ind.(m3)", "Forcheimer A", "Av.Vis.(m2/s)", "XCO2"
        ]
        return pd.DataFrame(all_rows, columns=columns).apply(pd.to_numeric, errors='coerce')

    def _extract_wellbore_profile_table(self):
        match = re.search(r"Depth\(m MD\).*?Mass Flo\(kg/s\).*?\n(.*?)\n#\*+", self.content, re.DOTALL)
        if not match:
            return pd.DataFrame()

        raw_rows = [re.split(r"\s+", line.strip()) for line in match.group(1).splitlines()
                    if line.strip() and len(line.split()) >= 20]
        # V9.105 added a trailing reservoir-temperature column "Tres" after the
        # "Choked?" column (gap G6). "Choked?" is blank when the well is not choked,
        # so a normal row has 21 tokens (Tres last) and a choked row has 22. The
        # first 20 columns (Depth..Psat) are always present; parse Choked?/Tres
        # from the right so Tres never lands in the wrong column.
        columns = [
            "Depth (m MD)", "Vert.Depth(m)", "Elevation(mASL)", "Press (Bara)", "Temp(oC)",
            "Flowing X", "Hliq(kJ/kg)", "Hvap(kJ/kg)", "V liq(m/s)", "V vap(m/s)",
            "Dw(kg/m3)", "Ds (kg/m3)", "Static H(kJ/kg)", "Rad (m)", "Regime", "XCO2",
            "Mass Flow (kg/s)", "Hflo(kJ/kg)", "P CO2", "Psat", "Choked?", "Tres"
        ]
        rows = []
        for row in raw_rows:
            fixed, rest = row[:20], row[20:]
            if len(rest) >= 2:
                choked, tres = rest[0], rest[1]
            elif len(rest) == 1:
                choked, tres = None, rest[0]
            else:
                choked, tres = None, None
            rows.append(fixed + [choked, tres])
        return pd.DataFrame(rows, columns=columns).apply(pd.to_numeric, errors='coerce', downcast='float')

    def _generate_summary_stats(self):
        if 'wellbore_profile' not in self.dataframes:
            return {}
        df = self.dataframes['wellbore_profile']
        return {
            "depth_range": (df['Depth (m MD)'].min(), df['Depth (m MD)'].max()),
            "pressure_range (Bara)": (df['Press (Bara)'].min(), df['Press (Bara)'].max()),
            "temperature_range (C)": (df['Temp(oC)'].min(), df['Temp(oC)'].max()),
            "mass_flow_avg (kg/s)": df['Mass Flow (kg/s)'].mean(),
            "XCO2_avg": df['XCO2'].mean()
        }

    def to_json(self):
        result = {
            "sections": self.sections,
            "tables": {k: v.to_dict(orient='split') if isinstance(v, pd.DataFrame) else v for k, v in self.dataframes.items()}
        }
        return result

    def to_excel(self, filepath):
        with pd.ExcelWriter(filepath) as writer:
            for name, df in self.dataframes.items():
                if isinstance(df, pd.DataFrame):
                    df.to_excel(writer, sheet_name=name[:31], index=False)

    def plot_output_curve(self):
        df = self.dataframes.get("wellhead_info_summary")
        if df is None or df.empty:
            print("No wellhead info summary data to plot.")
            return

        fig, ax1 = plt.subplots()

        color1 = 'tab:blue'
        ax1.set_xlabel('Wellhead Pressure (Bara)')
        ax1.set_ylabel('Total Flow (kg/s)', color=color1)
        ax1.plot(df['Wellhead Pressure (Bara)'].values[1:], df['Wellhead Total Flow (kg/s)'].values[1:], marker='o', color=color1, label='Total Flow')
        ax1.tick_params(axis='y', labelcolor=color1)
        ax1.grid(True, which='both', axis='both', linestyle='--', alpha=0.5)

        ax2 = ax1.twinx()
        color2 = 'tab:red'
        ax2.set_ylabel('Flowing Enthalpy (kJ/kg)', color=color2)
        ax2.plot(df['Wellhead Pressure (Bara)'].values[1:], df['Wellhead Flowing Enthalpy (kJ/kg)'].values[1:], marker='s', linestyle='--', color=color2, label='Flowing Enthalpy')
        ax2.tick_params(axis='y', labelcolor=color2)
        ax2.set_ylim(900, df['Wellhead Flowing Enthalpy (kJ/kg)'].max() * 1.05)
        ax2.grid(False)
        # ax2.grid(True, which='both', axis='both', linestyle='--', alpha=0.5)

        plt.title('Wellhead Output Curve', fontweight='bold')
        fig.tight_layout()
        plt.show()

    def plot_profile_value(self, fig=None, column='Press (Bara)', title=None, color='blue', style='dash', symbol='square'):
        if title is None:
            title = column
        
        if fig is None:
            fig = go.Figure()

            fig.update_layout(
                title=dict(
                    text=f"<b>{title}</b>",
                    # pad=dict(t=10),
                    x=0.5,
                    y=0.95,
                    font=dict(size=14, color="black", family="Arial Black", weight="bold")
                ),
                xaxis=dict(
                    title=dict(
                        text=f"<b>{column}</b>",
                        font=dict(size=12, color=color, family="Arial", weight="bold"),
                        standoff=0
                    ),
                    tickfont=dict(size=10, color=color, family="Arial"),
                    ticks="outside",
                    ticklen=1,
                    # range=[0, max_x],
                    side="bottom",
                    showgrid=True,
                    gridcolor="lightgray",
                    gridwidth=1,
                    griddash="dash"
                ),
                yaxis=dict(
                    title=dict(
                        text='<b>Depth (mMD)</b>',
                        font=dict(size=12, color="black", family="Arial", weight="bold"),
                        standoff=5
                    ),
                    tickfont=dict(size=10, color="black", family="Arial"),
                    ticks="outside",
                    ticklen=5,
                    autorange="reversed",
                    showgrid=True,
                    gridcolor="lightgray",
                    gridwidth=1,
                    griddash="dash",
                    # range=[0,1300]
                ),
                legend=dict(
                    title=dict(
                        text="Legend:",
                        font=dict(size=12, color="black", family="Arial", weight="bold"),
                        side="top"
                    ),
                    font=dict(size=10, color="black", family="Arial Narrow"),
                    x=0.5,
                    y=-0.155,
                    xanchor="center",
                    yanchor="top",
                    orientation="h",
                    traceorder="normal",
                    tracegroupgap=0.5,
                    bordercolor="gray",
                    borderwidth=1,
                    itemwidth=30,  # 👈 Controls the width of each legend item to help force line breaks
                ),
                height=850,   #fig, ax1 = plt.subplots(figsize=(8.27, 11.69)
                width=550,
                # height=11.69*81,
                template="plotly_white",
                # margin=dict(l=5, r=5, t=100, b=50),
                paper_bgcolor="white",
                plot_bgcolor="white",
                shapes=[
                    dict(
                        type="rect",
                        xref="paper",
                        yref="paper",
                        x0=0,
                        y0=0,
                        x1=1,
                        y1=1,
                        line=dict(color="grey", width=0.5)
                    )
                ]
            )
    
        fig.add_trace(go.Scatter(
            x=self.dataframes['wellbore_profile'][column],
            y=self.dataframes['wellbore_profile']['Depth (m MD)'],
            name=f"<b>{column}</b>",
            mode="lines+markers",
            line=dict(color=color, dash=style, width=1.5),
            marker=dict(symbol=symbol, size=5, color="rgba(0,0,0,0)", line=dict(width=0.5)),
            showlegend=True,
        ))

        return fig

class geoPTS:
    '''
    Notes to be confirmed:
    1. Should we exclude negative rps for calculation?
    2. Should we apply massrate calculation?
    3. Should we add PI calculation?
    4. Should we add correction in terms of velocity in directional well?
    '''
    def __init__(self):
        self.well_track = []
        self.pts_raw_data = {
            'log_down': [],
            'log_up': []
        }
        self.pts_interp_data = {
            'log_down': [],
            'log_up': []
        }
        self.slope = {}
        self.vfluid = {}

    def get_pos_depth(self, track):
        """Returns array of downhole depths corresponding to pos array."""
        return np.cumsum([0.] + [np.linalg.norm(pos - track[i]) for
                                i, pos in enumerate(track[1:])])

    def add_well_track(self, well_track: list | np.ndarray, delz=3.0):
        # get well elevation
        # get well depth
        # create depth with specific subdiv. length
        if isinstance(well_track, list):
            well_track = np.array(well_track)

        well_depth = self.get_pos_depth(well_track)

        self.well_depth = np.arange(0, well_depth[-1], delz)

        return self.well_depth

    def raw_data_smoothing(
            self, data:pd.DataFrame, 
            speed_limit_range=5, p_limit_range=1.1308, 
            T_limit_range=9.11, s_limit_range=65.62):
        # Maximum allowable data change per ft
        # Line speed  : 5 ft/min ~ 5 m/min per m 
        # Pressure    : 5 psia ~ 1.1308 bar per m
        # Temperature : 5 deg-F ~ 9.11 deg-C per m
        # Spinner     : 20 rps ~ 65.62 rps per m

        data = data.dropna()

        dMD = np.diff(data['depth'].values)
        dv = np.diff(data['vcable'].values)*60
        dp = np.diff(data['pres'].values)
        dT = np.diff(data['temp'].values)
        ds = np.diff(data['spinner'].values)
        
        dv_dMD = np.abs(dv/dMD)
        dp_dMD = np.abs(dp/dMD)
        dT_dMD = np.abs(dT/dMD)
        ds_dMD = np.abs(ds/dMD)

        mask = (
            (dv_dMD <= speed_limit_range) &
            (dp_dMD <= p_limit_range) &
            (dT_dMD <= T_limit_range) &
            (ds_dMD <= s_limit_range)
        )

        # Keep first row, then rows whose gradient from previous row is acceptable
        clean_data = data.iloc[np.concatenate([[True], mask])].copy()

        return clean_data
    
    def mitch_algorithm(self, data:pd.DataFrame, bin_size=3, method="median"):
        # bin increment 10 ft ~ 3 m
        # chatgpt said in geothermal mitch algorithm often use median instead of mean
        data["depth_bin"] = (
            np.floor(data["depth"] / bin_size) * bin_size
        )

        binned = (
            data.groupby("depth_bin", as_index=False)
            .agg({
                "pres": method,      # or "mean"
                "temp": method,
                "spinner": method,
                "vcable": method,
            })
        )

        binned.columns = ['depth', "pres", "temp", "spinner", "vcable"]

        return binned
    
    def interp_pts_data(self):
        # iterate pts data
            # interpolate pts data using interest depth
            # store rps and vcable each depth
        
        for key in self.pts_raw_data.keys():
            for data in self.pts_raw_data[key]:
                data = data.sort_values('depth')
                data_dirty = data.copy()
                data = self.raw_data_smoothing(data)
                data = self.mitch_algorithm(data)
                data_clean = data.copy()

                print('dirty')
                print(data_dirty)

                print('clean')
                print(data_clean)
                
                import matplotlib.pyplot as plt

                fig, ax = plt.subplots(figsize=(6, 8))

                ax.plot(data_dirty["vcable"], data_dirty["depth"], label="dirty")
                ax.plot(data_clean["vcable"], data_clean["depth"], label="clean")

                # Reverse the depth axis
                ax.invert_yaxis()

                ax.set_title(key)
                ax.set_xlabel("Cable Speed")
                ax.set_ylabel("Depth")
                ax.legend()

                # Save the figure
                plt.savefig(
                    f"{key}.png",
                    dpi=300,
                    bbox_inches="tight"
                )

                # Free memory by closing the figure
                plt.close(fig)

                new_data = pd.DataFrame({
                    'depth': self.well_depth,
                })
                data_depth = data['depth'].values
                for col in data.columns:
                    if col != 'depth':
                        res = np.full_like(self.well_depth, np.nan, dtype=float)
                        mask = (self.well_depth >= data_depth[0]) & (self.well_depth <= data_depth[-1])
                        res[mask] = np.interp(self.well_depth[mask], data_depth, data[col].values)
                        new_data[col] = res
                self.pts_interp_data[key].append(new_data)
        
        return self.pts_interp_data

    def calc_slope(self, verbose=False):
        # iterate depth
            # if number of rps and vcable data more than one
                # calculate slope (rps/(m/s)) and intercept rps
                # store them
        for depth in self.well_depth:
            self.slope[depth] = {
                'spinner': [],
                'vcable': [],
                'slope': None,
                'intercept': None,
                'spinner_calc': [],
                'vcable_calc': [],
            }
            for key in self.pts_interp_data.keys():
                for data in self.pts_interp_data[key]:
                    spinner = data.loc[data['depth'] == depth, 'spinner'].values[0]
                    vcable = data.loc[data['depth'] == depth, 'vcable'].values[0]
                    
                    if np.isnan(spinner):
                        spinner = None
                    if np.isnan(vcable):
                        vcable = None
                    
                    self.slope[depth]['spinner'].append(spinner)
                    self.slope[depth]['vcable'].append(vcable)
            
            try:
                df_xplot = pd.DataFrame({
                    'vcable': self.slope[depth]['vcable'],
                    'spinner': self.slope[depth]['spinner']
                })
                df_xplot = df_xplot[df_xplot['spinner'] > 0].copy().dropna()
                if len(df_xplot) > 1:
                    m, C = np.polyfit(df_xplot['vcable'].values, df_xplot['spinner'].values, 1)
                    # m, C = np.polyfit(np.array(self.slope[depth]['vcable']), np.array(self.slope[depth]['spinner']), 1)
                    self.slope[depth]['slope'] = m
                    self.slope[depth]['intercept'] = C
                    self.slope[depth]['vcable_calc'] = np.linspace(np.nanmin(df_xplot['vcable']), np.nanmax(df_xplot['vcable']), 12)
                    self.slope[depth]['spinner_calc'] = self.slope[depth]['vcable_calc']*m + C
            except Exception as e:
                if verbose:
                    print(f'❌ Found error: {str(e)} at depth {depth:.2f} mMD')

    def calc_fluid_velocity(self, slope_data: list | np.ndarray):
        # iterate pts data
            # calculate fluid velocity (vfluid = rps/slope + vcable)
        if isinstance(slope_data, list):
            slope_data = np.array(slope_data)
        
        log_abbrev = {'log_down': 'LD', 'log_up': 'LU'}

        for key in self.pts_interp_data.keys():
            for i, data in enumerate(self.pts_interp_data[key]):
                self.vfluid[f'{log_abbrev[key]}-{i+1}'] = data['spinner'].values/slope_data - data['vcable'].values
        
        df_vfluid = pd.DataFrame(self.vfluid)
        df_vfluid['Average'] = df_vfluid[[_ for _ in df_vfluid.columns]].apply(lambda row: np.nanmean(row.values), axis=1)

        self.vfluid['Average'] = df_vfluid['Average'].values

        return self.vfluid
    
    def plot_slope(self, slope_data=None, fig=None, title='Slope', color='blue', symbol='circle'):
        if fig is None:
            fig = go.Figure()
            
            fig.update_layout(
                title=dict(
                    text=f"<b>{title}</b>",
                    # pad=dict(t=10),
                    x=0.5,
                    y=0.95,
                    font=dict(size=14, color="black", family="Arial Black", weight="bold")
                ),
                xaxis=dict(
                    title=dict(
                        text=f"<b>Slope (RPS/(m/s))</b>",
                        font=dict(size=12, color=color, family="Arial", weight="bold"),
                        standoff=0
                    ),
                    tickfont=dict(size=10, color=color, family="Arial"),
                    ticks="outside",
                    ticklen=1,
                    # range=[0, max_x],
                    side="bottom",
                    showgrid=True,
                    gridcolor="lightgray",
                    gridwidth=1,
                    griddash="dash"
                ),
                yaxis=dict(
                    title=dict(
                        text='<b>Depth (mMD)</b>',
                        font=dict(size=12, color="black", family="Arial", weight="bold"),
                        standoff=5
                    ),
                    tickfont=dict(size=10, color="black", family="Arial"),
                    ticks="outside",
                    ticklen=5,
                    autorange="reversed",
                    showgrid=True,
                    gridcolor="lightgray",
                    gridwidth=1,
                    griddash="dash",
                    # range=[0,1300]
                ),
                legend=dict(
                    title=dict(
                        text="Legend:",
                        font=dict(size=12, color="black", family="Arial", weight="bold"),
                        side="top"
                    ),
                    font=dict(size=10, color="black", family="Arial Narrow"),
                    x=0.5,
                    y=-0.155,
                    xanchor="center",
                    yanchor="top",
                    orientation="h",
                    traceorder="normal",
                    tracegroupgap=0.5,
                    bordercolor="gray",
                    borderwidth=1,
                    itemwidth=30,  # 👈 Controls the width of each legend item to help force line breaks
                ),
                height=850,   #fig, ax1 = plt.subplots(figsize=(8.27, 11.69)
                width=450,
                # height=11.69*81,
                template="plotly_white",
                # margin=dict(l=5, r=5, t=100, b=50),
                paper_bgcolor="white",
                plot_bgcolor="white",
                shapes=[
                    dict(
                        type="rect",
                        xref="paper",
                        yref="paper",
                        x0=0,
                        y0=0,
                        x1=1,
                        y1=1,
                        line=dict(color="grey", width=0.5)
                    )
                ]
            )
        
        fig.add_trace(go.Scatter(
            x=[_['slope'] for _ in self.slope.values()],
            y=[_ for _ in self.slope.keys()],
            name=f"<b>Slope (RPS/(m/s))</b>",
            mode="markers",
            marker=dict(symbol=symbol, size=5, color=color, line=dict(width=0.5)),
            showlegend=True,
        ))

        if slope_data is not None:
            fig.add_trace(go.Scatter(
                x=[_[1] for _ in slope_data],
                y=[_[0] for _ in slope_data],
                name=f"<b>Slope Data (RPS/(m/s))</b>",
                mode="lines",
                line=dict(color='red', dash='dash', width=1.5),
                # marker=dict(symbol=symbol, size=5, color="rgba(0,0,0,0)", line=dict(width=0.5)),
                showlegend=True,
            ))

        return fig

    def plot_vfluid(self, fig=None, title='Velocity', column='Average', color='blue', style='solid', symbol='circle'):
        if fig is None:
            fig = go.Figure()
            
            fig.update_layout(
                title=dict(
                    text=f"<b>{title} {column}</b>",
                    # pad=dict(t=10),
                    x=0.5,
                    y=0.95,
                    font=dict(size=14, color="black", family="Arial Black", weight="bold")
                ),
                xaxis=dict(
                    title=dict(
                        text=f"<b>Velocity (m/s)</b>",
                        font=dict(size=12, color=color, family="Arial", weight="bold"),
                        standoff=0
                    ),
                    tickfont=dict(size=10, color=color, family="Arial"),
                    ticks="outside",
                    ticklen=1,
                    # range=[0, max_x],
                    side="bottom",
                    showgrid=True,
                    gridcolor="lightgray",
                    gridwidth=1,
                    griddash="dash"
                ),
                yaxis=dict(
                    title=dict(
                        text='<b>Depth (mMD)</b>',
                        font=dict(size=12, color="black", family="Arial", weight="bold"),
                        standoff=5
                    ),
                    tickfont=dict(size=10, color="black", family="Arial"),
                    ticks="outside",
                    ticklen=5,
                    autorange="reversed",
                    showgrid=True,
                    gridcolor="lightgray",
                    gridwidth=1,
                    griddash="dash",
                    # range=[0,1300]
                ),
                legend=dict(
                    title=dict(
                        text="Legend:",
                        font=dict(size=12, color="black", family="Arial", weight="bold"),
                        side="top"
                    ),
                    font=dict(size=10, color="black", family="Arial Narrow"),
                    x=0.5,
                    y=-0.155,
                    xanchor="center",
                    yanchor="top",
                    orientation="h",
                    traceorder="normal",
                    tracegroupgap=0.5,
                    bordercolor="gray",
                    borderwidth=1,
                    itemwidth=30,  # 👈 Controls the width of each legend item to help force line breaks
                ),
                height=850,   #fig, ax1 = plt.subplots(figsize=(8.27, 11.69)
                width=550,
                # height=11.69*81,
                template="plotly_white",
                # margin=dict(l=5, r=5, t=100, b=50),
                paper_bgcolor="white",
                plot_bgcolor="white",
                shapes=[
                    dict(
                        type="rect",
                        xref="paper",
                        yref="paper",
                        x0=0,
                        y0=0,
                        x1=1,
                        y1=1,
                        line=dict(color="grey", width=0.5)
                    )
                ]
            )
        
        fig.add_trace(go.Scatter(
            x=self.vfluid[column],
            y=self.well_depth,
            name=f"<b>V<sub>fluid</sub> {column} (m/s)</b>",
            mode="lines+markers",
            line=dict(color=color, dash=style, width=1.5),
            marker=dict(symbol=symbol, size=5, color="rgba(0,0,0,0)", line=dict(width=0.5)),
            showlegend=True,
        ))

        return fig

