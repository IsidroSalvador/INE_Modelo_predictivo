"""PASO 3: CONSTRUCCIÓN DEL PANEL HISTÓRICO SECCIÓN-AÑO.

¿QUÉ ES UN "PANEL"?
-------------------
En econometría y estadística, un panel es una tabla donde seguimos a las MISMAS
unidades (secciones electorales) a través del TIEMPO (2015, 2018, 2021, 2024 y 2027).

¿POR QUÉ ES NECESARIO ESTE ARCHIVO?
-----------------------------------
Para entrenar un modelo predictivo que prediga el futuro (2027), necesitamos poner
en cada fila todo lo que se sabía de una sección ANTES de esa elección:
  1. ¿Cuánto participó hace 6 años en la elección del MISMO tipo? (`part_lag6`)
     (Ejemplo: para predecir 2027 [intermedia], miramos 2021 [intermedia]).
  2. ¿Cuánto participó hace 3 años en la elección inmediata anterior? (`part_lag3`)
     (Ejemplo: para predecir 2027, miramos 2024 [presidencial]).
  3. ¿Qué porcentaje de jóvenes (18 a 34 años) tenía el padrón? (`sh_joven_lag3`)
  4. Variables del Censo 2020 de INEGI-INE:
     - Escolaridad promedio en años (`escolaridad`)
     - Porcentaje de hablantes de lengua indígena (`pct_indigena`)
     - Porcentaje de población migrante reciente (`pct_migrante`)
     - Porcentaje de población sin servicios de salud (`pct_sin_salud`)
  5. Se agrega una fila vacía para el año 2027 para cada sección vigente, lista
     para recibir la predicción en el paso 4.

SALIDAS:
  - `data/processed/panel_seccion.parquet` -> la base lista para entrenar y predecir.
  - `data/processed/equivalencias_seccion.csv` -> catálogo que vincula sección con municipio y distrito 2023.
"""

import zipfile
import numpy as np
import pandas as pd
from config import INTERIM, PROCESSED, RAW, TIPO_ELECCION

# Umbrales mínimos de control de calidad para considerar confiable una sección-año:
MIN_VALIDOS = 30      # Al menos 30 personas registradas en lista nominal
MAX_PCT_NS = 0.5      # Que no tenga más de 50% de votos "no especificados" (cuadernillos perdidos)

# 1. Cargamos el histórico agregado a nivel sección-año que creó el paso 01
df = pd.read_parquet(INTERIM / "ccpc_seccion_anio.parquet")
key = ["ent", "seccion"]

# ------------------------------------------------------------------------------
# 2. CALIDAD DE DATOS Y CARACTERÍSTICAS DEL ELECTORADO EN CADA AÑO
# ------------------------------------------------------------------------------
# Total de registros válidos analizados (Sí Votó + No Votó)
df["validos"] = df.SV + df.NV
df["pct_ns"] = df.NS / df.LN.where(df.LN > 0)

# Filtro de calidad: si la sección no cumple las condiciones, se descarta su tasa
df["ok"] = (df.validos >= MIN_VALIDOS) & (df.pct_ns <= MAX_PCT_NS)
df.loc[~df.ok, "part"] = np.nan

# Porcentaje de jóvenes (18 a 34 años) en la lista nominal de esa sección:
votos_jovenes = df.SV_e18_24 + df.NV_e18_24 + df.SV_e25_34 + df.NV_e25_34
df["sh_joven"] = votos_jovenes / df.validos.where(df.validos > 0)
df["part_joven"] = (df.SV_e18_24 + df.SV_e25_34) / votos_jovenes.where(votos_jovenes > 0)
df["sh_mujer"] = (df.SV_s1 + df.NV_s1) / df.validos.where(df.validos > 0)
df["sh_65m"] = (df.SV_e65m + df.NV_e65m) / df.validos.where(df.validos > 0)

# ------------------------------------------------------------------------------
# 3. IDENTIFICAR SECCIONES "ESTABLES" VS "NUEVAS/RESECCIONADAS"
# ------------------------------------------------------------------------------
n_anios = df.groupby(key).anio.nunique().rename("n_anios")
n_mun = df.groupby(key).mun.nunique().rename("n_mun")
s = df.sort_values(key + ["anio"])
s["ln_ratio"] = s.groupby(key).LN.pct_change() + 1
salto = s.groupby(key).ln_ratio.agg(lambda x: bool(((x < 0.5) | (x > 2)).any())).rename("salto_ln")
flags = pd.concat([n_anios, n_mun, salto], axis=1).reset_index()

