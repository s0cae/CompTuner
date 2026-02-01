# Manual de CompTuner

Audiencia: investigadores, desarrolladores y usuarios de laboratorio que necesitan un flujo
manual y confiable para la sintonía iterativa de compensadores en el dominio de la frecuencia.

## Tabla de contenidos

- [1) Visión general](#1-visión-general)
- [2) Requisitos](#2-requisitos)
- [3) Instalación](#3-instalación)
- [4) Ejecutar la aplicación](#4-ejecutar-la-aplicación)
- [5) Conceptos clave](#5-conceptos-clave)
- [6) Formatos de datos](#6-formatos-de-datos)
- [7) Guía de la interfaz](#7-guía-de-la-interfaz)
- [8) Presets](#8-presets)
- [9) Snapshots (registro de sintonía)](#9-snapshots-registro-de-sintonía)
- [10) Deshacer / Rehacer](#10-deshacer--rehacer)
- [11) Configuración](#11-configuración)
- [12) Flujos de trabajo comunes](#12-flujos-de-trabajo-comunes)
- [13) Solución de problemas](#13-solución-de-problemas)
- [14) Notas para desarrolladores](#14-notas-para-desarrolladores)
  - [14.1 Agregar bloques personalizados](#141-agregar-bloques-personalizados)

---

## 1) Visión general

CompTuner es una aplicación de escritorio para la sintonía manual e iterativa de compensadores
usando datos de respuesta en frecuencia medidos. Se enfoca en:

- Construcción de compensadores basada en bloques (ganancia, lead/lag, 2do orden, polo-cero real).
- Diagramas de Bode en vivo (magnitud + fase).
- Superposición de planta medida (Hf y su inversa Hfinv).
- Lecturas numéricas en frecuencias clave.
- Presets, snapshots, deshacer/rehacer y configuración persistente.

La herramienta es intencionalmente manual: permite visualizar el impacto de cambios de parámetros
de forma rápida y consistente, sin forzar optimización automática.

---

## 2) Requisitos

- Windows (probado en Windows 10/11).
- Python 3.11+ recomendado.
- Dependencias en `requirements.txt`:
  - PySide6
  - pyqtgraph
  - numpy
  - scipy

---

## 3) Instalación

Desde la raíz del proyecto:

1) Crear y activar el entorno virtual:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Nota PowerShell (opcional):
- Si la activación está bloqueada por la política de ejecución, puede ejecutar una vez:
  `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`
  o bien omitir la activación y usar siempre `.\.venv\Scripts\python ...`.

2) Instalar dependencias:

```powershell
.\.venv\Scripts\python -m pip install -r requirements.txt
```

Si `python` no está en PATH, use la ruta completa a su ejecutable de Python o el
Python Launcher (si está disponible) con `py -m venv .venv`.

---

## 4) Ejecutar la aplicación

```powershell
.\.venv\Scripts\python -m comp_tuner
```

Inicio rápido:
1) Haga clic en **Cargar datos** y cargue un CSV.
2) Ajuste bloques/parámetros y observe los Bode.
3) Guarde un snapshot (**Guardar snapshot**) y/o un preset (**Guardar preset**) para reproducibilidad.

---

## 5) Conceptos clave

### 5.1 Modelo del compensador
El compensador es una cascada de bloques:

```
Hc(jw) = product_i Hi(jw)
```

Cada bloque tiene parámetros y una respuesta en frecuencia. Al cambiar un parámetro,
la respuesta total se recalcula y se grafica inmediatamente.

### 5.2 Referencia vs actual
La aplicación mantiene:

- Un compensador **de referencia** (línea base).
- El compensador **actual** (el que se está sintonizando).

Se puede:
- Mostrar/ocultar la referencia.
- Copiar actual -> referencia.
- Cargar un preset como referencia.

### 5.3 Datos medidos
Los datos medidos pueden cargarse como:
- Hf (transferencia directa) y el sistema calcula Hfinv.
- O directamente como Hf complejo.

Se pueden graficar Hf y Hfinv para comparación visual.

### 5.4 Biblioteca de bloques (incluida)

CompTuner incluye actualmente estos tipos de bloque (ver `comp_tuner/blocks.py`):

- Ganancia (`gain`): `H(s) = K`
  - parámetros: `K` (sin unidades, slider logarítmico)
