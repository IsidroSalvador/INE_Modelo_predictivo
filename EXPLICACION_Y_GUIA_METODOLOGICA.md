# Guía Metodológica, Conceptual y de Código
## Proyecto: Hackea la Participación (INE) – Reto 2 (Riesgo de Abstención)

Esta guía fue preparada especialmente para que tengas **todo el contexto electoral, conceptual, matemático y de código** necesario para redactar tu **Reporte Metodológico** (10-15 cuartillas), tu presentación y resolver cualquier duda técnica o institucional.

---

## 1. Glosario Electoral y Geográfico (Desde Cero)

Para alguien que no viene del ámbito electoral, la terminología del INE puede parecer un laberinto de siglas. Aquí tienes la explicación clara y estructurada:

### 1.1 La jerarquía del territorio electoral en México
El país se divide territorialmente para fines electorales en diferentes niveles anidados:

```
[PAÍS: México]
   │
   ├── 32 ENTIDADES FEDERATIVAS (Estados + CDMX)
   │
   ├── 300 DISTRITOS ELECTORALES FEDERALES (DEF)
   │     └── Demarcaciones con población similar (~300,000 - 380,000 electores).
   │         En cada uno se elige 1 Diputado(a) Federal por Mayoría Relativa.
   │         El INE los actualiza periódicamente (la última fue la "Distritación 2023").
   │
   ├── ~2,470 MUNICIPIOS (o Alcaldías en CDMX)
   │     └── La división política y administrativa clásica de los estados.
   │
   └── ~70,700 SECCIONES ELECTORALES
         └── LA CÉLULA BÁSICA del sistema electoral.
             Es un área geográfica pequeña (un barrio, colonia o grupo de manzanas)
             que suele tener entre 100 y 3,000 personas empadronadas.
             Tu credencial para votar dice exactamente a qué "Sección" perteneces,
             y define en qué casilla te toca votar.
```

> **¿Por qué modelamos por Sección Electoral?**  
> Porque la sección es el nivel más fino de agregación sin datos personales. Te permite detectar con lupa qué colonia o barrio exacto se está absteniendo, en lugar de pintar a todo un municipio gigante del mismo color. Sin embargo, para la toma de decisiones institucionales, el semáforo también se agrega a **municipios** y **distritos**, porque las Juntas Distritales del INE operan a nivel distrital y municipal.

---

### 1.2 Tipos de elecciones federales: ¿Por qué no son todas iguales?
En México hay dos tipos de elecciones federales cada 3 años:
1. **Elección Presidencial (cada 6 años: 2012, 2018, 2024):**  
   Se vota por Presidencia de la República, Senadurías y Diputaciones Federales. La movilización ciudadana y la atención mediática son masivas. La participación nacional suele rondar entre el **60% y 63%**.
2. **Elección Intermedia (cada 6 años, intercalada: 2009, 2015, 2021, y la próxima en 2027):**  
   Solo se renueva la Cámara de Diputados Federal (más elecciones locales concurrentes). No hay elección de Presidente. Históricamente la participación cae drásticamente a un rango de **44% a 52%**.

> **Regla de oro metodológica:**  
> La elección a pronosticar es **2027**, que es **intermedia**. Si intentáramos predecir 2027 asumiendo el comportamiento de 2024 (presidencial), cometeríamos un sesgo enorme. Por eso, el punto de comparación natural y la línea base de 2027 es la intermedia anterior: **2021** (hace 6 años en el ciclo intermedia-intermedia).

---

### 1.3 Términos de los Conteos Censales de Participación Ciudadana (CCPC)
El INE publica tras cada elección los datos de los cuadernillos de lista nominal usados en las casillas:
- **Lista Nominal (LN):** Número de personas que tienen su credencial para votar vigente y recogida, listas para votar en esa sección.
- **SV (Sí Votaron):** Número de personas que acudieron a la casilla y cuya credencial fue marcada con sello de voto en el cuadernillo oficial.
- **NV (No Votaron):** Personas registradas en la lista nominal que **no acudieron** a votar (los abstencionistas).
- **NS (No Especificado):** Casillas o cuadernillos que no pudieron capturarse (por ejemplo, casillas que sufrieron robo de paquetes, violencia o cuadernillos retenidos por juicio electoral). Son una fracción muy pequeña (~2-6%).
- **Tasa de Participación:**  
  $$\text{Participación} = \frac{SV}{SV + NV}$$  
  Se calcula sobre los registros válidos verificados (excluyendo los cuadernillos no disponibles $NS$).

---

