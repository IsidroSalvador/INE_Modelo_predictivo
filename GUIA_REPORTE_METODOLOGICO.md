# GUÍA MAESTRA DE REDACCIÓN: REPORTE METODOLÓGICO Y ENTREGABLES
## Concurso "Hackea la Participación" (INE) — Reto 2: Predicción y Escenarios de Riesgo de Abstención

---

### PRESENTACIÓN GENERAL DE LOS ENTREGABLES

De acuerdo con las bases de la convocatoria, la entrega oficial del Reto 2 se compone de **tres elementos articulados**:

1. **Reporte metodológico y preventivo (PDF de 10 a 15 cuartillas):**
   * Documento formal que detalla el marco conceptual, las fuentes (CCPC central), el tratamiento de variables, la formulación econométrica/algorítmica, el semáforo territorial de riesgo y las recomendaciones de política institucional para focalizar recursos.
2. **Mapa de escenarios con y sin intervención (Archivos ejecutables y geoespaciales):**
   * Archivo interactivo ejecutable (`visor.html` basado en Leaflet para visualizar en cualquier navegador web sin requerir licencias de software).
   * Capas vectoriales georreferenciadas (`escenarios_seccion.gpkg`, `municipios.geojson`, `distritos.geojson`).
   * Mapas temáticos estáticos en alta resolución (`mapa_semaforo_municipal.png`, `mapa_escenarios_distritos.png`, `mapa_tijuana_secciones.png`).
3. **Base de datos anonimizada empleada:**
   * Archivo tabular plano (`base_anonimizada_seccion.csv`) que contiene las 69,380 secciones del país con su identificador geoelectoral disociado, atributos sociodemográficos consolidados, clasificación de riesgo y predicciones en cada escenario.

---

## ESQUEMA DE DISTRIBUCIÓN: LAS 12 CUARTILLAS DEL REPORTE (PÁGINA POR PÁGINA)

A continuación se detalla la estructura recomendada para un documento de **12 cuartillas** (longitud óptima que cumple el rango de 10 a 15 páginas sin relleno innecesario), indicando los títulos, contenidos, tablas y figuras exactas que debes colocar en cada página.

---

### CUARTILLA 1: Portada Institucional y Resumen Ejecutivo

* **Elementos de encabezado y portada:**
  * Título sugerido: *«Geografía del Desapego Cívico: Modelo Predictivo y Escenarios de Intervención Focalizada contra la Abstención Electoral en México 2027»*.
  * Subtítulo: *Reto 2 — Predicción y escenarios de riesgo de abstención (Datos abiertos y disociados)*.
  * Datos del participante o equipo: Nombre(s), edad (18-35 años), correo de contacto institucional y fecha (Octubre 2026).
  * Convocatoria: Concurso *Hackea la Participación*, Instituto Nacional Electoral (INE).

* **Resumen Ejecutivo (Párrafo destacado / Abstract, 250-300 palabras):**
  * **Problema:** En las elecciones intermedias federales, la participación ciudadana en México experimenta una contracción estructural de entre 10 y 12 puntos porcentuales respecto a los comicios presidenciales, concentrándose la abstención en enclaves territoriales específicos.
  * **Solución metodológica:** Utilizando como columna vertebral el Conteo Censal de Participación Ciudadana (CCPC 2009–2024), se desarrolló un modelo econométrico logit de cambio relativo (GLM Cuasi-Binomial con offset unitario) contrastado contra un modelo de Machine Learning (XGBoost). El modelo proyecta una participación nacional base de **51.8%** para las elecciones federales de 2027 en un escenario tendencial sin intervención.
  * **Semáforo y Hallazgo Central:** Se clasificó el territorio nacional en un semáforo de tres niveles, identificando **14,150 secciones electorales en Semáforo Rojo (Riesgo Crítico)**, las cuales concentran el 20.4% del electorado nacional y presentan una participación proyectada menor al 43.9%.
  * **Impacto de la intervención:** La simulación contrafactual demuestra que una intervención preventiva focalizada que logre un modesto incremento de entre +1.0 y +4.0 puntos porcentuales en estas zonas críticas movilizaría entre **246 mil y 987 mil votos adicionales**, logrando que más de 5,600 colonias salgan del rezago cívico.

---

### CUARTILLA 2: Planteamiento del Problema, Justificación y Principios de Privacidad

