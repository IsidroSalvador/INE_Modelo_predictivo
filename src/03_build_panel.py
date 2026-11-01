"""Construcción del panel sección-año con rezagos electorales (t-3, t-6) e indicadores del Censo 2020."""

import zipfile
import numpy as np
import pandas as pd
from config import INTERIM, PROCESSED, RAW, TIPO_ELECCION

MIN_VALIDOS = 30
MAX_PCT_NS = 0.5

df = pd.read_parquet(INTERIM / "ccpc_seccion_anio.parquet")
key = ["ent", "seccion"]

df["validos"] = df.SV + df.NV
df["pct_ns"] = df.NS / df.LN.where(df.LN > 0)
df["ok"] = (df.validos >= MIN_VALIDOS) & (df.pct_ns <= MAX_PCT_NS)
df.loc[~df.ok, "part"] = np.nan

votos_jovenes = df.SV_e18_24 + df.NV_e18_24 + df.SV_e25_34 + df.NV_e25_34
df["sh_joven"] = votos_jovenes / df.validos.where(df.validos > 0)
df["part_joven"] = (df.SV_e18_24 + df.SV_e25_34) / votos_jovenes.where(votos_jovenes > 0)
df["sh_mujer"] = (df.SV_s1 + df.NV_s1) / df.validos.where(df.validos > 0)
df["sh_65m"] = (df.SV_e65m + df.NV_e65m) / df.validos.where(df.validos > 0)

n_anios = df.groupby(key).anio.nunique().rename("n_anios")
n_mun = df.groupby(key).mun.nunique().rename("n_mun")
s = df.sort_values(key + ["anio"])
s["ln_ratio"] = s.groupby(key).LN.pct_change() + 1
salto = s.groupby(key).ln_ratio.agg(lambda x: bool(((x < 0.5) | (x > 2)).any())).rename("salto_ln")
flags = pd.concat([n_anios, n_mun, salto], axis=1).reset_index()
flags["estable"] = (flags.n_anios == 6) & (flags.n_mun == 1) & (~flags.salto_ln)

mun_year = (df[df.ok].groupby(["anio", "ent", "mun"])[["SV", "validos"]].sum()
            .assign(part_mun=lambda x: x.SV / x.validos)["part_mun"].reset_index())

cols_lag = ["part", "part_joven", "sh_joven", "sh_mujer", "sh_65m", "LN", "TIPOSEC"]
base = df[key + ["anio"] + cols_lag].copy()

f27 = df[df.anio == 2024][key + ["mun", "MPIONOM", "DEF"]].assign(anio=2027)
target = pd.concat([df[key + ["anio", "mun", "MPIONOM", "DEF", "part", "SV", "validos", "LN", "ok"]],
                    f27], ignore_index=True)


def pegar_rezago(tabla_destino, delta_anios, columnas, sufijo):
    lag = base[key + ["anio"] + columnas].copy()
    lag["anio"] = lag["anio"] + delta_anios
    lag = lag.rename(columns={c: f"{c}{sufijo}" for c in columnas})
    return tabla_destino.merge(lag, on=key + ["anio"], how="left")


panel = pegar_rezago(target, 6, ["part"], "_lag6")
panel = pegar_rezago(panel, 3, cols_lag, "_lag3")
panel = panel.rename(columns={"LN_lag3_lag3": "LN_lag3"})

# Imputación por media municipal para secciones nuevas o sin rezago válido
for k in (3, 6):
    m = mun_year.copy()
    m["anio"] += k
    panel = panel.merge(m.rename(columns={"part_mun": f"pmun_lag{k}"}), on=["anio", "ent", "mun"], how="left")

panel["lag_imput"] = (panel.part_lag6.isna() | panel.part_lag3.isna()).astype(int)
panel["part_lag6"] = panel.part_lag6.fillna(panel.pmun_lag6)
panel["part_lag3"] = panel.part_lag3.fillna(panel.pmun_lag3)

