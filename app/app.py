"""
Sistema de visualización y consulta
Mortalidad en la primera infancia - Región Pacífica (DANE EEVV 2022-2024)

Ejecutar desde la carpeta del proyecto:
    streamlit run app/app.py
"""
import json
import textwrap
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from scipy.stats import chi2
import streamlit as st

# ---------------------------------------------------------------------------
# 1. Rutas: se calculan a partir de la ubicación de este archivo
# ---------------------------------------------------------------------------
RAIZ = Path(__file__).resolve().parent.parent
ORO = RAIZ / "datos" / "oro"
REFERENCIA = RAIZ / "datos" / "referencia"

INDICADORES = ["Infantil (menores de 1 año)", "Menores de 5 años", "Neonatal", "Posneonatal"]
TERRITORIOS = ["Región Pacífica", "Cauca", "Chocó", "Nariño", "Valle del Cauca"]
DEPARTAMENTOS = ["Cauca", "Chocó", "Nariño", "Valle del Cauca"]
GRUPOS_EDAD = ["Neonatal", "Posneonatal", "1 a 4 años"]
ANIOS = [2022, 2023, 2024]


def nombre_propio(texto):
    """'SAN ANDRÉS DE TUMACO' -> 'San Andrés de Tumaco'."""
    menores = {"De", "Del", "La", "Las", "Los", "El", "Y"}
    palabras = str(texto).title().split()
    return " ".join(p.lower() if i > 0 and p in menores else p for i, p in enumerate(palabras))


def num(valor, decimales=1, signo=False):
    """Formatea un número con coma decimal: 12.1 -> '12,1'; con signo: '+2,1'."""
    texto = f"{valor:+.{decimales}f}" if signo else f"{valor:.{decimales}f}"
    return texto.replace(".", ",")


def graficar(fig):
    """Muestra un gráfico de Plotly con coma decimal y punto de miles."""
    fig.update_layout(separators=",.")
    st.plotly_chart(fig)


def csv_excel(tabla):
    """CSV para Excel en español: punto y coma entre columnas, coma decimal y un decimal."""
    return tabla.to_csv(index=False, sep=";", decimal=",", float_format="%.1f").encode("utf-8-sig")


def partir(texto, ancho=40):
    """Parte un texto largo en varias líneas para las etiquetas de los gráficos."""
    return "<br>".join(textwrap.wrap(str(texto), ancho))

st.set_page_config(page_title="Mortalidad primera infancia - Pacífico",
                   page_icon="📊", layout="wide")


# ---------------------------------------------------------------------------
# 2. Carga de datos (se lee una sola vez y queda en caché)
# ---------------------------------------------------------------------------
@st.cache_data
def cargar_datos():
    datos = {
        "tasas_anuales": pd.read_parquet(ORO / "tasas_anuales_infantil.parquet"),
        "razones": pd.read_parquet(ORO / "razones_tasas_vs_2022.parquet"),
        "serie_mensual": pd.read_parquet(ORO / "serie_mensual_infantil.parquet"),
        "causas": pd.read_parquet(ORO / "causas_conteos.parquet"),
        "causas_cambios": pd.read_parquet(ORO / "causas_cambios_2022_2024.parquet"),
        "sexo": pd.read_parquet(ORO / "defunciones_por_sexo.parquet"),
        "tasas_dpto": pd.read_parquet(ORO / "tasas_departamentales_acumuladas.parquet"),
        "tasas_mun": pd.read_parquet(ORO / "tasas_municipales_acumuladas.parquet"),
        "tasas_poblacion": pd.read_parquet(ORO / "tasas_poblacion_acumuladas.parquet"),
    }
    # Nombres de municipios (DIVIPOLA) unidos a las tasas municipales
    divipola = pd.read_csv(REFERENCIA / "divipola_municipios.csv", dtype=str, encoding="utf-8-sig")
    divipola["municipio"] = divipola["municipio"].map(nombre_propio)
    mun = datos["tasas_mun"].merge(divipola[["municipio_cod", "municipio"]], how="left", on="municipio_cod")
    mun["municipio"] = mun["municipio"].fillna(mun["municipio_cod"])
    mun["departamento"] = mun["departamento"].astype(str)
    # Tasa e intervalo exacto de Poisson para todos los municipios (acumulado 2022-2024)
    d = mun["defunciones"].astype(float)
    mun["tasa"] = d / mun["nacimientos"] * 1000
    mun["ic_inf"] = chi2.ppf(0.025, 2 * d).clip(min=0) / 2 / mun["nacimientos"] * 1000
    mun.loc[d == 0, "ic_inf"] = 0.0
    mun["ic_sup"] = chi2.ppf(0.975, 2 * (d + 1)) / 2 / mun["nacimientos"] * 1000
    datos["tasas_mun"] = mun
    datos["tasas_dpto"]["departamento"] = datos["tasas_dpto"]["departamento"].astype(str)
    return datos


