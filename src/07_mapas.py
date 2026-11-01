"""Generación de capas geoespaciales, autocorrelación espacial (I de Moran) y mapas estáticos."""

import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np
import pandas as pd
from esda.moran import Moran
from libpysal.weights import KNN
from config import INTERIM, PROCESSED, OUT_MAP, OUT_FIG, OUT_TAB

COLORES = {"verde": "#2e9e5b", "amarillo": "#f2c230", "rojo": "#d64541"}
GPKG = INTERIM / "cartografia.gpkg"


def semaforo(pred, caida_pp, p20, p40):
    return np.select([pred < p20, (pred < p40) | (caida_pp <= -3)], ["rojo", "amarillo"], "verde")


def agregar(df, llave):
    d = df.assign(w_pred=df.pred_2027 * df.LN, w_21=df.part_2021 * df.LN,
                  w_med=df.pred_interv_medio * df.LN,
                  LN_rojo=df.LN * (df.semaforo == "rojo"),
                  LN_rojo_medio=df.LN * (df.semaforo_medio == "rojo"))
    g = d.groupby(llave).agg(secciones=("seccion", "size"), LN=("LN", "sum"),
                             w_pred=("w_pred", "sum"), w_21=("w_21", "sum"), w_med=("w_med", "sum"),
                             LN_rojo=("LN_rojo", "sum"), LN_rojo_medio=("LN_rojo_medio", "sum"))
    g["pred_2027"] = g.w_pred / g.LN
    g["part_2021"] = g.w_21 / g.LN
    g["pred_interv_medio"] = g.w_med / g.LN
    g["pct_LN_rojo"] = g.LN_rojo / g.LN
    g["pct_LN_rojo_medio"] = g.LN_rojo_medio / g.LN
    return g.drop(columns=["w_pred", "w_21", "w_med"]).reset_index()


def mapa(gdf, columna, titulo, archivo, ax=None):
    nuevo = ax is None
    if nuevo:
        fig, ax = plt.subplots(figsize=(11, 7))
    gdf.plot(color=gdf[columna].map(COLORES).fillna("#cccccc"), linewidth=0, ax=ax)
    ax.set_title(titulo, fontsize=12)
    ax.set_axis_off()
    ax.legend(handles=[Patch(color=COLORES[k], label=k.capitalize()) for k in ("rojo", "amarillo", "verde")],
              loc="lower left", frameon=False)
    if nuevo:
        plt.tight_layout()
        plt.savefig(OUT_FIG / archivo, dpi=200)
        plt.close()


def main():
    df = pd.read_csv(PROCESSED / "base_anonimizada_seccion.csv")
    p20, p40 = df.pred_2027.quantile([0.20, 0.40])

    sec = gpd.read_file(GPKG, layer="seccion")[["ENTIDAD", "SECCION", "geometry"]]
    sec = sec.rename(columns={"ENTIDAD": "ent", "SECCION": "seccion"}).dissolve(["ent", "seccion"]).reset_index()
    sec = sec.merge(df, on=["ent", "seccion"], how="inner")
    print(f"Secciones con geometría: {len(sec)} de {len(df)} ({len(sec)/len(df):.1%})")
    sec.to_file(OUT_MAP / "escenarios_seccion.gpkg", layer="secciones", driver="GPKG")

    cent = sec.to_crs(6372).geometry.centroid
    w = KNN.from_array(np.column_stack([cent.x, cent.y]), k=8)
    w.transform = "r"
    res = pd.read_parquet(PROCESSED / "residuos_validacion.parquet")
    r24 = res[res.anio == 2024].assign(error=lambda x: x.pred_modelo - x.part)[["ent", "seccion", "error"]]
    s2 = sec[["ent", "seccion"]].merge(r24, how="left")
    filas = [{"variable": "pred_2027", **_moran(sec.pred_2027.values, w)}]
    ok = s2.error.notna().values
    if ok.all():
        filas.append({"variable": "error_validacion_2024", **_moran(s2.error.values, w)})
    else:
        c2 = cent[ok]
        w2 = KNN.from_array(np.column_stack([c2.x, c2.y]), k=8)
        w2.transform = "r"
        filas.append({"variable": "error_validacion_2024", **_moran(s2.error.values[ok], w2)})
    moran = pd.DataFrame(filas)
    moran.to_csv(OUT_TAB / "moran.csv", index=False)
    print(moran)

    mun_geo = gpd.read_file(GPKG, layer="municipio")[["ENTIDAD", "MUNICIPIO", "NOMBRE", "geometry"]]
    mun_geo = mun_geo.rename(columns={"ENTIDAD": "ent", "MUNICIPIO": "mun", "NOMBRE": "nombre"})
    mun = mun_geo.merge(agregar(df, ["ent", "mun"]), on=["ent", "mun"], how="left")

    dis_geo = gpd.read_file(GPKG, layer="distrito")[["ENTIDAD", "DISTRITO_F", "geometry"]]
    dis_geo = dis_geo.rename(columns={"ENTIDAD": "ent", "DISTRITO_F": "DEF"})
    dis = dis_geo.merge(agregar(df, ["ent", "DEF"]), on=["ent", "DEF"], how="left")

    for g in (mun, dis):
        g["semaforo"] = semaforo(g.pred_2027, (g.pred_2027 - g.part_2021) * 100, p20, p40)
        g["semaforo_medio"] = semaforo(g.pred_interv_medio, (g.pred_interv_medio - g.part_2021) * 100, p20, p40)
        g.loc[g.pred_2027.isna(), ["semaforo", "semaforo_medio"]] = "sin_dato"
        g.geometry = g.geometry.simplify(0.003, preserve_topology=True)
        for c in g.select_dtypes("float").columns:
            g[c] = g[c].round(4)
    mun.to_file(OUT_MAP / "municipios.geojson", driver="GeoJSON")
    dis.to_file(OUT_MAP / "distritos.geojson", driver="GeoJSON")

    COLORES["sin_dato"] = "#cccccc"
    mapa(mun, "semaforo", "Semáforo de riesgo de abstención 2027 (municipios, sin intervención)",
         "mapa_semaforo_municipal.png")
    fig, axes = plt.subplots(1, 2, figsize=(18, 7))
    mapa(dis, "semaforo", "Distritos 2027 – sin intervención", None, axes[0])
    mapa(dis, "semaforo_medio", "Distritos 2027 – con intervención (efecto medio +2.5 pp)", None, axes[1])
    plt.tight_layout()
    plt.savefig(OUT_FIG / "mapa_escenarios_distritos.png", dpi=200)
    plt.close()
    tij = sec[(sec.ent == 2) & (sec.mun == 4)]
    mapa(tij, "semaforo", "Tijuana: semáforo por sección (sin intervención)", "mapa_tijuana_secciones.png")


def _moran(valores, w):
    m = Moran(valores, w, permutations=199)
    return {"I_moran": round(m.I, 4), "p_valor": round(m.p_sim, 4)}


if __name__ == "__main__":
    main()