### 1.4 ¿Qué es el "Efecto Arrastre" de las Gubernaturas Concurrentes?
En México, cada estado decide cuándo renueva a su gobernador/a. Cuando la elección de gobernador coincide el mismo domingo que la elección federal ("elección concurrente"), la participación en ese estado sube fuertemente (entre 4 y 7 puntos porcentuales) porque hay campañas locales muy intensas.

- En **2021** hubo 15 gubernaturas en juego.
- En **2027** habrá **17 gubernaturas concurrentes** (las 15 de 2021 más **Aguascalientes** y **Quintana Roo**, cuyos calendarios sexenales concurren con la intermedia federal de 2027).  
- En el modelo, esta variable es crucial: si un estado tuvo gobernador en 2021 pero no en 2027 (o viceversa), su participación esperada cambiará significativamente por razones de calendario institucional, no por desinterés intrínseco.

---

## 2. Modelado y Escenarios: ¿Qué significan y cómo se pensaron?

### 2.1 La Línea Base (Benchmark)
En ciencia de datos, nunca se presenta un modelo complejo sin compararlo contra una regla simple y lógica.  
Nuestra **Línea Base** dice: *"La mejor estimación para 2027 es que cada sección participe exactamente igual que en la última elección del mismo tipo (2021)"*.  
Cualquier modelo predictivo debe demostrar que mejora el error de la línea base en pruebas hacia atrás en el tiempo.

### 2.2 El Modelo Principal: ¿Dónde está y cuál es su ecuación matemática?

En lugar de intentar predecir la participación desde cero con decenas de variables ruidosas, el modelo adopta un principio econométrico sólido:
$$\text{logit}(p_{i, 2027}) = \underbrace{1.0 \times \text{logit}(p_{i, 2021})}_{\text{PUNTO DE PARTIDA (OFFSET)}} + \beta_0 + \sum_{k=1}^K \beta_k X_{k, i}$$

Donde la función logit es:
$$\text{logit}(p) = \ln\left(\frac{p}{1 - p}\right)$$

#### Correspondencia exacta: Ecuación Matemática vs. Líneas de Código Python en `04_model_validate.py`:

| Término Matemático | Variable en Python (`FORMULA`) | ¿Qué significa en la realidad electoral? |
|---|---|---|
| $\text{logit}(p_{i, 2021})$ | `offset = train.lg_lag6` (en `ajustar`) | **Punto de partida con coeficiente fijo = 1.0.** Asume que la sección votará igual que en la última intermedia (2021), salvo por los ajustes de abajo. |
| $\beta_0$ | `Intercept` | Constante del modelo. |
| $\beta_1 \cdot \text{Tipo}$ | `C(tipo)` | Controla si la elección es presidencial o intermedia (en 2027 vale 0 por ser intermedia). |
| $\beta_2 \cdot \Delta_{\text{reciente}}$ | `d_lag3` | Tendencia reciente: diferencia entre la elección de 2024 y la de 2021. Si una colonia viene votando al alza, suma puntos. |
| $\beta_3 \cdot \Delta_{\text{gob}}$ | `d_gob` | **Cambio en concurrencia de gobernador:** vale $+1$ si el estado ahora elige gobernador pero en 2021 no; $-1$ en caso contrario; $0$ si no cambió. |
| $\beta_4 \cdot \text{Escolaridad}$ | `escolaridad` | Años promedio de estudio de las personas de 15+ años (Censo 2020 ECEG). A mayor escolaridad, mayor participación (+). |
| $\beta_5 \cdot \text{Indígena}$ | `pct_indigena` | Porcentaje de población que habla lengua indígena (Censo 2020). Históricamente en elecciones federales presentan mayor lealtad comunitaria (+). |
| $\beta_6 \cdot \text{Migración}$ | `pct_migrante` | Porcentaje de personas que vivían en otro estado hace 5 años (Censo 2020). Las zonas con alta población flotante votan menos (-). |
| $\beta_7 \cdot \text{SinSalud}$ | `pct_sin_salud` | Porcentaje sin afiliación a servicios médicos (proxy de vulnerabilidad/informalidad). |
| $\beta_8 \cdot \text{Jóvenes}$ | `sh_joven_lag3` | **Porcentaje de jóvenes (18 a 34 años)** en el padrón electoral. Su coeficiente es negativo ($\beta < 0$), confirmando que a más jóvenes en la colonia, menor participación histórica (-). |
| $\beta_9 \cdot \ln(\text{Padrón})$ | `log_ln` | Tamaño de la sección electoral (las secciones muy grandes suelen tener mayor abstención). |
| $\beta_{10} \cdot \text{Crecimiento}$ | `ln_growth` | Ritmo de crecimiento del padrón (colonias de reciente creación o fraccionamientos nuevos). |
| $\beta_{11} \cdot \text{TipoSecc}$ | `C(tiposec)` | Clasificación del INE: Urbana (U), Mixta (M) o Rural (R). |
| $\beta_{12} \cdot \text{Imputación}$ | `lag_imput` | Bandera de control: vale 1 si la sección es nueva y se le imputó el promedio municipal. |