* **2.1 El desafío estructural de las elecciones intermedias:**
  * Explicar el ciclo político mexicano: mientras en elecciones presidenciales concurridas (2018: 63.4%, 2024: 61.0%) la atención pública es masiva, en las elecciones intermedias (2015: 47.7%, 2021: 52.7%) el interés decae.
  * La abstención no es homogénea ni aleatoria: se reproduce de forma crónica en determinadas colonias y municipios con características urbanas y sociodemográficas particulares.
* **2.2 Justificación institucional para el INE:**
  * El presupuesto y personal del INE (Capacitadores-Asistentes Electorales - CAEs, módulos de atención ciudadana, campañas de difusión) son finitos.
  * No tiene sentido distribuir los esfuerzos de promoción cívica de manera uniforme por todo el país cuando hay secciones donde vota el 75% y otras donde no vota ni el 35%. La analítica predictiva permite pasar de una estrategia reactiva a una **focalización preventiva ex-ante**.
* **2.3 Cumplimiento estricto de la privacidad y disociación de datos:**
  * Subrayar de forma contundente: el proyecto opera **exclusivamente con datos agregados por sección electoral**.
  * No se utilizó ningún dato personal, nombre, domicilio o registro individual del Padrón Electoral. Se respeta al 100% la Ley General de Protección de Datos Personales y las directrices de anonimización del reto.

---

### CUARTILLA 3: Datos y Fuentes de Información (El CCPC como Columna Vertebral)

* **3.1 La fuente central: CCPC 2009–2024:**
  * Describir el trabajo de consolidación realizado en el script `01_build_ccpc.py`: se procesaron e integraron **192 archivos CSV oficiales del INE** que cubren 6 procesos electorales federales consecutivos (2009, 2012, 2015, 2018, 2021 y 2024).
  * Explicar que el CCPC no es una muestra ni una encuesta: es el conteo censal exhaustivo casilla por casilla del universo electoral mexicano.
* **3.2 Fuentes complementarias y armonización geográfica:**
  * **Censo de Población y Vivienda 2020 (INEGI - ECEG):** Estadísticas Censales a Escalas Geoelectorales. Aportó variables de educación, lengua indígena, migración reciente y carencias sociales a nivel sección.
  * **Cartografía BGD 2024 (INE):** 32 coberturas cartográficas vectoriales estatales para clasificar secciones en Urbanas, Rurales y Mixtas.
  * **Calendario Político-Institucional:** Mapeo de elecciones concurrentes de gobernador (17 estados en 2027, incluyendo Aguascalientes y Quintana Roo).
* **Tabla a insertar:** Tabla resumen de las fuentes integradas en el panel longitudinal (`outputs/tables/ccpc_qc_por_anio.csv`), mostrando año, tipo de elección, lista nominal auditada y participación promedio histórica.

---

### CUARTILLA 4: Diccionario y Tratamiento de Variables

* **4.1 Las 4 Dimensiones Analíticas del Modelo:**
  1. *Dimensión Inercial / Histórica:* `participacion_hace_6_anios` ($t-6$, comicio intermedio comparable) y `participacion_hace_3_anios` ($t-3$, tendencia coyuntural).
  2. *Dimensión Institucional:* Tipo de elección (presidencial vs intermedia) y concurrencia de elección a gobernador (`hay_eleccion_gobernador`, `hubo_gobernador_hace_6_anios`).
  3. *Dimensión Sociodemográfica (Censo INEGI 2020):* Escolaridad promedio, porcentaje de población hablante de lengua indígena, porcentaje de población migrante (menos de 5 años en la entidad) y porcentaje sin afiliación a servicios de salud.
  4. *Dimensión Territorial y del Padrón:* Tipo de sección (Urbana, Rural, Mixta), tamaño de la lista nominal ($\log(\text{LN})$), tasa de crecimiento del padrón (`ln_growth`) y porcentaje de población joven de 18 a 34 años.
* **4.2 Tratamiento técnico de secciones especiales:**
  * Explicar cómo se resolvió la redistritación y el crecimiento urbano mediante el script `03_build_panel.py`: para secciones de reciente creación que carecían de historial en $t-6$, se implementó un mecanismo de **imputación por media municipal** acompañado de una bandera binaria de control (`lag_imput`) para no sesgar los coeficientes.

---

### CUARTILLA 5: Metodología: Formulación Econométrica (GLM) vs Machine Learning (XGBoost)

