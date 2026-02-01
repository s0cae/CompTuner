from __future__ import annotations

import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QComboBox,
    QDoubleSpinBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from scipy.signal import savgol_filter

from .blocks import BLOCK_TYPES, ParamMeta
from .compensator import CompensatorModel
from .model import FREQ_GRID, FREQ_MARKERS, FREQ_REPORT, OMEGA_GRID, load_transfer_csv, mag_to_db

pg.setConfigOptions(antialias=True)

STRINGS = {
    "es": {
        "title": "Compensator Tuning",
        "blocks_box": "Bloques del compensador",
        "add_block": "Agregar bloque",
        "delete": "Eliminar",
        "move_up": "Subir",
        "move_down": "Bajar",
        "notes_box": "Notas y resumen",
        "notes_placeholder": "Escriba notas útiles aquí.",
        "ref_group": "Referencia y presets",
        "show_ref": "Mostrar referencia",
        "copy_to_ref": "Copiar actual a referencia",
        "load_ref_preset": "Cargar preset ref",
        "load_preset": "Cargar preset",
        "save_preset": "Guardar preset",
        "settings": "Configuración",
        "phase_group": "Procesamiento de fase",
        "unwrap": "Desenvolver fase medida",
        "smooth": "Suavizar fase medida",
        "window": "Ventana",
        "actions": "Acciones",
        "undo": "Deshacer",
        "redo": "Rehacer",
        "load_data": "Cargar datos",
        "save_snapshot": "Guardar snapshot",
        "table_headers": ["Hz", "Mag ref (dB)", "Mag (dB)", "Mag diff", "Fase ref", "Fase", "Fase diff"],
        "status_loaded": "Datos medidos cargados ({source})",
        "status_error": "Error: {msg}",
        "status_saved_snapshot": "Snapshot guardado en {name}",
        "status_saved_preset": "Preset guardado: {name}",
        "status_loaded_preset": "Preset cargado: {name}",
        "status_loaded_ref": "Preset cargado como referencia: {name}",
        "status_updated_ref": "Referencia actualizada desde el compensador.",
        "status_config": "Configuración actualizada.",
        "status_save_cfg_error": "No se pudo guardar configuración: {msg}",
        "status_load_cfg_error": "No se pudo leer configuración: {msg}",
        "status_invalid_cfg": "Configuración inválida: {msg}",
        "status_no_csv": "No CSV seleccionado y no se encontró transfer_measured.csv en la carpeta por defecto.",
        "lang_label": "Idioma",
        "lang_es": "Español",
        "lang_en": "English",
    },
    "en": {
        "title": "Compensator Tuning",
        "blocks_box": "Compensator blocks",
        "add_block": "Add block",
        "delete": "Delete",
        "move_up": "Move up",
        "move_down": "Move down",
        "notes_box": "Notes & summary",
        "notes_placeholder": "Write useful notes here.",
        "ref_group": "Reference & presets",
        "show_ref": "Show reference",
        "copy_to_ref": "Copy current to reference",
        "load_ref_preset": "Load ref preset",
        "load_preset": "Load preset",
        "save_preset": "Save preset",
        "settings": "Settings",
        "phase_group": "Phase processing",
        "unwrap": "Unwrap measured phase",
        "smooth": "Smooth measured phase",
        "window": "Window",
        "actions": "Actions",
        "undo": "Undo",
        "redo": "Redo",
        "load_data": "Load data",
        "save_snapshot": "Save snapshot",
        "table_headers": ["Hz", "Mag ref (dB)", "Mag (dB)", "Mag diff", "Phase ref", "Phase", "Phase diff"],
        "status_loaded": "Measured data loaded ({source})",
        "status_error": "Error: {msg}",
        "status_saved_snapshot": "Snapshot saved to {name}",
        "status_saved_preset": "Preset saved: {name}",
        "status_loaded_preset": "Preset loaded: {name}",
        "status_loaded_ref": "Preset loaded as reference: {name}",
        "status_updated_ref": "Reference updated from current.",
        "status_config": "Settings updated.",
        "status_save_cfg_error": "Could not save settings: {msg}",
        "status_load_cfg_error": "Could not read settings: {msg}",
        "status_invalid_cfg": "Invalid settings: {msg}",
        "status_no_csv": "No CSV selected and transfer_measured.csv not found in default folder.",
        "lang_label": "Language",
        "lang_es": "Español",
        "lang_en": "English",
    },
}


class SettingsDialog(QDialog):
    def __init__(self, parent: QWidget | None, settings: dict, on_apply=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Configuración general")
        self._on_apply = on_apply

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.freq_min = QDoubleSpinBox()
        self.freq_min.setRange(1e-6, 1e6)
        self.freq_min.setDecimals(6)
        self.freq_min.setValue(settings["freq_min"])
        form.addRow("Frecuencia mínima (Hz)", self.freq_min)

        self.freq_max = QDoubleSpinBox()
        self.freq_max.setRange(1e-6, 1e6)
        self.freq_max.setDecimals(6)
        self.freq_max.setValue(settings["freq_max"])
        form.addRow("Frecuencia máxima (Hz)", self.freq_max)

        self.freq_points = QSpinBox()
        self.freq_points.setRange(10, 20000)
        self.freq_points.setValue(settings["freq_points"])
        form.addRow("Puntos de la rejilla", self.freq_points)

        self.log_x = QCheckBox("Escala logarítmica en X")
        self.log_x.setChecked(settings["log_x"])
        form.addRow("", self.log_x)

        self.freq_markers = QLineEdit(settings["freq_markers"])
        form.addRow("Marcadores (Hz)", self.freq_markers)

        self.freq_report = QLineEdit(settings["freq_report"])
        form.addRow("Resumen (Hz)", self.freq_report)

        self.grid_alpha = QDoubleSpinBox()
        self.grid_alpha.setRange(0.0, 1.0)
        self.grid_alpha.setSingleStep(0.05)
        self.grid_alpha.setValue(settings["grid_alpha"])
        form.addRow("Grid alpha", self.grid_alpha)

        self.plot_bg = QLineEdit(settings["background"])
        form.addRow("Color fondo", self.plot_bg)

        self.antialias = QCheckBox("Antialias")
        self.antialias.setChecked(settings["antialias"])
        form.addRow("", self.antialias)

        self.meas_bins = QSpinBox()
        self.meas_bins.setRange(10, 5000)
        self.meas_bins.setValue(settings["meas_bins"])
        form.addRow("Bins medidos", self.meas_bins)

        self.lang_combo = QComboBox()
        self.lang_combo.addItem(STRINGS["es"]["lang_es"], "es")
        self.lang_combo.addItem(STRINGS["en"]["lang_en"], "en")
        idx = 0 if settings.get("lang", "es") == "es" else 1
        self.lang_combo.setCurrentIndex(idx)
        form.addRow("Idioma", self.lang_combo)

        layout.addLayout(form)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #d9534f;")
        layout.addWidget(self.error_label)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply)
        buttons.button(QDialogButtonBox.Apply).setText("Aplicar")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.Apply).clicked.connect(self._apply_clicked)
        layout.addWidget(buttons)

    def collect_settings(self) -> dict:
        return {
            "freq_min": self.freq_min.value(),
            "freq_max": self.freq_max.value(),
            "freq_points": self.freq_points.value(),
            "log_x": self.log_x.isChecked(),
            "freq_markers": self.freq_markers.text(),
            "freq_report": self.freq_report.text(),
            "grid_alpha": self.grid_alpha.value(),
            "background": self.plot_bg.text().strip() or "k",
            "antialias": self.antialias.isChecked(),
            "meas_bins": self.meas_bins.value(),
            "lang": self.lang_combo.currentData(),
        }

    def set_error(self, message: str) -> None:
        self.error_label.setText(message)

    def _apply_clicked(self) -> None:
        if self._on_apply is not None:
            ok, msg = self._on_apply(self.collect_settings(), persist=True)
            self.set_error("" if ok else msg)

    def accept(self) -> None:
        if self._on_apply is not None:
            ok, msg = self._on_apply(self.collect_settings(), persist=True)
            self.set_error("" if ok else msg)
            if not ok:
                return
        super().accept()