#### ¿Cómo se ajusta en Python?
En `src/04_model_validate.py` (función `ajustar`):
```python
modelo = smf.glm(
    formula=FORMULA, 
    data=train, 
    family=sm.families.Binomial(), 
    var_weights=train.validos, 
    offset=train.lg_lag6
)
return modelo.fit(scale="X2")
```
- `family=sm.families.Binomial()`: Porque la variable dependiente es una tasa o proporción de éxitos entre $SV$ y $NV$.
- `var_weights=train.validos`: **Ponderación censal.** Una sección de 3,500 electores tiene mayor peso estadístico que una de 40 electores, reduciendo el ruido de secciones diminutas.
- `offset=train.lg_lag6`: Fija el coeficiente de $p_{2021}$ en 1.0 (convirtiendo la regresión en un **modelo de cambio o desviación** respecto a la elección comparable).
- `scale="X2"`: Estimador cuasi-binomial de Pearson que corrige la sobredispersión para que los valores p y errores estándar sean rigurosos.

---

### 2.3 Validación Temporal (Rigor Metodológico)
Para evaluar el modelo **no usamos división aleatoria (K-Fold cross-validation)**, porque en series de tiempo eso constituiría "fuga de información" (predecir el pasado conociendo el futuro). Se utilizó **validación temporal estricta**:
- **Prueba 1 (2021):** Se entrenó con datos de 2015 y 2018 para predecir 2021 (intermedia).
  - *Línea Base MAE:* 9.93 pp  
  - *Modelo GLM MAE:* **7.69 pp** (reducción sustancial del error).
- **Prueba 2 (2024):** Se entrenó con 2015, 2018 y 2021 para predecir 2024 (presidencial).
  - *Línea Base MAE:* 5.11 pp  
  - *Modelo GLM MAE:* 5.35 pp (competitivo, capturando con mayor precisión el ordenamiento intra-estatal: 3.94 pp frente a 4.14 pp).

---

### 2.4 El Semáforo de Riesgo Territorial
El reto exige clasificar las áreas según su riesgo de abstención. Para evitar decisiones arbitrarias, se fijaron criterios estadísticos transparentes y replicables sobre la participación esperada 2027:
- **Rojo (Riesgo Alto):** Secciones con participación esperada menor al **Percentil 20 nacional** (por debajo del **43.9%**). Son zonas de abstención crítica.
- **Amarillo (Riesgo Medio / Alerta de Deterioro):** Secciones con participación entre el **Percentil 20 y el Percentil 40** (entre **43.9% y 50.6%**) **O** secciones que, aun estando más arriba, proyectan una **caída esperada de 3 puntos porcentuales o más** respecto a 2021.
- **Verde (Bajo Riesgo):** Secciones con participación esperada superior al 50.6% y sin alertas de caída severa.

---

### 2.5 Escenarios: "¿Sin Intervención" vs. "Con Intervención"?
Esta es una parte central del Reto 2 y debe explicarse con mucho rigor en tu reporte:

- **Escenario (a) "Sin Intervención" (Línea Base Inercial):**  
  Representa el futuro más probable si el INE, los partidos y la sociedad civil mantienen sus dinámicas habituales de operación. Es la predicción pura del modelo para 2027.
  - Participación nacional esperada: **51.8%**
  - Secciones en Rojo: **14,150 secciones** (albergan a 24.7 millones de electores).

- **Escenario (b) "Con Intervención" (Simulación de Priorización Preventiva):**  
  El INE no puede forzar a nadie a votar, pero sí puede focalizar recursos preventivos: módulos de atención ciudadana itinerantes, campañas intensivas de credencialización y voto joven, talleres de educación cívica y coordinación comunitaria.  
  Como no se dispone de un experimento causal previo para conocer el impacto exacto de estas campañas, la literatura y la rúbrica exigen plantearlo como un **SUPUESTO con Análisis de Sensibilidad**:
  1. *Efecto Bajo (+1.0 pp en secciones rojas):* Generaría ~247,000 votos adicionales; 1,586 secciones saldrían del nivel rojo.
  2. *Efecto Medio (+2.5 pp en secciones rojas):* Generaría ~617,000 votos adicionales; 3,757 secciones superarían el umbral rojo.
  3. *Efecto Alto (+4.0 pp en secciones rojas):* Generaría ~987,000 votos adicionales; 5,619 secciones saldrían de alerta roja.