# Una sección es 100% estable si existió en los 6 comicios, no cambió de municipio y no sufrió desdoblamiento
flags["estable"] = (flags.n_anios == 6) & (flags.n_mun == 1) & (~flags.salto_ln)

# Calculamos el promedio municipal de participación por año (nos servirá para imputar si a una sección le falta historia)
mun_year = (df[df.ok].groupby(["anio", "ent", "mun"])[["SV", "validos"]].sum()
            .assign(part_mun=lambda x: x.SV / x.validos)["part_mun"].reset_index())

# ------------------------------------------------------------------------------
# 4. CONSTRUCCIÓN DE REZAGOS HISTÓRICOS (LAGS)
# ------------------------------------------------------------------------------
# Queremos que la fila de 2027 contenga:
# - la participación de 2021 (t - 6 años)
# - la participación de 2024 (t - 3 años)
cols_lag = ["part", "part_joven", "sh_joven", "sh_mujer", "sh_65m", "LN", "TIPOSEC"]
base = df[key + ["anio"] + cols_lag].copy()

# Generamos las filas vacías para 2027 tomando las secciones activas en 2024
f27 = df[df.anio == 2024][key + ["mun", "MPIONOM", "DEF"]].assign(anio=2027)
target = pd.concat([df[key + ["anio", "mun", "MPIONOM", "DEF", "part", "SV", "validos", "LN", "ok"]],
                    f27], ignore_index=True)

def pegar_rezago(tabla_destino, delta_anios, columnas, sufijo):
    """Toma los datos de hace `delta_anios` y los pega en el año actual."""
    lag = base[key + ["anio"] + columnas].copy()
    lag["anio"] = lag["anio"] + delta_anios
    lag = lag.rename(columns={c: f"{c}{sufijo}" for c in columnas})
    return tabla_destino.merge(lag, on=key + ["anio"], how="left")

# Pegamos rezago de 6 años (elección comparable del mismo tipo)
panel = pegar_rezago(target, 6, ["part"], "_lag6")

# Pegamos rezago de 3 años (elección inmediata previa)
panel = pegar_rezago(panel, 3, cols_lag, "_lag3")
panel = panel.rename(columns={"LN_lag3_lag3": "LN_lag3"})

# ------------------------------------------------------------------------------
# 5. IMPUTACIÓN TRANSPARENTE PARA SECCIONES RECIENTES
# ------------------------------------------------------------------------------
# Si una sección se creó recientemente (ej. en 2024) y no existía en 2021, no podemos
# inventar un dato. Le asignamos la participación promedio de su municipio y encendemos
# una bandera (`lag_imput = 1`) para que el modelo y el semáforo sepan que tiene menor certeza.
for k in (3, 6):
    m = mun_year.copy(); m["anio"] += k
    panel = panel.merge(m.rename(columns={"part_mun": f"pmun_lag{k}"}), on=["anio", "ent", "mun"], how="left")

panel["lag_imput"] = (panel.part_lag6.isna() | panel.part_lag3.isna()).astype(int)
panel["part_lag6"] = panel.part_lag6.fillna(panel.pmun_lag6)
panel["part_lag3"] = panel.part_lag3.fillna(panel.pmun_lag3)

# Relleno de seguridad con medianas estatales si el municipio tampoco tenía dato
for c in ("part_lag6", "part_lag3"):
    panel[c] = panel[c].fillna(panel.groupby(["anio", "ent"])[c].transform("median"))
for c in ["part_joven_lag3", "sh_joven_lag3", "sh_mujer_lag3", "sh_65m_lag3"]:
    panel[c] = panel[c].fillna(panel.groupby(["anio", "ent", "mun"])[c].transform("median"))
    panel[c] = panel[c].fillna(panel.groupby(["anio", "ent"])[c].transform("median"))

panel["LN_lag3"] = panel.LN_lag3.fillna(panel.LN)
panel["TIPOSEC_lag3"] = panel.TIPOSEC_lag3.fillna("U")  # Urbana por defecto

