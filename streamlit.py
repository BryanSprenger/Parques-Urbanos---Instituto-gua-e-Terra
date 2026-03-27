import streamlit as st
from streamlit_folium import st_folium
import folium
import geopandas as gpd
import pandas as pd
import plotly.express as px
from folium import IFrame

# ============================
# URLs 
# ============================
url_planilha = "https://raw.githubusercontent.com/BryanSprenger/Parques-Urbanos---Instituto-gua-e-Terra/refs/heads/main/Parques%20Urbanos.csv"
url_municipios = "https://raw.githubusercontent.com/BryanSprenger/Parques-Urbanos---Instituto-gua-e-Terra/refs/heads/main/municipios.geojson"
url_imagens = "https://raw.githubusercontent.com/BryanSprenger/Parques-Urbanos---Instituto-gua-e-Terra/main/Imagens/"
# ============================
# CONFIG STREAMLIT
# ============================
st.set_page_config(page_title="Parques Urbanos", layout="wide")

# ============================
# CACHE (ESSENCIAL)
# ============================
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


df = carregar_dados()
gdf = carregar_municipios()

# ============================
# FUNÇÕES
# ============================
def cor_status(status):
    status = str(status).lower()
    if "concluido" in status or "concluído" in status:
        return "#2ecc71"
    elif "em andamento" in status:
        return "#95a5a6"
    else:
        return "#bdc3c7"


def criar_popup(row):

    nome = str(row.get('nome oficial do parque', 'Sem nome'))
    cidade = str(row.get('cidade', 'Não informado'))
    valor = str(row.get('valor do convênio', 'Não informado'))
    status = str(row.get('status', 'Não informado'))
    area = str(row.get('area', 'Não informado'))
    ano = str(row.get('ano', 'Não informado'))

    # ----------------------------
    # URL da imagem 
    # ----------------------------
    nome_img = cidade.strip().replace(" ", "%20")
    img_url = f"{url_imagens}{nome_img}.png"

    # ----------------------------
    # Cor do status
    # ----------------------------
    cor = cor_status(status)

    # ----------------------------
    # ----------------------------
    # Formatação do valor
    # ----------------------------
    try:
        valor_num = float(valor)
        valor_formatado = f"{valor_num:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        valor_formatado = str(valor)
    
    # ----------------------------
    # HTML estilizado
    # ----------------------------
    html = f"""
    <div style="
        width:260px;
        font-family: 'Segoe UI', sans-serif;
        border-radius:12px;
        overflow:hidden;
        box-shadow:0 4px 12px rgba(0,0,0,0.25);
        background:white;
    ">
    
        <!-- Imagem -->
        <div style="height:160px; background:#f0f0f0;">
            <img src="{img_url}" 
                 style="width:100%; height:100%; object-fit:cover;">
        </div>
    
        <!-- Conteúdo -->
        <div style="padding:12px;">
    
            <h4 style="
                margin:0 0 6px 0;
                font-size:16px;
                color:#2c3e50;
            ">
                {nome}
            </h4>
    
            <!-- Status -->
            <div style="margin-bottom:8px;">
                <span style="
                    background:{cor};
                    color:white;
                    padding:4px 10px;
                    border-radius:10px;
                    font-size:12px;
                    font-weight:500;
                ">
                    {status}
                </span>
            </div>
    
            <!-- Infos -->
            <p style="margin:3px 0; font-size:13px;">
                <b>Cidade:</b> {cidade}
            </p>
    
            <p style="margin:3px 0; font-size:13px;">
                <b>Ano:</b> {ano}
            </p>
    
            <p style="margin:3px 0; font-size:13px;">
                <b>Área:</b> {area}
            </p>
    
            <p style="margin:3px 0; font-size:13px;">
                <b>Convênio:</b> R$ {valor_formatado}
            </p>
    
        </div>
    </div>
    """

    return IFrame(html=html, width=270, height=340)


# ============================
# MENU
# ============================
st.sidebar.title("Navegação")
pagina = st.sidebar.radio(
    "Selecione:",
    ["🏠 Home", "🗺️ Mapa Interativo", "📊 Análise Estatística"]
)