- Lead/Lag (`leadlag`): `H(s) = (a T s + 1) / (T s + 1)`
  - parámetros: `T` (segundos), `a` (sin unidades)
  - interpretación: `a > 1` agrega adelanto de fase; `a < 1` agrega atraso de fase.
- Sección de 2do orden (`sos`): `H(s) = K * wn^2 / (s^2 + 2*zeta*wn*s + wn^2)`
  - parámetros: `fn` (Hz), `zeta` (sin unidades), `K` (sin unidades)
- Polo-cero real (`real_pole_zero`): `H(s) = K * (s/wz + 1) / (s/wp + 1)`
  - parámetros: `fz` (Hz), `fp` (Hz), `K` (sin unidades)

Todos los parámetros de frecuencia se ingresan en Hz y se convierten internamente usando `w = 2*pi*f`.

---

## 6) Formatos de datos

### 6.1 CSV de entrada
El cargador acepta **uno de estos esquemas** (cabecera requerida):

1) Respuesta compleja:
```
freq_hz,h_real,h_imag
```

2) Magnitud + fase:
```
freq_hz,mag_db,phase_deg
```

Notas:
- La frecuencia debe ser positiva.
- La fase se interpreta en grados.

### 6.2 Ejemplo de CSV
```
freq_hz,mag_db,phase_deg
0.1,-20.3,45.0
0.2,-18.7,41.2
0.5,-12.1,10.0
```

### 6.3 Generar CSV desde MAT (opcional)
Si tiene archivos MAT `data_a1_cut.mat` y `data_xddot_d_cut.mat`, puede generar un
CSV con:

```powershell
.\.venv\Scripts\python generate_transfer_csv.py --out data\transfer_measured.csv
```

---

## 7) Guía de la interfaz

### 7.1 Gráficas
- **Magnitud (dB)**: magnitud de referencia, actual y medidas.
- **Fase (grados)**: fase de referencia, actual y medidas.

### 7.2 Editor de bloques
En "Bloques del compensador":
- Agregar, eliminar, mover bloques.
- Ajustar parámetros con sliders o campos numéricos.

### 7.3 Notas y resumen
"Notas y resumen" incluye:
- Tabla de valores en frecuencias clave (resumen).
- Campo de notas guardado en snapshots.

### 7.4 Procesamiento de fase (datos medidos)
- **Desenvolver fase medida**: hace unwrap para continuidad (elimina saltos +/-180).
- **Suavizar fase medida**: aplica suavizado Savitzky-Golay (opcional).
- **Ventana**: longitud de la ventana de suavizado (número impar).

Por qué es importante desenvolver (unwrap):
- La fase usualmente se reporta como valor principal en [-180, 180] grados (módulo 360), lo que introduce saltos artificiales.
- CompTuner desenvuelve la fase del modelo, por lo que desenvolver la fase medida hace la comparación consistente y permite
  interpretar la pendiente de fase (comportamiento tipo retraso).

El suavizado está apagado por defecto y debe usarse con cuidado (una ventana grande puede ocultar detalles estrechos).

### 7.5 Cargar CSV medido

1) Haga clic en **Cargar datos** y seleccione un archivo CSV.
2) Si cancela el diálogo, CompTuner intentará cargar `data/transfer_measured.csv` (si existe).

Para graficar más rápido, las curvas medidas se deciman en una rejilla logarítmica de frecuencia. Puede controlar esto con
la opción "Bins medidos" (más alto = más puntos, más lento).

---

## 8) Presets

Los presets son archivos JSON que guardan la lista de bloques del compensador.

### 8.1 Cargar / guardar
- **Cargar preset**: reemplaza el compensador actual.
- **Guardar preset**: guarda el compensador actual en JSON.
- **Cargar preset ref**: carga un preset como referencia.

### 8.2 Formato de preset (ejemplo)
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

Sugerencia: considere guardar presets en una carpeta dedicada (por ejemplo `presets/`) y versionarlos si desea
líneas base reproducibles y revisables.

---

## 9) Snapshots (registro de sintonía)

Los snapshots registran el estado actual del compensador y valores clave de fase.

- Archivo: `tuning_log.csv`
- Campos:
  - `timestamp` (ISO 8601)
  - `phase_1Hz_deg`
  - `phase_3Hz_deg`
  - `blocks` (lista legible de bloques; para reproducibilidad exacta use presets)
  - `note` (texto del campo de notas)