---

## 3. ¿Qué hace exactamente cada script del proyecto?

Todo el pipeline está en la carpeta `src/` y está diseñado para ejecutarse secuencialmente:

### 3.1 `config.py` (Configuración central)
Define las rutas a carpetas (`data/raw`, `data/processed`, etc.), los años electorales (2009 a 2024), qué elección es intermedia y cuál es presidencial, y los rangos de edad.

### 3.2 `01_build_ccpc.py` (Agrupación de datos del INE)
Los archivos originales del CCPC vienen divididos en 192 archivos CSV gigantes (32 estados x 6 elecciones) desglosados persona por persona por sexo y edad. Este script los lee, calcula la participación en cada sección ($SV / [SV + NV]$) y los guarda en una sola tabla limpia: `ccpc_seccion_anio.parquet`.

### 3.3 `02_explore_secciones.py` (Auditoría y estabilidad de secciones)
**¿Qué hace exactamente?**  
Es el control de calidad previo al modelado. Revisa si las secciones han cambiado con los años:
- Mide cuántas secciones han existido de forma ininterrumpida desde 2009 hasta 2024 (descubre que **el 87.4% del padrón electoral actual vive en secciones con historia completa**).
- Detecta si alguna sección cambió de municipio.
- Detecta "desdoblamientos": secciones que de pronto pierden la mitad de su gente porque el INE las partió en dos.
- Comprueba que el 99.9% de las secciones coincidan con el Censo 2020 (ECEG).  
*No entrena modelos ni altera datos; solo produce tablas para que en tu reporte demuestres que conoces la calidad del padrón.*

### 3.4 `03_build_panel.py` (Unión de pasado, presente y Censo 2020)
**¿Qué hace exactamente?**  
Construye la matriz analítica donde cada fila representa una sección en un año específico. Para que el modelo pueda aprender, este script pone en la misma fila:
1. Lo que pasó en ese año (la variable a predecir, $y$).
2. Lo que pasó hace 6 años en la elección del mismo tipo (`part_lag6`).
3. Lo que pasó hace 3 años en la presidencial anterior (`part_lag3`).
4. La proporción de jóvenes en la sección (`sh_joven_lag3`).
5. Las características del Censo 2020 (escolaridad promedio, etnicidad, migración, salud).
6. Crea las filas vacías del año 2027 (con sus rezagos de 2021 y 2024 ya listos) para que en el siguiente paso el modelo solo tenga que calcular la predicción.

### 3.5 `04_model_validate.py` (El modelo econométrico principal: GLM)
**¿Qué hace exactamente?**  
Contiene la ecuación matemática descrita en la sección 2.2.
1. Ejecuta la validación temporal hacia atrás (2021 y 2024) para medir con honestidad qué tan bien predice en elecciones que ya ocurrieron.
2. Ajusta el modelo final con toda la historia disponible (2015-2024).
3. Calcula el pronóstico puntual para cada una de las 70,751 secciones en la elección federal de 2027.

### 3.6 `04b_modelo_xgboost.py` (Modelo alternativo de contraste: Machine Learning)
**¿Qué hace exactamente?**  
Cumpliendo con la rúbrica del INE de poner a prueba un modelo de árboles tipo Gradient Boosting:
1. Entrena un algoritmo **XGBoost** con las mismas variables explicativas y bajo las mismas pruebas temporales (2021 y 2024).
2. Genera una tabla comparativa directa: **Línea Base vs. GLM vs. XGBoost** (`outputs/tables/comparacion_glm_vs_xgboost.csv`).
3. Mide la **Importancia de Variables (Feature Importance)**: revela qué factores tienen mayor peso predictivo para los árboles de decisión (`outputs/tables/importancia_variables_xgboost.csv`).
4. **Hallazgo clave:** XGBoost le da un **46.7% de peso a la participación previa**, validando matemáticamente por qué el GLM con offset fue una decisión correcta. Ambos modelos convergen en una participación nacional esperada para 2027 muy similar (**51.0%** en XGBoost vs. **51.8%** en GLM).

