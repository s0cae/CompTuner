from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

import numpy as np

from .blocks import BLOCK_TYPES


@dataclass
class BlockInstance:
    type_name: str
    params: Dict[str, float]
    enabled: bool = True


@dataclass
class CompensatorModel:
    blocks: List[BlockInstance] = field(default_factory=list)

    def add_block(self, type_name: str) -> None:
        if type_name not in BLOCK_TYPES:
            raise ValueError(f"Unknown block type: {type_name}")
        block_cls = BLOCK_TYPES[type_name]
        defaults = {k: meta.default for k, meta in block_cls.params_meta.items()}
        self.blocks.append(BlockInstance(type_name=type_name, params=defaults))

    def remove_block(self, index: int) -> None:
        if 0 <= index < len(self.blocks):
            self.blocks.pop(index)

    def move_block(self, old_idx: int, new_idx: int) -> None:
        if not (0 <= old_idx < len(self.blocks)):
            return
        new_idx = max(0, min(new_idx, len(self.blocks) - 1))
        if old_idx == new_idx:
            return
        blk = self.blocks.pop(old_idx)
        self.blocks.insert(new_idx, blk)

    def freq_response(self, w: np.ndarray) -> np.ndarray:
        h_total = np.ones_like(w, dtype=complex)
        for blk in self.blocks:
            if not blk.enabled:
                continue
            blk_cls = BLOCK_TYPES.get(blk.type_name)
            if blk_cls is None:
                continue
            h_total *= blk_cls.freq_response(w, blk.params)
        return h_total

    def to_dict(self) -> Dict[str, Any]:
        blocks = []
        for blk in self.blocks:
            blocks.append(
                {
                    "type": blk.type_name,
                    "params": {k: float(v) for k, v in blk.params.items()},
                    "enabled": bool(blk.enabled),
                }
            )
        return {"version": 1, "blocks": blocks}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CompensatorModel":
        if not isinstance(data, dict) or "blocks" not in data:
            raise ValueError("Preset inválido: falta la clave 'blocks'.")
        blocks_data = data.get("blocks") or []
        model = cls()
        for blk in blocks_data:
            type_name = blk.get("type")
            if type_name not in BLOCK_TYPES:
                raise ValueError(f"Tipo de bloque desconocido: {type_name}")
            block_cls = BLOCK_TYPES[type_name]
            params = {k: meta.default for k, meta in block_cls.params_meta.items()}
            for key, val in (blk.get("params") or {}).items():
                if key in block_cls.params_meta:
                    params[key] = float(val)
            enabled = bool(blk.get("enabled", True))
            model.blocks.append(BlockInstance(type_name=type_name, params=params, enabled=enabled))
        return model
