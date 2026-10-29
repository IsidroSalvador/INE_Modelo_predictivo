"""PASO 5: SEMÁFORO DE RIESGO, ESCENARIOS DE INTERVENCIÓN E INCERTIDUMBRE.

¿QUÉ HACE ESTE SCRIPT?
----------------------
1. Calcula los INTERVALOS DE INCERTIDUMBRE (± 9 puntos porcentuales con 80% de confianza)
   basándose en los errores empíricos que cometió el modelo en las pruebas reales de 2021 y 2024.
2. Asigna el SEMÁFORO TERRITORIAL (Verde, Amarillo, Rojo) con criterios estadísticos claros:
   - Rojo: El 20% de secciones con menor participación del país (< 43.9%).
   - Amarillo: Entre el percentil 20 y 40 (43.9% a 50.6%) O si caen más de 3 puntos vs 2021.
   - Verde: El resto de las secciones.
3. Simula los ESCENARIOS DE INTERVENCIÓN INSTITUCIONAL:
   - Escenario sin intervención (la predicción tendencial pura).
   - Escenarios con intervención supuesta en secciones rojas:
     * Efecto Bajo: +1.0 punto porcentual de participación.
     * Efecto Medio: +2.5 puntos porcentuales.
     * Efecto Alto: +4.0 puntos porcentuales.
4. Genera las tablas de PRIORIZACIÓN INSTITUCIONAL agregadas a nivel MUNICIPIO y DISTRITO.
5. Exporta el archivo final anonimizado por sección (`base_anonimizada_seccion.csv`).
"""

import numpy as np
import pandas as pd
from config import PROCESSED, OUT_TAB

# Supuestos de intervención en las secciones en rojo (análisis de sensibilidad)
EFECTOS = {
    "bajo": 0.010,    # +1.0% de participación
    "medio": 0.025,   # +2.5% de participación
    "alto": 0.040     # +4.0% de participación
}
CAIDA_ALERTA = -3.0   # Si una sección cae 3 pp o más respecto a 2021, entra en alerta amarilla


def clasificar(pred, caida_pp, p20, p40):
    """
    Función que asigna el color del semáforo:
    - 'rojo': si la participación esperada está por debajo del percentil 20 nacional.
    - 'amarillo': si está entre percentil 20 y 40, O si su caída esperada es severa (<= -3 pp).
    - 'verde': en cualquier otro caso.
    """
    return np.select(
        [pred < p20, (pred < p40) | (caida_pp <= CAIDA_ALERTA)],
        ["rojo", "amarillo"],
        default="verde"
    )


def main():
    # 1. Cargamos el pronóstico de 2027 y la tabla de residuos (errores) de la validación
    df = pd.read_parquet(PROCESSED / "pronostico_2027.parquet")
    res = pd.read_parquet(PROCESSED / "residuos_validacion.parquet")

    # --------------------------------------------------------------------------
    # 2. CÁLCULO DE INCERTIDUMBRE (INTERVALO DEL 80%)
    # --------------------------------------------------------------------------
    # Medimos los errores reales fuera de muestra (Real - Modelo).
    res["err"] = res.part - res.pred_modelo
    choque = res.groupby("anio").err.mean()
    # Centramos los residuos para aislar la incertidumbre propia de cada sección
    err_centrado = res.err - res.anio.map(choque)
    q10, q90 = err_centrado.quantile([0.10, 0.90])

    # El intervalo empírico de cada sección queda delimitado por:
    df["pred_inf"] = (df.pred_2027 + q10).clip(0, 1)
    df["pred_sup"] = (df.pred_2027 + q90).clip(0, 1)
    print("=== 1. INTERVALO DE INCERTIDUMBRE ===")
    print(f"Rango del 80% por sección: [{q10*100:+.1f} pp, {q90*100:+.1f} pp]")

    # --------------------------------------------------------------------------
    # 3. ASIGNACIÓN DEL SEMÁFORO TERRITORIAL
    # --------------------------------------------------------------------------
    p20, p40 = df.pred_2027.quantile([0.20, 0.40])
    df["caida_pp"] = (df.pred_2027 - df.part_2021) * 100
    df["semaforo"] = clasificar(df.pred_2027, df.caida_pp, p20, p40)

    # Nivel de confianza: 'alta' para secciones históricas, 'baja' para secciones nuevas o imputadas
    df["confianza"] = np.where(df.estable.astype(bool) & (df.lag_imput == 0), "alta", "baja")

    print("\n=== 2. SEMÁFORO NACIONAL 2027 (SIN INTERVENCIÓN) ===")
    print(f"Umbral Rojo (P20): < {p20:.1%}")
    print(f"Umbral Amarillo (P40): {p20:.1%} a {p40:.1%}")
    print(df.groupby("semaforo").agg(secciones=("seccion", "size"), Lista_Nominal=("LN", "sum")))

    # --------------------------------------------------------------------------
    # 4. SIMULACIÓN DE ESCENARIOS DE INTERVENCIÓN (SENSIBILIDAD)
    # --------------------------------------------------------------------------
    # Escenario base (sin intervención)
    filas_escenarios = [{
        "escenario": "sin_intervencion",
        "efecto_pp": 0.0,
        "part_nacional": np.average(df.pred_2027, weights=df.LN),
        "votos_adicionales": 0,
        "secciones_rojas": int((df.semaforo == "rojo").sum())
    }]

    # Aplicamos hipotéticamente el efecto solo a las secciones que están en rojo
    rojo = df.semaforo == "rojo"
    for nivel, efecto in EFECTOS.items():
        col_pred = f"pred_interv_{nivel}"
        # Se suma el efecto porcentual a la sección roja (sin rebasar el 100%)
        df[col_pred] = np.where(rojo, (df.pred_2027 + efecto).clip(0, 1), df.pred_2027)

        # Re-evaluamos el semáforo bajo este nuevo escenario
        sem = clasificar(df[col_pred], (df[col_pred] - df.part_2021) * 100, p20, p40)
        df[f"semaforo_{nivel}"] = sem

        # Calculamos el impacto en votos y salida de alerta roja
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
    print("\n=== 3. COMPARATIVA DE ESCENARIOS ===")
    print(esc.to_string(index=False))

    # Guardamos la base de datos anonimizada oficial para el concurso
    df.to_csv(PROCESSED / "base_anonimizada_seccion.csv", index=False, encoding="utf-8")

    # --------------------------------------------------------------------------
    # 5. PRIORIZACIÓN INSTITUCIONAL POR MUNICIPIO Y DISTRITO
    # --------------------------------------------------------------------------
    # Agregamos las secciones para decirle al INE en qué municipios y distritos
    # hay más personas en lista nominal viviendo en secciones rojas.
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

        print(f"\nTop 5 {nivel}s prioritarios (mayor padrón en secciones rojas):")
        print(g.head(5)[llave + ["LN", "LN_rojo", "secc_rojas", "pred_2027", "pct_LN_rojo"]].round(3).to_string(index=False))

    print("\nTablas y bases guardadas en data/processed/ y outputs/tables/")


if __name__ == "__main__":
    main()
