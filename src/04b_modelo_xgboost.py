"""MODELO ALTERNATIVO DE CONTRASTE: XGBOOST (MACHINE LEARNING).

¿POR QUÉ CREAMOS ESTE ARCHIVO?
------------------------------
En el plan del proyecto y en la rúbrica del INE se sugiere probar un modelo de
Machine Learning (como XGBoost o LightGBM) para CONTRASTAR contra el modelo principal (GLM):
1. Ver si un algoritmo de árboles con interacciones no lineales logra mejorar el error.
2. Identificar qué variables considera más importantes el algoritmo (Feature Importance).
3. Entender en qué casos la regresión GLM es mejor (más interpretable, no se sobreajusta)
   y dónde XGBoost puede aportar valor.

METODOLOGÍA DE EVALUACIÓN:
--------------------------
Usa exactamente los mismos datos y las mismas pruebas temporales que el GLM:
- Prueba 2021: Entrena con 2015 y 2018 -> Evalúa en 2021.
- Prueba 2024: Entrena con 2015, 2018 y 2021 -> Evalúa en 2024.
"""

import numpy as np
import pandas as pd
from xgboost import XGBRegressor
from config import PROCESSED, OUT_TAB, RAW

# Lista de variables explicativas (con nombres claros en español)
VARIABLES_MODELO = [
    "participacion_hace_6_anios",   # part_lag6 (la intermedia previa)
    "participacion_hace_3_anios",   # part_lag3 (la presidencial previa)
    "es_eleccion_presidencial",     # 1 si es presidencial, 0 si es intermedia
    "hay_eleccion_gobernador",      # 1 si concurre elección de gobernador
    "hubo_gobernador_hace_6_anios", # 1 si hubo gobernador en la elección comparable
    "escolaridad_promedio",         # Años de estudio según Censo 2020
    "porcentaje_poblacion_indigena",# % que habla lengua indígena
    "porcentaje_migrantes",         # % que llegó de otro estado en últimos 5 años
    "porcentaje_sin_salud",         # % sin afiliación médica
    "porcentaje_jovenes",           # % de electores de 18 a 34 años en el padrón
    "tamano_padron_log",            # Logaritmo de la lista nominal
    "crecimiento_padron",           # Crecimiento del electorado en la sección
    "es_seccion_urbana",            # 1 si es urbana, 0 si no
    "es_seccion_rural",             # 1 si es rural, 0 si no
    "es_seccion_imputada"           # 1 si la sección es nueva y no tenía historia previa
]


def preparar_datos_simples(panel):
    """
    Toma el panel procesado y prepara las columnas con nombres claros y números limpios.
    """
    df = panel.copy()

    # Leemos el calendario de gobernadores
    calendario = pd.read_csv(RAW / "calendario_gubernaturas.csv")
    estados_con_gobernador = set(zip(calendario.anio, calendario.ent))

    # Creamos las columnas con nombres legibles
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
    """Calcula los errores en puntos porcentuales (pp) para evaluar el modelo."""
    error = (valores_predichos - valores_reales) * 100
    error_dentro_del_estado = error - error.groupby(estados).transform("mean")

    return {
        "MAE": error.abs().mean(),                             # Error promedio absoluto en pp
        "RMSE": np.sqrt((error ** 2).mean()),                  # Raíz del error cuadrático
        "sesgo": error.mean(),                                 # Sesgo (+ sobreestima, - subestima)
        "MAE_intraestatal": error_dentro_del_estado.abs().mean(), # Precisión para ordenar colonias locales
        "spearman": valores_reales.corr(valores_predichos, method="spearman") # Correlación de rangos
    }


