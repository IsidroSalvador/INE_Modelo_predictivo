"""Ajuste del modelo GLM cuasi-binomial con offset, validación temporal y pronóstico 2027."""

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from config import PROCESSED, OUT_TAB, RAW

FORMULA = (
    "part ~ C(tipo) + d_lag3 + d_gob + lag_imput"
    " + escolaridad + pct_indigena + pct_migrante + pct_sin_salud"
    " + sh_joven_lag3 + log_ln + ln_growth + C(tiposec)"
)


def logit(p):
    p = np.clip(p, 0.005, 0.995)
    return np.log(p / (1 - p))


def inv_logit(x):
    return 1 / (1 + np.exp(-x))


def preparar(panel):
    df = panel.copy()
    df["lg_lag6"] = logit(df.part_lag6)
    df["d_lag3"] = logit(df.part_lag3) - df.lg_lag6
    df["log_ln"] = np.log(df.LN_lag3.clip(lower=10))
    df["tiposec"] = df.tiposec.fillna("U")

    cal = pd.read_csv(RAW / "calendario_gubernaturas.csv")
    gob = set(zip(cal.anio, cal.ent))
    df["gob_t"] = [int((a, e) in gob) for a, e in zip(df.anio, df.ent)]
    df["gob_lag6"] = [int((a - 6, e) in gob) for a, e in zip(df.anio, df.ent)]
    df["d_gob"] = df.gob_t - df.gob_lag6
    return df


def ajustar(train):
    modelo = smf.glm(
        formula=FORMULA,
        data=train,
        family=sm.families.Binomial(),
        var_weights=train.validos,
        offset=train.lg_lag6
    )
    return modelo.fit(scale="X2")


def predecir_anclado(res, df):
    lp = res.predict(df, offset=df.lg_lag6, which="linear")
    nivel_objetivo = np.average(df.part_lag6, weights=df.LN_lag3)

    lo, hi = -3, 3
    for _ in range(50):
        mid = (lo + hi) / 2
        nivel = np.average(inv_logit(lp + mid), weights=df.LN_lag3)
        lo, hi = (mid, hi) if nivel < nivel_objetivo else (lo, mid)

    return inv_logit(lp + mid)


def metricas(real, pred, ent):
    err = (pred - real) * 100
    err_intra = err - err.groupby(ent).transform("mean")
    return {
        "MAE": err.abs().mean(),
        "RMSE": np.sqrt((err ** 2).mean()),
        "sesgo": err.mean(),
        "MAE_intraestatal": err_intra.abs().mean(),
        "spearman": real.corr(pred, method="spearman")
    }


def main():
    panel = preparar(pd.read_parquet(PROCESSED / "panel_seccion.parquet"))
    obs = panel[panel.part.notna() & panel.ok.astype(bool)]

    filas, residuos = [], []
    for anio_prueba, anios_train in [(2021, [2015, 2018]), (2024, [2015, 2018, 2021])]:
        train = obs[obs.anio.isin(anios_train)]
        test = obs[obs.anio == anio_prueba].copy()

        test["pred_base"] = test.part_lag6
        modelo_entrenado = ajustar(train)
        test["pred_modelo"] = predecir_anclado(modelo_entrenado, test)

        for nombre in ["base", "modelo"]:
            m = metricas(test.part, test[f"pred_{nombre}"], test.ent)
            filas.append({"prueba": anio_prueba, "modelo": nombre, "n": len(test), **m})

        residuos.append(test[["anio", "ent", "seccion", "part", "pred_base", "pred_modelo",
                              "estable", "lag_imput"]])

    val = pd.DataFrame(filas).round(3)
    val.to_csv(OUT_TAB / "validacion_temporal.csv", index=False)
    pd.concat(residuos).to_parquet(PROCESSED / "residuos_validacion.parquet", index=False)
    print(val.to_string(index=False))

    res_final = ajustar(obs)
    coef = pd.DataFrame({
        "coef": res_final.params,
        "error_std": res_final.bse,
        "p_valor": res_final.pvalues
    })
    coef["efecto_multiplicativo_odds"] = np.exp(coef.coef)
    coef.round(4).to_csv(OUT_TAB / "coeficientes_modelo.csv")
    print("\nCoeficientes GLM:")
    print(coef.round(4))

    f27 = panel[panel.anio == 2027].copy()
    f27["pred_2027"] = predecir_anclado(res_final, f27)
    f27 = f27.rename(columns={"part_lag6": "part_2021", "part_lag3": "part_2024"})
    f27["LN"] = f27.LN_lag3

    cols_guardar = [
        "ent", "seccion", "mun", "MPIONOM", "DEF", "tiposec", "LN", "estable",
        "lag_imput", "censo_imput", "gob_t", "part_2021", "part_2024", "pred_2027"
    ]
    f27[cols_guardar].to_parquet(PROCESSED / "pronostico_2027.parquet", index=False)

    print("\nParticipación nacional esperada 2027:",
          round(np.average(f27.pred_2027, weights=f27.LN), 4))


if __name__ == "__main__":
    main()
