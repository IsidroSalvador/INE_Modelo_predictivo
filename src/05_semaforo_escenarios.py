"""Cálculo de bandas de incertidumbre, clasificación de semáforo territorial y simulación de escenarios."""

import numpy as np
import pandas as pd
from config import PROCESSED, OUT_TAB

EFECTOS = {
    "bajo": 0.010,
    "medio": 0.025,
    "alto": 0.040
}
CAIDA_ALERTA = -3.0


def clasificar(pred, caida_pp, p20, p40):
    return np.select(
        [pred < p20, (pred < p40) | (caida_pp <= CAIDA_ALERTA)],
        ["rojo", "amarillo"],
        default="verde"
    )


def main():
    df = pd.read_parquet(PROCESSED / "pronostico_2027.parquet")
    res = pd.read_parquet(PROCESSED / "residuos_validacion.parquet")

    res["err"] = res.part - res.pred_modelo
    choque = res.groupby("anio").err.mean()
    err_centrado = res.err - res.anio.map(choque)
    q10, q90 = err_centrado.quantile([0.10, 0.90])

    df["pred_inf"] = (df.pred_2027 + q10).clip(0, 1)
    df["pred_sup"] = (df.pred_2027 + q90).clip(0, 1)
    print(f"Banda empírica 80% por sección: [{q10*100:+.1f} pp, {q90*100:+.1f} pp]")

    p20, p40 = df.pred_2027.quantile([0.20, 0.40])
    df["caida_pp"] = (df.pred_2027 - df.part_2021) * 100
    df["semaforo"] = clasificar(df.pred_2027, df.caida_pp, p20, p40)
    df["confianza"] = np.where(df.estable.astype(bool) & (df.lag_imput == 0), "alta", "baja")

    print(f"Umbrales semáforo -> P20: {p20:.1%} | P40: {p40:.1%}")
    print(df.groupby("semaforo").agg(secciones=("seccion", "size"), Lista_Nominal=("LN", "sum")))

    filas_escenarios = [{
        "escenario": "sin_intervencion",
        "efecto_pp": 0.0,
        "part_nacional": np.average(df.pred_2027, weights=df.LN),
        "votos_adicionales": 0,
        "secciones_rojas": int((df.semaforo == "rojo").sum())
    }]

    rojo = df.semaforo == "rojo"
    for nivel, efecto in EFECTOS.items():
        col_pred = f"pred_interv_{nivel}"
        df[col_pred] = np.where(rojo, (df.pred_2027 + efecto).clip(0, 1), df.pred_2027)

        sem = clasificar(df[col_pred], (df[col_pred] - df.part_2021) * 100, p20, p40)
        df[f"semaforo_{nivel}"] = sem

        votos_mas = int(((df[col_pred] - df.pred_2027) * df.LN).sum())
        filas_escenarios.append({
            "escenario": f"intervencion_{nivel}",
            "efecto_pp": efecto * 100,
            "part_nacional": np.average(df[col_pred], weights=df.LN),
            "votos_adicionales": votos_mas,
            "secciones_rojas": int((sem == "rojo").sum())
        })

    esc = pd.DataFrame(filas_escenarios)
    esc["part_nacional"] = esc.part_nacional.round(4)
    esc.to_csv(OUT_TAB / "escenarios_resumen.csv", index=False)
    print("\nEscenarios:")
    print(esc.to_string(index=False))

    df.to_csv(PROCESSED / "base_anonimizada_seccion.csv", index=False, encoding="utf-8")

    df["LN_rojo"] = df.LN * (df.semaforo == "rojo")
    for nivel, llave in [("municipio", ["ent", "mun", "MPIONOM"]), ("distrito", ["ent", "DEF"])]:
        g = df.assign(
            sv_pred=df.pred_2027 * df.LN,
            sv_21=df.part_2021 * df.LN
        ).groupby(llave).agg(
            secciones=("seccion", "size"),
            LN=("LN", "sum"),
            LN_rojo=("LN_rojo", "sum"),
            secc_rojas=("semaforo", lambda s: (s == "rojo").sum()),
            sv_pred=("sv_pred", "sum"),
            sv_21=("sv_21", "sum")
        ).reset_index()

        g["pred_2027"] = g.sv_pred / g.LN
        g["part_2021"] = g.sv_21 / g.LN
        g["pct_LN_rojo"] = g.LN_rojo / g.LN
        g = g.drop(columns=["sv_pred", "sv_21"]).sort_values("LN_rojo", ascending=False)
        g.to_csv(OUT_TAB / f"prioridad_{nivel}.csv", index=False, encoding="utf-8")


if __name__ == "__main__":
    main()
