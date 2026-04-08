# ============================================
# 1. IMPORTS
# ============================================
import streamlit as st
from streamlit_folium import st_folium
import folium
import geopandas as gpd
import pandas as pd
import plotly.express as px
from folium import IFrame
from folium.plugins import MarkerCluster, HeatMap

# ============================================
st.set_page_config(
    page_title="Parques Urbanos | IAT",  
    page_icon="🌳",                 
    layout="wide"
)

# URLs
url_planilha = "https://raw.githubusercontent.com/BryanSprenger/Parques-Urbanos---Instituto-gua-e-Terra/refs/heads/main/Parques%20Urbanos.csv"
url_municipios = "https://raw.githubusercontent.com/BryanSprenger/Parques-Urbanos---Instituto-gua-e-Terra/refs/heads/main/municipios.geojson"
url_imagens = "https://raw.githubusercontent.com/BryanSprenger/Parques-Urbanos---Instituto-gua-e-Terra/main/Imagens/"

# ============================================
# 3. CACHE - CARREGAMENTO
# ============================================
@st.cache_data
def carregar_dados():
    df = pd.read_csv(url_planilha)
    df.columns = df.columns.str.strip().str.lower()

    def limpar_coord(valor):
        try:
            return float(str(valor).replace(',', '.'))
        except:
            return None

    df['lat'] = df['coordenada x'].apply(limpar_coord)
    df['lon'] = df['coordenada y'].apply(limpar_coord)

    return df


@st.cache_data
def carregar_municipios():
    gdf = gpd.read_file(url_municipios)
    return gdf.to_crs(epsg=4326)


# ============================================
# 4. PREPARAÇÃO DOS DADOS
# ============================================
@st.cache_data
def preparar_dados(df):
    df = df.copy()

    df['cidade'] = df['cidade'].astype(str)
    df['status'] = df['status'].astype(str)
    df['ano'] = pd.to_numeric(df['ano'], errors='coerce')

    df['valor'] = (
        df['valor do convênio']
        .astype(str)
        .str.replace('.', '', regex=False)
        .str.replace(',', '.', regex=False)
    )
    df['valor'] = pd.to_numeric(df['valor'], errors='coerce')

    return df


df = preparar_dados(carregar_dados())
gdf = carregar_municipios()

# ============================================
# 5. FILTROS GLOBAIS
# ============================================
st.sidebar.title("🔎 Filtros")

municipios = sorted(df['cidade'].dropna().unique())
status_list = sorted(df['status'].dropna().unique())

filtro_municipio = st.sidebar.multiselect("Município", municipios, default=municipios)
filtro_status = st.sidebar.multiselect("Status", status_list, default=status_list)

ano_min = int(df['ano'].min())
ano_max = int(df['ano'].max())

filtro_ano = st.sidebar.slider("Ano", ano_min, ano_max, (ano_min, ano_max))

mostrar_cluster = st.sidebar.checkbox("Cluster", True)
mostrar_heatmap = st.sidebar.checkbox("Heatmap", False)

# DataFrame filtrado (CORE)
df_filtrado = df[
    (df['cidade'].isin(filtro_municipio)) &
    (df['status'].isin(filtro_status)) &
    (df['ano'].between(filtro_ano[0], filtro_ano[1]))
]

# ============================================
# 6. FUNÇÕES AUXILIARES
# ============================================
def cor_status(status):
    status = str(status).lower()
    if "concluido" in status or "concluído" in status:
        return "#2ecc71"
    elif "em andamento" in status:
        return "#95a5a6"
    return "#bdc3c7"


def escala_raio(valor, vmin, vmax):
    if pd.isna(valor):
        return 4
    return 4 + (valor - vmin) / (vmax - vmin + 1e-9) * 12


def criar_popup(row):
    nome = row.get('nome oficial do parque', 'Sem nome')
    cidade = row.get('cidade', '')
    valor = row.get('valor', '')
    status = row.get('status', '')
    area = row.get('area', '')
    ano = row.get('ano', '')

    nome_img = cidade.strip().replace(" ", "%20")
    img_url = f"{url_imagens}{nome_img}.png"

    cor = cor_status(status)

    valor_formatado = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    html = f"""
    <div style="width:260px;font-family:sans-serif;background:white;border-radius:10px;">
        <img src="{img_url}" style="width:100%; height:140px; object-fit:cover;">
        <div style="padding:10px;">
            <h4>{nome}</h4>
            <span style="background:{cor};color:white;padding:4px 8px;border-radius:8px;">{status}</span>
            <p><b>Cidade:</b> {cidade}</p>
            <p><b>Ano:</b> {ano}</p>
            <p><b>Área:</b> {area}</p>
            <p><b>Convênio:</b> R$ {valor_formatado}</p>
        </div>
    </div>
    """

    return IFrame(html=html, width=260, height=300)

