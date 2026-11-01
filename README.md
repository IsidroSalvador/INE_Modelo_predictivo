# Hackea la participación (INE) – Reto 2: riesgo de abstención

Predicción de participación por **sección electoral** para la elección federal intermedia de **2027**,
semáforo de riesgo territorial y escenarios con y sin intervención.
La fuente central son los **Conteos Censales de Participación Ciudadana (CCPC) 2009–2024** del INE.

## Cómo reproducir

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
cd src
..\.venv\Scripts\python 01_build_ccpc.py          # CCPC -> sección-año
..\.venv\Scripts\python 02_explore_secciones.py   # diagnóstico de estabilidad
..\.venv\Scripts\python 03_build_panel.py         # panel con rezagos + Censo 2020
..\.venv\Scripts\python 04_model_validate.py      # línea base vs GLM, validación, pronóstico 2027
..\.venv\Scripts\python 04b_modelo_xgboost.py     # contraste con XGBoost e importancia de variables
..\.venv\Scripts\python 05_semaforo_escenarios.py # semáforo, incertidumbre, escenarios
..\.venv\Scripts\python 06_cartografia.py        # extrae capas de la BGD del INE
..\.venv\Scripts\python 07_mapas.py              # GPKG/GeoJSON, mapas PNG, Moran
..\.venv\Scripts\python 08_visor.py              # visor web: outputs/maps/visor.html
```

## Estructura del pipeline

| Script | Entrada | Salida |
|---|---|---|
| `01_build_ccpc.py` | CSV del CCPC (sección × sexo × edad) | `data/interim/ccpc_seccion_anio.parquet`, `ccpc_qc_por_anio.csv` |
| `02_explore_secciones.py` | CCPC consolidado + ECEG 2020 | `estabilidad_secciones.csv` |
| `03_build_panel.py` | CCPC consolidado + ECEG 2020 | `data/processed/panel_seccion.parquet`, `equivalencias_seccion.csv` |
| `04_model_validate.py` | Panel sección-año | `validacion_temporal.csv`, `coeficientes_modelo.csv`, `pronostico_2027.parquet` |
| `04b_modelo_xgboost.py` | Panel sección-año | `comparacion_glm_vs_xgboost.csv`, `importancia_variables_xgboost.csv` |
| `05_semaforo_escenarios.py` | Pronóstico + residuos | `base_anonimizada_seccion.csv`, `escenarios_resumen.csv`, `prioridad_*.csv` |
| `06_cartografia.py` | `data/raw/cartografia/bgd_*_Shapefile.zip` | `data/interim/cartografia.gpkg` |
| `07_mapas.py` | Base anonimizada + cartografía | `escenarios_seccion.gpkg`, `municipios.geojson`, `distritos.geojson`, `mapa_*.png`, `moran.csv` |
| `08_visor.py` | GeoJSON + resumen de escenarios | `outputs/maps/visor.html` |

## Fuentes de datos (agregadas, públicas)

| Fuente | Uso | Archivo |
|---|---|---|
| INE – CCPC 2009-2024 | Variable objetivo e historial de participación | `data/raw/ccpc/` |
| INEGI-INE – ECEG 2020 (Censo por sección) | Escolaridad, % indígena, % migrante, % sin salud | `data/raw/eceg_2020_csv.zip` |
| Calendario electoral (gubernaturas concurrentes) | Contexto institucional | `data/raw/calendario_gubernaturas.csv` |
| INE – Base Geográfica Digital (32 entidades) | Cartografía electoral | `data/raw/cartografia/` |