def main():
    print("Cargando datos del panel...")
    panel_completo = pd.read_parquet(PROCESSED / "panel_seccion.parquet")
    df = preparar_datos_simples(panel_completo)

    # Filtramos filas históricas que tienen resultado electoral confirmado
    datos_observados = df[df.part.notna() & df.ok.astype(bool)].copy()

    resultados_evaluacion = []

    # --------------------------------------------------------------------------
    # 1. EVALUACIÓN TEMPORAL (2021 Y 2024)
    # --------------------------------------------------------------------------
    for anio_prueba, anios_entrenamiento in [(2021, [2015, 2018]), (2024, [2015, 2018, 2021])]:
        print(f"\n--- Probando predicción para el año {anio_prueba} ---")
        entrenamiento = datos_observados[datos_observados.anio.isin(anios_entrenamiento)]
        prueba = datos_observados[datos_observados.anio == anio_prueba].copy()

        X_train = entrenamiento[VARIABLES_MODELO]
        y_train = entrenamiento["part"]
        pesos_train = entrenamiento["validos"]  # Ponderamos por tamaño de lista nominal

        X_test = prueba[VARIABLES_MODELO]
        y_test = prueba["part"]

        # Creamos y entrenamos el modelo XGBoost con hiperparámetros conservadores
        # (para evitar sobreajuste y mantener la estabilidad)
        modelo_xgb = XGBRegressor(
            n_estimators=120,      # 120 árboles secuenciales
            max_depth=4,           # Profundidad moderada de 4 niveles
            learning_rate=0.08,    # Tasa de aprendizaje suave
            subsample=0.8,         # Usa el 80% de las filas por árbol para reducir varianza
            colsample_bytree=0.8,  # Usa el 80% de columnas por árbol
            random_state=42,
            n_jobs=-1
        )

        modelo_xgb.fit(X_train, y_train, sample_weight=pesos_train)

        # Predicción puntual de XGBoost
        prediccion_xgb = modelo_xgb.predict(X_test)
        prediccion_xgb = np.clip(prediccion_xgb, 0.01, 0.99)  # Aseguramos que quede entre 1% y 99%

        # Evaluación
        metricas_xgb = calcular_metricas(y_test, pd.Series(prediccion_xgb, index=y_test.index), prueba.ent)
        metricas_xgb["modelo"] = "XGBoost"
        metricas_xgb["prueba"] = anio_prueba
        metricas_xgb["n_secciones"] = len(prueba)
        resultados_evaluacion.append(metricas_xgb)

    # --------------------------------------------------------------------------
    # 2. COMPARACIÓN CON LA LÍNEA BASE Y EL MODELO GLM
    # --------------------------------------------------------------------------
    # Leemos los resultados del GLM que obtuvimos en el paso 04
    val_glm = pd.read_csv(OUT_TAB / "validacion_temporal.csv")

    df_xgb = pd.DataFrame(resultados_evaluacion)[["prueba", "modelo", "MAE", "RMSE", "sesgo", "MAE_intraestatal", "spearman"]]
    df_comparacion = pd.concat([val_glm, df_xgb], ignore_index=True).sort_values(["prueba", "MAE"])
    df_comparacion = df_comparacion.round(3)

    print("\n=== TABLA COMPARATIVA: LÍNEA BASE vs. GLM vs. XGBOOST ===")
    print(df_comparacion.to_string(index=False))
    df_comparacion.to_csv(OUT_TAB / "comparacion_glm_vs_xgboost.csv", index=False)

    # --------------------------------------------------------------------------
    # 3. ENTRENAMIENTO FINAL Y ANÁLISIS DE IMPORTANCIA DE VARIABLES
    # --------------------------------------------------------------------------
    print("\nEntrenando XGBoost final con todo el histórico (2015-2024)...")
    X_todo = datos_observados[VARIABLES_MODELO]
    y_todo = datos_observados["part"]
    pesos_todo = datos_observados["validos"]

    modelo_final_xgb = XGBRegressor(
        n_estimators=120, max_depth=4, learning_rate=0.08,
        subsample=0.8, colsample_bytree=0.8, random_state=42, n_jobs=-1
    )
    modelo_final_xgb.fit(X_todo, y_todo, sample_weight=pesos_todo)

    # Extraemos la importancia de cada variable (cuánto aporta a la reducción de error)
    importancias = pd.DataFrame({
        "variable": VARIABLES_MODELO,
        "importancia_porcentual": (modelo_final_xgb.feature_importances_ * 100).round(2)
    }).sort_values("importancia_porcentual", ascending=False)

    print("\n=== IMPORTANCIA DE VARIABLES SEGÚN XGBOOST ===")
    print(importancias.to_string(index=False))
    importancias.to_csv(OUT_TAB / "importancia_variables_xgboost.csv", index=False)

    # --------------------------------------------------------------------------
    # 4. PRONÓSTICO 2027 CON XGBOOST
    # --------------------------------------------------------------------------
    filas_2027 = df[df.anio == 2027].copy()
    X_2027 = filas_2027[VARIABLES_MODELO]
    filas_2027["pred_xgboost_2027"] = np.clip(modelo_final_xgb.predict(X_2027), 0.01, 0.99)

    promedio_nacional_xgb = np.average(filas_2027["pred_xgboost_2027"], weights=filas_2027["LN_lag3"])
    print(f"\nParticipación nacional esperada para 2027 según XGBoost: {promedio_nacional_xgb:.1%}")

    # Guardamos las predicciones de XGBoost
    filas_2027[["ent", "seccion", "mun", "pred_xgboost_2027"]].to_parquet(
        PROCESSED / "pronostico_2027_xgboost.parquet", index=False
    )
    print("Resultados guardados con éxito en outputs/tables/ y data/processed/")


if __name__ == "__main__":
    main()
