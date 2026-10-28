# Mortalidad en la primera infancia en la Región Pacífica de Colombia (2022-2024)

Análisis descriptivo de las defunciones de menores de 5 años con residencia en Chocó, Valle del Cauca, Cauca y Nariño, a partir de los microdatos de Estadísticas Vitales del DANE, con un sistema de visualización y consulta en Streamlit.

## 1. Objetivos

1. Identificar patrones en las defunciones de la primera infancia mediante técnicas estadísticas y de análisis temporal.
2. Analizar la distribución territorial de las defunciones a nivel departamental y municipal, y sus diferencias en frecuencia, causas y comportamiento.
3. Implementar un sistema de visualización y consulta que permita explorar la evolución, las causas y la distribución territorial de las defunciones.

## 2. Fuentes de datos

| Fuente | Uso | Dónde obtenerla |
|---|---|---|
| Microdatos de Estadísticas Vitales 2022, 2023 y 2024 (defunciones no fetales y nacimientos) | Datos base del análisis | DANE, catálogo de microdatos (operación EEVV) |
| Libros de códigos DDI `COL-DANE-EEVV-2022`, `2023` y `2024` | Significado y códigos de las variables | DANE, catálogo de microdatos |
| Lista de causas 6/67 OMS/OPS | Agrupación de causas de muerte | DANE (2020), *Homologación listas de causas de defunción agrupadas 6/66 vs 6/67 OMS/OPS CIE-10* |
| Proyecciones de población departamental por área, sexo y edad simple, 2018-2050 (actualización de julio de 2025) | Denominadores de las tasas por población | DANE, página de proyecciones de población (`PPED-AreaSexoEdadDep-2018-2050_VP.xlsx`) |
| Marco Geoestadístico Nacional 2018 | Nombres y límites de municipios | DANE, geoportal (versión simplificada en GeoJSON del repositorio público `caticoa3/colombia_mapa`) |

Los microdatos no se incluyen en el repositorio por su tamaño. La carpeta `datos/` está excluida en `.gitignore`.

## 3. Estructura del proyecto

```
Proyecto_EEVV/
├── app/
│   └── app.py                          Sistema de visualización y consulta (Streamlit)
├── datos/                              (no se versiona)
│   ├── extraido/                       CSV originales del DANE
│   ├── crudo/                          Capa cruda: CSV convertidos a Parquet, sin cambios
│   ├── procesado/                      Capa procesada: población de estudio limpia y tipada
│   ├── oro/                            Capa oro: resultados calculados que lee el sistema
│   └── referencia/                     Proyecciones, lista DIVIPOLA y mapa de municipios
├── documentacion/
│   └── diccionario_variables_eevv.xlsx Diccionario de variables y catálogo de causas 6/67
├── notebooks/
│   ├── 01_preparacion_parquet.ipynb
│   ├── 02_exploracion.ipynb
│   ├── 03_analisis_temporal.ipynb
│   ├── 04_analisis_territorial.ipynb
│   └── 05_analisis_causas.ipynb
├── requirements.txt
└── README.md
```

### Archivos de entrada esperados

En `datos/extraido/`:

```
defuncion_no_fetal_2022.csv
defuncion_no_fetal_2023.csv
defunciones_no_fetales_2024.csv
nacimientos_2022.csv
nacimientos_2023.csv
nacimientos_2024.csv
```

En `datos/referencia/`:

```
PPED-AreaSexoEdadDep-2018-2050_VP.xlsx
divipola_municipios.csv
municipios_pacifico.geojson
```

## 4. Instalación

Se usó Python 3.13 en un entorno de Anaconda.

```
conda activate Learning
pip install -r requirements.txt
```

Versiones con las que se probó el proyecto: pandas 3.0.6, pyarrow 25 y 26, openpyxl 3.1, scipy 1.18, matplotlib 3.11, streamlit 1.65 y plotly 7.1.

Los notebooks se ejecutan en VS Code con las extensiones Python y Jupyter, seleccionando el kernel del entorno. En cada notebook, la variable `BASE` de la primera celda debe apuntar a la carpeta del proyecto.

## 5. Cómo reproducir el análisis

Ejecutar los notebooks en orden, cada uno con **Restart** y **Run All**:

| Notebook | Qué hace | Lee | Produce |
|---|---|---|---|
| `01_preparacion_parquet` | **A.** Convierte los CSV a Parquet. **B.** Renombra las variables con el diccionario. **C.** Asigna tipos y trata los códigos de "sin información". **D.** Filtra la población de estudio. **E.** Guarda y verifica la capa procesada. | `datos/extraido/`, diccionario | `datos/crudo/`, `datos/procesado/` |
| `02_exploracion` | Composición, vacíos y coherencia de los datos (paso 3). | `datos/procesado/`, diccionario | Solo resultados en pantalla |
| `03_analisis_temporal` | Tasas anuales, razones frente a 2022, serie mensual, descomposición, prueba de estacionalidad y gráfico de control. Fase 2: tasas con población proyectada. | `datos/procesado/`, proyecciones | Tablas de tasas, razones, serie mensual y tasas por población |
| `04_analisis_territorial` | Departamentos frente a la región y tasas municipales con niveles de confiabilidad. | `datos/procesado/` | Tasas departamentales y municipales |
| `05_analisis_causas` | Rankings, composición por departamento, cambios entre años y conteos por sexo. | `datos/procesado/`, diccionario | Conteos de causas, cambios y defunciones por sexo |

Cada notebook incluye celdas de verificación (`assert` y conteos esperados) que detienen la ejecución si algo no cuadra.

### Cifras de control