* **5.1 El Modelo Principal: GLM Cuasi-Binomial Logit con Offset:**
  * Presentar formalmente la ecuación matemática del script `04_model_validate.py`:
    $$\text{logit}(p_{i, t}) = 1.0 \times \text{logit}(p_{i, t-6}) + \beta_0 + \sum_{k} \beta_k X_{k, i, t} + \varepsilon_{i}$$
  * **Justificación técnica del Offset Unitario ($1.0$):** El modelo no intenta predecir el voto "desde cero" ni asume que una colonia nace en cada elección. La inercia previa es el ancla natural; el modelo estima estrictamente el **cambio marginal** atribuible a factores demográficos, políticos y de crecimiento poblacional.
* **5.2 El Modelo de Contraste: XGBoost:**
  * Explicar por qué se programó `04b_modelo_xgboost.py`: comprobar si algoritmos de ensamble basados en árboles de decisión (*gradient boosting*) descubren relaciones no lineales que el GLM pase por alto.
* **5.3 Razón de la selección del GLM como modelo definitivo:**
  * Aunque XGBoost logra un error similar, el GLM ofrece **parsimonia, total interpretabilidad en sus coeficientes y garantías de monotonicidad** (evita decisiones de "caja negra"), satisfaciendo los criterios de rigor científico solicitados por el jurado.

---

### CUARTILLA 6: Validación Temporal Estricta y Evaluación de Desempeño

* **6.1 Metodología de Validación Temporal (Backtesting Causal):**
  * Advertir sobre el error metodológico común de usar validación cruzada aleatoria ($K$-fold tradicional), la cual "hace trampa" al mezclar datos del futuro con el pasado.
  * Nuestro protocolo entrenó modelos estrictamente con elecciones pasadas para pronosticar elecciones futuras no vistas:
    * *Prueba 1 (2021):* Entrenado con 2015 y 2018 $\rightarrow$ Evaluado contra el resultado real de 2021.
    * *Prueba 2 (2024):* Entrenado con 2015, 2018 y 2021 $\rightarrow$ Evaluado contra el resultado real de 2024.
* **Tabla a insertar:** Comparativa de desempeño (`outputs/tables/comparacion_glm_vs_xgboost.csv`):
  * Mostrar MAE (Error Absoluto Medio) de **5.35 pp** en GLM y **5.15 pp** en XGBoost para 2024.
  * Destacar el **MAE intraestatal de 3.9 pp** (capacidad sobresaliente para ordenar qué colonias dentro de un mismo estado votarán más o menos) y la correlación de Spearman de **0.81**.
* **6.2 Diagnóstico Espacial y Bandas de Incertidumbre:**
  * Citar el resultado de la I de Moran sobre los residuos ($I = 0.59$, $p = 0.005$, de `outputs/tables/moran.csv`), reconociendo la existencia de dinámicas regionales.
  * Presentar la banda empírica de incertidumbre al 80%: $[-9.3\text{ pp}, +8.6\text{ pp}]$.

---

### CUARTILLA 7: El Semáforo de Riesgo Territorial

* **7.1 Criterios objetivos y transparentes de estratificación:**
  * Detallar cómo se definieron los umbrales del semáforo en `05_semaforo_escenarios.py` para evitar arbitrariedades:
    1. **Semáforo Rojo (Riesgo Crítico de Abstención):** Secciones con participación proyectada en el quintil inferior nacional ($< 43.9\%$) O con una caída proyectada severa ($\ge 3.0$ puntos porcentuales respecto a la intermedia previa). Total: **14,150 secciones (20.4%)**, que agrupan a **20.3 millones de electores**.
    2. **Semáforo Amarillo (Riesgo Moderado):** Participación proyectada entre 43.9% y 50.0%. Total: **14,028 secciones (20.2%)**.
    3. **Semáforo Verde (Baja Abstención / Estable):** Participación proyectada $> 50.0\%$. Total: **41,202 secciones (59.4%)**.
* **Gráfica / Tabla a insertar:** Distribución de secciones y lista nominal por color de semáforo.
* **Figura a insertar:** Mapa general de la República Mexicana con la semaforización a nivel municipal (`outputs/figures/mapa_semaforo_municipal.png`).

---

### CUARTILLA 8: Diagnóstico Geoelectoral: ¿Dónde se Concentra la Abstención?

* **8.1 El perfil territorial del abstencionismo crónico:**
  * Explicar los hallazgos espaciales: el riesgo crítico no está repartido uniformemente en el campo mexicano; se concentra de manera alarmante en **ciudades fronterizas del norte y periferias metropolitanas de rápido crecimiento**.
  * *¿Por qué ocurre esto?* Combinación de alta movilidad laboral (alta tasa de migrantes que no actualizan su credencial para votar), alta proporción de población joven de 18 a 34 años, y fraccionamientos periféricos con deficiente infraestructura urbana y desconexión social.