# Crecimiento del padrón electoral entre las dos elecciones anteriores (dinamismo poblacional)
ln6 = base[key + ["anio", "LN"]].copy(); ln6["anio"] += 6
panel = panel.merge(ln6.rename(columns={"LN": "LN_lag6"}), on=key + ["anio"], how="left")
panel["ln_growth"] = np.log(panel.LN_lag3 / panel.LN_lag6).clip(-1, 1).fillna(0)

# ------------------------------------------------------------------------------
# 6. INTEGRACIÓN DEL CENSO 2020 POR SECCIÓN (ECEG INEGI-INE)
# ------------------------------------------------------------------------------
# Leemos las estadísticas del Censo 2020 agregadas por sección electoral
ECEG_COLS = ["ENTIDAD", "SECCION", "POBTOT", "P_3YMAS", "P_5YMAS", "GRAPROES", "P3YM_HLI",
             "PRESOE15", "PSINDER", "TVIVPARHAB", "VPH_INTER", "PDESOCUP", "PEA"]

with zipfile.ZipFile(RAW / "eceg_2020_csv.zip") as z:
    with z.open("conjunto_de_datos/INE_SECCION_2020.csv") as f:
        e = pd.read_csv(f, usecols=ECEG_COLS, encoding="latin-1", na_values=["*", "N/D"])

e = e.rename(columns={"ENTIDAD": "ent", "SECCION": "seccion"})
for c in ECEG_COLS[2:]:
    e[c] = pd.to_numeric(e[c], errors="coerce")
    e.loc[e[c] < 0, c] = np.nan   # En INEGI, valores negativos son códigos de reserva

# Creamos las variables sociodemográficas normalizadas (proporciones de 0 a 1):
cen = pd.DataFrame({
    "ent": e.ent,
    "seccion": e.seccion,
    "escolaridad": e.GRAPROES,                                   # Años promedio de estudio (personas 15+)
    "pct_indigena": e.P3YM_HLI / e.P_3YMAS,                      # % hablantes de lengua indígena
    "pct_migrante": e.PRESOE15 / e.P_5YMAS,                      # % que vivía en otro estado en 2015
    "pct_sin_salud": e.PSINDER / e.POBTOT,                       # % sin afiliación médica
    "pct_internet": e.VPH_INTER / e.TVIVPARHAB,                  # % viviendas con internet
    "pct_desocup": e.PDESOCUP / e.PEA,                           # Tasa de desocupación económica
}).replace([np.inf, -np.inf], np.nan)

# Pegamos las variables censales al panel
panel = panel.merge(cen, on=key, how="left")
panel["censo_imput"] = panel.escolaridad.isna().astype(int)

# Si una sección no tiene censo, toma la mediana de su municipio
for c in cen.columns[2:]:
    panel[c] = panel[c].clip(0, 1) if c.startswith("pct_") else panel[c]
    panel[c] = panel[c].fillna(panel.groupby(["ent", "mun"])[c].transform("median"))
    panel[c] = panel[c].fillna(panel.groupby("ent")[c].transform("median"))

# Pegamos banderas de estabilidad y tipo de sección
panel = panel.merge(flags, on=key, how="left")
panel["tipo"] = panel.anio.map({**TIPO_ELECCION, 2027: "intermedia"})
panel["tiposec"] = panel.TIPOSEC_lag3.str.strip().str.upper().str[0]

# Filtramos solo años que ya tienen rezagos históricos disponibles (2015 a 2027)
panel = panel[panel.anio >= 2015].reset_index(drop=True)

# Guardamos el dataset final listo para modelar
panel.to_parquet(PROCESSED / "panel_seccion.parquet", index=False)

# Guardamos el catálogo de equivalencias (sección -> municipio, distrito 2023)
eq = (df[df.anio == 2024][key + ["mun", "MPIONOM", "DEF", "TIPOSEC"]]
      .rename(columns={"DEF": "df_2023", "MPIONOM": "mun_nombre"})
      .merge(flags, on=key, how="left")
      .merge(cen[key].assign(en_eceg2020=True), on=key, how="left"))
eq["en_eceg2020"] = eq.en_eceg2020.notna()
eq.to_csv(PROCESSED / "equivalencias_seccion.csv", index=False, encoding="utf-8")

print("=== PANEL CONSTRUIDO CON ÉXITO ===")
print("Filas por año (2015 a 2027):")
print(panel.groupby("anio").size())
