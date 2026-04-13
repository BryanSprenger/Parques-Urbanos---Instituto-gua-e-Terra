
# ============================================
# PARQUES URBANOS - APP STREAMLIT (CORRIGIDO)
# ============================================

import streamlit as st
from streamlit_folium import st_folium
import folium
import geopandas as gpd
import pandas as pd
import plotly.express as px
from folium import IFrame
from folium.plugins import MarkerCluster, HeatMap
import math

# ============================================
# CONFIG
# ============================================
st.set_page_config(page_title="Parques Urbanos | IAT", page_icon="🌳", layout="wide")

# ============================================
# URLs
# ============================================
url_planilha  = "https://raw.githubusercontent.com/BryanSprenger/Parques-Urbanos---Instituto-gua-e-Terra/refs/heads/main/Parques%20Urbanos.csv"
url_municipios = "https://raw.githubusercontent.com/BryanSprenger/Parques-Urbanos---Instituto-gua-e-Terra/refs/heads/main/municipios.geojson"

# ============================================
# LOAD
# ============================================
@st.cache_data
def carregar_dados():
    df = pd.read_csv(url_planilha)
    df.columns = df.columns.str.strip().str.lower()

    df = df.rename(columns={
        'município': 'cidade',
        'valor conveniado': 'valor',
        'coordenada x': 'coord_x',
        'coordenada y': 'coord_y'
    })

    def limpar_numero(valor):
        try:
            return float(str(valor).replace('.', '').replace(',', '.'))
        except:
            return None

    df['lat'] = df['coord_x'].apply(limpar_numero) if 'coord_x' in df else None
    df['lon'] = df['coord_y'].apply(limpar_numero) if 'coord_y' in df else None
    df['valor'] = df['valor'].apply(limpar_numero) if 'valor' in df else None
    df['ano'] = pd.to_numeric(df.get('ano'), errors='coerce')
    df['cidade'] = df.get('cidade', '').astype(str)
    df['status'] = df.get('status', '').astype(str)

    return df

@st.cache_data
def carregar_municipios():
    return gpd.read_file(url_municipios).to_crs(epsg=4326)

df = carregar_dados()
gdf = carregar_municipios()

# ============================================
# FUNÇÕES
# ============================================
def cor_status(status):
    status = str(status).lower()
    if "concluido" in status or "concluído" in status:
        return "#27ae60"
    elif "andamento" in status:
        return "#f39c12"
    return "#95a5a6"

def escala_raio(valor, vmin, vmax):
    if pd.isna(valor):
        return 5
    return 5 + (valor - vmin) / (vmax - vmin + 1e-9) * 14

def criar_popup(row):
    nome = row.get('nome oficial do parque') or 'Sem nome'
    cidade = row.get('cidade') or ''
    valor = row.get('valor')
    status = row.get('status') or ''
    ano = row.get('ano')

    cor = cor_status(status)

    try:
        valor_fmt = f"{float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        valor_fmt = "—"

    try:
        ano_fmt = int(ano)
    except:
        ano_fmt = "—"

    html = f"""
    <div style="width:240px">
        <h4>{nome}</h4>
        <b>{cidade}</b><br>
        Status: {status}<br>
        Ano: {ano_fmt}<br>
        Valor: R$ {valor_fmt}
    </div>
    """
    return IFrame(html=html, width=250, height=180)

# ============================================
# SIDEBAR
# ============================================
pagina = st.sidebar.radio("Página", ["Mapa", "Análise"])

ano_min = int(df['ano'].min()) if df['ano'].notna().any() else 2000
ano_max = int(df['ano'].max()) if df['ano'].notna().any() else 2025

filtro_ano = st.sidebar.slider("Ano", ano_min, ano_max, (ano_min, ano_max))

valores_validos = df['valor'].dropna()
valor_min = int(valores_validos.min()) if len(valores_validos) else 0
valor_max = int(valores_validos.max()) if len(valores_validos) else 1

filtro_valor = st.sidebar.slider("Valor", valor_min, valor_max, (valor_min, valor_max))

# ============================================
# FILTRO
# ============================================
df_filtrado = df[
    (df['ano'].between(filtro_ano[0], filtro_ano[1])) &
    ((df['valor'].between(filtro_valor[0], filtro_valor[1])) | df['valor'].isna())
]

# ============================================
# MAPA
# ============================================
if pagina == "Mapa":
    st.title("Mapa de Parques")

    mapa = folium.Map(location=[-24.5, -51.5], zoom_start=7)

    vmin = df_filtrado['valor'].min()
    vmax = df_filtrado['valor'].max()

    for _, row in df_filtrado.iterrows():
        if pd.isna(row['lat']) or pd.isna(row['lon']):
            continue

        folium.CircleMarker(
            location=[row['lat'], row['lon']],
            radius=escala_raio(row['valor'], vmin, vmax),
            color=cor_status(row['status']),
            fill=True,
            popup=folium.Popup(criar_popup(row))
        ).add_to(mapa)

    st_folium(mapa, width=800, height=500)

# ============================================
# ANALISE
# ============================================
else:
    st.title("Análise")

    df_valid = df_filtrado.dropna(subset=['valor'])

    st.metric("Total", f"R$ {df_valid['valor'].sum():,.0f}".replace(",", "."))

    fig = px.histogram(df_valid, x='valor')
    st.plotly_chart(fig, use_container_width=True)