* **Tabla a insertar:** Los 10 Municipios de Mayor Prioridad Nacional (extraída de `outputs/tables/prioridad_municipio.csv`):
  * **Tijuana, Baja California:** 957 secciones rojas de 1,175 (82.6% del padrón en riesgo crítico; participación predicha: 37.4%).
  * **Juárez, Chihuahua:** 962 secciones rojas de 1,197 (78.2% del padrón en riesgo; participación predicha: 37.6%).
  * **Mexicali, Baja California:** 420 secciones rojas (76.5% del padrón en riesgo; participación predicha: 38.4%).
  * **Tonalá y Tlajomulco de Zúñiga, Jalisco:** >74% del padrón en riesgo crítico (participación predicha: ~38.0%).
  * **León, Guanajuato; Puebla, Puebla; Zapopan, Jalisco; Reynosa, Tamaulipas; Hermosillo, Sonora.**

---

### CUARTILLA 9: Simulación de Escenarios: Con Intervención vs. Sin Intervención

* **9.1 Lógica contrafactual de la intervención preventiva:**
  * El modelo sin intervención proyecta una participación nacional de **51.83%** (línea base inercial).
  * Se simularon tres escenarios de intervención institucional focalizada **exclusivamente en las 14,150 secciones en Semáforo Rojo**, evaluando su retorno cívico (votos adicionales y secciones rescatadas):
* **Tabla central a insertar:** Resumen de escenarios (`outputs/tables/escenarios_resumen.csv`):

| Escenario | Efecto en Secciones Rojas | Participación Nacional Proyectada | Votos Ciudadanos Adicionales | Secciones que Salen del Semáforo Rojo |
|---|:---:|:---:|:---:|:---:|
| **Sin Intervención (Inercial)** | 0.0 pp | **51.83%** | 0 | 0 |
| **Intervención Focalizada Leve** | +1.0 pp | **52.08%** | +246,834 | 1,586 secciones |
| **Intervención Focalizada Moderada** | +2.5 pp | **52.45%** | +617,086 | 3,757 secciones |
| **Intervención Focalizada Intensiva** | +4.0 pp | **52.83%** | **+987,337** | **5,619 secciones** |

* **Comentario analítico:** Demostrar que un esfuerzo institucional focalizado en solo una quinta parte del territorio nacional puede movilizar a casi **un millón de votantes adicionales** a nivel nacional y transformar el mapa cívico del país.

---

### CUARTILLA 10: Evidencia Cartográfica y Herramientas Visuales

* **10.1 Comparativa visual de escenarios:**
  * Inserción de la figura `outputs/figures/mapa_escenarios_distritos.png` o el acercamiento detallado seccional `outputs/figures/mapa_tijuana_secciones.png`.
  * Explicar cómo el mapa muestra la reducción visible de "manchas rojas" al transitar del escenario inercial al escenario de intervención moderada.
* **10.2 Descripción de los entregables geoespaciales:**
  * Explicar al jurado que la propuesta incluye un visor interactivo autónomo (`outputs/maps/visor.html`) desarrollado en HTML/JavaScript/Leaflet:
    * No requiere instalación de software propietario (funciona en cualquier navegador Chrome, Edge o Firefox con doble clic).
    * Permite a las Juntas Locales y Distritales del INE navegar el mapa seccional, filtrar por municipio y alternar entre escenarios con y sin intervención con botones dinámicos.
  * Mencionar la disponibilidad del paquete GeoPackage (`escenarios_seccion.gpkg`) con geometrías oficiales en EPSG:4326 para sistemas SIG como QGIS o ArcGIS.

---

### CUARTILLA 11: Recomendaciones Preventivas y Estrategia de Priorización de Recursos

Traducir los hallazgos matemáticos en **4 líneas de acción operativa concretas para el INE**:

1. **Módulos Móviles de Actualización y Credencialización Temprana:**
   * *Diagnóstico:* En los municipios fronterizos (Tijuana, Juárez, Reynosa) y periféricos (Tlajomulco, Tonalá), la abstención está ligada a credenciales no actualizadas tras cambios de domicilio.
   * *Acción:* Instalar módulos móviles del Registro Federal de Electores (RFE) directamente en zonas industriales (parques maquiladores) y nodos de transporte masivo de las secciones rojas durante los 6 meses previos al cierre del padrón.
