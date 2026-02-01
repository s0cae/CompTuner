# CompTuner Manual

Audience: researchers, developers, and lab users who need a reliable, manual workflow
for iterative compensator tuning in the frequency domain.


## Table of contents

- [1) Overview](#1-overview)
- [2) Requirements](#2-requirements)
- [3) Installation](#3-installation)
- [4) Running the App](#4-running-the-app)
- [5) Core Concepts](#5-core-concepts)
- [6) Data Formats](#6-data-formats)
- [7) UI Guide](#7-ui-guide)
- [8) Presets](#8-presets)
- [9) Snapshots (tuning logs)](#9-snapshots-tuning-logs)
- [10) Undo / Redo](#10-undo--redo)
- [11) Settings](#11-settings)
- [12) Common Workflows](#12-common-workflows)
- [13) Troubleshooting](#13-troubleshooting)
- [14) Notes for Developers](#14-notes-for-developers)
  - [14.1 Adding custom blocks](#141-adding-custom-blocks)

---

## 1) Overview

CompTuner is a desktop application for manual, iterative tuning of compensators using
measured frequency response data. It focuses on:

- Block-based compensator construction (gain, lead/lag, 2nd order, real pole/zero).
- Live Bode plots (magnitude + phase).
- Measured plant overlays (Hf and its inverse Hfinv).
- Numeric readouts at key frequencies.
- Presets, snapshots, undo/redo, and persistent settings.

This tool is intentionally manual-first: it helps you see the impact of parameter
changes quickly and consistently, without forcing automatic optimization.

---

## 2) Requirements

- Windows (tested on Windows 10/11).
- Python 3.11+ recommended.
- Dependencies listed in `requirements.txt`:
  - PySide6
  - pyqtgraph
  - numpy
  - scipy

---

## 3) Installation

From the project root:

1) Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

PowerShell note (optional):
- If activation is blocked, either run `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` once,
  or skip activation and always use `.\.venv\Scripts\python ...`.

2) Install dependencies:

```powershell
.\.venv\Scripts\python -m pip install -r requirements.txt
```

If `python` is not on PATH, use the full path to your Python executable or the
Python Launcher (if available) with `py -m venv .venv`.

---

## 4) Running the App

```powershell
.\.venv\Scripts\python -m comp_tuner
```

Quick start:
1) Click **Cargar datos** and load a CSV.
2) Adjust blocks/parameters and watch the Bode plots.
3) Save a snapshot (**Guardar snapshot**) and/or a preset (**Guardar preset**) for reproducibility.

---

## 5) Core Concepts

### 5.1 Compensator model
The compensator is a cascade of blocks:

```
Hc(jw) = product_i Hi(jw)
```

Each block has parameters and a frequency response. When you change a parameter,
the total response is re-computed and plotted immediately.

### 5.2 Reference vs current
The app keeps:

- A **reference** compensator (baseline).
- The **current** compensator (what you are tuning).

You can:
- Show/hide the reference.
- Copy current -> reference.
- Load a preset as the reference.

### 5.3 Measured data
Measured data can be loaded as:
- Hf (forward transfer), and the app computes Hfinv.
- Or directly as complex Hf.

Both Hf and Hfinv can be plotted for visual comparison.

### 5.4 Built-in block library

CompTuner currently provides these block types (see `comp_tuner/blocks.py`):

- Gain (`gain`): `H(s) = K`
  - params: `K` (unitless, logarithmic slider)
- Lead/Lag (`leadlag`): `H(s) = (a T s + 1) / (T s + 1)`
  - params: `T` (seconds), `a` (unitless)
  - interpretation: `a > 1` gives phase lead; `a < 1` gives phase lag.
- 2nd order section (`sos`): `H(s) = K * wn^2 / (s^2 + 2*zeta*wn*s + wn^2)`
  - params: `fn` (Hz), `zeta` (unitless), `K` (unitless)
- Real pole-zero (`real_pole_zero`): `H(s) = K * (s/wz + 1) / (s/wp + 1)`
  - params: `fz` (Hz), `fp` (Hz), `K` (unitless)