@st.cache_data
def cargar_mapa():
    with open(REFERENCIA / "municipios_pacifico.geojson", encoding="utf-8") as f:
        return json.load(f)
    for tabla in datos.values():
        if "anio" in tabla.columns:
            tabla["anio"] = tabla["anio"].astype(int)


datos = cargar_datos()
mapa = cargar_mapa()

# ---------------------------------------------------------------------------
# 3. Encabezado y filtros comunes (barra lateral)
# ---------------------------------------------------------------------------
st.title("Mortalidad en la primera infancia en la Región Pacífica")
st.caption("Defunciones de menores de 5 años con residencia en Chocó, Valle del Cauca, "
           "Cauca y Nariño. Fuente: DANE, Estadísticas Vitales 2022-2024.")

with st.sidebar:
    st.header("Filtros")
    indicador = st.selectbox("Indicador", INDICADORES)
    territorios = st.multiselect("Territorios", TERRITORIOS, default=TERRITORIOS)
    st.caption("Tasas por 1.000 nacidos vivos. Las barras y bandas muestran el "
               "intervalo de confianza del 95%.")

if not territorios:
    st.warning("Selecciona al menos un territorio en la barra lateral.")
    st.stop()

tab_evolucion, tab_causas, tab_territorio, tab_metodologia = st.tabs(
    ["Evolución", "Causas", "Territorio", "Metodología"])