2. **Campañas de Promoción Cívica Focalizadas en Jóvenes (18 a 34 años):**
   * *Diagnóstico:* El modelo identificó que una mayor proporción de jóvenes reduce la participación promedio seccional en hasta 1.7%.
   * *Acción:* La DECEYEC debe sustituir la publicidad genérica en medios tradicionales por micro-campañas digitales georreferenciadas (redes sociales y plataformas comunitarias) con vocería juvenil y temáticas locales que resuenen en estas colonias.
3. **Logística y Accesibilidad de Casillas Electorales:**
   * *Diagnóstico:* En secciones urbanas extensas de reciente crecimiento, la lejanía física de la casilla desincentiva el voto.
   * *Acción:* Desdoblamiento estratégico de casillas extraordinarias y contiguas para reducir tiempos de traslado a menos de 10 minutos a pie en colonias del Semáforo Rojo.
4. **Convenios de Responsabilidad Cívica con Empleadores Locales:**
   * *Acción:* En municipios con fuerte presencia manufacturera y de servicios, firmar convenios de estímulo y flexibilidad horaria con cámaras empresariales locales para asegurar que los turnos dominicales no obstaculicen el ejercicio del sufragio.

---

### CUARTILLA 12: Conclusiones, Reproducibilidad y Gobernanza de Datos

* **12.1 Conclusión institucional:**
  * La abstención no es un destino inevitable ni una apatía uniforme: es un fenómeno predecible y territorialmente concentrado.
  * Demostrar que el uso sistemático de los datos históricos del CCPC permite al INE maximizar la eficiencia de sus recursos operativos y salvaguardar la legitimidad democrática.
* **12.2 Protocolo de Reproducibilidad Técnica:**
  * Estructura limpia y modular: scripts numerados secuencialmente del `01` al `08` en lenguaje Python.
  * Tiempos de ejecución auditados (pipeline completo en menos de 10 minutos en una computadora convencional).
  * Semilla aleatoria fijada (`random_state=42`) para garantizar que cualquier auditor del INE obtenga exactamente los mismos resultados numéricos.
* **12.3 Especificaciones de la Base Anonimizada Entregada:**
  * Descripción de los campos del archivo `data/processed/base_anonimizada_seccion.csv`:
    * `seccion_id`: Clave única disociada (Entidad + Sección).
    * `entidad_nombre`, `municipio_nombre`: Ubicación administrativa.
    * `tipo_seccion`: Urbana, Rural, Mixta.
    * `lista_nominal`: Electorado registrado.
    * `prediccion_2027_inercial`: Tasa de participación proyectada sin intervención.
    * `semaforo_riesgo`: Categoría asignada (Rojo, Amarillo, Verde).
    * `prediccion_con_intervencion_baja`, `_media`, `_alta`: Estimaciones bajo cada escenario contrafactual.

---

## ESTRUCTURA DEL PAQUETE FINAL DE ENTREGA (.ZIP)

Para cumplir al 100% con los requisitos de entrega de la convocatoria, tu archivo ZIP final debe organizarse de la siguiente manera:

```text
HackeaLaParticipacion_Reto2_Equipo.zip
│
├── 01_Reporte_Escrito/
│   └── Reporte_Metodologico_y_Preventivo_Reto2.pdf   (Las 12 cuartillas en formato PDF)
│
├── 02_Mapas_y_Escenarios/
│   ├── visor_interactivo.html                        (Visor ejecutable Leaflet standalone)
│   ├── escenarios_seccion.gpkg                       (Capa espacial seccional georreferenciada)
│   ├── municipios_riesgo.geojson                     (Polígonos municipales simplificados)
│   ├── distritos_riesgo.geojson                      (Polígonos distritales federales)
│   └── figuras_estaticas/                            (Imágenes PNG de alta resolución insertadas en el reporte)
│       ├── mapa_semaforo_municipal.png
│       ├── mapa_escenarios_distritos.png
│       └── mapa_tijuana_secciones.png
│
├── 03_Base_Anonimizada/
│   └── base_anonimizada_seccion.csv                  (Dataset seccional con semáforo y predicciones)
│
└── 04_Codigo_Reproducible/
    ├── README.md                                     (Instrucciones de reproducción rápida)
    ├── requirements.txt                              (Librerías utilizadas)
    └── src/
        ├── config.py
        ├── 01_build_ccpc.py
        ├── 02_explore_secciones.py
        ├── 03_build_panel.py
        ├── 04_model_validate.py
        ├── 04b_modelo_xgboost.py
        ├── 05_semaforo_escenarios.py
        ├── 06_cartografia.py
        ├── 07_mapas.py
        └── 08_visor.py
```
