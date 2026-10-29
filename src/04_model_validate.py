"""PASO 4: MODELO DE PARTICIPACIÓN Y VALIDACIÓN TEMPORAL.

================================================================================
¿DÓNDE ESTÁ EL MODELO Y CUÁL ES SU ECUACIÓN MATEMÁTICA?
================================================================================

La variable a predecir es la tasa de participación electoral de la sección $i$ en
el año $t$:
                p_{i, t} = SV_{i, t} / (SV_{i, t} + NV_{i, t})
Como es una proporción acotada entre 0 y 1 (o 0% y 100%), no se usa regresión
lineal ordinaria (que podría predecir valores absurdos como -5% o 115%). Se usa la
función logit:
                logit(p) = ln( p / (1 - p) )

LA ECUACIÓN MATEMÁTICA DEL MODELO ES:
------------------------------------
logit(p_{i, t}) = 1.0 * logit(p_{i, t-6})          <- PUNTO DE PARTIDA (OFFSET)
                  + beta_0                         <- Intercepto
                  + beta_1 * TipoEleccion          <- Presidencial vs Intermedia
                  + beta_2 * TendenciaReciente     <- d_lag3 (2024 vs 2021)
                  + beta_3 * CambioGubernatura     <- d_gob (si hay elección de gobernador)
                  + beta_4 * Escolaridad           <- Años de estudio (Censo 2020)
                  + beta_5 * PctIndigena           <- % lengua indígena (Censo 2020)
                  + beta_6 * PctMigrante           <- % migración reciente (Censo 2020)
                  + beta_7 * PctSinSalud           <- % sin afiliación médica (Censo 2020)
                  + beta_8 * PctJovenes            <- % personas de 18-34 años en el padrón
                  + beta_9 * LogListaNominal       <- Tamaño de la sección
                  + beta_10 * CrecimientoPadron    <- Dinamismo de la sección
                  + beta_11 * TipoSeccion          <- Urbana, Mixta o Rural
                  + beta_12 * BanderaImputacion    <- Si la sección no tenía dato previo

¿Por qué el término `1.0 * logit(p_{i, t-6})` tiene coeficiente fijo en 1.0?
A esto en estadística se le llama un OFFSET. En palabras cotidianas significa:
  "La mejor predicción para 2027 es asumir que la sección votará igual que en 2021.
   El modelo estadístico NO inventa una cifra desde la nada: solo calcula cuántos
   puntos SUMA o RESTA cada factor sociodemográfico e institucional a ese punto de partida."

================================================================================
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from config import PROCESSED, OUT_TAB, RAW

# ------------------------------------------------------------------------------
# 1. LA FÓRMULA EN CÓDIGO (Sintaxis de Patsy / Statsmodels)
# ------------------------------------------------------------------------------
# Nota: La variable `part_lag6` (t-6) no se pone aquí en la fórmula porque entra
# como `offset` en la función `smf.glm` (su coeficiente está fijado en 1.0).
FORMULA = (
    "part ~ C(tipo) + d_lag3 + d_gob + lag_imput"
    " + escolaridad + pct_indigena + pct_migrante + pct_sin_salud"
    " + sh_joven_lag3 + log_ln + ln_growth + C(tiposec)"
)


def logit(p):
    """Transforma una proporción (0 a 1) a escala log-odds (-inf a +inf)."""
    p = np.clip(p, 0.005, 0.995)
    return np.log(p / (1 - p))


def inv_logit(x):
    """Función inversa (sigmoide): regresa de log-odds a proporción (0 a 1)."""
    return 1 / (1 + np.exp(-x))


def preparar(panel):
    """Calcula las variables exactas que entrarán a la ecuación."""
    df = panel.copy()

    # Punto de partida: logit de la participación de hace 6 años (última intermedia)
    df["lg_lag6"] = logit(df.part_lag6)

    # Tendencia reciente: diferencia entre la intermedia previa y la presidencial previa
    df["d_lag3"] = logit(df.part_lag3) - df.lg_lag6

    # Logaritmo del tamaño del padrón
    df["log_ln"] = np.log(df.LN_lag3.clip(lower=10))
    df["tiposec"] = df.tiposec.fillna("U")

    # Calendario institucional: ¿Hay elección de gobernador en ese estado?
    cal = pd.read_csv(RAW / "calendario_gubernaturas.csv")
    gob = set(zip(cal.anio, cal.ent))

    # gob_t = 1 si el estado elige gobernador ese año; 0 si no
    df["gob_t"] = [int((a, e) in gob) for a, e in zip(df.anio, df.ent)]
    # gob_lag6 = 1 si el estado eligió gobernador hace 6 años; 0 si no
    df["gob_lag6"] = [int((a - 6, e) in gob) for a, e in zip(df.anio, df.ent)]
    # d_gob = cambio neto en concurrencia (+1 si ahora sí hay gobernador, -1 si antes hubo y ahora no)
    df["d_gob"] = df.gob_t - df.gob_lag6
    return df


# ------------------------------------------------------------------------------
# 2. LA FUNCIÓN DE AJUSTE (DONDE SE ENTRENA EL MODELO)
# ------------------------------------------------------------------------------
def ajustar(train):
    """
    Ajusta el Modelo Lineal Generalizado (GLM).
    - family=sm.families.Binomial(): especifica que modelamos una proporción de eventos (votos).
    - var_weights=train.validos: PONDERACIÓN por número de electores. Una sección de 3,000 electores
      aporta más información que una de 60 electores (reduce varianza residual).
    - offset=train.lg_lag6: fija el coeficiente de la participación previa en 1.0 (modelo de cambio).
    - scale='X2': cuasi-binomial, estima la sobredispersión para corregir las pruebas de hipótesis.
    """
    modelo = smf.glm(
        formula=FORMULA,
        data=train,
        family=sm.families.Binomial(),
        var_weights=train.validos,
        offset=train.lg_lag6
    )
    return modelo.fit(scale="X2")


# ------------------------------------------------------------------------------
# 3. ANCLAJE NACIONAL EX-ANTE (CALIBRACIÓN MACRO)
# ------------------------------------------------------------------------------
def predecir_anclado(res, df):
    """
    Toma las predicciones del modelo y las calibra en un solo parámetro global para que
    la media nacional ponderada iguale el nivel histórico de una elección intermedia (51.8%).
    PRESERVA EL ORDEN TERRITORIAL: las secciones de mayor abstención siguen siendo exactamente
    las mismas, pero se elimina el sesgo del promedio nacional.
    """
    lp = res.predict(df, offset=df.lg_lag6, which="linear")
    nivel_objetivo = np.average(df.part_lag6, weights=df.LN_lag3)

    # Búsqueda binaria simple para encontrar el desplazamiento constante `mid`
    lo, hi = -3, 3
    for _ in range(50):
        mid = (lo + hi) / 2
        nivel = np.average(inv_logit(lp + mid), weights=df.LN_lag3)
        lo, hi = (mid, hi) if nivel < nivel_objetivo else (lo, mid)

    return inv_logit(lp + mid)


def metricas(real, pred, ent):
    """Calcula las métricas de error en puntos porcentuales (pp)."""
    err = (pred - real) * 100                                   # Error en puntos porcentuales
    err_intra = err - err.groupby(ent).transform("mean")        # Error dentro del estado (ordenamiento local)
    return {
        "MAE": err.abs().mean(),                                # Error Absoluto Medio
        "RMSE": np.sqrt((err ** 2).mean()),                     # Raíz del Error Cuadrático Medio
        "sesgo": err.mean(),                                    # Sesgo promedio (sobre o subestimación)
        "MAE_intraestatal": err_intra.abs().mean(),             # Precisión para ordenar colonias dentro de cada estado
        "spearman": real.corr(pred, method="spearman")          # Correlación de rangos (1.0 = orden perfecto)
    }


# ------------------------------------------------------------------------------
# 4. FLUJO PRINCIPAL: VALIDACIÓN TEMPORAL Y PRONÓSTICO 2027
# ------------------------------------------------------------------------------
def main():
    # Preparamos los datos
    panel = preparar(pd.read_parquet(PROCESSED / "panel_seccion.parquet"))
    obs = panel[panel.part.notna() & panel.ok.astype(bool)]

    # --------------------------------------------------------------------------
    # A) VALIDACIÓN TEMPORAL ESTRICTA (Sin mirar al futuro)
    # --------------------------------------------------------------------------
    # Prueba 1: Entrenar con 2015-2018 -> Evaluar en 2021 (intermedia)
    # Prueba 2: Entrenar con 2015-2021 -> Evaluar en 2024 (presidencial)
    filas, residuos = [], []
    for anio_prueba, anios_train in [(2021, [2015, 2018]), (2024, [2015, 2018, 2021])]:
        train = obs[obs.anio.isin(anios_train)]
        test = obs[obs.anio == anio_prueba].copy()

        # Línea base: predecir exactamente igual a t-6 (la elección previa del mismo tipo)
        test["pred_base"] = test.part_lag6

        # Modelo estadístico GLM
        modelo_entrenado = ajustar(train)
        test["pred_modelo"] = predecir_anclado(modelo_entrenado, test)

        # Calculamos métricas para ambos
        for nombre in ["base", "modelo"]:
            m = metricas(test.part, test[f"pred_{nombre}"], test.ent)
            filas.append({"prueba": anio_prueba, "modelo": nombre, "n": len(test), **m})

        residuos.append(test[["anio", "ent", "seccion", "part", "pred_base", "pred_modelo",
                              "estable", "lag_imput"]])

    val = pd.DataFrame(filas).round(3)
    val.to_csv(OUT_TAB / "validacion_temporal.csv", index=False)
    pd.concat(residuos).to_parquet(PROCESSED / "residuos_validacion.parquet", index=False)
    print("=== RESULTADOS DE VALIDACIÓN TEMPORAL (ERROR EN PP) ===")
    print(val.to_string(index=False))

    # --------------------------------------------------------------------------
    # B) MODELO FINAL (2015-2024) Y PRONÓSTICO PARA 2027
    # --------------------------------------------------------------------------
    # Ahora que el modelo está validado, usamos toda la historia disponible para 2027
    res_final = ajustar(obs)

    # Guardamos la tabla de coeficientes para interpretarlos en el reporte
    coef = pd.DataFrame({
        "coef": res_final.params,
        "error_std": res_final.bse,
        "p_valor": res_final.pvalues
    })
    # El Odds Ratio indica el impacto multiplicativo:
    # > 1 significa que aumenta la participación; < 1 significa que la reduce.
    coef["efecto_multiplicativo_odds"] = np.exp(coef.coef)
    coef.round(4).to_csv(OUT_TAB / "coeficientes_modelo.csv")
    print("\n=== COEFICIENTES DEL MODELO FINAL ===")
    print(coef.round(4))

    # Predecimos la participación de 2027
    f27 = panel[panel.anio == 2027].copy()
    f27["pred_2027"] = predecir_anclado(res_final, f27)
    f27 = f27.rename(columns={"part_lag6": "part_2021", "part_lag3": "part_2024"})
    f27["LN"] = f27.LN_lag3  # Lista nominal de 2024 como proxy del tamaño del electorado

    cols_guardar = [
        "ent", "seccion", "mun", "MPIONOM", "DEF", "tiposec", "LN", "estable",
        "lag_imput", "censo_imput", "gob_t", "part_2021", "part_2024", "pred_2027"
    ]
    f27[cols_guardar].to_parquet(PROCESSED / "pronostico_2027.parquet", index=False)

    print("\nParticipación nacional esperada para 2027 (promedio ponderado):",
          round(np.average(f27.pred_2027, weights=f27.LN), 4))


if __name__ == "__main__":
    main()