# ---------------------------------------------------------------------------
# 4. Vista: Evolución
# ---------------------------------------------------------------------------
with tab_evolucion:
    anual = datos["tasas_anuales"]
    anual = anual[(anual["indicador"] == indicador) & (anual["territorio"].isin(territorios))]

    # 4.1 Indicadores clave: tasa 2024 y cambio frente a 2022
    st.subheader(f"Tasa {indicador.lower()} en 2024, por 1.000 nacidos vivos")
    razones_24 = datos["razones"]
    razones_24 = razones_24[(razones_24["indicador"] == indicador) & (razones_24["anio"] == 2024)]
    razones_24 = razones_24.set_index("territorio")
    columnas = st.columns(len(territorios))
    for col, terr in zip(columnas, territorios):
        fila = anual[anual["territorio"] == terr].set_index("anio")
        t22, t24 = fila.loc[2022, "tasa"], fila.loc[2024, "tasa"]
        rz = razones_24.loc[terr]
        col.metric(terr, num(t24),
                   delta=f"{num(t24 - t22, signo=True)} frente a 2022",
                   delta_color="inverse",
                   help=(f"2022: {num(t22)} · 2024: {num(t24)} por 1.000 nacidos vivos.  \n"
                         f"Razón de tasas 2024/2022: {num(rz['razon'], 2)} "
                         f"(IC 95%: {num(rz['ic_inf'], 2)} a {num(rz['ic_sup'], 2)})."))
    st.caption("Flecha roja: la tasa subió frente a 2022; flecha verde: bajó. Pasa el mouse sobre "
               "el ícono (?) de cada tarjeta para ver el detalle.")

    # 4.2 Tasas anuales con intervalos de confianza
    graf = anual.assign(error_sup=anual["ic_sup"] - anual["tasa"],
                        error_inf=anual["tasa"] - anual["ic_inf"])
    fig = px.line(graf, x="anio", y="tasa", color="territorio", markers=True,
                  error_y="error_sup", error_y_minus="error_inf",
                  category_orders={"territorio": TERRITORIOS},
                  hover_data={"defunciones": True, "nacimientos": ":,", "error_sup": False,
                              "error_inf": False},
                  labels={"anio": "Año", "tasa": "Por 1.000 nacidos vivos",
                          "territorio": "Territorio"},
                  title="Tasa anual por territorio")
    fig.update_xaxes(tickvals=[2022, 2023, 2024])
    graficar(fig)

    # 4.3 Serie mensual o trimestral de un territorio
    st.subheader("Serie en el tiempo")
    c1, c2 = st.columns(2)
    terr_serie = c1.selectbox("Territorio", territorios, key="terr_serie")
    periodo = c2.radio("Agrupar por", ["Trimestre", "Mes"], horizontal=True)

    serie = datos["serie_mensual"]
    serie = serie[(serie["indicador"] == indicador) & (serie["territorio"] == terr_serie)].copy()
    if periodo == "Trimestre":
        serie["periodo"] = serie["fecha"].dt.to_period("Q").dt.to_timestamp()
        serie = (serie.groupby("periodo", as_index=False)[["defunciones", "nacimientos"]].sum())
        serie["tasa"] = serie["defunciones"] / serie["nacimientos"] * 1000
    else:
        serie = serie.rename(columns={"fecha": "periodo"})

    promedio = serie["defunciones"].sum() / serie["nacimientos"].sum() * 1000
    fig = px.line(serie, x="periodo", y="tasa", markers=True,
                  hover_data={"defunciones": True, "nacimientos": ":,"},
                  labels={"periodo": "", "tasa": "Por 1.000 nacidos vivos"},
                  title=f"{indicador} - {terr_serie} ({periodo.lower()})")
    fig.add_hline(y=promedio, line_dash="dash", line_color="gray",
                  annotation_text=f"Promedio 2022-2024: {num(promedio)}")
    MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    if periodo == "Trimestre":
        marcas = serie["periodo"]
        textos = [f"T{(f.month - 1) // 3 + 1} {f.year}" for f in marcas]
    else:
        marcas = serie["periodo"].iloc[::3]
        textos = [f"{MESES[f.month - 1]} {f.year}" for f in marcas]
    fig.update_xaxes(tickvals=marcas, ticktext=textos)
    graficar(fig)
    if terr_serie != "Región Pacífica" and periodo == "Mes":
        st.info("Por departamento, la serie mensual tiene pocos casos por mes y varía mucho "
                "por azar. La vista trimestral es más estable.")

    # 4.4 Cambios frente a 2022
    st.subheader("Cambios frente a 2022")
    razones = datos["razones"]
    razones = razones[(razones["indicador"] == indicador) & (razones["territorio"].isin(territorios))]
    tabla = (razones[["territorio", "anio", "razon", "ic_inf", "ic_sup"]]
             .sort_values(["territorio", "anio"])
             .rename(columns={"territorio": "Territorio", "anio": "Año",
                              "razon": "Razón de tasas", "ic_inf": "IC inferior",
                              "ic_sup": "IC superior"}))
    st.dataframe(tabla, hide_index=True,
                 column_config={c: st.column_config.NumberColumn(format="%.2f")
                                for c in ["Razón de tasas", "IC inferior", "IC superior"]})
    st.caption("Razón de tasas = tasa del año / tasa de 2022. IC: intervalo de confianza del 95%.")