All frequency parameters are entered in Hz and converted internally using `w = 2*pi*f`.

---

## 6) Data Formats

### 6.1 CSV input
The loader accepts **one of these schemas** (header required):

1) Complex response:
```
freq_hz,h_real,h_imag
```

2) Magnitude + phase:
```
freq_hz,mag_db,phase_deg
```

Notes:
- Frequency must be positive.
- Phase is interpreted in degrees.

### 6.2 Example CSV
```
freq_hz,mag_db,phase_deg
0.1,-20.3,45.0
0.2,-18.7,41.2
0.5,-12.1,10.0
```

### 6.3 Generating transfer CSV from MAT data (optional)
If you have MATLAB MAT files `data_a1_cut.mat` and `data_xddot_d_cut.mat`, you can
generate a CSV using:

```powershell
.\.venv\Scripts\python generate_transfer_csv.py --out data\transfer_measured.csv
```

---

## 7) UI Guide

### 7.1 Plots
- **Magnitud (dB)**: magnitude of reference, current, and measured curves.
- **Fase (grados)**: phase of reference, current, and measured curves.

### 7.2 Block editor
In "Bloques del compensador":
- Add, remove, move blocks.
- Adjust parameters with sliders or numeric fields.

### 7.3 Notes and summary
"Notas y resumen" includes:
- A table of values at key frequencies (report points).
- A notes field saved with snapshots.

### 7.4 Phase processing (measured data)
- **Desenvolver fase medida**: unwraps the measured phase so it is continuous
  across frequency (removes +/-180 deg jumps).
- **Suavizar fase medida**: applies Savitzky-Golay smoothing (optional).
- **Ventana**: smoothing window length (odd number).

Why unwrap matters:
- Most tools return phase as a principal value in [-180, 180] deg (modulo 360 deg), which introduces artificial jumps.
- CompTuner unwraps the model phase, so unwrapping the measured phase makes comparisons consistent and makes phase slope
  (delay-like behavior) interpretable.

Smoothing is off by default and should be used conservatively (it can hide narrow features if the window is too large).

### 7.5 Loading measured CSV

1) Click **Cargar datos** and select a CSV file.
2) If you cancel the dialog, CompTuner will attempt to load `data/transfer_measured.csv` (if it exists).

For faster plotting, measured curves are decimated on a logarithmic frequency grid. You can control this with the
"Bins medidos" setting (higher = more points, slower plotting).

---

## 8) Presets

Presets are JSON files that store the compensator block list.

### 8.1 Load / Save
- **Cargar preset**: replaces the current compensator.
- **Guardar preset**: saves current compensator to JSON.
- **Cargar preset ref**: loads a preset as the reference.

### 8.2 Preset format (example)
```json
{
  "version": 1,
  "blocks": [
    {"type": "gain", "params": {"K": 1.0}, "enabled": true},
    {"type": "leadlag", "params": {"T": 0.004, "a": 1.7}, "enabled": true},
    {"type": "sos", "params": {"fn": 20.0, "zeta": 0.55, "K": 1.0}, "enabled": true}
  ]
}
```

Tip: consider storing presets in a dedicated folder (e.g., `presets/`) and committing them if you want reproducible,
reviewable tuning baselines.

---

## 9) Snapshots (tuning logs)

Snapshots record the current compensator state and key phase values.

- File: `tuning_log.csv`
- Fields:
  - `timestamp` (ISO 8601)
  - `phase_1Hz_deg`
  - `phase_3Hz_deg`
  - `blocks` (human-readable block list; for exact configs use presets)
  - `note` (from the notes box)

Use snapshots as an audit trail for manual tuning sessions. For exact reproduction of a compensator configuration,
save a JSON preset as well.

---

## 10) Undo / Redo

- **Undo**: Ctrl+Z (or "Deshacer" button)
- **Redo**: Ctrl+Y (or "Rehacer" button)

Undo/redo covers parameter changes, block add/remove/move, and preset loads.
History is capped to 100 states.

---

## 11) Settings

Open **Configuración** to change plot and tuning defaults:

