"""
Standalone helper script to generate a forward transfer CSV (freq_hz,h_real,h_imag)
from MAT files (data_a1_cut.mat, data_xddot_d_cut.mat).

Usage:
    python generate_transfer_csv.py [--out data/transfer_measured.csv] [--nfft 16384]

The script searches for the data folder in ./data or ./reference_matlab_code/data
relative to this file.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from scipy import io, signal


def find_data_directory(base_dir: Path) -> Path:
    """
    Locate the data folder relative to base_dir.

    Checks ./data then ./reference_matlab_code/data.
    """
    candidates = [base_dir / "data", base_dir / "reference_matlab_code" / "data"]
    for cand in candidates:
        if cand.is_dir():
            return cand
    raise FileNotFoundError("No data directory found (expected data/ or reference_matlab_code/data/).")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate forward transfer CSV from MAT data.")
    parser.add_argument("--out", type=Path, default=Path("data/transfer_measured.csv"), help="Output CSV path.")
    parser.add_argument("--nfft", type=int, default=16384, help="FFT/window length for CPSD.")
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent
    data_dir = find_data_directory(base_dir)

    a1_path = data_dir / "data_a1_cut.mat"
    x_path = data_dir / "data_xddot_d_cut.mat"
    if not a1_path.is_file() or not x_path.is_file():
        raise FileNotFoundError("Missing data_a1_cut.mat or data_xddot_d_cut.mat in data folder.")

    data_a1 = io.loadmat(a1_path).get("data_a1")
    data_x = io.loadmat(x_path).get("data_xddot_d")
    if data_a1 is None or data_x is None:
        raise ValueError("data_a1 or data_xddot_d variables are not present in the MAT files.")

    t = np.asarray(data_x[0, :], dtype=float)
    a1sig = np.asarray(data_a1[1, :], dtype=float)
    xddot = np.asarray(data_x[1, :], dtype=float)
    if t.ndim != 1 or a1sig.ndim != 1 or xddot.ndim != 1:
        raise ValueError("Unexpected MAT file shape; expected 2xN arrays.")

    sr = 1.0 / float(np.mean(np.diff(t)))
    window_size = int(args.nfft)
    movement = 60
    div = int(np.floor((len(t) - window_size) / movement))
    overlap = int(window_size - div)
    cut_length = int(window_size + movement * div)
    if cut_length <= 0 or cut_length > len(t):
        raise ValueError("Not enough samples to compute CPSD with the requested window.")

    window = signal.windows.hann(window_size, sym=False)
    freq, x_psd = signal.csd(
        xddot[:cut_length],
        xddot[:cut_length],
        fs=sr,
        window=window,
        nperseg=window_size,
        noverlap=overlap,
        nfft=args.nfft,
        detrend=False,
        return_onesided=True,
        scaling="density",
    )
    _, a1x_psd = signal.csd(
        a1sig[:cut_length],
        xddot[:cut_length],
        fs=sr,
        window=window,
        nperseg=window_size,
        noverlap=overlap,
        nfft=args.nfft,
        detrend=False,
        return_onesided=True,
        scaling="density",
    )

    h_f = a1x_psd / x_psd  # forward transfer (not inverted)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    header = "freq_hz,h_real,h_imag"
    data = np.column_stack((freq, np.real(h_f), np.imag(h_f)))
    np.savetxt(args.out, data, delimiter=",", header=header, comments="")
    print(f"Wrote {len(freq)} rows to {args.out}")


if __name__ == "__main__":
    main()
