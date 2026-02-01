from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import numpy as np


@dataclass(frozen=True)
class ParamMeta:
    label: str
    default: float
    min: float
    max: float
    scale: str = "linear"  # "linear" or "log"
    unit: str = ""


class BlockBase:
    name: str
    display_name: str
    latex: str
    params_meta: Dict[str, ParamMeta]

    @staticmethod
    def freq_response(w: np.ndarray, params: Dict[str, float]) -> np.ndarray:
        raise NotImplementedError


class GainBlock(BlockBase):
    name = "gain"
    display_name = "Ganancia"
    latex = "K"
    params_meta = {
        "K": ParamMeta(label="K", default=1.0, min=0.01, max=100.0, scale="log"),
    }

    @staticmethod
    def freq_response(w: np.ndarray, params: Dict[str, float]) -> np.ndarray:
        return np.full_like(w, fill_value=params.get("K", 1.0), dtype=complex)


class LeadLagBlock(BlockBase):
    name = "leadlag"
    display_name = "Lead/Lag"
    latex = r"\frac{aTs+1}{Ts+1}"
    params_meta = {
        "T": ParamMeta(label="T", default=0.004, min=1e-4, max=1.0, scale="log", unit="s"),
        "a": ParamMeta(label="a", default=1.7, min=0.1, max=10.0, scale="log"),
    }

    @staticmethod
    def freq_response(w: np.ndarray, params: Dict[str, float]) -> np.ndarray:
        T = params.get("T", 0.004)
        a = params.get("a", 1.7)
        s = 1j * w
        num = a * T * s + 1.0
        den = T * s + 1.0
        return num / den


class SecondOrderSection(BlockBase):
    name = "sos"
    display_name = "2° Orden"
    latex = r"\frac{K\ \omega_n^2}{s^2 + 2\zeta\omega_n s + \omega_n^2}"
    params_meta = {
        "fn": ParamMeta(label="fn", default=20.0, min=0.1, max=100.0, scale="log", unit="Hz"),
        "zeta": ParamMeta(label="zeta", default=0.55, min=0.1, max=2.0, scale="linear"),
        "K": ParamMeta(label="K", default=1.0, min=0.1, max=10.0, scale="log"),
    }

    @staticmethod
    def freq_response(w: np.ndarray, params: Dict[str, float]) -> np.ndarray:
        fn = params.get("fn", 20.0)
        zeta = params.get("zeta", 0.55)
        K = params.get("K", 1.0)
        wn = 2 * np.pi * fn
        s = 1j * w
        num = K * (wn**2)
        den = s**2 + 2 * zeta * wn * s + wn**2
        return num / den


class RealPoleZeroBlock(BlockBase):
    name = "real_pole_zero"
    display_name = "Real Pole–Zero"
    latex = r"H(s) = K \frac{s/\omega_z + 1}{s/\omega_p + 1}"
    params_meta = {
        "fz": ParamMeta(label="f_z (Hz)", default=1.0, min=0.01, max=100.0, scale="log", unit="Hz"),
        "fp": ParamMeta(label="f_p (Hz)", default=5.0, min=0.01, max=100.0, scale="log", unit="Hz"),
        "K": ParamMeta(label="K", default=1.0, min=0.1, max=10.0, scale="log"),
    }

    @staticmethod
    def freq_response(w, params):
        s = 1j * w
        fz = params.get("fz", 1.0)
        fp = params.get("fp", 5.0)
        K = params.get("K", 1.0)
        wz = 2 * np.pi * fz
        wp = 2 * np.pi * fp
        num = s + wz
        den = s + wp
        return K * num / den
    


BLOCK_TYPES = {
    GainBlock.name: GainBlock,
    LeadLagBlock.name: LeadLagBlock,
    SecondOrderSection.name: SecondOrderSection,
    RealPoleZeroBlock.name: RealPoleZeroBlock,
}