- Frequency range (min/max)
- Grid resolution (points)
- Log/linear X-axis
- Marker frequencies
- Summary report frequencies
- Grid alpha
- Background color
- Antialias
- Measured decimation bins

### 11.1 Apply vs OK
- **Aplicar**: apply changes without closing the dialog.
- **OK**: apply and close.

### 11.2 Persistence
Settings are saved to:

```
settings/general_settings.json
```

This file is user-specific. If you use git, consider adding `settings/` to `.gitignore`.

---

## 12) Common Workflows

### 12.1 Basic tuning loop
1) Load measured CSV.
2) Add/remove blocks to set your structure.
3) Adjust parameters while observing the Bode plots.
4) Save snapshots at key milestones.
5) Export a preset for reproducibility.

### 12.2 Reference-based tuning
1) Load a preset as reference.
2) Tune current compensator against that baseline.
3) Copy current -> reference when satisfied.

---

## 13) Troubleshooting

### 13.1 "No CSV found" or format errors
- Ensure the CSV has headers and correct columns.
- Verify `freq_hz` is present and positive.

### 13.2 Plots look wrong after settings change
- Check that frequency min/max are valid.
- For log axis, freq_min must be > 0.

### 13.3 Invalid background color
- Use a valid color name (`k`, `w`, `r`) or hex (`#202020`).

### 13.4 PowerShell venv activation fails
- If `Activate.ps1` is blocked by execution policy, either set a per-user policy:
  `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`
  or skip activation and run everything via `.\.venv\Scripts\python ...`.

### 13.5 Python / pip issues
- If `python` is not found, use the full path to `python.exe` (or install Python 3.x).
- If dependency installation fails, try upgrading pip:
  `.\.venv\Scripts\python -m pip install --upgrade pip`

---

## 14) Notes for Developers

Key modules:
- `comp_tuner/blocks.py`: block definitions and frequency responses.
- `comp_tuner/compensator.py`: compensator model, preset serialization.
- `comp_tuner/model.py`: CSV loading and helper math.
- `comp_tuner/ui.py`: GUI logic.

### 14.1 Adding custom blocks

To add a new block type:

1) Create a new class in `comp_tuner/blocks.py` that inherits `BlockBase`.
2) Define:
   - `name` (unique string)
   - `display_name` (UI label)
   - `latex` (optional string used in docs/exports)
   - `params_meta` (parameter definitions)
3) Implement `freq_response(w, params)` returning a complex array.
4) Register the class in `BLOCK_TYPES`.

Once registered in `BLOCK_TYPES`, the block appears automatically in the "Agregar bloque" menu (no UI changes required).

Minimal example (template):

```python
from typing import Dict

import numpy as np

class MyBlock(BlockBase):
    name = "my_block"
    display_name = "Mi Bloque"
    latex = r"H(s) = \frac{s/\omega_z + 1}{s/\omega_p + 1}"
    params_meta = {
        "fz": ParamMeta(label="f_z", default=1.0, min=0.01, max=100.0, scale="log", unit="Hz"),
        "fp": ParamMeta(label="f_p", default=5.0, min=0.01, max=100.0, scale="log", unit="Hz"),
        "K": ParamMeta(label="K", default=1.0, min=0.1, max=10.0, scale="log"),
    }

    @staticmethod
    def freq_response(w: np.ndarray, params: Dict[str, float]) -> np.ndarray:
        s = 1j * w
        fz = params.get("fz", 1.0)
        fp = params.get("fp", 5.0)
        K = params.get("K", 1.0)
        wz = 2 * np.pi * fz
        wp = 2 * np.pi * fp
        return K * (s + wz) / (s + wp)

BLOCK_TYPES[MyBlock.name] = MyBlock
```

Guidelines:
- Use **Hz** for frequency parameters and convert to rad/s internally.
- Choose parameter ranges that are safe for interactive sliders.
- Keep `scale="log"` for parameters that span decades.
- Ensure `freq_response` is vectorized over `w`.
- The order of `params_meta` controls the parameter order shown in the UI.

---

## 15) License / Attribution

Author: Emanuel Camacho @s0cae

License: GNU General Public License v3.0 or later (GPL-3.0-or-later).
