# ============================================
# 1. IMPORTS
# ============================================
import streamlit as st
from streamlit_folium import st_folium
import folium
import geopandas as gpd
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from folium import IFrame
from folium.plugins import MarkerCluster, HeatMap

# ============================================
# 2. CONFIGURAÇÃO DA PÁGINA
# ============================================
st.set_page_config(
    page_title="Parques Urbanos | IAT",
    page_icon="🌳",
    layout="wide"
)

# CSS customizado para melhorar a aparência geral
st.markdown("""
<style>
    /* Fundo geral */
    .main { background-color: #f4f6f4; }
    
    /* Sidebar com tom esverdeado suave */
    [data-testid="stSidebar"] {
        background-color: #1e3d2f;
    }
    [data-testid="stSidebar"] * {
        color: #e8f0eb !important;
    }
    [data-testid="stSidebar"] .stRadio label,
    [data-testid="stSidebar"] .stCheckbox label {
        color: #c8dbc e !important;
        font-size: 0.9rem;
    }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #a8d5a2 !important;
    }
    [data-testid="stSidebar"] .stSlider label {
        color: #c8dbce !important;
    }

    /* Divisor na sidebar */
    [data-testid="stSidebar"] hr {
        border-color: #3a6b4a;
    }

    /* Cards de métrica */
    [data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #d4e6d4;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06);
    }
    [data-testid="metric-container"] label {
        color: #5a7a5a !important;
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    [data-testid="metric-container"] [data-testid="stMetricValue"] {
        color: #1e3d2f !important;
        font-size: 1.5rem !important;
        font-weight: 700 !important;
    }

    /* Títulos de página */
    h1 { color: #1e3d2f !important; }
    h2, h3 { color: #2e5c3e !important; }

    /* Borda dos gráficos */
    .js-plotly-plot {
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0,0,0,0.07);
    }
    
    /* Bloco do mapa */
    iframe {
        border-radius: 12px !important;
        box-shadow: 0 4px 14px rgba(0,0,0,0.1) !important;
    }

    /* Badge de status na Home */
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 6px;
    }
    
    /* Separadores suaves */
    .section-divider {
        border: none;
        border-top: 2px solid #d4e6d4;
        margin: 24px 0;
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# 3. URLs
# ============================================
url_planilha  = "https://raw.githubusercontent.com/BryanSprenger/Parques-Urbanos---Instituto-gua-e-Terra/refs/heads/main/Parques%20Urbanos.csv"
url_municipios = "https://raw.githubusercontent.com/BryanSprenger/Parques-Urbanos---Instituto-gua-e-Terra/refs/heads/main/municipios.geojson"
url_imagens   = "https://raw.githubusercontent.com/BryanSprenger/Parques-Urbanos---Instituto-gua-e-Terra/main/Imagens/"

# ============================================
# 4. CACHE — CARREGAMENTO
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
# 5. PREPARAÇÃO DOS DADOS
# ============================================
@st.cache_data
def preparar_dados(df):
    df = df.copy()
    df['cidade']  = df['cidade'].astype(str)
    df['status']  = df['status'].astype(str)
    df['ano']     = pd.to_numeric(df['ano'], errors='coerce')
    df['valor']   = (
        df['valor do convênio']
        .astype(str)
        .str.replace('.', '', regex=False)
        .str.replace(',', '.', regex=False)
    )
    df['valor'] = pd.to_numeric(df['valor'], errors='coerce')
    return df


df  = preparar_dados(carregar_dados())
gdf = carregar_municipios()

# ============================================
# 6. FUNÇÕES AUXILIARES
# ============================================
def cor_status(status):
    status = str(status).lower()
    if "concluido" in status or "concluído" in status:
        return "#27ae60"
    elif "em andamento" in status:
        return "#f39c12"
    return "#95a5a6"


def escala_raio(valor, vmin, vmax):
    if pd.isna(valor):
        return 5
    return 5 + (valor - vmin) / (vmax - vmin + 1e-9) * 14


def criar_popup(row):
    nome   = row.get('nome oficial do parque', 'Sem nome')
    cidade = row.get('cidade', '')
    valor  = row.get('valor', '')
    status = row.get('status', '')
    area   = row.get('area', '')
    ano    = row.get('ano', '')

    nome_img = cidade.strip().replace(" ", "%20")
    img_url  = f"{url_imagens}{nome_img}.png"
    cor      = cor_status(status)

    try:
        valor_fmt = f"{float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        valor_fmt = "—"

    html = f"""
    <div style="width:260px;font-family:'Segoe UI',sans-serif;background:#fff;border-radius:10px;overflow:hidden;">
        <img src="{img_url}" style="width:100%;height:140px;object-fit:cover;"
             onerror="this.style.display='none'">
        <div style="padding:12px;">
            <h4 style="margin:0 0 6px;color:#1e3d2f;font-size:0.95rem;">{nome}</h4>
            <span style="background:{cor};color:white;padding:3px 10px;border-radius:20px;
                         font-size:0.75rem;font-weight:600;">{status}</span>
            <table style="margin-top:10px;width:100%;font-size:0.82rem;border-collapse:collapse;">
                <tr><td style="color:#777;padding:3px 0;">🏙️ Cidade</td>
                    <td style="font-weight:600;color:#333;">{cidade}</td></tr>
                <tr><td style="color:#777;padding:3px 0;">📅 Ano</td>
                    <td style="font-weight:600;color:#333;">{int(ano) if ano == ano else '—'}</td></tr>
                <tr><td style="color:#777;padding:3px 0;">📐 Área</td>
                    <td style="font-weight:600;color:#333;">{area}</td></tr>
                <tr><td style="color:#777;padding:3px 0;">💰 Convênio</td>
                    <td style="font-weight:600;color:#1e3d2f;">R$ {valor_fmt}</td></tr>
            </table>
        </div>
    </div>
    """
    return IFrame(html=html, width=270, height=310)


def formatar_reais(valor):
    return f"R$ {valor:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ============================================
# 7. SIDEBAR — FILTROS INTEGRADOS
# ============================================
st.sidebar.markdown("## 🌳 Parques Urbanos")
st.sidebar.markdown("**Instituto Água e Terra — Paraná**")
st.sidebar.markdown("---")

# Navegação
pagina = st.sidebar.radio(
    "Navegação",
    ["🏠 Home", "🗺️ Mapa", "📊 Análise"],
    label_visibility="collapsed"
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎛️ Filtros")

# --- Ano (slider) ---
ano_min = int(df['ano'].min())
ano_max = int(df['ano'].max())
filtro_ano = st.sidebar.slider(
    "Período",
    ano_min, ano_max,
    (ano_min, ano_max),
    format="%d"
)

# --- Status (radio elegante, sem multiselect pesado) ---
opcoes_status = ["Todos"] + sorted(df['status'].dropna().unique().tolist())
filtro_status = st.sidebar.radio(
    "Status",
    opcoes_status,
    index=0
)

# --- Faixa de valor (slider) ---
valor_min_global = int(df['valor'].dropna().min())
valor_max_global = int(df['valor'].dropna().max())
filtro_valor = st.sidebar.slider(
    "Valor do Convênio (R$)",
    valor_min_global,
    valor_max_global,
    (valor_min_global, valor_max_global),
    step=10_000,
    format="R$ %d"
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🗺️ Opções do Mapa")
mostrar_cluster  = st.sidebar.checkbox("Clusterização", value=False)
mostrar_heatmap  = st.sidebar.checkbox("Mapa de Calor",  value=False)

# ============================================
# 8. FILTRAGEM
# ============================================
df_filtrado = df[
    (df['ano'].between(filtro_ano[0], filtro_ano[1])) &
    (df['valor'].between(filtro_valor[0], filtro_valor[1], inclusive='both') |
     df['valor'].isna())
]

if filtro_status != "Todos":
    df_filtrado = df_filtrado[df_filtrado['status'] == filtro_status]

# ============================================
# 9. HOME
# ============================================
if pagina == "🏠 Home":

    st.title("🌳 Parques Urbanos do Paraná")
    st.markdown("##### Monitoramento e Análise de Investimentos em Áreas Verdes Urbanas")
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    # KPIs rápidos no topo da Home
    df_home = df.dropna(subset=['valor'])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Parques Cadastrados",    f"{len(df):,}".replace(",", "."))
    c2.metric("Total Investido",        formatar_reais(df_home['valor'].sum()))
    c3.metric("Municípios Atendidos",   df['cidade'].nunique())
    c4.metric("Período dos Dados",      f"{ano_min} – {ano_max}")

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("### 📌 Sobre o Projeto")
        st.markdown("""
        Este painel apresenta uma análise exploratória dos **parques urbanos financiados
        por convênios no estado do Paraná**, com base em dados do
        **Instituto Água e Terra (IAT)**.

        O objetivo é compreender a distribuição espacial dos investimentos públicos
        voltados à implantação e qualificação de **áreas verdes urbanas**, contribuindo
        para o planejamento territorial e a avaliação de políticas públicas ambientais.
        """)

        st.markdown("### 🎯 Objetivos")
        st.markdown("""
        - Analisar a **distribuição espacial** dos parques
        - Identificar **padrões territoriais** de investimento
        - Avaliar **desigualdades regionais** no acesso a áreas verdes
        - Apoiar estudos em **planejamento urbano e ambiental**
        """)

    with col_b:
        st.markdown("### 🧠 Metodologia")
        st.markdown("""
        - Integração de dados tabulares de convênios públicos
        - Georreferenciamento dos parques por coordenadas
        - Análise espacial exploratória com SIG Web
        - Visualização interativa com Folium e Plotly
        """)

        st.markdown("### ⚠️ Limitações")
        st.markdown("""
        - Possíveis inconsistências nas coordenadas geográficas
        - Qualidade dos dados dependente da base original
        - Análises têm caráter **exploratório**
        - Valores podem não refletir execução financeira total
        """)

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    # Legenda de status
    st.markdown("### 🟢 Legenda de Status")
    col_leg1, col_leg2, col_leg3, _ = st.columns([1, 1, 1, 3])
    col_leg1.markdown(
        '<span class="badge" style="background:#27ae60;color:white;">✔ Concluído</span>',
        unsafe_allow_html=True
    )
    col_leg2.markdown(
        '<span class="badge" style="background:#f39c12;color:white;">⏳ Em Andamento</span>',
        unsafe_allow_html=True
    )
    col_leg3.markdown(
        '<span class="badge" style="background:#95a5a6;color:white;">— Outros</span>',
        unsafe_allow_html=True
    )

# ============================================
# 10. MAPA
# ============================================
elif pagina == "🗺️ Mapa":

    st.title("🗺️ Distribuição Espacial dos Parques")

    # Contadores rápidos acima do mapa
    df_mv = df_filtrado.dropna(subset=['valor'])
    m1, m2, m3 = st.columns(3)
    m1.metric("Parques Exibidos",   len(df_filtrado))
    m2.metric("Investimento Total", formatar_reais(df_mv['valor'].sum()) if len(df_mv) else "—")
    m3.metric("Municípios",         df_filtrado['cidade'].nunique())

    st.markdown("---")

    # Base do mapa
    mapa = folium.Map(location=[-24.5, -51.5], zoom_start=7, tiles=None)

    # Camada principal: ruas (OSM)
    folium.TileLayer('OpenStreetMap', name='Ruas (OSM)').add_to(mapa)

    # Camada secundária: satélite
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Satélite',
        overlay=False,
        control=True
    ).add_to(mapa)

    # Camada de municípios
    folium.GeoJson(
        gdf,
        style_function=lambda x: {
            'fillColor': '#2e5c3e',
            'color':      '#4a8c5c',
            'weight':      0.6,
            'fillOpacity': 0.05
        }
    ).add_to(mapa)

    # Escala de raio por valor
    vmin = df_filtrado['valor'].min()
    vmax = df_filtrado['valor'].max()

    # Layer de marcadores (cluster ou não)
    layer = MarkerCluster(name="Parques").add_to(mapa) if mostrar_cluster else mapa

    for _, row in df_filtrado.iterrows():
        lat, lon = row['lat'], row['lon']
        if pd.isna(lat) or pd.isna(lon):
            continue

        raio = escala_raio(row['valor'], vmin, vmax)
        cor  = cor_status(row['status'])

        folium.CircleMarker(
            location=[lat, lon],
            radius=raio,
            color=cor,
            fill=True,
            fill_color=cor,
            fill_opacity=0.72,
            weight=1.5,
            popup=folium.Popup(criar_popup(row)),
            tooltip=row.get('nome oficial do parque', row.get('cidade', ''))
        ).add_to(layer)

    # Heatmap opcional
    if mostrar_heatmap:
        heat_data = df_filtrado[['lat', 'lon', 'valor']].dropna().values.tolist()
        HeatMap(
            heat_data,
            name="Mapa de Calor",
            radius=18,
            blur=14,
            min_opacity=0.4,
            gradient={0.3: '#74c69d', 0.6: '#f39c12', 1.0: '#c0392b'}
        ).add_to(mapa)

    folium.LayerControl(collapsed=False).add_to(mapa)

    st_folium(mapa, width="100%", height=600)

    # Legenda inline
    st.markdown("""
    <div style="display:flex;gap:20px;margin-top:8px;font-size:0.82rem;color:#555;">
        <span>⬤ <span style="color:#27ae60;font-weight:600;">Concluído</span></span>
        <span>⬤ <span style="color:#f39c12;font-weight:600;">Em Andamento</span></span>
        <span>⬤ <span style="color:#95a5a6;font-weight:600;">Outros</span></span>
        <span style="margin-left:16px;">⊙ Tamanho do círculo proporcional ao valor do convênio</span>
    </div>
    """, unsafe_allow_html=True)

# ============================================
# 11. ANÁLISE
# ============================================
elif pagina == "📊 Análise":

    st.title("📊 Análise Estatística")

    df_valid = df_filtrado.dropna(subset=['valor', 'ano'])

    # --- Métricas principais ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Investido",     formatar_reais(df_valid['valor'].sum()))
    c2.metric("Número de Parques",   len(df_filtrado))
    c3.metric("Média por Parque",    formatar_reais(df_valid['valor'].mean()) if len(df_valid) else "—")
    c4.metric("Maior Convênio",      formatar_reais(df_valid['valor'].max()) if len(df_valid) else "—")

    st.markdown("---")

    # --- Linha 1: Temporal + Status ---
    col_a, col_b = st.columns([2, 1])

    with col_a:
        inv_ano = df_valid.groupby('ano')['valor'].sum().reset_index()
        fig_bar = px.bar(
            inv_ano,
            x='ano', y='valor',
            title="Investimento Total por Ano",
            color='valor',
            color_continuous_scale=[[0, '#74c69d'], [0.5, '#2e5c3e'], [1, '#1e3d2f']],
            labels={'valor': 'Investimento (R$)', 'ano': 'Ano'}
        )
        fig_bar.update_layout(
            plot_bgcolor='white', paper_bgcolor='white',
            coloraxis_showscale=False,
            font=dict(family='Segoe UI', size=12),
            title_font_size=15,
            margin=dict(t=40, b=30)
        )
        fig_bar.update_traces(marker_line_width=0)
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_b:
        status_count = df_filtrado['status'].value_counts().reset_index()
        status_count.columns = ['status', 'quantidade']

        cores_status = {
            s: cor_status(s) for s in status_count['status']
        }

        fig_pie = px.pie(
            status_count,
            names='status',
            values='quantidade',
            title="Distribuição por Status",
            color='status',
            color_discrete_map=cores_status,
            hole=0.45
        )
        fig_pie.update_layout(
            plot_bgcolor='white', paper_bgcolor='white',
            font=dict(family='Segoe UI', size=11),
            title_font_size=15,
            legend=dict(orientation='h', yanchor='bottom', y=-0.25),
            margin=dict(t=40, b=10)
        )
        fig_pie.update_traces(textinfo='percent+label', showlegend=False)
        st.plotly_chart(fig_pie, use_container_width=True)

    # --- Linha 2: Top municípios + Distribuição de valores ---
    col_c, col_d = st.columns(2)

    with col_c:
        top_cidades = (
            df_valid.groupby('cidade')['valor']
            .sum()
            .sort_values(ascending=True)
            .tail(12)
            .reset_index()
        )
        fig_h = px.bar(
            top_cidades,
            x='valor', y='cidade',
            orientation='h',
            title="Top 12 Municípios por Investimento",
            color='valor',
            color_continuous_scale=[[0, '#a8d5a2'], [1, '#1e3d2f']],
            labels={'valor': 'Investimento (R$)', 'cidade': ''}
        )
        fig_h.update_layout(
            plot_bgcolor='white', paper_bgcolor='white',
            coloraxis_showscale=False,
            font=dict(family='Segoe UI', size=11),
            title_font_size=15,
            margin=dict(t=40, b=30)
        )
        fig_h.update_traces(marker_line_width=0)
        st.plotly_chart(fig_h, use_container_width=True)

    with col_d:
        fig_hist = px.histogram(
            df_valid,
            x='valor',
            nbins=20,
            title="Distribuição dos Valores de Convênio",
            color_discrete_sequence=['#2e5c3e'],
            labels={'valor': 'Valor do Convênio (R$)', 'count': 'Quantidade'}
        )
        fig_hist.update_layout(
            plot_bgcolor='white', paper_bgcolor='white',
            font=dict(family='Segoe UI', size=11),
            title_font_size=15,
            bargap=0.08,
            margin=dict(t=40, b=30)
        )
        st.plotly_chart(fig_hist, use_container_width=True)

    # --- Linha 3: Evolução acumulada + Parques por município ---
    col_e, col_f = st.columns(2)

    with col_e:
        inv_acum = inv_ano.copy()
        inv_acum['acumulado'] = inv_acum['valor'].cumsum()
        fig_line = px.line(
            inv_acum,
            x='ano', y='acumulado',
            title="Investimento Acumulado ao Longo do Tempo",
            markers=True,
            color_discrete_sequence=['#27ae60'],
            labels={'acumulado': 'Investimento Acumulado (R$)', 'ano': 'Ano'}
        )
        fig_line.update_traces(line_width=2.5, marker_size=7)
        fig_line.update_layout(
            plot_bgcolor='white', paper_bgcolor='white',
            font=dict(family='Segoe UI', size=11),
            title_font_size=15,
            margin=dict(t=40, b=30)
        )
        st.plotly_chart(fig_line, use_container_width=True)

    with col_f:
        parques_cidade = (
            df_filtrado.groupby('cidade')
            .size()
            .sort_values(ascending=False)
            .head(10)
            .reset_index(name='quantidade')
        )
        fig_pc = px.bar(
            parques_cidade,
            x='cidade', y='quantidade',
            title="Top 10 Municípios por Número de Parques",
            color='quantidade',
            color_continuous_scale=[[0, '#a8d5a2'], [1, '#1e3d2f']],
            labels={'quantidade': 'Nº de Parques', 'cidade': ''}
        )
        fig_pc.update_layout(
            plot_bgcolor='white', paper_bgcolor='white',
            coloraxis_showscale=False,
            font=dict(family='Segoe UI', size=11),
            title_font_size=15,
            xaxis_tickangle=-35,
            margin=dict(t=40, b=60)
        )
        fig_pc.update_traces(marker_line_width=0)
        st.plotly_chart(fig_pc, use_container_width=True)

    # --- Tabela detalhada ---
    st.markdown("---")
    st.markdown("### 📋 Tabela de Parques")

    colunas_exibir = ['nome oficial do parque', 'cidade', 'status', 'ano', 'valor']
    colunas_validas = [c for c in colunas_exibir if c in df_filtrado.columns]

    df_tabela = df_filtrado[colunas_validas].copy()
    df_tabela.columns = ['Nome', 'Município', 'Status', 'Ano', 'Valor (R$)'][: len(colunas_validas)]

    if 'Valor (R$)' in df_tabela.columns:
        df_tabela['Valor (R$)'] = df_tabela['Valor (R$)'].apply(
            lambda x: f"R$ {x:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".") if pd.notna(x) else "—"
        )

    st.dataframe(
        df_tabela.reset_index(drop=True),
        use_container_width=True,
        height=340
    )
