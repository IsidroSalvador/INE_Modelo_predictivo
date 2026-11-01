"""Diagnóstico de estabilidad longitudinal de secciones electorales (2009-2024) y cruce con ECEG 2020."""

import zipfile
import pandas as pd
from config import INTERIM, RAW, OUT_TAB, YEARS

df = pd.read_parquet(INTERIM / "ccpc_seccion_anio.parquet")
df["valida"] = (df.SV + df.NV) > 0

pres = df.pivot_table(index=["ent", "seccion"], columns="anio", values="LN",
                      aggfunc="size", fill_value=0).astype(bool)
pres["n_anios"] = pres[YEARS].sum(axis=1)
pres["patron"] = pres[YEARS].astype(int).astype(str).agg("".join, axis=1)

print("Total secciones distintas (2009-2024):", len(pres))
print(pres["n_anios"].value_counts().sort_index())
print("\nPatrones más frecuentes:")
print(pres["patron"].value_counts().head(10))

mun_n = df.groupby(["ent", "seccion"])["mun"].nunique()
print("\nSecciones con cambio de municipio (2009-2024):", int((mun_n > 1).sum()))

d24 = df[df.anio == 2024].merge(pres["n_anios"].reset_index(), on=["ent", "seccion"])
cov = d24.groupby("n_anios").LN.sum() / d24.LN.sum()
print("\nCobertura de LN 2024 por número de elecciones presentes:")
print((cov * 100).round(2).astype(str) + " %")

full = df.merge(pres["n_anios"].reset_index(), on=["ent", "seccion"])
full = full[full.n_anios == 6].sort_values(["ent", "seccion", "anio"])
full["ln_ratio"] = full.groupby(["ent", "seccion"]).LN.pct_change() + 1
salto = full.groupby(["ent", "seccion"]).ln_ratio.agg(lambda s: ((s < 0.5) | (s > 2)).any())
print("\nSecciones con saltos bruscos de padrón:", int(salto.sum()), "de", len(salto))

with zipfile.ZipFile(RAW / "eceg_2020_csv.zip") as z:
    with z.open("conjunto_de_datos/INE_SECCION_2020.csv") as f:
        eceg = pd.read_csv(f, usecols=["ENTIDAD", "SECCION", "POBTOT"], encoding="latin-1")
eceg = eceg.rename(columns={"ENTIDAD": "ent", "SECCION": "seccion"})
print("\nCruce con ECEG 2020 (total secciones censo:", len(eceg), "):")
for y in (2018, 2021, 2024):
    dy = df[df.anio == y].merge(eceg, on=["ent", "seccion"], how="left", indicator=True)
    m = dy["_merge"] == "both"
    print(f"  {y}: {m.mean():.2%} secciones ({dy.LN[m].sum()/dy.LN.sum():.2%} de LN)")

pres.reset_index().to_csv(OUT_TAB / "estabilidad_secciones.csv", index=False)
