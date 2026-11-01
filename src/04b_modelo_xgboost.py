"""Modelo alternativo de contraste con XGBoost y análisis de importancia de variables."""

import numpy as np
import pandas as pd
from xgboost import XGBRegressor
from config import PROCESSED, OUT_TAB, RAW

VARIABLES_MODELO = [
    "participacion_hace_6_anios",
    "participacion_hace_3_anios",
    "es_eleccion_presidencial",
    "hay_eleccion_gobernador",
    "hubo_gobernador_hace_6_anios",
    "escolaridad_promedio",
    "porcentaje_poblacion_indigena",
    "porcentaje_migrantes",
    "porcentaje_sin_salud",
    "porcentaje_jovenes",
    "tamano_padron_log",
    "crecimiento_padron",
    "es_seccion_urbana",
    "es_seccion_rural",
    "es_seccion_imputada"
]


def preparar_datos_simples(panel):
    df = panel.copy()
    calendario = pd.read_csv(RAW / "calendario_gubernaturas.csv")
    estados_con_gobernador = set(zip(calendario.anio, calendario.ent))

    df["participacion_hace_6_anios"] = df["part_lag6"]
    df["participacion_hace_3_anios"] = df["part_lag3"]
    df["es_eleccion_presidencial"] = (df["tipo"] == "presidencial").astype(int)

    df["hay_eleccion_gobernador"] = [int((a, e) in estados_con_gobernador) for a, e in zip(df.anio, df.ent)]
    df["hubo_gobernador_hace_6_anios"] = [int((a - 6, e) in estados_con_gobernador) for a, e in zip(df.anio, df.ent)]

    df["escolaridad_promedio"] = df["escolaridad"]
    df["porcentaje_poblacion_indigena"] = df["pct_indigena"]
    df["porcentaje_migrantes"] = df["pct_migrante"]
    df["porcentaje_sin_salud"] = df["pct_sin_salud"]
    df["porcentaje_jovenes"] = df["sh_joven_lag3"]
    df["tamano_padron_log"] = np.log(df["LN_lag3"].clip(lower=10))
    df["crecimiento_padron"] = df["ln_growth"]

    df["es_seccion_urbana"] = (df["tiposec"] == "U").astype(int)
    df["es_seccion_rural"] = (df["tiposec"] == "R").astype(int)
    df["es_seccion_imputada"] = df["lag_imput"]

    return df


def calcular_metricas(valores_reales, valores_predichos, estados):
    error = (valores_predichos - valores_reales) * 100
    error_dentro_del_estado = error - error.groupby(estados).transform("mean")

    return {
        "MAE": error.abs().mean(),
        "RMSE": np.sqrt((error ** 2).mean()),
        "sesgo": error.mean(),
        "MAE_intraestatal": error_dentro_del_estado.abs().mean(),
        "spearman": valores_reales.corr(valores_predichos, method="spearman")
    }


def main():
    panel_completo = pd.read_parquet(PROCESSED / "panel_seccion.parquet")
    df = preparar_datos_simples(panel_completo)
    datos_observados = df[df.part.notna() & df.ok.astype(bool)].copy()

    resultados_evaluacion = []

    for anio_prueba, anios_entrenamiento in [(2021, [2015, 2018]), (2024, [2015, 2018, 2021])]:
        entrenamiento = datos_observados[datos_observados.anio.isin(anios_entrenamiento)]
        prueba = datos_observados[datos_observados.anio == anio_prueba].copy()

        X_train = entrenamiento[VARIABLES_MODELO]
        y_train = entrenamiento["part"]
        pesos_train = entrenamiento["validos"]

        X_test = prueba[VARIABLES_MODELO]
        y_test = prueba["part"]

        modelo_xgb = XGBRegressor(
            n_estimators=120,
            max_depth=4,
            learning_rate=0.08,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1
        )
        modelo_xgb.fit(X_train, y_train, sample_weight=pesos_train)

        prediccion_xgb = np.clip(modelo_xgb.predict(X_test), 0.01, 0.99)
        metricas_xgb = calcular_metricas(y_test, pd.Series(prediccion_xgb, index=y_test.index), prueba.ent)
        metricas_xgb["modelo"] = "XGBoost"
        metricas_xgb["prueba"] = anio_prueba
        metricas_xgb["n_secciones"] = len(prueba)
        resultados_evaluacion.append(metricas_xgb)

    val_glm = pd.read_csv(OUT_TAB / "validacion_temporal.csv")
    df_xgb = pd.DataFrame(resultados_evaluacion)[["prueba", "modelo", "MAE", "RMSE", "sesgo", "MAE_intraestatal", "spearman"]]
    df_comparacion = pd.concat([val_glm, df_xgb], ignore_index=True).sort_values(["prueba", "MAE"]).round(3)

    print(df_comparacion.to_string(index=False))
    df_comparacion.to_csv(OUT_TAB / "comparacion_glm_vs_xgboost.csv", index=False)

    X_todo = datos_observados[VARIABLES_MODELO]
    y_todo = datos_observados["part"]
    pesos_todo = datos_observados["validos"]

    modelo_final_xgb = XGBRegressor(
        n_estimators=120, max_depth=4, learning_rate=0.08,
        subsample=0.8, colsample_bytree=0.8, random_state=42, n_jobs=-1
    )
    modelo_final_xgb.fit(X_todo, y_todo, sample_weight=pesos_todo)

    importancias = pd.DataFrame({
        "variable": VARIABLES_MODELO,
        "importancia_porcentual": (modelo_final_xgb.feature_importances_ * 100).round(2)
    }).sort_values("importancia_porcentual", ascending=False)

    print("\nImportancia de variables (XGBoost):")
    print(importancias.to_string(index=False))
    importancias.to_csv(OUT_TAB / "importancia_variables_xgboost.csv", index=False)

    filas_2027 = df[df.anio == 2027].copy()
    X_2027 = filas_2027[VARIABLES_MODELO]
    filas_2027["pred_xgboost_2027"] = np.clip(modelo_final_xgb.predict(X_2027), 0.01, 0.99)

    promedio_nacional_xgb = np.average(filas_2027["pred_xgboost_2027"], weights=filas_2027["LN_lag3"])
    print(f"\nParticipación nacional esperada 2027 (XGBoost): {promedio_nacional_xgb:.1%}")

    filas_2027[["ent", "seccion", "mun", "pred_xgboost_2027"]].to_parquet(
        PROCESSED / "pronostico_2027_xgboost.parquet", index=False
    )


if __name__ == "__main__":
    main()
