# CompTuner

Manual, block-based compensator tuning tool for measured frequency responses. Built with PySide6 + pyqtgraph; includes live Bode plots, presets, snapshots, undo/redo, and bilingual manuals.

## Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m comp_tuner
```

Open **Configuración/Settings** to adjust plot ranges and language, click **Cargar datos/Load data** to load a CSV, tune blocks, and save a preset or snapshot.

Language: switch between Español/English in the Settings dialog.

Screenshot: `ui.png`

## Docs

- English manual: `docs/MANUAL.md`
- Manual en español: `docs/MANUAL_ES.md`

## License

GPL-3.0-or-later. See `LICENSE`.