# ---------------------------------------------------------------------------
# 5. Vista: Causas
# ---------------------------------------------------------------------------
with tab_causas:
    st.markdown("Esta vista incluye a todos los menores de 5 años (también el grupo de 1 a 4 "
                "años), por eso tiene sus propios filtros en lugar del indicador de la barra lateral.")
    f1, f2, f3 = st.columns(3)
    anios_c = f1.multiselect("Años", ANIOS, default=ANIOS, key="anios_causas")
    edades_c = f2.multiselect("Grupos de edad", GRUPOS_EDAD, default=GRUPOS_EDAD, key="edades_causas")
    dptos_c = f3.multiselect("Departamentos", DEPARTAMENTOS, default=DEPARTAMENTOS, key="dptos_causas")

    if not (anios_c and edades_c and dptos_c):
        st.warning("Selecciona al menos un año, un grupo de edad y un departamento.")
    else:
        causas = datos["causas"]
        sel = causas[causas["anio"].isin(anios_c)
                     & causas["grupo_edad_analisis"].isin(edades_c)
                     & causas["dpto_residencia_nombre"].isin(dptos_c)]
        total = int(sel["defunciones"].sum())
        st.metric("Defunciones en la selección", f"{total:,}".replace(",", "."))

        # 5.1 Ranking de causas
        st.subheader("Principales causas")
        r1, r2 = st.columns([2, 1])
        nivel = r1.radio("Nivel", ["Causa (lista 6/67)", "Gran grupo"], horizontal=True)
        n_top = r2.slider("Cuántas mostrar", 5, 20, 10)
        col_nivel = "causa" if nivel.startswith("Causa") else "gran_grupo"
        ranking = (sel.groupby(col_nivel, as_index=False)["defunciones"].sum()
                   .sort_values("defunciones", ascending=False).head(n_top))
        ranking["%"] = ranking["defunciones"] / total * 100
        ranking["etiqueta"] = ranking[col_nivel].map(partir)
        fig = px.bar(ranking.sort_values("defunciones"), x="defunciones", y="etiqueta",
                     orientation="h", text=ranking.sort_values("defunciones")["%"].map(lambda v: f"{num(v)}%"),
                     labels={"defunciones": "Defunciones", "etiqueta": ""},
                     height=120 + 38 * len(ranking))
        fig.update_traces(textposition="outside", cliponaxis=False)
        graficar(fig)

        # 5.2 Composición por departamento (10 causas principales del total + otras)
        st.subheader("Composición de causas por departamento")
        top10 = (causas.groupby("causa")["defunciones"].sum()
                 .sort_values(ascending=False).head(10).index.tolist())
        comp = sel.assign(causa_grupo=sel["causa"].where(sel["causa"].isin(top10), "Otras causas"))
        comp = comp.groupby(["dpto_residencia_nombre", "causa_grupo"], observed=True,
                            as_index=False)["defunciones"].sum()
        comp["%"] = comp["defunciones"] / comp.groupby("dpto_residencia_nombre", observed=True)[
            "defunciones"].transform("sum") * 100
        fig = px.bar(comp, x="%", y="dpto_residencia_nombre", color="causa_grupo",
                     orientation="h", category_orders={"causa_grupo": top10 + ["Otras causas"]},
                     hover_data={"defunciones": True, "%": ":.1f"},
                     labels={"dpto_residencia_nombre": "", "causa_grupo": "Causa",
                             "%": "% de las defunciones del departamento"},
                     color_discrete_sequence=px.colors.qualitative.Dark24, height=640)
        fig.update_layout(legend=dict(font=dict(size=11), tracegroupgap=2))
        fig.for_each_trace(lambda t: t.update(name=partir(t.name, 45)))
        graficar(fig)
        st.caption("Se comparan porcentajes, no riesgos: si un departamento tiene muchas muertes "
                   "por causas evitables, el porcentaje de las demás causas baja.")

        # 5.3 Defunciones por sexo
        st.subheader("Defunciones por sexo y grupo de edad")
        sx = datos["sexo"]
        sx = sx[sx["anio"].isin(anios_c) & sx["grupo_edad_analisis"].isin(edades_c)
                & sx["dpto_residencia_nombre"].isin(dptos_c) & (sx["sexo"] != "Indeterminado")]
        sx = sx.groupby(["grupo_edad_analisis", "sexo"], observed=True, as_index=False)["defunciones"].sum()
        fig = px.bar(sx, x="grupo_edad_analisis", y="defunciones", color="sexo", barmode="group",
                     category_orders={"grupo_edad_analisis": GRUPOS_EDAD},
                     labels={"grupo_edad_analisis": "", "defunciones": "Defunciones", "sexo": "Sexo"})
        graficar(fig)
        masc = sx.loc[sx["sexo"] == "Masculino", "defunciones"].sum()
        if sx["defunciones"].sum() > 0:
            st.caption(f"Hombres: {num(masc / sx['defunciones'].sum() * 100)}% de las defunciones "
                       "con sexo definido. Se excluyen los casos de sexo indeterminado.")

        # 5.4 Tabla consultable y descarga
        st.subheader("Consulta detallada")
        detalle = (sel.groupby(["causa_lista_667", "causa", "gran_grupo"], as_index=False)["defunciones"]
                   .sum().sort_values("defunciones", ascending=False))
        detalle["%"] = (detalle["defunciones"] / total * 100).round(1)
        detalle = detalle.rename(columns={"causa_lista_667": "Código 6/67", "causa": "Causa",
                                          "gran_grupo": "Gran grupo", "defunciones": "Defunciones"})
        st.dataframe(detalle, hide_index=True)
        st.download_button("Descargar tabla (CSV)",
                           csv_excel(detalle),
                           file_name="causas_seleccion.csv", mime="text/csv")

    # 5.5 Cambios entre 2022 y 2024 (toda la región y todas las edades)
    st.subheader("Causas que cambiaron de peso entre 2022 y 2024")
    cambios = datos["causas_cambios"].drop(columns="concluyente").rename(columns={
        "causa_grupo": "Causa", "diferencia_pp": "Diferencia (puntos)",
        "ic_inf": "IC inferior", "ic_sup": "IC superior"})
    st.dataframe(cambios.sort_values("Diferencia (puntos)"), hide_index=True,
                 column_config={c: st.column_config.NumberColumn(format="%.1f")
                                for c in ["% 2022", "% 2024", "Diferencia (puntos)",
                                          "IC inferior", "IC superior"]})
    st.caption("Calculado para toda la región y todos los menores de 5 años; no depende de los "
               "filtros. IC: intervalo de confianza del 95% de la diferencia.")

