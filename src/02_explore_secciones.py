"""PASO 2: EXPLORACIÓN Y DIAGNÓSTICO DE SECCIONES ELECTORALES (2009-2024).

¿POR QUÉ EXISTE ESTE ARCHIVO?
----------------------------
Las secciones electorales no son estáticas en el tiempo:
1. Una colonia que antes era un terreno baldío se puebla y el INE crea una sección nueva.
2. Una sección muy poblada se "desdobla" (el INE la divide en dos o más secciones).
3. A veces cambian de límites municipales por decretos estatales.

Este script es una AUDITORÍA de calidad de datos antes de modelar:
- Responde: ¿Cuántas secciones existen ininterrumpidamente desde 2009 hasta 2024?
- Responde: ¿Qué porcentaje del padrón electoral actual (2024) vive en secciones estables?
- Responde: ¿Se pueden unir con el Censo 2020 (ECEG) sin perder información?

NOTA: Este script no modifica datos ni entrena modelos; solo genera tablas de
diagnóstico para fundamentar los supuestos en el reporte metodológico.
"""

import zipfile
import pandas as pd
from config import INTERIM, RAW, OUT_TAB, YEARS

# 1. Cargamos el archivo que armó el script 01 (una fila por sección y por año)
df = pd.read_parquet(INTERIM / "ccpc_seccion_anio.parquet")

# Una sección es "válida" si tiene al menos un voto registrado (SV + NV > 0)
df["valida"] = (df.SV + df.NV) > 0

# ------------------------------------------------------------------------------
# 2. MATRIZ DE PRESENCIA: ¿En cuáles elecciones ha existido cada sección?
# ------------------------------------------------------------------------------
# Creamos una tabla donde las filas son (entidad, seccion) y las columnas los años (2009..2024).
# True = la sección participó en ese año; False = no existía o no se instaló casilla.
pres = df.pivot_table(index=["ent", "seccion"], columns="anio", values="LN",
                      aggfunc="size", fill_value=0).astype(bool)

# Contamos en cuántas elecciones (de las 6 posibles) estuvo presente cada sección
pres["n_anios"] = pres[YEARS].sum(axis=1)

# Armamos un "patrón" de texto, p.ej. '111111' = existió en todas; '000001' = nació en 2024
pres["patron"] = pres[YEARS].astype(int).astype(str).agg("".join, axis=1)

print("=== 1. DIAGNÓSTICO DE HISTORIAL ===")
print("Total de secciones distintas que han existido (2009-2024):", len(pres))
print("Distribución según número de elecciones presentes:")
print(pres["n_anios"].value_counts().sort_index())
print("\nLos patrones de supervivencia más comunes:")
print(pres["patron"].value_counts().head(10))

# ------------------------------------------------------------------------------
# 3. CAMBIO DE MUNICIPIO: ¿Alguna sección cambió de municipio?
# ------------------------------------------------------------------------------
# Agrupamos por sección y contamos cuántos municipios distintos tuvo a lo largo del tiempo.
mun_n = df.groupby(["ent", "seccion"])["mun"].nunique()
print("\n=== 2. ESTABILIDAD MUNICIPAL ===")
print("Secciones que cambiaron de municipio entre 2009 y 2024:", int((mun_n > 1).sum()))

# ------------------------------------------------------------------------------
# 4. COBERTURA DEL ELECTORADO ACTUAL
# ------------------------------------------------------------------------------
# De los votantes vigentes en 2024, ¿cuántos viven en secciones con historia completa?
d24 = df[df.anio == 2024].merge(pres["n_anios"].reset_index(), on=["ent", "seccion"])
cov = d24.groupby("n_anios").LN.sum() / d24.LN.sum()
print("\n=== 3. COBERTURA DE LA LISTA NOMINAL 2024 ===")
print("Porcentaje de electores 2024 según los años de historia de su sección:")
print((cov * 100).round(2).astype(str) + " %")
# Resultado clave: Más del 87.4% de los electores viven en secciones con historia 100% completa (patrón 111111).

# ------------------------------------------------------------------------------
# 5. DETECCIÓN DE DESDOBLAMIENTOS (RESECCIONAMIENTOS)
# ------------------------------------------------------------------------------
# Si una sección completa de pronto pierde más de la mitad de su padrón o se duplica de golpe,
# significa que el INE modificó sus fronteras territoriales (desdoblamiento de sección).
full = df.merge(pres["n_anios"].reset_index(), on=["ent", "seccion"])
full = full[full.n_anios == 6].sort_values(["ent", "seccion", "anio"])
full["ln_ratio"] = full.groupby(["ent", "seccion"]).LN.pct_change() + 1
salto = full.groupby(["ent", "seccion"]).ln_ratio.agg(lambda s: ((s < 0.5) | (s > 2)).any())
print("\n=== 4. CAMBIOS BRUSCOS DE TAMAÑO (DESDOBLAMIENTOS) ===")
print("Secciones con saltos bruscos de padrón:", int(salto.sum()), "de", len(salto))

# ------------------------------------------------------------------------------
# 6. CRUCE CON EL CENSO 2020 (ECEG INEGI-INE)
# ------------------------------------------------------------------------------
# Verificamos si las claves de sección del INE coinciden con las del Censo por sección de INEGI.
with zipfile.ZipFile(RAW / "eceg_2020_csv.zip") as z:
    with z.open("conjunto_de_datos/INE_SECCION_2020.csv") as f:
        eceg = pd.read_csv(f, usecols=["ENTIDAD", "SECCION", "POBTOT"], encoding="latin-1")
eceg = eceg.rename(columns={"ENTIDAD": "ent", "SECCION": "seccion"})
print("\n=== 5. CRUCE CON CENSO 2020 ===")
print("Total secciones en el Censo 2020:", len(eceg))
for y in (2018, 2021, 2024):
    dy = df[df.anio == y].merge(eceg, on=["ent", "seccion"], how="left", indicator=True)
    m = dy["_merge"] == "both"
    print(f"  Año {y}: {m.mean():.2%} de las secciones coinciden con el Censo (cubren {dy.LN[m].sum()/dy.LN.sum():.2%} del padrón)")

# ------------------------------------------------------------------------------
# 7. GUARDAMOS TABLAS DE RESULTADOS
# ------------------------------------------------------------------------------
pres.reset_index().to_csv(OUT_TAB / "estabilidad_secciones.csv", index=False)
print("\nDiagnóstico completado. Tablas guardadas en outputs/tables/")