# ============================================
# 7. MENU
# ============================================
pagina = st.sidebar.radio(
    "Navegação",
    ["🏠 Home", "🗺️ Mapa", "📊 Análise"]
)

# ============================================
# 8. HOME
# ============================================
if pagina == "🏠 Home":

    st.title("🌳 Mapa de Parques Urbanos - Paraná")

    st.markdown("""
    ### 📌 Sobre o Projeto
    
    Este dashboard apresenta uma análise exploratória dos parques urbanos financiados por convênios no estado do Paraná,
    com base em dados do Instituto Água e Terra (IAT).
    
    O objetivo é compreender a distribuição espacial dos investimentos públicos voltados à implantação e qualificação
    de áreas verdes urbanas, contribuindo para o planejamento territorial e avaliação de políticas públicas.
    """)

    st.markdown("""
    ### 🎯 Objetivos
    
    - Analisar a distribuição espacial dos parques urbanos
    - Identificar padrões territoriais de investimento
    - Avaliar desigualdades regionais
    - Apoiar estudos em planejamento urbano e ambiental
    """)

    st.markdown("""
    ### 🧠 Metodologia
    
    - Integração de dados tabulares (convênios)
    - Georreferenciamento dos parques
    - Análise espacial exploratória
    - Visualização interativa com SIG Web
    """)

    st.markdown("""
    ### ⚠️ Limitações
    
    - Possíveis inconsistências nas coordenadas
    - Dados dependem da qualidade da base original
    - Análises têm caráter exploratório
    """)

# ============================================
# 9. MAPA
# ============================================
elif pagina == "🗺️ Mapa":

    st.title("🗺️ Análise Espacial dos Parques")

    # 1. Primeiro criamos a base do mapa
    mapa = folium.Map(location=[-24.5, -51.5], zoom_start=7, tiles=None)

    # 2. Adicionando camadas base (agora que 'mapa' já existe)
    folium.TileLayer('OpenStreetMap', name='Rúas (OSM)').add_to(mapa)
    
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Satélite',
        overlay=False,
        control=True
    ).add_to(mapa)
    

    # base municipal
    folium.GeoJson(
        gdf,
        style_function=lambda x: {
            'fillColor': '#000000',
            'color': '#666666',
            'weight': 0.5,
            'fillOpacity': 0.05
        }
    ).add_to(mapa)

    # escala
    vmin = df_filtrado['valor'].min()
    vmax = df_filtrado['valor'].max()

    # cluster
    layer = MarkerCluster().add_to(mapa) if mostrar_cluster else mapa

    # pontos
    for _, row in df_filtrado.iterrows():
        lat, lon = row['lat'], row['lon']

        if pd.isna(lat) or pd.isna(lon):
            continue

        raio = escala_raio(row['valor'], vmin, vmax)

        folium.CircleMarker(
            location=[lat, lon],
            radius=raio,
            color=cor_status(row['status']),
            fill=True,
            fill_opacity=0.6,
            popup=folium.Popup(criar_popup(row)),
        ).add_to(layer)

    # heatmap
    if mostrar_heatmap:
        heat_data = df_filtrado[['lat', 'lon', 'valor']].dropna().values.tolist()
        HeatMap(heat_data).add_to(mapa)

    folium.LayerControl().add_to(mapa)

    st_folium(mapa, width=1200, height=600)

# ============================================
# 10. ANÁLISE
# ============================================
elif pagina == "📊 Análise":

    st.title("📊 Análise Estatística")

    df_valid = df_filtrado.dropna(subset=['valor', 'ano'])

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Investido", f"R$ {df_valid['valor'].sum():,.0f}")
    col2.metric("Número de Parques", len(df_filtrado))
    col3.metric("Média por Parque", f"R$ {df_valid['valor'].mean():,.0f}")

    investimento_ano = df_valid.groupby('ano')['valor'].sum().reset_index()

    fig1 = px.bar(
        investimento_ano,
        x='ano',
        y='valor',
        title="Distribuição Temporal dos Investimentos"
    )

    st.plotly_chart(fig1, use_container_width=True)

    status_count = df_filtrado['status'].value_counts().reset_index()
    status_count.columns = ['status', 'quantidade']

    fig2 = px.pie(
        status_count,
        names='status',
        values='quantidade',
        title="Distribuição por Status"
    )

    st.plotly_chart(fig2, use_container_width=True)