# ---------------------------------------------------------------------------
# 6. Vista: Territorio
# ---------------------------------------------------------------------------
with tab_territorio:
    # 6.1 Departamentos frente a la región (usa el indicador de la barra lateral)
    st.subheader(f"Departamentos frente a la región - {indicador.lower()}, 2022-2024")
    dpto = datos["tasas_dpto"]
    dpto = dpto[dpto["indicador"] == indicador].sort_values("tasa")
    fig = px.scatter(dpto, x="tasa", y="departamento", color="frente_a_region",
                     error_x=dpto["ic_sup"] - dpto["tasa"], error_x_minus=dpto["tasa"] - dpto["ic_inf"],
                     color_discrete_map={"Por encima": "#d62728", "Similar": "#7f7f7f",
                                         "Por debajo": "#2ca02c"},
                     hover_data={"defunciones": True, "nacimientos": ":,", "tasa": ":.1f"},
                     labels={"tasa": "Por 1.000 nacidos vivos (acumulado 2022-2024)",
                             "departamento": "", "frente_a_region": "Frente a la región"},
                     height=320)
    fig.update_traces(marker_size=12)
    fig.add_vline(x=dpto["tasa_region"].iloc[0], line_dash="dash", line_color="black",
                  annotation_text=f"Región: {num(dpto['tasa_region'].iloc[0])}")
    graficar(fig)

    # 6.2 Tasas con población proyectada (1 a 4 años y causas seleccionadas)
    st.subheader("Tasas por 100.000 niños, 2022-2024")
    tp = datos["tasas_poblacion"]
    ind_pob = st.selectbox("Indicador", tp["indicador"].unique().tolist(), key="ind_poblacion")
    tp = tp[tp["indicador"] == ind_pob].sort_values("tasa")
    fig = px.scatter(tp, x="tasa", y="territorio", color="frente_a_region",
                     error_x=tp["ic_sup"] - tp["tasa"], error_x_minus=tp["tasa"] - tp["ic_inf"],
                     color_discrete_map={"Por encima": "#d62728", "Similar": "#7f7f7f",
                                         "Por debajo": "#2ca02c", "Referencia": "#1f77b4"},
                     hover_data={"defunciones": True, "poblacion": ":,.0f", "tasa": ":.1f"},
                     labels={"tasa": "Por 100.000 niños (acumulado 2022-2024)", "territorio": "",
                             "frente_a_region": "Frente a la región", "poblacion": "Población"},
                     height=340)
    fig.update_traces(marker_size=12)
    graficar(fig)
    st.warning("Estas tasas usan como denominador las proyecciones de población del DANE, que "
               "suponen más niños de los que nacieron en 2022-2024 (los nacimientos cayeron con "
               "fuerza). Por eso sus valores absolutos probablemente están subestimados y solo se "
               "presentan para el período acumulado, para comparar territorios. La distorsión parece "
               "mayor en el Chocó, así que su diferencia con los demás es, si acaso, conservadora.")

    # 6.3 Mapa municipal (siempre mortalidad infantil acumulada)
    st.subheader("Mortalidad infantil por municipio, 2022-2024")
    st.caption("A nivel municipal solo se calcula la tasa infantil (menores de 1 año), "
               "acumulando los tres años para tener más casos.")
    mun = datos["tasas_mun"]
    dptos_t = st.multiselect("Departamentos", DEPARTAMENTOS, default=DEPARTAMENTOS, key="dptos_territorio")

    if not dptos_t:
        st.warning("Selecciona al menos un departamento.")
    else:
        mun_sel = mun[mun["departamento"].isin(dptos_t)]
        TOPE = 40

        fig = go.Figure(go.Choropleth(
            geojson=mapa, featureidkey="properties.municipio_cod",
            locations=mun_sel["municipio_cod"], z=mun_sel["tasa"].clip(upper=TOPE),
            zmin=0, zmax=TOPE, colorscale="YlOrRd",
            colorbar=dict(title="Por 1.000<br>n.v.", tickvals=[0, 10, 20, 30, 40],
                          ticktext=["0", "10", "20", "30", f"{TOPE}+"]),
            marker_line_color="white", marker_line_width=0.5,
            customdata=mun_sel[["municipio", "departamento", "defunciones", "nacimientos",
                                "tasa", "ic_inf", "ic_sup"]],
            hovertemplate=("<b>%{customdata[0]}</b> (%{customdata[1]})<br>"
                           "Tasa: %{customdata[4]:.1f} (IC 95%: %{customdata[5]:.1f}-%{customdata[6]:.1f})<br>"
                           "Defunciones: %{customdata[2]}<br>Nacimientos: %{customdata[3]:,}"
                           "<extra></extra>")))
        fig.update_geos(fitbounds="locations", visible=False)
        fig.update_layout(height=650, margin=dict(l=0, r=0, t=10, b=0))
        graficar(fig)
        st.caption(f"Las tasas mayores a {TOPE} se muestran con el color máximo; su valor exacto "
                   "aparece al pasar el mouse. Nuevo Belén de Bajirá (Chocó) no aparece en el mapa "
                   "porque fue creado después de 2018, pero sí en la tabla.")

        # 6.4 Municipios con 20 o más defunciones, con su intervalo
        st.subheader("Municipios con 20 o más defunciones infantiles")
        conf = (mun_sel[mun_sel["defunciones"] >= 20].sort_values("tasa")
                .assign(etiqueta=lambda d: d["municipio"] + " (" + d["departamento"] + ")"))
        if conf.empty:
            st.info("Ningún municipio de la selección tiene 20 o más defunciones.")
        else:
            fig = px.scatter(conf, x="tasa", y="etiqueta",
                             error_x=conf["ic_sup"] - conf["tasa"],
                             error_x_minus=conf["tasa"] - conf["ic_inf"],
                             hover_data={"defunciones": True, "nacimientos": ":,", "tasa": ":.1f",
                                         "etiqueta": False},
                             labels={"tasa": "Por 1.000 nacidos vivos", "etiqueta": ""},
                             height=160 + 26 * len(conf))
            tasas_d = datos["tasas_dpto"]
            region_infantil = tasas_d.loc[tasas_d["indicador"] == INDICADORES[0], "tasa_region"].iloc[0]
            fig.add_vline(x=region_infantil, line_dash="dash", line_color="black",
                          annotation_text=f"Región: {num(region_infantil)}")
            graficar(fig)
        st.warning("Las tasas muy altas de algunos municipios pequeños del Chocó pueden estar "
                   "infladas por nacimientos no registrados (denominador incompleto). Deben "
                   "leerse junto con su número de nacimientos.")

        # 6.5 Tabla consultable
        st.subheader("Consulta por municipio")
        tabla = (mun_sel[["departamento", "municipio_cod", "municipio", "defunciones",
                          "nacimientos", "tasa", "ic_inf", "ic_sup"]]
                 .sort_values(["departamento", "municipio"])
                 .rename(columns={"departamento": "Departamento", "municipio_cod": "Código",
                                  "municipio": "Municipio", "defunciones": "Defunciones",
                                  "nacimientos": "Nacimientos", "tasa": "Tasa",
                                  "ic_inf": "IC inferior", "ic_sup": "IC superior"}))
        st.dataframe(tabla, hide_index=True,
                     column_config={c: st.column_config.NumberColumn(format="%.1f")
                                    for c in ["Tasa", "IC inferior", "IC superior"]})
        st.download_button("Descargar tabla (CSV)", csv_excel(tabla),
                           file_name="municipios_seleccion.csv", mime="text/csv")
        st.caption("Tasa infantil por 1.000 nacidos vivos, acumulada 2022-2024. IC: intervalo de "
                   "confianza del 95%.")

