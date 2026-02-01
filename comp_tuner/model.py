from __future__ import annotations

from pathlib import Path
from typing import Tuple

import numpy as np
from scipy import signal

FREQ_GRID = np.logspace(np.log10(0.1), np.log10(100.0), 2000)
OMEGA_GRID = 2 * np.pi * FREQ_GRID
FREQ_MARKERS = (1.0, 3.0)
FREQ_REPORT = np.array([0.5, 1.0, 3.0, 10.0])


def mag_to_db(mag: np.ndarray) -> np.ndarray:
    return 20 * np.log10(np.maximum(mag, np.finfo(float).eps))


def bode_mag_phase(num: np.ndarray, den: np.ndarray, omega: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    _, h = signal.freqs(num, den, worN=omega)
    mag = np.abs(h)
    phs = np.degrees(np.unwrap(np.angle(h)))
    return mag, phs


def load_transfer_csv(path: Path) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Load an experimental transfer function from CSV and return both Hf and Hfinv mag/phase.

    Supported schemas (header row required):
    - freq_hz, h_real, h_imag          (complex Hf values)
    - freq_hz, mag_db, phase_deg       (Hf magnitude/phase)
    """
    if not path.is_file():
        raise FileNotFoundError(f"No CSV found at {path}")
    data = np.genfromtxt(path, delimiter=",", names=True)
    cols = set(data.dtype.names or [])
    if "freq_hz" not in cols:
        raise ValueError("CSV must contain a 'freq_hz' column.")

    freq = np.asarray(data["freq_hz"], dtype=float)
    if freq.size == 0:
        raise ValueError("CSV contains no data rows.")

    if {"h_real", "h_imag"}.issubset(cols):
        h_f = np.asarray(data["h_real"], dtype=float) + 1j * np.asarray(data["h_imag"], dtype=float)
    elif {"mag_db", "phase_deg"}.issubset(cols):
        mag = 10 ** (np.asarray(data["mag_db"], dtype=float) / 20.0)
        phase_rad = np.deg2rad(np.asarray(data["phase_deg"], dtype=float))
        h_f = mag * np.exp(1j * phase_rad)
    else:
        raise ValueError("CSV must contain either (freq_hz,h_real,h_imag) or (freq_hz,mag_db,phase_deg).")

    h_inv = 1.0 / h_f
    mag_db_inv = mag_to_db(np.abs(h_inv))
    phs_deg_inv = np.degrees(np.angle(h_inv))

    mag_db_fwd = mag_to_db(np.abs(h_f))
    phs_deg_fwd = np.degrees(np.angle(h_f))

    mask = (
        np.isfinite(freq)
        & (freq > 0)
        & np.isfinite(mag_db_inv)
        & np.isfinite(phs_deg_inv)
        & np.isfinite(mag_db_fwd)
        & np.isfinite(phs_deg_fwd)
    )
    return freq[mask], mag_db_inv[mask], phs_deg_inv[mask], mag_db_fwd[mask], phs_deg_fwd[mask]
