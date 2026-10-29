"""PASO 1: LECTURA Y CONSOLIDACIÓN DE LOS CONTEOS CENSALES DE PARTICIPACIÓN (CCPC).

¿QUÉ HACE ESTE SCRIPT?
----------------------
El INE publica los microdatos del CCPC en carpetas separadas para cada elección:
2009, 2012, 2015, 2018, 2021 y 2024.
Dentro de cada año hay 32 archivos CSV (uno por cada estado de la República).

En esos archivos originales, cada fila es un cruce muy fino:
(Sección, Sexo, Edad, Lista Nominal, Votantes SV, No Votantes NV, No Especificados NS).

Este script:
1. Detecta la codificación de cada archivo (evitando errores por caracteres especiales o BOM).
2. Suma todos los votantes y abstencionistas para dejar UNA SOLA FILA por (Año, Entidad, Sección).
3. Calcula la tasa oficial de participación ciudadana:
               Participación = SV / (SV + NV)
4. Guarda un archivo Parquet compacto y rápido de consultar:
   `data/interim/ccpc_seccion_anio.parquet`
"""

import codecs
import glob
import pandas as pd
import numpy as np
from config import CCPC_DIR, INTERIM, OUT_TAB, YEARS, TIPO_ELECCION, EDAD_BINS, EDAD_LABELS

# Columnas mínimas necesarias para optimizar uso de memoria
USECOLS = [
    "AELEC", "EDOCVE", "MPIOCVE", "MPIONOM", "SECCION", "TIPOSEC",
    "DEF", "SEXO", "EDAD", "LN", "SV", "NV", "NS"
]

# Tipos de datos para reducir uso de RAM
DTYPES = {
    "AELEC": "int16", "EDOCVE": "int8", "MPIOCVE": "int16", "SECCION": "int32",
    "SEXO": "int8", "EDAD": "int16", "LN": "int32", "SV": "int32",
    "NV": "int32", "NS": "int32"
}


def read_year(year: int) -> pd.DataFrame:
    """Lee los 32 archivos CSV correspondientes a un año electoral específico."""
    files = sorted(glob.glob(str(CCPC_DIR / f"*{year}" / "*.csv")))
    assert len(files) == 32, f"Año {year}: se esperaban 32 archivos estatales, pero hay {len(files)}"
    parts = []

    for f in files:
        # Detectamos automáticamente si el archivo viene en UTF-8 con BOM o Latin-1
        with open(f, "rb") as fh:
            sample = fh.read(2_000_000)
        if sample.startswith(b"\xef\xbb\xbf"):
            enc = "utf-8-sig"
        else:
            try:
                codecs.getincrementaldecoder("utf-8")().decode(sample, final=False)
                enc = "utf-8"
            except UnicodeDecodeError:
                enc = "latin-1"

        # Leemos el CSV
        d = pd.read_csv(
            f, usecols=USECOLS, encoding=enc,
            dtype={"TIPOSEC": "string", "MPIONOM": "string"},
            low_memory=False
        )
        d["DEF"] = pd.to_numeric(d["DEF"], errors="coerce")
        for c, t in DTYPES.items():
            d[c] = pd.to_numeric(d[c], errors="coerce").fillna(0).astype(t)

        parts.append(d)

    return pd.concat(parts, ignore_index=True)


def aggregate(d: pd.DataFrame) -> pd.DataFrame:
    """Agrupa las filas de edades individuales para obtener los totales de la sección electoral."""
    key = ["AELEC", "EDOCVE", "SECCION"]
    d["grupo_edad"] = pd.cut(d["EDAD"], EDAD_BINS, labels=EDAD_LABELS)

    # Sumamos lista nominal (LN), personas que votaron (SV), que no votaron (NV) y no especificados (NS)
    base = d.groupby(key, observed=True).agg(
        MPIOCVE=("MPIOCVE", "first"),
        MPIONOM=("MPIONOM", "first"),
        TIPOSEC=("TIPOSEC", "first"),
        DEF=("DEF", "first"),
        LN=("LN", "sum"),
        SV=("SV", "sum"),
        NV=("NV", "sum"),
        NS=("NS", "sum"),
        edad_media=("EDAD", lambda s: np.nan)
    )

    # Calculamos la edad media ponderada por número de electores
    w = d.assign(_e=d["EDAD"] * d["LN"]).groupby(key)[["_e", "LN"]].sum()
    base["edad_media"] = w["_e"] / w["LN"].replace(0, np.nan)

    # Desglosamos también votos por rangos de edad y por sexo (útil para análisis de voto joven)
    for col, prefix in (("grupo_edad", "e"), ("SEXO", "s")):
        p = d.groupby(key + [col], observed=True)[["SV", "NV"]].sum().unstack(col, fill_value=0)
        p.columns = [f"{v}_{prefix}{c}" for v, c in p.columns]
        base = base.join(p)

    base = base.reset_index().rename(columns={
        "AELEC": "anio", "EDOCVE": "ent", "SECCION": "seccion", "MPIOCVE": "mun"
    })
    base["tipo"] = base["anio"].map(TIPO_ELECCION)

    # Tasa oficial de participación electoral
    base["part"] = base["SV"] / (base["SV"] + base["NV"]).replace(0, np.nan)
    return base


def main():
    out, qc = [], []
    for y in YEARS:
        print(f"Procesando año {y}...")
        raw = read_year(y)
        agg = aggregate(raw)
        out.append(agg)

        # Control de calidad para documentar en el reporte
        part_prom = agg.SV.sum() / (agg.SV.sum() + agg.NV.sum())
        qc.append({
            "anio": y,
            "secciones": len(agg),
            "municipios": agg[["ent", "mun"]].drop_duplicates().shape[0],
            "Lista_Nominal": int(agg.LN.sum()),
            "Votantes_SV": int(agg.SV.sum()),
            "Abstencion_NV": int(agg.NV.sum()),
            "Participacion_Nacional": round(part_prom, 4),
            "Pct_No_Especificado": round(agg.NS.sum() / agg.LN.sum(), 4)
        })

    # Guardamos el archivo final consolidado
    df = pd.concat(out, ignore_index=True)
    df.to_parquet(INTERIM / "ccpc_seccion_anio.parquet", index=False)

    # Guardamos la tabla de control de calidad
    df_qc = pd.DataFrame(qc)
    df_qc.to_csv(OUT_TAB / "ccpc_qc_por_anio.csv", index=False)
    print("\n=== RESUMEN POR ELECCIÓN CONSOLIDADO ===")
    print(df_qc.to_string(index=False))
    print("\nArchivo guardado en data/interim/ccpc_seccion_anio.parquet")


if __name__ == "__main__":
    main()