Use los snapshots como rastro de auditoría de la sesión de sintonía manual. Para reproducir exactamente una
configuración de compensador, guarde también un preset JSON.

---

## 10) Deshacer / Rehacer

- **Deshacer**: Ctrl+Z (o botón "Deshacer")
- **Rehacer**: Ctrl+Y (o botón "Rehacer")

Deshacer/rehacer cubre cambios de parámetros, agregar/eliminar/mover bloques
y cargas de presets. El historial se limita a 100 estados.

---

## 11) Configuración

Abra **Configuración** para modificar valores por defecto:

- Rango de frecuencia (mín/max)
- Resolución de la rejilla (puntos)
- Eje X log/lineal
- Frecuencias de marcadores
- Frecuencias del resumen
- Alpha de la grilla
- Color de fondo
- Antialias
- Bins de decimación medidos

### 11.1 Aplicar vs OK
- **Aplicar**: aplica cambios sin cerrar el diálogo.
- **OK**: aplica y cierra.

### 11.2 Persistencia
La configuración se guarda en:

```
settings/general_settings.json
```

Este archivo es específico del usuario. Si usa git, considere agregar `settings/` a `.gitignore`.

---

## 12) Flujos de trabajo comunes

### 12.1 Ciclo básico de sintonía
1) Cargar CSV medido.
2) Agregar/eliminar bloques para definir estructura.
3) Ajustar parámetros observando los Bode.
4) Guardar snapshots en puntos clave.
5) Exportar un preset para reproducibilidad.

### 12.2 Sintonía con referencia
1) Cargar un preset como referencia.
2) Sintonizar el compensador actual contra esa base.
3) Copiar actual -> referencia al finalizar.

---

## 13) Solución de problemas

### 13.1 "No CSV found" o errores de formato
- Verifique cabeceras y columnas correctas.
- Asegúrese de que `freq_hz` exista y sea positivo.

### 13.2 Las gráficas se ven mal tras cambiar configuración
- Verifique que el rango de frecuencias sea válido.
- Para eje log, freq_min debe ser > 0.

### 13.3 Color de fondo inválido
- Use un color válido (`k`, `w`, `r`) o hex (`#202020`).

### 13.4 Fallas al activar el venv en PowerShell
- Si `Activate.ps1` está bloqueado por la política de ejecución, puede cambiarla por usuario:
  `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`
  o bien omitir la activación y ejecutar todo con `.\.venv\Scripts\python ...`.

### 13.5 Problemas con Python / pip
- Si `python` no aparece, use la ruta completa a `python.exe` (o instale Python 3.x).
- Si falla la instalación de dependencias, intente actualizar pip:
  `.\.venv\Scripts\python -m pip install --upgrade pip`

---

## 14) Notas para desarrolladores

Módulos clave:
- `comp_tuner/blocks.py`: definiciones de bloques y respuestas en frecuencia.
- `comp_tuner/compensator.py`: modelo del compensador, serialización de presets.
- `comp_tuner/model.py`: carga de CSV y utilidades matemáticas.
- `comp_tuner/ui.py`: lógica de la interfaz.

### 14.1 Agregar bloques personalizados

Para añadir un nuevo bloque:

1) Cree una nueva clase en `comp_tuner/blocks.py` que herede de `BlockBase`.
2) Defina:
   - `name` (cadena única)
   - `display_name` (etiqueta de UI)
   - `latex` (opcional, para documentación/exportación)
   - `params_meta` (definición de parámetros)
3) Implemente `freq_response(w, params)` devolviendo un arreglo complejo.
4) Registre la clase en `BLOCK_TYPES`.

Una vez registrada en `BLOCK_TYPES`, el bloque aparece automáticamente en el menú "Agregar bloque" (no requiere cambios de UI).

Ejemplo mínimo (plantilla):

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

Guías:
- Use **Hz** para parámetros de frecuencia y convierta a rad/s internamente.
- Elija rangos seguros para los sliders interactivos.
- Use `scale="log"` en parámetros que abarcan décadas.
- Asegure que `freq_response` sea vectorizado sobre `w`.
- El orden de `params_meta` controla el orden de parámetros mostrado en la UI.

---

## 15) Licencia / Atribución

Autor: Emanuel Camacho @s0cae

Licencia: GNU General Public License v3.0 o posterior (GPL-3.0-or-later).