# ---------------------------------------------------------------------------
# 7. Vista: Metodología
# ---------------------------------------------------------------------------
with tab_metodologia:
    total_def = int(datos["causas"]["defunciones"].sum())
    ta = datos["tasas_anuales"]
    total_nac = int(ta.loc[(ta["territorio"] == "Región Pacífica")
                           & (ta["indicador"] == INDICADORES[0]), "nacimientos"].sum())

    st.subheader("Metodología")
    miles = lambda n: f"{n:,}".replace(",", ".")   # 3217 -> "3.217"
    st.markdown(
        f"Este sistema presenta el análisis descriptivo de **{miles(total_def)} defunciones** de menores "
        f"de 5 años y **{miles(total_nac)} nacimientos** de madres residentes en la Región Pacífica, "
        "entre 2022 y 2024. Todas las cifras se calcularon previamente en los notebooks del "
        "proyecto; el sistema solo las presenta.")

    with st.expander("1\\. Fuentes de información", expanded=True):
        st.markdown("""
- **Microdatos de Estadísticas Vitales del DANE (2022, 2023 y 2024):** defunciones no fetales y
  nacimientos. Las defunciones fetales no hacen parte del alcance.
- **Proyecciones de población departamental del DANE** por área, sexo y edad simple, 2018-2050
  (actualización de julio de 2025).
- **Libros de códigos del DANE** (COL-DANE-EEVV-2022, 2023 y 2024), usados para confirmar el
  significado de cada variable y sus códigos.
- **Lista 6/67 de la OPS** para agrupar las causas de muerte, según el documento del DANE
  *Homologación listas de causas de defunción agrupadas 6/66 vs 6/67 OMS/OPS CIE-10* (2020).
- **Marco Geoestadístico Nacional 2018 del DANE** para los nombres y los límites de los municipios
  (versión simplificada para el mapa).
""")

    with st.expander("2\\. Población de estudio"):
        st.markdown("""
- **Primera infancia:** menores de 5 años, definidos con la variable de grupo de edad detallado
  del DANE (códigos 00 a 08). El filtro se verificó fila por fila con la variable de grupo de
  edad agrupado (códigos 01 y 02).
- **Región Pacífica:** Chocó, Valle del Cauca, Cauca y Nariño.
- **Criterio territorial: residencia, no lugar de la defunción.** Para los menores de 1 año, el
  DANE registra la residencia de la madre, el mismo criterio de los nacimientos, de modo que
  numerador y denominador describen la misma población. Este criterio importa: cerca de un tercio
  de los niños del Cauca y del Chocó murió fuera de su departamento.
- Se excluyeron las defunciones de menores de 5 años sin departamento de residencia (650 en todo
  el país), porque no pueden asignarse a ningún territorio.
""")

    with st.expander("3\\. Grupos de edad e indicadores"):
        st.markdown("""
| Grupo | Edad | Códigos DANE |
|---|---|---|
| Neonatal | Menos de 28 días | 00 a 03 |
| Posneonatal | 28 días a 11 meses | 04 a 06 |
| 1 a 4 años | 1 a 4 años cumplidos | 07 y 08 |

**Indicadores por 1.000 nacidos vivos** (defunciones del grupo / nacidos vivos del mismo período):
infantil (neonatal + posneonatal), neonatal, posneonatal y **menores de 5 años**, el indicador
resumen oficial. Se presentan por año, con comparación entre años.

**Indicadores por 100.000 niños** (con la población proyectada por el DANE como denominador),
solo para el período acumulado 2022-2024:
- Mortalidad de 1 a 4 años (población de 1 a 4 años).
- Mortalidad por desnutrición (CIE-10 E40-E46), enfermedad diarreica aguda (A00-A09) e
  infección respiratoria aguda (J00-J22) en menores de 5 años (población de 0 a 4 años). Se usan
  las definiciones CIE-10 de los indicadores oficiales del sector salud.

Todos los indicadores llevan **intervalos de confianza del 95%** exactos de Poisson, adecuados
para conteos pequeños.
""")

    with st.expander("4\\. Denominadores: nacimientos y proyecciones"):
        st.markdown("""
- **Nacimientos:** son los nacidos vivos registrados por el DANE, por residencia de la madre.
- **Proyecciones de población:** serie departamental por sexo y edad simple del DANE, basada
  en el censo de 2018 y actualizada en julio de 2025. Se usa la población a mitad de año y se
  suman los tres años (persona-años).
- **Las dos fuentes no cuadran:** en el país, los nacimientos registrados equivalen al 77% de la
  población de 0 años proyectada en 2022 y al 62% en 2024, porque los nacimientos cayeron más de
  lo que suponen las proyecciones. En el Chocó y Nariño la razón baja a 0,45 en 2024.
- **Consecuencias:** los indicadores por nacidos vivos no se ven afectados. Los que usan
  proyecciones probablemente están subestimados y no permiten seguir tendencias anuales; por eso
  solo se presentan acumulados. Como la distorsión parece mayor en el Chocó, sus diferencias con
  los demás departamentos son, si acaso, conservadoras.
""")

    with st.expander("5\\. Comparaciones y su interpretación"):
        st.markdown("""
- **Entre años:** razón de tasas frente a 2022, con intervalo de confianza. Si el intervalo
  incluye el 1, el cambio puede deberse al azar.
- **Entre territorios:** cada departamento se compara con la tasa regional ("por encima",
  "similar" o "por debajo") según si su intervalo la incluye.
- **Causas:** se comparan porcentajes (composición), no riesgos. Los cambios entre 2022 y 2024 se
  evalúan con la diferencia de porcentajes y su intervalo.
- **Comparaciones múltiples:** al hacer muchas comparaciones, alguna puede mostrar un cambio
  aparente solo por azar. Los resultados más sólidos son los que se repiten en varios años o se
  confirman desde varios análisis.
- **Con tres años de datos** se describen variaciones y comportamientos observados, no tendencias
  consolidadas. No se encontró estacionalidad mensual estadísticamente significativa.
""")

    with st.expander("6\\. Análisis municipal"):
        st.markdown("""
Las tasas municipales acumulan los tres años para tener más casos. La precisión de una tasa
depende del número de defunciones: en los municipios con pocos casos, la tasa cambia mucho con una
sola defunción y su intervalo de confianza es amplio. Por eso conviene leer cada tasa junto con su
intervalo y su número de defunciones, y el gráfico de municipios incluye solo los que tienen 20 o
más defunciones infantiles.
""")

    with st.expander("7\\. Calidad de los datos y decisiones"):
        st.markdown("""
- **Duplicados exactos:** se conservaron y quedaron marcados. La mayoría de los nacimientos
  duplicados corresponden a partos múltiples (gemelos con registros idénticos).
- **Códigos de "sin información":** se convirtieron en vacíos en las variables numéricas y se
  conservaron como categoría en las demás, para poder medir la calidad del registro.
- **Las variables principales están completas:** edad, sexo, territorio, año, mes y causa no
  tienen faltantes.
- **El contexto materno es incompleto:** al nivel educativo y al estado civil de la madre les
  falta información en el 20% a 27% de los casos.
- **El Chocó tiene un registro perinatal más débil:** le falta el tiempo de gestación en cerca
  del 30% de los menores de 1 año, frente al 6% a 8% de los demás departamentos.
- **Posible subregistro de nacimientos** en municipios pequeños del Chocó, que podría inflar sus
  tasas. Deben leerse junto con su número de nacimientos.
- **Los meses más recientes** pueden estar subregistrados si algunas defunciones se registran
  tarde.
- **Las causas mal definidas** son menos del 5% en todos los departamentos y años.
""")

    with st.expander("8\\. Limitaciones"):
        st.markdown("""
- El análisis es descriptivo: no establece causas socioeconómicas de la mortalidad.
- Tres años de información limitan el análisis temporal.
- Muchos municipios tienen muy pocos casos, en especial en Nariño.
- Las tasas con proyecciones de población dependen de supuestos demográficos que no reflejan
  por completo la caída reciente de los nacimientos.
""")

