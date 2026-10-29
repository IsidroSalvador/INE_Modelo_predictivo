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
..\.venv\Scripts\python 02_explore_secciones.py   # diagnóstico (opcional)
..\.venv\Scripts\python 03_build_panel.py         # panel con rezagos + Censo 2020
..\.venv\Scripts\python 04_model_validate.py      # línea base vs modelo, validación, pronóstico 2027
..\.venv\Scripts\python 05_semaforo_escenarios.py # semáforo, incertidumbre, escenarios
..\.venv\Scripts\python 06_cartografia.py        # extrae capas de la BGD del INE
..\.venv\Scripts\python 07_mapas.py              # GPKG/GeoJSON, mapas PNG, Moran
..\.venv\Scripts\python 08_visor.py              # visor web: outputs/maps/visor.html
```

## Qué hace cada paso

| Script | Entrada | Salida |
|---|---|---|
| `01_build_ccpc.py` | CSV del CCPC (sección × sexo × edad) | `data/interim/ccpc_seccion_anio.parquet` |
| `02_explore_secciones.py` | lo anterior + ECEG | tablas de estabilidad y calidad |
| `03_build_panel.py` | lo anterior | `data/processed/panel_seccion.parquet`, `equivalencias_seccion.csv` |
| `04_model_validate.py` | panel | `validacion_temporal.csv`, `coeficientes_modelo.csv`, `pronostico_2027.parquet` |
| `05_semaforo_escenarios.py` | pronóstico | `base_anonimizada_seccion.csv`, `escenarios_resumen.csv`, `prioridad_*.csv` |
| `06_cartografia.py` | `data/raw/cartografia/bgd_*_Shapefile.zip` | `data/interim/cartografia.gpkg` |
| `07_mapas.py` | base + cartografía | `escenarios_seccion.gpkg`, `municipios.geojson`, `distritos.geojson`, `mapa_*.png`, `moran.csv` |
| `08_visor.py` | GeoJSON | `outputs/maps/visor.html` |

## Decisiones clave

- **Participación** = SV / (SV + NV). Se excluyen los registros NS (cuadernillos no capturables).
- **Calidad**: una sección-año solo cuenta si tiene ≥ 30 registros válidos y ≤ 50 % de NS.
- **Unidad**: sección electoral. Las secciones nuevas o reseccionadas toman la participación de su
  municipio y se marcan con `lag_imput=1` / `confianza="baja"`.
- **Línea base**: participación igual a la de la última elección del mismo tipo.
- **Modelo**: GLM quasi-binomial "de cambio": parte de la participación de la última elección
  comparable y explica la desviación (tendencia reciente, gubernatura concurrente, Censo 2020,
  % jóvenes, tipo de sección). El nivel nacional se ancla al de la última elección comparable.
- **Validación temporal**: se entrena con 2015-2018 y se prueba en 2021; luego se entrena con 2015-2021 y se prueba en 2024.
- **Semáforo**: rojo = por debajo del percentil 20 nacional de participación esperada;
  amarillo = entre los percentiles 20 y 40, o con una caída esperada ≥ 3 pp respecto a 2021; verde = resto.
- **Escenarios**: efecto hipotético (no causal) en secciones rojas de +1 / +2.5 / +4 pp.

## Fuentes (agregadas, públicas)

| Fuente | Uso | Archivo |
|---|---|---|
| INE – CCPC 2009-2024 | variable a explicar e historial | `data/raw/ccpc/` |
| INEGI-INE – ECEG 2020 (Censo por sección) | escolaridad, % indígena, % migrante, % sin salud | `data/raw/eceg_2020_csv.zip` |
| Calendario electoral (gubernaturas concurrentes) | contexto institucional | `data/raw/calendario_gubernaturas.csv` |
| INE – Base Geográfica Digital (32 entidades) | mapas | `data/raw/cartografia/` |

## Limitaciones

- Falacia ecológica: los resultados describen secciones, no personas.
- El Censo 2020 es fijo en el tiempo; los reseccionamientos se aproximan con el municipio.
- El choque nacional de cada elección no es predecible desde el territorio (en la validación fue de +4.8 pp en 2021 y −3.3 pp en 2024).
- Los efectos de intervención son supuestos, no efectos estimados.