### 3.7 `05_semaforo_escenarios.py` (Semáforo, incertidumbre y escenarios)
**¿Qué hace exactamente?**  
1. Toma las predicciones de 2027 y les asigna los colores del semáforo (Verde, Amarillo, Rojo).
2. Calcula los intervalos de incertidumbre empíricos ($\pm 9$ puntos porcentuales al 80%).
3. Simula los escenarios hipotéticos de intervención preventiva (Bajo +1 pp, Medio +2.5 pp, Alto +4 pp en secciones rojas).
4. Genera las tablas agregadas por municipio y por distrito electoral para orientar al INE dónde priorizar sus recursos (`prioridad_municipio.csv`).
5. Exporta `base_anonimizada_seccion.csv`.

### 3.7 `06_cartografia.py` (Extracción de mapas del INE)
Descomprime los 32 archivos de la Base Geográfica Digital del INE y extrae únicamente las capas vectoriales necesarias (polígonos de secciones, municipios y distritos federales).

### 3.8 `07_mapas.py` (Análisis espacial y mapas estáticos)
1. Calcula el **Índice de Moran ($I = 0.71$)**, demostrando estadísticamente que la abstención se agrupa en conglomerados territoriales contiguos.
2. Genera los mapas de México en formato PNG con y sin intervención para incluir en el reporte y la presentación.
3. Exporta las capas geográficas entregables (`escenarios_seccion.gpkg`, `municipios.geojson`, `distritos.geojson`).

### 3.9 `08_visor.py` (Visor web interactivo)
Ensambla un archivo HTML (`outputs/maps/visor.html`) con la librería Leaflet que permite al jurado o al personal del INE hacer zoom, explorar cada municipio o distrito del país y alternar entre los escenarios con y sin intervención con solo un clic.

---

---

## 4. Hallazgos Clave para tu Reporte Metodológico

Al redactar tu reporte, estos son los argumentos más sólidos que debes destacar:

1. **Persistencia Territorial y Autocorrelación Espacial (Índice de Moran = 0.71):**  
   El riesgo de abstención no es aleatorio ni está disperso como confeti; forma clusters geográficos contiguos muy claros (franja fronteriza norte de Baja California, Sonora, Chihuahua, Ciudad Juárez, Tijuana y ciertas zonas metropolitanas de Guanajuato y Puebla). Esto fundamenta científicamente la intervención regional del INE.
2. **Los Municipios más Críticos por Volumen de Abstención:**  
   Si el INE quiere maximizar el retorno de sus recursos preventivos, la tabla `prioridad_municipio.csv` muestra dónde está concentrado el padrón en rojo:
   - **Tijuana, BC:** 1.35 millones de electores en secciones rojas (82.6% de su lista nominal).
   - **Juárez, Chih.:** 976 mil electores en secciones rojas (78.2%).
   - **Mexicali, BC:** 663 mil electores en secciones rojas (76.5%).
   - **León, Gto.:** 535 mil electores en secciones rojas (42.1%).
   - **Puebla, Pue.:** 505 mil electores en secciones rojas (36.8%).
3. **El Papel de la Juventud (18 a 34 años):**  
   El coeficiente del modelo confirma que las secciones con mayor proporción de jóvenes presentan una propensión significativamente menor a votar (odds ratio de 0.88), lo que valida la pertinencia del concurso y orienta a enfocar la intervención en campañas para primeros votantes y universitarios.
4. **Incertidumbre Explícita:**  
   Cumpliendo estrictamente con la rúbrica, el reporte no oculta el error: se reporta un intervalo de incertidumbre empírico del 80% ($\pm 9$ puntos porcentuales a nivel de sección individual) y se explica que la mayor fuente de error proviene de los choques macro-nacionales de cada elección. Por ello, se recomienda al INE tomar decisiones estratégicas agregando a nivel municipal y distrital.

---

## 5. Dónde encontrar cada resultado en tu carpeta

- **Para tus gráficos y mapas:** `outputs/figures/` (tienes mapas de distritos con y sin intervención, el mapa nacional municipal y un zoom detallado de Tijuana).
- **Para tus tablas del reporte:** `outputs/tables/` (`validacion_temporal.csv`, `escenarios_resumen.csv`, `prioridad_municipio.csv`, `prioridad_distrito.csv`, `moran.csv`).
- **Para los entregables digitales del concurso:**  
  - Base anonimizada: `data/processed/base_anonimizada_seccion.csv`
  - Capas espaciales: `outputs/maps/escenarios_seccion.gpkg`
  - Visor interactivo: `outputs/maps/visor.html`
