"""Extracción de capas vectoriales (SECCION, MUNICIPIO, DISTRITO_FEDERAL) de la BGD del INE."""

import io
import zipfile
import geopandas as gpd
import pandas as pd
import py7zr
from config import RAW, INTERIM

CAPAS = {"SECCION": "seccion", "MUNICIPIO": "municipio", "DISTRITO_FEDERAL": "distrito"}
CARPETA = RAW / "cartografia"
EXTRAIDO = CARPETA / "extraido"


def extraer(zip_path):
    with zipfile.ZipFile(zip_path) as z:
        datos_7z = z.read(z.namelist()[0])
    with py7zr.SevenZipFile(io.BytesIO(datos_7z)) as arch:
        nombres = [n for n in arch.getnames()
                   if n.split("/")[-1].split(".")[0].upper() in CAPAS]
    with py7zr.SevenZipFile(io.BytesIO(datos_7z)) as arch:
        arch.extract(path=EXTRAIDO, targets=nombres)


def main():
    zips = sorted(CARPETA.glob("bgd_*_Shapefile.zip"))
    print(f"{len(zips)} archivos zip encontrados")
    for zp in zips:
        print("  extrayendo", zp.name)
        extraer(zp)

    for capa_shp, capa_salida in CAPAS.items():
        partes = []
        for shp in EXTRAIDO.rglob(f"{capa_shp}.shp"):
            g = gpd.read_file(shp)
            g.columns = [c.upper() if c != "geometry" else c for c in g.columns]
            partes.append(g.to_crs(4326))
        nacional = gpd.GeoDataFrame(pd.concat(partes, ignore_index=True), crs=4326)
        nacional.to_file(INTERIM / "cartografia.gpkg", layer=capa_salida, driver="GPKG")
        print(f"{capa_salida}: {len(nacional)} polígonos")


if __name__ == "__main__":
    main()