| Control | Valor esperado |
|---|---|
| Defunciones no fetales 2022 / 2023 / 2024 | 287.251 / 268.411 / 275.778 |
| Nacimientos 2022 / 2023 / 2024 | 573.625 / 515.549 / 453.901 |
| Defunciones de menores de 5 años en la región | 3.217 |
| Nacimientos de madres residentes en la región | 211.367 |

### Capa oro

| Archivo | Contenido |
|---|---|
| `tasas_anuales_infantil.parquet` | Tasas anuales por territorio e indicador, con intervalos |
| `razones_tasas_vs_2022.parquet` | Razones de tasas frente a 2022 |
| `serie_mensual_infantil.parquet` | Series mensuales por territorio e indicador |
| `tasas_departamentales_acumuladas.parquet` | Tasas 2022-2024 por departamento frente a la región |
| `tasas_municipales_acumuladas.parquet` | Tasas municipales con nivel de confiabilidad |
| `causas_conteos.parquet` | Defunciones por año, departamento, grupo de edad y causa |
| `causas_cambios_2022_2024.parquet` | Cambio en el peso de cada causa entre 2022 y 2024 |
| `defunciones_por_sexo.parquet` | Defunciones por año, departamento, grupo de edad y sexo |
| `poblacion_proyectada.parquet` | Población de 0 a 4 y de 1 a 4 años por territorio y año |
| `tasas_poblacion_acumuladas.parquet` | Tasas por 100.000 niños: 1 a 4 años, desnutrición, EDA e IRA |

## 6. Sistema de visualización y consulta

Desde Anaconda Prompt:

```
conda activate Learning
cd C:\ruta\a\Proyecto_EEVV
streamlit run app/app.py
```

Se abre en el navegador en `http://localhost:8501`. Para detenerlo, `Ctrl+C` en la terminal.

El sistema solo lee la capa oro y los archivos de referencia: no recalcula nada, de modo que muestra exactamente las cifras validadas en los notebooks. Tiene cuatro vistas:

- **Evolución:** tasas anuales con intervalos, serie trimestral o mensual y cambios frente a 2022.
- **Causas:** ranking, composición por departamento, defunciones por sexo, tabla descargable y causas que cambiaron de peso.
- **Territorio:** departamentos frente a la región, tasas por 100.000 niños, mapa municipal con niveles de confiabilidad y tabla descargable.
- **Metodología:** definiciones, decisiones y limitaciones.

## 7. Decisiones metodológicas principales

El detalle completo está en la pestaña **Metodología** del sistema y en el diccionario de variables.

- **Población de estudio:** menores de 5 años (`GRU_ED1` de 00 a 08), verificado fila por fila con `GRU_ED2` (01 y 02) y confirmado en los libros de códigos del DANE.
- **Grupos de edad:** neonatal (00 a 03, menos de 28 días), posneonatal (04 a 06) y 1 a 4 años (07 y 08).
- **Criterio territorial:** residencia. Para los menores de 1 año, el DANE registra la residencia de la madre, el mismo criterio de los nacimientos.
- **Indicadores por 1.000 nacidos vivos:** infantil, neonatal, posneonatal y menores de 5 años, con series anuales.
- **Indicadores por 100.000 niños**, con proyecciones de población y solo para el período acumulado: mortalidad de 1 a 4 años y por desnutrición (E40-E46), enfermedad diarreica aguda (A00-A09) e infección respiratoria aguda (J00-J22).
- **Intervalos de confianza del 95%** exactos de Poisson. Comparaciones entre años con razones de tasas.
- **Municipios:** tasas acumuladas 2022-2024 con tres niveles: confiable (20 o más defunciones), usar con precaución (10 a 19) y datos insuficientes (menos de 10, sin tasa).
- **Causas:** lista 6/67 de la OPS, con las 10 causas principales y "otras causas" en las comparaciones.
- **Duplicados exactos:** se conservan, marcados. La mayoría de los nacimientos duplicados corresponden a partos múltiples.
- **Códigos de "sin información":** se convierten en vacíos en las variables numéricas y se conservan como categoría en las demás.

## 8. Principales hallazgos

- La mortalidad en menores de 5 años del Chocó (39,9 por 1.000 nacidos vivos en 2022-2024) casi triplica la del resto de la región (entre 12,0 y 13,7).
- El exceso del Chocó se concentra después del primer mes de vida: su tasa posneonatal es 3,4 veces la regional, y su mortalidad de 1 a 4 años, 5 veces la del Valle del Cauca.
- Las causas evitables explican buena parte de la diferencia: la mortalidad por desnutrición en el Chocó es casi 20 veces la del resto de la región, y la diarreica, más de 10 veces.
- Entre 2022 y 2024, la mortalidad posneonatal del Chocó aumentó de forma concluyente, al mismo tiempo que sus muertes por enfermedad diarreica se triplicaron.
- Dentro de cada departamento, los municipios del litoral pacífico tienen tasas más altas que los de la zona andina.
- No se encontró estacionalidad mensual estadísticamente significativa.

## 9. Limitaciones

- El análisis es descriptivo y no establece causas socioeconómicas.
- Tres años de información limitan el análisis de tendencias.
- Las proyecciones de población suponen más niños de los que nacieron en 2022-2024, por lo que las tasas por población probablemente están subestimadas y solo se presentan acumuladas.
- El registro perinatal del Chocó es más incompleto, y en algunos de sus municipios pequeños podría haber subregistro de nacimientos.
- Muchos municipios tienen muy pocos casos, en especial en Nariño.

## 10. Pendientes

- Nombres de la Lista Colombia 105 (`causa_homologada`). No se usan en el análisis ni en el sistema.
- Confirmar el significado de `C_MUERTEE` (`causa_det_e`), cuya etiqueta cambia en 2023.