for c in ("part_lag6", "part_lag3"):
    panel[c] = panel[c].fillna(panel.groupby(["anio", "ent"])[c].transform("median"))
for c in ["part_joven_lag3", "sh_joven_lag3", "sh_mujer_lag3", "sh_65m_lag3"]:
    panel[c] = panel[c].fillna(panel.groupby(["anio", "ent", "mun"])[c].transform("median"))
    panel[c] = panel[c].fillna(panel.groupby(["anio", "ent"])[c].transform("median"))

panel["LN_lag3"] = panel.LN_lag3.fillna(panel.LN)
panel["TIPOSEC_lag3"] = panel.TIPOSEC_lag3.fillna("U")

ln6 = base[key + ["anio", "LN"]].copy()
ln6["anio"] += 6
panel = panel.merge(ln6.rename(columns={"LN": "LN_lag6"}), on=key + ["anio"], how="left")
panel["ln_growth"] = np.log(panel.LN_lag3 / panel.LN_lag6).clip(-1, 1).fillna(0)

ECEG_COLS = ["ENTIDAD", "SECCION", "POBTOT", "P_3YMAS", "P_5YMAS", "GRAPROES", "P3YM_HLI",
             "PRESOE15", "PSINDER", "TVIVPARHAB", "VPH_INTER", "PDESOCUP", "PEA"]

with zipfile.ZipFile(RAW / "eceg_2020_csv.zip") as z:
    with z.open("conjunto_de_datos/INE_SECCION_2020.csv") as f:
        e = pd.read_csv(f, usecols=ECEG_COLS, encoding="latin-1", na_values=["*", "N/D"])

e = e.rename(columns={"ENTIDAD": "ent", "SECCION": "seccion"})
for c in ECEG_COLS[2:]:
    e[c] = pd.to_numeric(e[c], errors="coerce")
    e.loc[e[c] < 0, c] = np.nan

cen = pd.DataFrame({
    "ent": e.ent,
    "seccion": e.seccion,
    "escolaridad": e.GRAPROES,
    "pct_indigena": e.P3YM_HLI / e.P_3YMAS,
    "pct_migrante": e.PRESOE15 / e.P_5YMAS,
    "pct_sin_salud": e.PSINDER / e.POBTOT,
    "pct_internet": e.VPH_INTER / e.TVIVPARHAB,
    "pct_desocup": e.PDESOCUP / e.PEA,
}).replace([np.inf, -np.inf], np.nan)

panel = panel.merge(cen, on=key, how="left")
panel["censo_imput"] = panel.escolaridad.isna().astype(int)

for c in cen.columns[2:]:
    panel[c] = panel[c].clip(0, 1) if c.startswith("pct_") else panel[c]
    panel[c] = panel[c].fillna(panel.groupby(["ent", "mun"])[c].transform("median"))
    panel[c] = panel[c].fillna(panel.groupby("ent")[c].transform("median"))

panel = panel.merge(flags, on=key, how="left")
panel["tipo"] = panel.anio.map({**TIPO_ELECCION, 2027: "intermedia"})
panel["tiposec"] = panel.TIPOSEC_lag3.str.strip().str.upper().str[0]

panel = panel[panel.anio >= 2015].reset_index(drop=True)
panel.to_parquet(PROCESSED / "panel_seccion.parquet", index=False)

eq = (df[df.anio == 2024][key + ["mun", "MPIONOM", "DEF", "TIPOSEC"]]
      .rename(columns={"DEF": "df_2023", "MPIONOM": "mun_nombre"})
      .merge(flags, on=key, how="left")
      .merge(cen[key].assign(en_eceg2020=True), on=key, how="left"))
eq["en_eceg2020"] = eq.en_eceg2020.notna()
eq.to_csv(PROCESSED / "equivalencias_seccion.csv", index=False, encoding="utf-8")

print("Panel construido. Filas por año:")
print(panel.groupby("anio").size())