class CompensatorTuner(QMainWindow):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Compensator Tuning")
        self.base_dir = Path(__file__).resolve().parent.parent
        self.settings_dir = self.base_dir / "settings"
        self.settings_path = self.settings_dir / "general_settings.json"
        self.lang = "es"

        self.freq_min = float(FREQ_GRID.min())
        self.freq_max = float(FREQ_GRID.max())
        self.freq_points = int(len(FREQ_GRID))
        self.log_x = True
        self.grid_alpha = 0.25
        self.plot_background = "k"
        self.antialias = True
        self.freq_markers = list(FREQ_MARKERS)

        self.freq = FREQ_GRID
        self.omega = OMEGA_GRID
        self.freq_report = FREQ_REPORT
        self.meas_bins = 500
        self._meas_raw_freq: np.ndarray | None = None
        self._meas_raw_mag: np.ndarray | None = None
        self._meas_raw_phase: np.ndarray | None = None
        self._meas_raw_mag_fwd: np.ndarray | None = None
        self._meas_raw_phase_fwd: np.ndarray | None = None

        self.comp_model = self._default_model()
        self.ref_model = self._default_model()
        self.mag_ref_db, self.phase_ref = self._compute_reference()
        self._last_mag_adj = self.mag_ref_db
        self._last_phase_adj = self.phase_ref
        self.reference_enabled = True
        self._undo_stack: list[dict] = []
        self._redo_stack: list[dict] = []
        self._undo_limit = 100
        self._undo_pending = False
        self._undo_timer = QTimer(self)
        self._undo_timer.setSingleShot(True)
        self._undo_timer.timeout.connect(self._clear_undo_pending)
        self._suspend_undo = False

        pg.setConfigOptions(antialias=self.antialias)
        self._build_ui()
        self._load_settings_from_disk()
        self._apply_language()
        self.update_plots()

    def _tr(self, key: str, **kwargs) -> str:
        bundle = STRINGS.get(self.lang, STRINGS["es"])
        text = bundle.get(key, key)
        try:
            return text.format(**kwargs)
        except Exception:
            return text

    # ---------- Models ----------
    def _default_model(self) -> CompensatorModel:
        model = CompensatorModel()
        model.add_block("gain")
        model.blocks[-1].params["K"] = 1.0
        model.add_block("leadlag")
        model.blocks[-1].params.update({"T": 0.004, "a": 1.7})
        model.add_block("leadlag")
        model.blocks[-1].params.update({"T": 0.005, "a": 1.4})
        model.add_block("sos")
        model.blocks[-1].params.update({"fn": 20.0, "zeta": 0.55, "K": 1.0})
        model.add_block("sos")
        model.blocks[-1].params.update({"fn": 30.0, "zeta": 0.3, "K": 1.0})
        return model

    def _compute_reference(self) -> Tuple[np.ndarray, np.ndarray]:
        h_ref = self.ref_model.freq_response(self.omega)
        return mag_to_db(np.abs(h_ref)), np.degrees(np.unwrap(np.angle(h_ref)))

    # ---------- UI ----------
    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(12)

        plots_layout = QVBoxLayout()
        plots_layout.setSpacing(12)
        self.mag_plot = self._create_plot_widget("Magnitud (dB)")
        self.phase_plot = self._create_plot_widget("Fase (grados)")
        plots_layout.addWidget(self.mag_plot, 1)
        plots_layout.addWidget(self.phase_plot, 1)
        root_layout.addLayout(plots_layout, 3)

        controls_layout = QVBoxLayout()
        controls_layout.setSpacing(12)
        controls_layout.addWidget(self._build_blocks_box())
        controls_layout.addWidget(self._build_log_box())
        root_layout.addLayout(controls_layout, 2)

        self._init_plots()
        self._init_shortcuts()
        self._update_undo_ui()

    def _init_shortcuts(self) -> None:
        undo_shortcut = QShortcut(QKeySequence.Undo, self)
        undo_shortcut.activated.connect(self._undo)
        redo_shortcut = QShortcut(QKeySequence.Redo, self)
        redo_shortcut.activated.connect(self._redo)

    def _create_plot_widget(self, y_label: str, show_legend: bool = True) -> pg.PlotWidget:
        plot = pg.PlotWidget(background=self.plot_background)
        plot.setLogMode(x=self.log_x, y=False)
        plot.showGrid(x=True, y=True, alpha=self.grid_alpha)
        plot.setLabel("bottom", "Frecuencia", units="Hz")
        plot.setLabel("left", y_label)
        plot.enableAutoRange(x=True, y=False)
        plot.getPlotItem().getAxis("bottom").enableAutoSIPrefix(False)
        if show_legend:
            plot.addLegend(offset=(10, 10))
        return plot

    def _init_plots(self) -> None:
        ref_pen = pg.mkPen((0, 114, 189), width=2)
        adj_pen = pg.mkPen((220, 20, 60), width=2)
        meas_pen = pg.mkPen((0, 160, 0), width=2)
        self._marker_lines_mag: list[pg.InfiniteLine] = []
        self._marker_lines_phase: list[pg.InfiniteLine] = []
        self._update_marker_lines()

        self.mag_ref_curve = self.mag_plot.plot(self.freq, self.mag_ref_db, pen=ref_pen, name="Referencia")
        self.mag_adj_curve = self.mag_plot.plot(self.freq, self.mag_ref_db, pen=adj_pen, name="Ajustada")
        self.mag_meas_curve = self.mag_plot.plot([], [], pen=meas_pen, name="Medido (Hfinv)")
        self.mag_meas_curve.setVisible(False)
        self.mag_meas_fwd_curve = self.mag_plot.plot(
            [], [], pen=pg.mkPen((120, 80, 200), width=2), name="Medido (Hf)"
        )
        self.mag_meas_fwd_curve.setVisible(False)

        self.phase_ref_curve = self.phase_plot.plot(self.freq, self.phase_ref, pen=ref_pen, name="Fase ref")
        self.phase_adj_curve = self.phase_plot.plot(self.freq, self.phase_ref, pen=adj_pen, name="Fase ajustada")
        self.phase_meas_curve = self.phase_plot.plot([], [], pen=meas_pen, name="Fase medida")
        self.phase_meas_curve.setVisible(False)
        self.phase_meas_fwd_curve = self.phase_plot.plot(
            [], [], pen=pg.mkPen((120, 80, 200), width=2), name="Fase medida (Hf)"
        )
        self.phase_meas_fwd_curve.setVisible(False)
        self._configure_curves(
            self.mag_ref_curve,
            self.mag_adj_curve,
            self.mag_meas_curve,
            self.mag_meas_fwd_curve,
            self.phase_ref_curve,
            self.phase_adj_curve,
            self.phase_meas_curve,
            self.phase_meas_fwd_curve,
        )
        self.mag_ref_curve.setVisible(self.reference_enabled)
        self.phase_ref_curve.setVisible(self.reference_enabled)
        self._apply_limits()

    def _configure_curves(self, *curves: pg.PlotDataItem) -> None:
        for curve in curves:
            curve.setDownsampling(auto=False)
            curve.setClipToView(False)
            curve.setDynamicRangeLimit(None)
        self.mag_meas_curve.setDownsampling(auto=True, method="peak")
        self.mag_meas_curve.setClipToView(True)
        self.mag_meas_fwd_curve.setDownsampling(auto=True, method="peak")
        self.mag_meas_fwd_curve.setClipToView(True)
        self.phase_meas_curve.setDownsampling(auto=True, method="peak")
        self.phase_meas_curve.setClipToView(True)
        self.phase_meas_fwd_curve.setDownsampling(auto=True, method="peak")
        self.phase_meas_fwd_curve.setClipToView(True)

    def _update_marker_lines(self) -> None:
        for line in self._marker_lines_mag:
            self.mag_plot.removeItem(line)
        for line in self._marker_lines_phase:
            self.phase_plot.removeItem(line)
        self._marker_lines_mag.clear()
        self._marker_lines_phase.clear()
        pen = pg.mkPen((150, 150, 150), width=1, style=Qt.DotLine)
        for marker in self.freq_markers:
            line_mag = pg.InfiniteLine(pos=marker, angle=90, pen=pen)
            line_phase = pg.InfiniteLine(pos=marker, angle=90, pen=pen)
            self.mag_plot.addItem(line_mag)
            self.phase_plot.addItem(line_phase)
            self._marker_lines_mag.append(line_mag)
            self._marker_lines_phase.append(line_phase)

    def _build_blocks_box(self) -> QGroupBox:
        box = QGroupBox("")
        self.blocks_box = box
        layout = QVBoxLayout(box)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        self.block_list = QListWidget()
        self.block_list.currentRowChanged.connect(self._on_block_selected)
        layout.addWidget(self.block_list, 2)

        btn_row = QHBoxLayout()
        self.add_btn = QPushButton()
        self.add_btn.clicked.connect(self._on_add_block)
        self.del_btn = QPushButton()
        self.del_btn.clicked.connect(self._on_delete_block)
        self.up_btn = QPushButton()
        self.up_btn.clicked.connect(self._on_move_up)
        self.down_btn = QPushButton()
        self.down_btn.clicked.connect(self._on_move_down)
        btn_row.addWidget(self.add_btn)
        btn_row.addWidget(self.del_btn)
        btn_row.addWidget(self.up_btn)
        btn_row.addWidget(self.down_btn)
        layout.addLayout(btn_row)

        self.params_scroll = QScrollArea()
        self.params_scroll.setWidgetResizable(True)
        self.params_container = QWidget()
        self.params_layout = QVBoxLayout(self.params_container)
        self.params_layout.setContentsMargins(0, 0, 0, 0)
        self.params_layout.setSpacing(8)
        self.params_scroll.setWidget(self.params_container)
        layout.addWidget(self.params_scroll, 3)

        self._refresh_block_list()
        return box

    def _build_log_box(self) -> QGroupBox:
        box = QGroupBox("")
        self.log_box = box
        layout = QVBoxLayout(box)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.table = QTableWidget(len(self.freq_report), 7, box)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setMinimumHeight(170)
        layout.addWidget(self.table)

        self.notes = QTextEdit(box)
        layout.addWidget(self.notes, 1)

        self.ref_group = QGroupBox("")
        ref_layout = QGridLayout(self.ref_group)
        ref_layout.setContentsMargins(8, 8, 8, 8)
        ref_layout.setHorizontalSpacing(8)
        ref_layout.setVerticalSpacing(6)
        self.reference_checkbox = QCheckBox()
        self.reference_checkbox.setChecked(self.reference_enabled)
        self.reference_checkbox.stateChanged.connect(self._on_reference_toggle)
        self.ref_copy_btn = QPushButton()
        self.ref_copy_btn.clicked.connect(self._copy_current_to_reference)
        self.ref_load_btn = QPushButton()
        self.ref_load_btn.clicked.connect(lambda: self._load_preset(target="reference"))
        self.preset_load_btn = QPushButton()
        self.preset_load_btn.clicked.connect(lambda: self._load_preset(target="current"))
        self.preset_save_btn = QPushButton()
        self.preset_save_btn.clicked.connect(self._save_preset)
        self.settings_btn = QPushButton()
        self.settings_btn.clicked.connect(self._open_settings)
        ref_layout.addWidget(self.reference_checkbox, 0, 0)
        ref_layout.addWidget(self.ref_copy_btn, 0, 1)
        ref_layout.addWidget(self.ref_load_btn, 0, 2)
        ref_layout.addWidget(self.preset_load_btn, 1, 0)
        ref_layout.addWidget(self.preset_save_btn, 1, 1)
        ref_layout.addWidget(self.settings_btn, 1, 2)
        ref_layout.setColumnStretch(3, 1)
        layout.addWidget(self.ref_group)

        self.proc_group = QGroupBox("")
        proc_row = QHBoxLayout(self.proc_group)
        self.unwrap_checkbox = QCheckBox()
        self.unwrap_checkbox.setChecked(True)
        self.unwrap_checkbox.stateChanged.connect(self._on_measured_processing_changed)
        self.smooth_checkbox = QCheckBox()
        self.smooth_checkbox.setChecked(False)
        self.smooth_checkbox.stateChanged.connect(self._on_measured_processing_changed)
        self.smooth_window = QSpinBox()
        self.smooth_window.setRange(5, 301)
        self.smooth_window.setSingleStep(2)
        self.smooth_window.setValue(41)
        self.smooth_window.setToolTip("Ventana (impar) para Savitzky-Golay")
        self.smooth_window.setEnabled(False)
        self.smooth_window.valueChanged.connect(self._on_measured_processing_changed)
        proc_row.addWidget(self.unwrap_checkbox)
        proc_row.addWidget(self.smooth_checkbox)
        self.window_label = QLabel()
        proc_row.addWidget(self.window_label)
        proc_row.addWidget(self.smooth_window)
        proc_row.addStretch(1)
        layout.addWidget(self.proc_group)

        self.actions_group = QGroupBox("")
        actions_row = QGridLayout(self.actions_group)
        actions_row.setContentsMargins(8, 8, 8, 8)
        actions_row.setHorizontalSpacing(8)
        actions_row.setVerticalSpacing(6)
        self.undo_btn = QPushButton()
        self.undo_btn.clicked.connect(self._undo)
        self.redo_btn = QPushButton()
        self.redo_btn.clicked.connect(self._redo)
        self.load_btn = QPushButton()
        self.load_btn.clicked.connect(self.load_measured_data)
        self.save_btn = QPushButton()
        self.save_btn.clicked.connect(self.save_snapshot)
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        actions_row.addWidget(self.undo_btn, 0, 0)
        actions_row.addWidget(self.redo_btn, 0, 1)
        actions_row.addWidget(self.load_btn, 0, 2)
        actions_row.addWidget(self.save_btn, 0, 3)
        actions_row.addWidget(self.status_label, 1, 0, 1, 4)
        actions_row.setColumnStretch(4, 1)

        layout.addWidget(self.actions_group)
        return box

    # ---------- Block editor ----------
    def _on_add_block(self) -> None:
        menu = QMenu(self)
        for type_name, cls in BLOCK_TYPES.items():
            action = menu.addAction(cls.display_name)
            action.triggered.connect(lambda _checked=False, t=type_name: self._add_block_type(t))
        menu.exec(self.cursor().pos())

    def _add_block_type(self, type_name: str) -> None:
        self._push_undo_state()
        self.comp_model.add_block(type_name)
        self._refresh_block_list(select_last=True)
        self.update_plots()

    def _on_delete_block(self) -> None:
        idx = self.block_list.currentRow()
        if idx < 0:
            return
        self._push_undo_state()
        self.comp_model.remove_block(idx)
        self._refresh_block_list()
        self.update_plots()

    def _on_move_up(self) -> None:
        idx = self.block_list.currentRow()
        if idx > 0:
            self._push_undo_state()
            self.comp_model.move_block(idx, idx - 1)
            self._refresh_block_list(select_index=idx - 1)
            self.update_plots()

    def _on_move_down(self) -> None:
        idx = self.block_list.currentRow()
        if 0 <= idx < len(self.comp_model.blocks) - 1:
            self._push_undo_state()
            self.comp_model.move_block(idx, idx + 1)
            self._refresh_block_list(select_index=idx + 1)
            self.update_plots()

    def _refresh_block_list(self, select_last: bool = False, select_index: int | None = None) -> None:
        self.block_list.blockSignals(True)
        self.block_list.clear()
        for blk in self.comp_model.blocks:
            self.block_list.addItem(QListWidgetItem(self._block_item_text(blk)))
        self.block_list.blockSignals(False)
        if select_last and self.block_list.count():
            self.block_list.setCurrentRow(self.block_list.count() - 1)
        elif select_index is not None:
            self.block_list.setCurrentRow(select_index)
        elif self.block_list.count():
            self.block_list.setCurrentRow(0)
        self._render_param_forms()

    def _on_block_selected(self, idx: int) -> None:
        # no-op; params panel shows all blocks
        pass

    def _render_param_forms(self) -> None:
        while self.params_layout.count():
            item = self.params_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for idx, blk in enumerate(self.comp_model.blocks):
            blk_cls = BLOCK_TYPES.get(blk.type_name)
            if blk_cls is None:
                continue
            grp = QGroupBox(f"{blk_cls.display_name}")
            form = QFormLayout(grp)
            form.setContentsMargins(8, 8, 8, 8)
            form.setSpacing(6)
            for key, meta in blk_cls.params_meta.items():
                slider = QSlider(Qt.Horizontal)
                slider.setRange(0, 1000)
                spin = QDoubleSpinBox()
                spin.setRange(meta.min, meta.max)
                spin.setDecimals(6)
                spin.setSingleStep((meta.max - meta.min) / 200.0 if meta.scale == "linear" else 0.01)
                val = blk.params.get(key, meta.default)
                slider.setValue(self._val_to_slider(val, meta))
                spin.setValue(val)
                slider.valueChanged.connect(
                    lambda v, i=idx, k=key, m=meta, s=spin: self._on_slider_change(i, k, m, v, s)
                )
                spin.valueChanged.connect(
                    lambda v, i=idx, k=key, m=meta, sl=slider: self._on_spin_change(i, k, m, v, sl)
                )
                row = QWidget()
                row_layout = QHBoxLayout(row)
                row_layout.setContentsMargins(0, 0, 0, 0)
                row_layout.addWidget(slider, 1)
                row_layout.addWidget(spin, 0)
                form.addRow(f"{meta.label} {meta.unit}".strip(), row)
            self.params_layout.addWidget(grp)
        self.params_layout.addStretch(1)

    def _on_slider_change(self, blk_idx: int, key: str, meta: ParamMeta, slider_value: int, spin: QDoubleSpinBox) -> None:
        val = self._slider_to_val(slider_value, meta)
        if spin.value() != val:
            spin.blockSignals(True)
            spin.setValue(val)
            spin.blockSignals(False)
        self._update_param(blk_idx, key, val)

    def _on_spin_change(self, blk_idx: int, key: str, meta: ParamMeta, value: float, slider: QSlider) -> None:
        val = float(np.clip(value, meta.min, meta.max))
        slider_val = self._val_to_slider(val, meta)
        if slider.value() != slider_val:
            slider.blockSignals(True)
            slider.setValue(slider_val)
            slider.blockSignals(False)
        self._update_param(blk_idx, key, val)

    def _update_param(self, blk_idx: int, key: str, value: float) -> None:
        if 0 <= blk_idx < len(self.comp_model.blocks):
            self._push_undo_state()
            self.comp_model.blocks[blk_idx].params[key] = value
            self._update_block_list_item(blk_idx)
            self.update_plots()

    def _block_item_text(self, blk) -> str:
        cls = BLOCK_TYPES.get(blk.type_name)
        name = cls.display_name if cls else blk.type_name
        params_text = ", ".join(f"{k}={v:.4g}" for k, v in blk.params.items())
        return f"{name} ({params_text})"

    def _update_block_list_item(self, idx: int) -> None:
        if 0 <= idx < self.block_list.count():
            blk = self.comp_model.blocks[idx]
            self.block_list.item(idx).setText(self._block_item_text(blk))

    @staticmethod
    def _slider_to_val(slider_value: int, meta: ParamMeta) -> float:
        ratio = np.clip(slider_value / 1000.0, 0.0, 1.0)
        if meta.scale == "log":
            return float(np.exp(np.log(meta.min) + ratio * (np.log(meta.max) - np.log(meta.min))))
        return float(meta.min + ratio * (meta.max - meta.min))

    @staticmethod
    def _val_to_slider(value: float, meta: ParamMeta) -> int:
        value = np.clip(value, meta.min, meta.max)
        if meta.scale == "log":
            ratio = (np.log(value) - np.log(meta.min)) / (np.log(meta.max) - np.log(meta.min))
        else:
            ratio = (value - meta.min) / (meta.max - meta.min)
        return int(round(np.clip(ratio, 0.0, 1.0) * 1000))

    # ---------- Undo / Redo ----------
    def _clear_undo_pending(self) -> None:
        self._undo_pending = False

    def _push_undo_state(self) -> None:
        if self._suspend_undo:
            return
        if not self._undo_pending:
            self._undo_stack.append(self.comp_model.to_dict())
            if len(self._undo_stack) > self._undo_limit:
                self._undo_stack.pop(0)
            self._redo_stack.clear()
            self._undo_pending = True
        self._undo_timer.start(350)
        self._update_undo_ui()

    def _apply_model(self, model: CompensatorModel) -> None:
        self.comp_model = model
        self._refresh_block_list(select_last=False)
        self.update_plots()

    def _undo(self) -> None:
        if not self._undo_stack:
            return
        self._suspend_undo = True
        try:
            self._redo_stack.append(self.comp_model.to_dict())
            data = self._undo_stack.pop()
            self._undo_pending = False
            self._undo_timer.stop()
            self._apply_model(CompensatorModel.from_dict(data))
        finally:
            self._suspend_undo = False
            self._update_undo_ui()

    def _redo(self) -> None:
        if not self._redo_stack:
            return
        self._suspend_undo = True
        try:
            self._undo_stack.append(self.comp_model.to_dict())
            data = self._redo_stack.pop()
            self._undo_pending = False
            self._undo_timer.stop()
            self._apply_model(CompensatorModel.from_dict(data))
        finally:
            self._suspend_undo = False
            self._update_undo_ui()

    def _update_undo_ui(self) -> None:
        if hasattr(self, "undo_btn"):
            self.undo_btn.setEnabled(bool(self._undo_stack))
        if hasattr(self, "redo_btn"):
            self.redo_btn.setEnabled(bool(self._redo_stack))

    # ---------- Plot updates ----------
    def update_plots(self) -> None:
        h_adj = self.comp_model.freq_response(self.omega)
        mag_adj_db = mag_to_db(np.abs(h_adj))
        phase_adj = np.degrees(np.unwrap(np.angle(h_adj)))

        self.mag_adj_curve.setData(self.freq, mag_adj_db)
        self.phase_adj_curve.setData(self.freq, phase_adj)
        self._update_summary_table(mag_adj_db, phase_adj)
        self._autoscale(mag_adj_db, phase_adj)
        self._apply_limits()

        self._last_mag_adj = mag_adj_db
        self._last_phase_adj = phase_adj

    def _update_summary_table(self, mag_adj_db: np.ndarray, phase_adj: np.ndarray) -> None:
        mag_adj_rows = np.interp(self.freq_report, self.freq, mag_adj_db)
        phase_adj_rows = np.interp(self.freq_report, self.freq, phase_adj)
        if self.reference_enabled:
            mag_ref_rows = np.interp(self.freq_report, self.freq, self.mag_ref_db)
            phase_ref_rows = np.interp(self.freq_report, self.freq, self.phase_ref)
            rows = np.column_stack(
                [
                    self.freq_report,
                    mag_ref_rows,
                    mag_adj_rows,
                    mag_adj_rows - mag_ref_rows,
                    phase_ref_rows,
                    phase_adj_rows,
                    phase_adj_rows - phase_ref_rows,
                ]
            )
            for r, values in enumerate(rows):
                for c, val in enumerate(values):
                    item = QTableWidgetItem(f"{val:.3f}")
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    self.table.setItem(r, c, item)
        else:
            for r, freq in enumerate(self.freq_report):
                display = [
                    f"{freq:.3f}",
                    "-",
                    f"{mag_adj_rows[r]:.3f}",
                    "-",
                    "-",
                    f"{phase_adj_rows[r]:.3f}",
                    "-",
                ]
                for c, val in enumerate(display):
                    item = QTableWidgetItem(val)
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    self.table.setItem(r, c, item)
        self.table.resizeColumnsToContents()

    def _autoscale(self, mag_adj_db: np.ndarray, phase_adj: np.ndarray) -> None:
        def limits(arrays, pad: float):
            data = np.hstack([np.asarray(a, dtype=float).ravel() for a in arrays if a is not None])
            data = data[np.isfinite(data)]
            if data.size == 0:
                return None
            ymin = float(np.min(data))
            ymax = float(np.max(data))
            margin = max(pad, 0.05 * max(ymax - ymin, 1.0))
            return ymin - margin, ymax + margin

        mag_arrays = [mag_adj_db]
        phase_arrays = [phase_adj]
        if self.reference_enabled:
            mag_arrays.insert(0, self.mag_ref_db)
            phase_arrays.insert(0, self.phase_ref)
        if self.mag_meas_curve.isVisible():
            _, y = self.mag_meas_curve.getData()
            if y is not None:
                mag_arrays.append(np.asarray(y))
        if self.mag_meas_fwd_curve.isVisible():
            _, y = self.mag_meas_fwd_curve.getData()
            if y is not None:
                mag_arrays.append(np.asarray(y))
        if self.phase_meas_curve.isVisible():
            _, y = self.phase_meas_curve.getData()
            if y is not None:
                phase_arrays.append(np.asarray(y))
        if self.phase_meas_fwd_curve.isVisible():
            _, y = self.phase_meas_fwd_curve.getData()
            if y is not None:
                phase_arrays.append(np.asarray(y))

        mag_limits = limits(mag_arrays, pad=1.0)
        if mag_limits:
            self.mag_plot.setYRange(*mag_limits, padding=0)
        phase_limits = limits(phase_arrays, pad=5.0)
        if phase_limits:
            self.phase_plot.setYRange(*phase_limits, padding=0)

    def _apply_limits(self) -> None:
        xmin = max(1e-6, self.freq_min * 0.95)
        xmax_candidates = [float(self.freq.max())]
        if self._meas_raw_freq is not None and len(self._meas_raw_freq) > 0:
            xmax_candidates.append(float(np.max(self._meas_raw_freq)))
        xmax = max(xmax_candidates)
        for plot in (self.mag_plot, self.phase_plot):
            vb = plot.getPlotItem().getViewBox()
            vb.setLimits(xMin=xmin, xMax=xmax * 1.05)
            plot.enableAutoRange(x=True, y=False)
            vb.enableAutoRange(axis=pg.ViewBox.XAxis, enable=True)
            vb.updateAutoRange()

    def _current_settings(self) -> dict:
        return {
            "freq_min": self.freq_min,
            "freq_max": self.freq_max,
            "freq_points": self.freq_points,
            "log_x": self.log_x,
            "freq_markers": ", ".join(f"{m:g}" for m in self.freq_markers),
            "freq_report": ", ".join(f"{f:g}" for f in self.freq_report),
            "grid_alpha": self.grid_alpha,
            "background": self.plot_background,
            "antialias": self.antialias,
            "meas_bins": self.meas_bins,
            "lang": self.lang,
        }

    @staticmethod
    def _parse_freq_list(text: str, fallback: list[float]) -> list[float]:
        parts = [p for p in re.split(r"[,\s]+", text.strip()) if p]
        values: list[float] = []
        for part in parts:
            try:
                val = float(part)
            except ValueError:
                continue
            if val > 0:
                values.append(val)
        if not values:
            return fallback
        values = sorted(set(values))
        return values

    def _rebuild_frequency_grid(self) -> None:
        if self.log_x:
            self.freq = np.logspace(np.log10(self.freq_min), np.log10(self.freq_max), self.freq_points)
        else:
            self.freq = np.linspace(self.freq_min, self.freq_max, self.freq_points)
        self.omega = 2 * np.pi * self.freq

    def _apply_plot_style(self) -> None:
        pg.setConfigOptions(antialias=self.antialias)
        for plot in (self.mag_plot, self.phase_plot):
            plot.setBackground(self.plot_background)
            plot.setLogMode(x=self.log_x, y=False)
            plot.showGrid(x=True, y=True, alpha=self.grid_alpha)

    def _apply_language(self) -> None:
        t = self._tr
        self.setWindowTitle(t("title"))
        # Group titles
        self.blocks_box.setTitle(t("blocks_box"))
        self.log_box.setTitle(t("notes_box"))
        self.ref_group.setTitle(t("ref_group"))
        self.proc_group.setTitle(t("phase_group"))
        self.actions_group.setTitle(t("actions"))
        # Buttons and labels
        self.add_btn.setText(t("add_block"))
        self.del_btn.setText(t("delete"))
        self.up_btn.setText(t("move_up"))
        self.down_btn.setText(t("move_down"))

        self.reference_checkbox.setText(t("show_ref"))
        self.ref_copy_btn.setText(t("copy_to_ref"))
        self.ref_load_btn.setText(t("load_ref_preset"))
        self.preset_load_btn.setText(t("load_preset"))
        self.preset_save_btn.setText(t("save_preset"))
        self.settings_btn.setText(t("settings"))

        self.unwrap_checkbox.setText(t("unwrap"))
        self.smooth_checkbox.setText(t("smooth"))
        self.window_label.setText(t("window"))

        self.undo_btn.setText(t("undo"))
        self.redo_btn.setText(t("redo"))
        self.load_btn.setText(t("load_data"))
        self.save_btn.setText(t("save_snapshot"))

        self.notes.setPlaceholderText(t("notes_placeholder"))

        # Table headers
        headers = t("table_headers")
        if isinstance(headers, list) and len(headers) == self.table.columnCount():
            self.table.setHorizontalHeaderLabels(headers)

        # Settings dialog language labels not updated here (they reflect current lang in creation)

        # Axis labels
        bottom = "Frequency" if self.lang == "en" else "Frecuencia"
        mag_left = "Magnitude (dB)" if self.lang == "en" else "Magnitud (dB)"
        phase_left = "Phase (deg)" if self.lang == "en" else "Fase (grados)"
        self.mag_plot.setLabel("bottom", bottom, units="Hz")
        self.mag_plot.setLabel("left", mag_left)
        self.phase_plot.setLabel("bottom", bottom, units="Hz")
        self.phase_plot.setLabel("left", phase_left)

    def _status(self, key: str, **kwargs) -> None:
        self.status_label.setText(self._tr(key, **kwargs))

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self, self._current_settings(), on_apply=self._apply_settings)
        dialog.exec()

    def _apply_settings(self, settings: dict, persist: bool = True) -> tuple[bool, str]:
        def fail(message: str) -> tuple[bool, str]:
            msg = self._tr("status_invalid_cfg", msg=message)
            self.status_label.setText(msg)
            return False, msg

        freq_min = float(settings["freq_min"])
        freq_max = float(settings["freq_max"])
        if freq_min <= 0 or freq_max <= 0 or freq_max <= freq_min:
            return fail("Configuración inválida: rango de frecuencia.")
        if settings["log_x"] and freq_min <= 0:
            return fail("Configuración inválida: log requiere freq > 0.")
        freq_points = int(settings["freq_points"])
        if freq_points < 10:
            return fail("Configuración inválida: puntos insuficientes.")

        background = settings["background"] or "k"
        try:
            pg.mkColor(background)
        except Exception:
            return fail("Configuración inválida: color de fondo.")

        self.freq_min = freq_min
        self.freq_max = freq_max
        self.freq_points = freq_points
        self.log_x = bool(settings["log_x"])
        self.grid_alpha = float(settings["grid_alpha"])
        self.plot_background = background
        self.antialias = bool(settings["antialias"])
        self.meas_bins = int(settings["meas_bins"])
        self.lang = settings.get("lang", "es")

        self.freq_markers = self._parse_freq_list(settings["freq_markers"], self.freq_markers)
        self.freq_report = np.array(self._parse_freq_list(settings["freq_report"], list(self.freq_report)))

        self._apply_plot_style()
        self._rebuild_frequency_grid()
        self._update_marker_lines()

        self.mag_ref_db, self.phase_ref = self._compute_reference()
        self.mag_ref_curve.setData(self.freq, self.mag_ref_db)
        self.phase_ref_curve.setData(self.freq, self.phase_ref)

        h_adj = self.comp_model.freq_response(self.omega)
        mag_adj_db = mag_to_db(np.abs(h_adj))
        phase_adj = np.degrees(np.unwrap(np.angle(h_adj)))
        self.mag_adj_curve.setData(self.freq, mag_adj_db)
        self.phase_adj_curve.setData(self.freq, phase_adj)
        self._last_mag_adj = mag_adj_db
        self._last_phase_adj = phase_adj

        self.table.setRowCount(len(self.freq_report))
        self._update_summary_table(mag_adj_db, phase_adj)
        self._update_measured_curves()
        self._autoscale(mag_adj_db, phase_adj)
        self._apply_limits()
        self._status("status_config")
        if persist:
            self._save_settings_to_disk()
        self._apply_language()
        return True, ""

    def _save_settings_to_disk(self) -> None:
        try:
            self.settings_dir.mkdir(parents=True, exist_ok=True)
            with self.settings_path.open("w", encoding="utf-8") as f:
                json.dump(self._current_settings(), f, indent=2, ensure_ascii=False)
        except Exception as exc:
            self._status("status_save_cfg_error", msg=str(exc))

    def _load_settings_from_disk(self) -> None:
        if not self.settings_path.is_file():
            return
        try:
            with self.settings_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            self._apply_settings(data, persist=False)
        except Exception as exc:
            self._status("status_load_cfg_error", msg=str(exc))

    def _on_reference_toggle(self) -> None:
        self.reference_enabled = self.reference_checkbox.isChecked()
        self.mag_ref_curve.setVisible(self.reference_enabled)
        self.phase_ref_curve.setVisible(self.reference_enabled)
        self._update_summary_table(self._last_mag_adj, self._last_phase_adj)
        self._autoscale(self._last_mag_adj, self._last_phase_adj)
        self._apply_limits()

    def _copy_current_to_reference(self) -> None:
        self.ref_model = CompensatorModel.from_dict(self.comp_model.to_dict())
        self.mag_ref_db, self.phase_ref = self._compute_reference()
        self.mag_ref_curve.setData(self.freq, self.mag_ref_db)
        self.phase_ref_curve.setData(self.freq, self.phase_ref)
        self._status("status_updated_ref")
        self._update_summary_table(self._last_mag_adj, self._last_phase_adj)
        self._autoscale(self._last_mag_adj, self._last_phase_adj)

    def _load_preset(self, target: str = "current") -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Cargar preset",
            str(self.base_dir),
            "JSON Files (*.json);;All Files (*)",
        )
        if not file_path:
            return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            model = CompensatorModel.from_dict(data)
        except Exception as exc:
            self._status("status_error", msg=str(exc))
            return

        if target == "reference":
            self.ref_model = model
            self.mag_ref_db, self.phase_ref = self._compute_reference()
            self.mag_ref_curve.setData(self.freq, self.mag_ref_db)
            self.phase_ref_curve.setData(self.freq, self.phase_ref)
            self._status("status_loaded_ref", name=Path(file_path).name)
            self._update_summary_table(self._last_mag_adj, self._last_phase_adj)
            self._autoscale(self._last_mag_adj, self._last_phase_adj)
        else:
            self._push_undo_state()
            self.comp_model = model
            self._refresh_block_list(select_last=False)
            self.update_plots()
            self._status("status_loaded_preset", name=Path(file_path).name)

    def _save_preset(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar preset",
            str(self.base_dir / "compensator_preset.json"),
            "JSON Files (*.json);;All Files (*)",
        )
        if not file_path:
            return
        try:
            data = self.comp_model.to_dict()
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self._status("status_saved_preset", name=Path(file_path).name)
        except Exception as exc:
            self._status("status_error", msg=str(exc))

    # ---------- IO ----------
    def load_measured_data(self) -> None:
        try:
            default_dir = self.base_dir / "data"
            if not default_dir.is_dir():
                default_dir = self.base_dir
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Seleccione CSV de transferencia experimental",
                str(default_dir),
                "CSV Files (*.csv);;All Files (*)",
            )
            csv_path = Path(file_path) if file_path else default_dir / "transfer_measured.csv"
            if not csv_path.is_file():
                raise FileNotFoundError(self._tr("status_no_csv"))
            freq, mag_db_inv, phase_deg_inv, mag_db_fwd, phase_deg_fwd = load_transfer_csv(csv_path)
            source_msg = f"CSV: {csv_path.name}"
        except Exception as exc:
            self._status("status_error", msg=str(exc))
            return

        self._meas_raw_freq = freq
        self._meas_raw_mag = mag_db_inv
        self._meas_raw_phase = phase_deg_inv
        self._meas_raw_mag_fwd = mag_db_fwd
        self._meas_raw_phase_fwd = phase_deg_fwd

        self._update_measured_curves()

        self._status("status_loaded", source=source_msg)
        self._autoscale(self._last_mag_adj, self._last_phase_adj)
        self._apply_limits()

    def save_snapshot(self) -> None:
        phase = self._last_phase_adj
        phase_1 = float(np.interp(1.0, self.freq, phase))
        phase_3 = float(np.interp(3.0, self.freq, phase))
        blocks_desc = "; ".join(f"{blk.type_name}:{blk.params}" for blk in self.comp_model.blocks)
        row = {
            "timestamp": datetime.now().isoformat(),
            "phase_1Hz_deg": phase_1,
            "phase_3Hz_deg": phase_3,
            "blocks": blocks_desc,
            "note": self.notes.toPlainText().strip(),
        }
        outfile = self.base_dir / "tuning_log.csv"
        write_header = not outfile.exists()
        with outfile.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "timestamp",
                    "phase_1Hz_deg",
                    "phase_3Hz_deg",
                    "blocks",
                    "note",
                ],
            )
            if write_header:
                writer.writeheader()
            writer.writerow(row)
        self._status("status_saved_snapshot", name=outfile.name)

    # ---------- Helpers ----------
    def _thin_data(self, x: np.ndarray, y: np.ndarray, max_points: int = 4000) -> Tuple[np.ndarray, np.ndarray]:
        if len(x) <= max_points:
            return x, y
        step = max(1, int(len(x) / max_points))
        return x[::step], y[::step]

    def _on_measured_processing_changed(self) -> None:
        if self.smooth_window is not None:
            self.smooth_window.setEnabled(self.smooth_checkbox.isChecked())
            val = int(self.smooth_window.value())
            if val % 2 == 0:
                self.smooth_window.blockSignals(True)
                self.smooth_window.setValue(val + 1)
                self.smooth_window.blockSignals(False)
        self._update_measured_curves()

    def _process_phase(self, phase_deg: np.ndarray | None) -> np.ndarray | None:
        if phase_deg is None:
            return None
        phase = np.asarray(phase_deg, dtype=float)
        if self.unwrap_checkbox.isChecked():
            phase = np.degrees(np.unwrap(np.deg2rad(phase)))
        if self.smooth_checkbox.isChecked():
            window = self._get_smooth_window(len(phase))
            if window >= 5:
                poly = 3 if window >= 7 else 2
                phase = savgol_filter(phase, window, polyorder=poly, mode="interp")
        return phase

    def _get_smooth_window(self, length: int) -> int:
        if not self.smooth_checkbox.isChecked():
            return 0
        window = int(self.smooth_window.value())
        if window % 2 == 0:
            window += 1
        if length <= 0:
            return 0
        if window > length:
            window = length if length % 2 == 1 else max(1, length - 1)
        return window

    def _update_measured_curves(self) -> None:
        if (
            self._meas_raw_freq is None
            or self._meas_raw_mag is None
            or self._meas_raw_phase is None
            or self._meas_raw_mag_fwd is None
            or self._meas_raw_phase_fwd is None
        ):
            return

        freq = self._meas_raw_freq
        mag_inv = self._meas_raw_mag
        phase_inv = self._process_phase(self._meas_raw_phase)
        mag_fwd = self._meas_raw_mag_fwd
        phase_fwd = self._process_phase(self._meas_raw_phase_fwd)
        if phase_inv is None or phase_fwd is None:
            return

        freq_inv_d, mag_inv_d, phase_inv_d = self._decimate_log(freq, mag_inv, phase_inv, self.meas_bins)
        freq_inv_d, phase_inv_d = self._thin_data(freq_inv_d, phase_inv_d)
        freq_inv_d, mag_inv_d = self._thin_data(freq_inv_d, mag_inv_d)

        freq_fwd_d, mag_fwd_d, phase_fwd_d = self._decimate_log(freq, mag_fwd, phase_fwd, self.meas_bins)
        freq_fwd_d, phase_fwd_d = self._thin_data(freq_fwd_d, phase_fwd_d)
        freq_fwd_d, mag_fwd_d = self._thin_data(freq_fwd_d, mag_fwd_d)

        self.mag_meas_curve.setData(freq_inv_d, mag_inv_d)
        self.phase_meas_curve.setData(freq_inv_d, phase_inv_d)
        self.mag_meas_curve.setVisible(True)
        self.phase_meas_curve.setVisible(True)

        self.mag_meas_fwd_curve.setData(freq_fwd_d, mag_fwd_d)
        self.phase_meas_fwd_curve.setData(freq_fwd_d, phase_fwd_d)
        self.mag_meas_fwd_curve.setVisible(True)
        self.phase_meas_fwd_curve.setVisible(True)
        self._autoscale(self._last_mag_adj, self._last_phase_adj)
        self._apply_limits()

    @staticmethod
    def _decimate_log(
        freq: np.ndarray, mag_db: np.ndarray, phase_deg: np.ndarray, bins: int
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        mask = freq > 0
        freq = freq[mask]
        mag_db = mag_db[mask]
        phase_deg = phase_deg[mask]
        if len(freq) == 0:
            return freq, mag_db, phase_deg
        fmin = freq.min()
        fmax = freq.max()
        if fmin <= 0 or fmax <= fmin:
            return freq, mag_db, phase_deg
        edges = np.geomspace(fmin, fmax, num=bins + 1)
        out_f = []
        out_mag = []
        out_ph = []
        idx = 0
        for i in range(len(edges) - 1):
            left, right = edges[i], edges[i + 1]
            while idx < len(freq) and freq[idx] < left:
                idx += 1
            start = idx
            while idx < len(freq) and freq[idx] < right:
                idx += 1
            end = idx
            if end > start:
                out_f.append(np.mean(freq[start:end]))
                out_mag.append(np.max(mag_db[start:end]))
                out_ph.append(np.mean(phase_deg[start:end]))
        return np.array(out_f), np.array(out_mag), np.array(out_ph)


def run_app() -> None:
    app = QApplication(sys.argv)
    window = CompensatorTuner()
    window.resize(1280, 800)
    window.show()
    sys.exit(app.exec())