# ============================
# HOME
# ============================
if pagina == "🏠 Home":
    st.title("📒 Parques Urbanos - IAT")
    st.markdown("Sistema interativo para análise de parques urbanos no Paraná.")

# ============================
# MAPA
# ============================
elif pagina == "🗺️ Mapa Interativo":

    st.title("🗺️ Mapa de Parques Urbanos")

    mapa = folium.Map(location=[-24.5, -51.5], zoom_start=7)

    # municípios
    folium.GeoJson(
        gdf,
        style_function=lambda x: {
            'fillColor': '#000000',
            'color': '#666666',
            'weight': 0.5,
            'fillOpacity': 0.05
        }
    ).add_to(mapa)

    # pontos
    for _, row in df.iterrows():

        lat = row['lat']
        lon = row['lon']

        if pd.isna(lat) or pd.isna(lon):
            continue

        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            continue

        cor = cor_status(row.get('status'))

        folium.CircleMarker(
            location=[lat, lon],
            radius=6,
            color=cor,
            fill=True,
            fill_color=cor,
            fill_opacity=0.6,
            popup=folium.Popup(criar_popup(row), max_width=300),
            tooltip=row.get('nome oficial do parque', '')
        ).add_to(mapa)

    st_folium(mapa, width=1200, height=600)

    # VERIFICADOR ESPECÍFICO (ABAIXO DO MAPA)
    # ============================
    st.divider()
    st.subheader("🔍 Diagnóstico: Querência do Norte")
    
    # Filtra a linha específica (ajuste o nome se estiver diferente no CSV)
    diagnostico = df[df['cidade'].str.contains("Querência do Norte", case=False, na=False)]
    
    if not diagnostico.empty:
        linha = diagnostico.iloc[0]
        st.write(f"**Nome no CSV:** {linha['nome oficial do parque']}")
        st.write(f"**Latitude lida (X):** `{linha['lat']}`")
        st.write(f"**Longitude lida (Y):** `{linha['lon']}`")
        st.write(f"**Status:** {linha['status']}")
        
        # Lógica de erro
        if linha['lat'] < -40:
            st.error("🚨 **Erro detectado:** A Latitude está abaixo de -40. Isso indica que as coordenadas estão INVERTIDAS na planilha (a Longitude foi digitada na coluna X).")
        elif pd.isna(linha['lat']):
            st.warning("⚠️ **Aviso:** As coordenadas estão vazias ou em formato inválido para esta linha.")
        else:
            st.success("✅ As coordenadas parecem estar dentro do intervalo esperado para o Paraná.")
    else:
        st.error("❌ Não foi possível encontrar a linha de 'Querência do Norte' no DataFrame. Verifique a escrita do nome na planilha.")

# ============================
# ANÁLISE
# ============================
elif pagina == "📊 Análise Estatística":

    st.title("📊 Indicadores e Análise do Programa")

    # limpeza básica
    df_valid = df.dropna(subset=['valor do convênio', 'ano'])

    # converter valor
    df_valid['valor'] = (
        df_valid['valor do convênio']
        .astype(str)
        .str.replace('.', '', regex=False)
        .str.replace(',', '.', regex=False)
        .astype(float)
    )

    # ----------------------------
    # KPIs
    # ----------------------------
    col1, col2, col3 = st.columns(3)

    col1.metric("Total Investido", f"R$ {df_valid['valor'].sum():,.0f}")
    col2.metric("Número de Parques", len(df))
    col3.metric("Média por Parque", f"R$ {df_valid['valor'].mean():,.0f}")

    # ----------------------------
    # gráfico por ano
    # ----------------------------
    investimento_ano = df_valid.groupby('ano')['valor'].sum().reset_index()

    fig1 = px.bar(investimento_ano, x='ano', y='valor',
                  title="Investimento por Ano")

    st.plotly_chart(fig1, use_container_width=True)

    # ----------------------------
    # status
    # ----------------------------
    status_count = df['status'].value_counts().reset_index()
    status_count.columns = ['status', 'quantidade']

    fig2 = px.pie(status_count, names='status', values='quantidade',
                  title="Distribuição por Status")

    st.plotly_chart(fig2, use_container_width=True)
