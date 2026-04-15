# ============================================
# 1. IMPORTS
# ============================================
import re
import math
import streamlit as st
from streamlit_folium import st_folium
import folium
import geopandas as gpd
import pandas as pd
import plotly.express as px
from folium.plugins import MarkerCluster, HeatMap

# ============================================
# 2. CONFIGURAÇÃO DA PÁGINA
# ============================================
st.set_page_config(
    page_title="Parques Urbanos | IAT",
    page_icon="🌳",
    layout="wide"
)

st.markdown("""
<style>
    .main { background-color: #f4f6f4; }

    [data-testid="stSidebar"] { background-color: #1e3d2f; }
    [data-testid="stSidebar"] * { color: #e8f0eb !important; }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 { color: #a8d5a2 !important; }
    [data-testid="stSidebar"] hr { border-color: #3a6b4a; }

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

    h1 { color: #1e3d2f !important; }
    h2, h3 { color: #2e5c3e !important; }

    iframe {
        border-radius: 12px !important;
        box-shadow: 0 4px 14px rgba(0,0,0,0.1) !important;
    }

    .section-divider {
        border: none;
        border-top: 2px solid #d4e6d4;
        margin: 24px 0;
    }

    .hint-box {
        background: #f0f7f2;
        border: 1px dashed #a8d5a2;
        border-radius: 10px;
        padding: 16px 20px;
        color: #5a7a5a;
        font-size: 0.88rem;
        text-align: center;
        margin-top: 4px;
    }

    .park-card {
        background: #ffffff;
        border: 1px solid #d4e6d4;
        border-radius: 14px;
        overflow: hidden;
        box-shadow: 0 4px 16px rgba(0,0,0,0.08);
    }
    .park-card-header {
        background: linear-gradient(135deg, #1e3d2f 0%, #2e5c3e 100%);
        padding: 18px 22px 14px;
    }
    .park-card-body { padding: 4px 0 0; }
    .detail-row {
        display: flex;
        align-items: flex-start;
        gap: 12px;
        padding: 10px 22px;
        border-bottom: 1px solid #f0f4f0;
        font-size: 0.88rem;
    }
    .detail-row:last-child { border-bottom: none; }
    .detail-label {
        color: #7a9a7a;
        font-weight: 700;
        min-width: 150px;
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        padding-top: 2px;
        flex-shrink: 0;
    }
    .detail-value { color: #1e3d2f; font-weight: 500; line-height: 1.4; }
    .badge-status {
        display: inline-block;
        padding: 3px 14px;
        border-radius: 20px;
        font-size: 0.76rem;
        font-weight: 700;
        letter-spacing: 0.03em;
        margin-top: 6px;
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# 3. URLs
# ============================================
url_planilha   = "https://raw.githubusercontent.com/BryanSprenger/Parques-Urbanos---Instituto-gua-e-Terra/refs/heads/main/Parques%20Urbanos.csv"
url_municipios = "https://raw.githubusercontent.com/BryanSprenger/Parques-Urbanos---Instituto-gua-e-Terra/refs/heads/main/municipios.geojson"
url_imagens    = "https://raw.githubusercontent.com/BryanSprenger/Parques-Urbanos---Instituto-gua-e-Terra/main/Imagens/"
url_fallback   = f"{url_imagens}Placa%20-%20Modelo%20Parques.png"

# ============================================
# 4. CACHE — CARREGAMENTO E FUNÇÕES DE LIMPEZA
# ============================================

def _limpar_coord(valor):
    """ Corrige coordenadas corrompidas do Excel/CSV. """
    try:
        s = str(valor).strip()
        if s in ('', 'nan', 'NaN', 'None'):
            return None
        digits = re.sub(r'[^0-9]', '', s)
        if len(digits) < 3:
            return None
        result = float(f'{digits[:2]}.{digits[2:]}')
        return -abs(result)
    except Exception:
        return None

def _limpar_valor_brl(raw):
    """ Converte strings no formato brasileiro 'R$ 1.234.567,89' para float. """
    s = str(raw).strip()
    if s in ('', 'nan', 'NaN', 'None', '-'):
        return None
    s = re.sub(r'[^\d,.]', '', s)
    s = s.replace('.', '')
    s = s.replace(',', '.')
    try:
        return float(s)
    except Exception:
        return None

def _limpar_area(raw):
    return _limpar_valor_brl(raw)

def _limpar_habitantes(raw):
    """ Evita que o número de habitantes como 9.000 seja lido como 9.0 """
    s = str(raw).strip()
    if s in ('', 'nan', 'NaN', 'None', '-'):
        return None
    # Remove pontos usados para milhares
    s = s.replace('.', '')
    # Se vier com decimais usando vírgula, descartamos
    s = s.split(',')[0]
    try:
        return float(s)
    except Exception:
        return None

@st.cache_data
def carregar_dados():
    try:
        # dtype=str preserva os zeros garantindo a precisão dos milhares
        df = pd.read_csv(url_planilha, dtype=str)
    except Exception as e:
        st.error(f"Erro ao acessar a planilha no GitHub. Detalhes: {e}")
        return pd.DataFrame()
    
    # Normaliza nomes: remove espaços e coloca em minúsculo
    df.columns = df.columns.str.strip().str.lower()

    colunas_esperadas = ['coordenada x', 'coordenada y', 'município', 'ano', 'status', 'valor conveniado', 'valor executado', 'área', 'habitantes', 'endereço']
    for col in colunas_esperadas:
        if col not in df.columns:
            df[col] = pd.NA

    df['lat'] = df['coordenada x'].apply(_limpar_coord)
    df['lon'] = df['coordenada y'].apply(_limpar_coord)
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
    if df.empty:
        return df

    df = df.copy()

    df['município'] = df['município'].astype(str).str.strip().replace('nan', pd.NA)
    df['ano'] = pd.to_numeric(df['ano'], errors='coerce')
    df['status'] = df['status'].astype(str).str.strip().replace('nan', pd.NA)
    df['valor_conveniado'] = df['valor conveniado'].apply(_limpar_valor_brl)
    df['valor_executado']  = df['valor executado'].apply(_limpar_valor_brl)
    df['area_m2'] = df['área'].apply(_limpar_area)
    df['habitantes'] = df['habitantes'].apply(_limpar_habitantes)
    df['endereço'] = df['endereço'].astype(str).str.strip().replace('nan', pd.NA)

    return df

df  = preparar_dados(carregar_dados())
gdf = carregar_municipios()

# ============================================
# 6. FUNÇÕES AUXILIARES DE EXIBIÇÃO
# ============================================
def cor_status(status):
    s = str(status).lower()
    if "conclu" in s:
        return "#27ae60"
    elif "andamento" in s:
        return "#f39c12"
    return "#95a5a6"

def escala_raio(valor, vmin, vmax):
    if pd.isna(valor):
        return 5
    return 5 + (valor - vmin) / (vmax - vmin + 1e-9) * 14

def formatar_reais(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def formatar_area(valor):
    if pd.isna(valor):
        return "—"
    return f"{valor:,.2f} m²".replace(",", "X").replace(".", ",").replace("X", ".")

def formatar_habitantes(valor):
    if pd.isna(valor):
        return "—"
    return f"{int(valor):,}".replace(",", ".") + " hab."

def criar_popup_minimo(row):
    nome      = str(row.get('nome oficial do parque', ''))
    municipio = str(row.get('município', ''))
    status    = str(row.get('status', ''))
    cor       = cor_status(status)

    nome_display = nome if nome not in ('nan', '', 'None', '<NA>') else municipio
    status_display = status if status not in ('nan', '', 'None', '<NA>') else 'Não informado'
    img_url = f"{url_imagens}{municipio.strip().replace(' ', '%20')}.png"

    # Truque CSS: A imagem de fallback fica como background da div pai
    html = f"""
    <div style="width:215px;font-family:'Segoe UI',sans-serif;
                background:#fff;border-radius:10px;overflow:hidden;
                box-shadow:0 2px 8px rgba(0,0,0,0.12);">
        <div style="width:100%;height:115px;background-image:url('{url_fallback}');
                    background-size:cover;background-position:center;background-color:#e8f0eb;">
            <img src="{img_url}"
                 style="width:100%;height:100%;object-fit:cover;color:transparent;"
                 alt=""
                 onerror="this.style.display='none';">
        </div>
        <div style="padding:10px 12px 12px;">
            <div style="font-weight:700;color:#1e3d2f;font-size:0.87rem;
                        margin-bottom:4px;line-height:1.3;">{nome_display}</div>
            <div style="color:#666;font-size:0.79rem;margin-bottom:7px;">🏙️ {municipio}</div>
            <span style="background:{cor};color:white;padding:3px 10px;
                         border-radius:20px;font-size:0.72rem;font-weight:700;">
                {status_display}
            </span>
        </div>
    </div>
    """
    return folium.Popup(html, max_width=230)

def buscar_parque_por_coords(df_base, lat, lon, tolerancia=0.05):
    """Retorna a linha do parque mais próxima. Tolerância 0.05 atende marcadores gigantes."""
    df_geo = df_base.dropna(subset=['lat', 'lon'])
    if df_geo.empty:
        return None
    dist = (df_geo['lat'] - lat).abs() + (df_geo['lon'] - lon).abs()
    idx_min = dist.idxmin()
    return df_base.loc[idx_min] if dist[idx_min] < tolerancia else None

def str_vazia(v):
    return str(v) in ('nan', '', 'None', '<NA>', 'NaT')

# ============================================
# 7. SIDEBAR — NAVEGAÇÃO E FILTROS
# ============================================
st.sidebar.markdown("## 🌳 Parques Urbanos")
st.sidebar.markdown("**Instituto Água e Terra — Paraná**")
st.sidebar.markdown("---")

pagina = st.sidebar.radio(
    "Navegação",
    ["🏠 Home", "🗺️ Mapa", "📊 Análise"],
    label_visibility="collapsed"
)

if df.empty:
    st.warning("O conjunto de dados não foi carregado corretamente.")
    st.stop()

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎛️ Filtros")

ano_min = int(df['ano'].dropna().min()) if not df['ano'].dropna().empty else 2000
ano_max = int(df['ano'].dropna().max()) if not df['ano'].dropna().empty else 2030
filtro_ano = st.sidebar.slider("Período", ano_min, ano_max, (ano_min, ano_max), format="%d")

_status_unicos = sorted(df['status'].dropna().unique().tolist())
opcoes_status  = ["Todos"] + _status_unicos
filtro_status  = st.sidebar.radio("Status", opcoes_status, index=0)

_vals = df['valor_conveniado'].dropna()
if len(_vals) > 0 and math.isfinite(float(_vals.min())) and math.isfinite(float(_vals.max())):
    _vmin = int(_vals.min())
    _vmax = int(_vals.max())
    if _vmin >= _vmax:
        _vmax = _vmin + 1
    filtro_valor = st.sidebar.slider(
        "Valor Conveniado (R$)",
        _vmin, _vmax, (_vmin, _vmax),
        step=max(1, (_vmax - _vmin) // 100),
        format="R$ %d"
    )
else:
    filtro_valor = (0, 9_999_999_999)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🗺️ Opções do Mapa")
mostrar_cluster = st.sidebar.checkbox("Clusterização", value=False)
mostrar_heatmap = st.sidebar.checkbox("Mapa de Calor",  value=False)

# ============================================
# 8. FILTRAGEM
# ============================================
df_filtrado = df[
    df['ano'].between(filtro_ano[0], filtro_ano[1], inclusive='both') | df['ano'].isna()
].copy()

df_filtrado = df_filtrado[
    df_filtrado['valor_conveniado'].between(filtro_valor[0], filtro_valor[1], inclusive='both') |
    df_filtrado['valor_conveniado'].isna()
]

if filtro_status != "Todos":
    df_filtrado = df_filtrado[df_filtrado['status'] == filtro_status]

df_filtrado = df_filtrado.reset_index(drop=True)

# ============================================
# 9. HOME
# ============================================
if pagina == "🏠 Home":

    st.title("🌳 Parques Urbanos do Paraná")
    st.markdown("##### Monitoramento e Análise de Investimentos em Áreas Verdes")
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    df_home_conv = df.dropna(subset=['valor_conveniado'])
    df_home_exec = df.dropna(subset=['valor_executado'])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Parques Cadastrados",   f"{len(df):,}".replace(",", "."))
    c2.metric("Total Conveniado",      formatar_reais(df_home_conv['valor_conveniado'].sum()))
    c3.metric("Total Executado",       formatar_reais(df_home_exec['valor_executado'].sum()))
    c4.metric("Municípios Atendidos",  df['município'].nunique())

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
        - Analisar a **distribuição espacial** dos parques no Paraná
        - Identificar **padrões temporais** de investimento público
        - Avaliar **desigualdades regionais** no acesso a áreas verdes
        - Apoiar estudos em **planejamento urbano e ambiental**
        """)

    with col_b:
        st.markdown("### 🧠 Metodologia")
        st.markdown("""
        - Integração de dados tabulares de convênios públicos
        - Georreferenciamento dos parques por coordenadas geográficas
        - Análise espacial exploratória com SIG Web (Folium)
        - Visualização interativa de indicadores com Plotly
        """)
        st.markdown("### ⚠️ Limitações")
        st.markdown("""
        - Parcela dos parques ainda sem coordenadas cadastradas
        - Qualidade dos dados dependente da base original do IAT
        - Análises têm caráter **exploratório**, não normativo
        - Valores conveniados e executados podem diferir por aditivos
        """)

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    st.markdown("### 🟢 Legenda de Status")
    col_l1, col_l2, col_l3, _ = st.columns([1, 1.2, 0.8, 3])
    col_l1.markdown(
        '<span style="background:#27ae60;color:white;padding:4px 14px;border-radius:20px;font-size:0.82rem;font-weight:700;">✔ Concluído</span>',
        unsafe_allow_html=True)
    col_l2.markdown(
        '<span style="background:#f39c12;color:white;padding:4px 14px;border-radius:20px;font-size:0.82rem;font-weight:700;">⏳ Em Andamento</span>',
        unsafe_allow_html=True)
    col_l3.markdown(
        '<span style="background:#95a5a6;color:white;padding:4px 14px;border-radius:20px;font-size:0.82rem;font-weight:700;">— Outros</span>',
        unsafe_allow_html=True)

# ============================================
# 10. MAPA
# ============================================
elif pagina == "🗺️ Mapa":

    st.title("🗺️ Distribuição Espacial dos Parques")

    df_mv = df_filtrado.dropna(subset=['valor_conveniado'])
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Parques no Filtro",   len(df_filtrado))
    m2.metric("Com Coordenadas",     df_filtrado.dropna(subset=['lat', 'lon']).shape[0])
    m3.metric("Total Conveniado",    formatar_reais(df_mv['valor_conveniado'].sum()) if len(df_mv) else "—")
    m4.metric("Municípios",          df_filtrado['município'].nunique())

    st.markdown("---")

    mapa = folium.Map(location=[-24.5, -51.5], zoom_start=7, tiles=None)

    folium.TileLayer('OpenStreetMap', name='Ruas (OSM)').add_to(mapa)

    
    folium.GeoJson(
        gdf,
        style_function=lambda x: {
            'fillColor': '#2e5c3e',
            'color':     '#4a8c5c',
            'weight':     0.6,
            'fillOpacity': 0.05
        },
        name='Municípios'
    ).add_to(mapa)

    vmin = df_filtrado['valor_conveniado'].min()
    vmax = df_filtrado['valor_conveniado'].max()

    layer = MarkerCluster(name="Parques (cluster)").add_to(mapa) if mostrar_cluster else mapa

    for _, row in df_filtrado.iterrows():
        lat, lon = row['lat'], row['lon']
        if pd.isna(lat) or pd.isna(lon):
            continue

        raio = escala_raio(row['valor_conveniado'], vmin, vmax)
        cor  = cor_status(row['status'])

        nome_tt = str(row.get('nome oficial do parque', ''))
        if str_vazia(nome_tt):
            nome_tt = str(row.get('município', ''))

        folium.CircleMarker(
            location=[lat, lon],
            radius=raio,
            color=cor,
            fill=True,
            fill_color=cor,
            fill_opacity=0.75,
            weight=1.5,
            popup=criar_popup_minimo(row),
            tooltip=f"<b>{nome_tt}</b><br><small style='color:#aaa;'>clique para detalhes</small>"
        ).add_to(layer)

    if mostrar_heatmap:
        heat_data = df_filtrado[['lat', 'lon', 'valor_conveniado']].dropna().values.tolist()
        HeatMap(
            heat_data,
            name="Mapa de Calor",
            radius=18, blur=14, min_opacity=0.4,
            gradient={0.3: '#74c69d', 0.6: '#f39c12', 1.0: '#c0392b'}
        ).add_to(mapa)

    folium.LayerControl(collapsed=False).add_to(mapa)

    mapa_retorno = st_folium(
        mapa,
        width="100%",
        height=580,
        returned_objects=["last_object_clicked"]
    )

    st.markdown("""
    <div style="display:flex;flex-wrap:wrap;gap:18px;margin-top:8px;font-size:0.82rem;color:#666;">
        <span>⬤ <span style="color:#27ae60;font-weight:600;">Concluído</span></span>
        <span>⬤ <span style="color:#f39c12;font-weight:600;">Em Andamento</span></span>
        <span>⬤ <span style="color:#95a5a6;font-weight:600;">Outros / Não preenchido</span></span>
        <span style="margin-left:8px;color:#aaa;">⊙ Tamanho proporcional ao valor conveniado</span>
    </div>
    """, unsafe_allow_html=True)

    # ----------------------------------------
    # PAINEL DE DETALHES
    # ----------------------------------------
    st.markdown("---")

    clique = mapa_retorno.get("last_object_clicked") if mapa_retorno else None
    if clique and clique.get("lat") and clique.get("lng"):
        st.session_state["parque_lat"] = clique["lat"]
        st.session_state["parque_lon"] = clique["lng"]

    parque_lat = st.session_state.get("parque_lat")
    parque_lon = st.session_state.get("parque_lon")
    parque = buscar_parque_por_coords(df_filtrado, parque_lat, parque_lon) \
             if (parque_lat and parque_lon) else None

    if parque is None:
        st.markdown("""
        <div class="hint-box">
            🖱️ <strong>Clique em um marcador no mapa</strong> para ver as informações
            detalhadas do parque aqui abaixo.
        </div>
        """, unsafe_allow_html=True)
    else:
        nome      = str(parque.get('nome oficial do parque', ''))
        municipio = str(parque.get('município', '—'))
        status    = str(parque.get('status', ''))
        ano       = parque.get('ano', None)
        v_conv    = parque.get('valor_conveniado', None)
        v_exec    = parque.get('valor_executado', None)
        area      = parque.get('area_m2', None)
        hab       = parque.get('habitantes', None)
        endereco  = str(parque.get('endereço', ''))
        maps_url  = str(parque.get('maps', ''))

        nome_display    = nome if not str_vazia(nome) else municipio
        status_display  = status if not str_vazia(status) else 'Não preenchido'
        cor             = cor_status(status)
        img_url         = f"{url_imagens}{municipio.strip().replace(' ', '%20')}.png"

        ano_display  = int(ano) if pd.notna(ano) else "—"
        conv_display = formatar_reais(v_conv) if pd.notna(v_conv) else "—"
        exec_display = formatar_reais(v_exec) if pd.notna(v_exec) else "Não executado"
        area_display = formatar_area(area)
        hab_display  = formatar_habitantes(hab)
        end_display  = endereco if not str_vazia(endereco) else "—"

        if pd.notna(v_conv) and pd.notna(v_exec):
            diff = v_exec - v_conv
            sinal = "+" if diff >= 0 else ""
            diff_display = f"{sinal}{formatar_reais(diff)}"
            diff_color = "#27ae60" if diff >= 0 else "#e74c3c"
        else:
            diff_display = None

        maps_link = (
            f'<a href="{maps_url}" target="_blank" '
            f'style="color:#27ae60;font-weight:600;text-decoration:none;">'
            f'🗺️ Abrir no Google Maps ↗</a>'
            if not str_vazia(maps_url) else
            f"{parque_lat:.5f}, {parque_lon:.5f}"
        )

        col_img, col_info = st.columns([1, 2.4])

        with col_img:
            # Fallback seguro via CSS Background
            st.markdown(f"""
            <div style="border-radius:12px;overflow:hidden;
                        box-shadow:0 4px 14px rgba(0,0,0,0.10);
                        height:290px;
                        background-image:url('{url_fallback}');
                        background-size:cover;background-position:center;background-color:#e8f0eb;">
                <img src="{img_url}"
                     style="width:100%;height:100%;object-fit:cover;color:transparent;"
                     alt=""
                     onerror="this.style.display='none';">
            </div>
            """, unsafe_allow_html=True)

        with col_info:
            # HTML formatado em uma linha para evitar erro de código no Markdown
            diff_row = (
                f'<div class="detail-row">'
                f'<span class="detail-label">📊 Diferença Conv/Exec</span>'
                f'<span class="detail-value" style="color:{diff_color};font-weight:700;">{diff_display}</span>'
                f'</div>'
            ) if diff_display else ""

            st.markdown(f"""
            <div class="park-card">
                <div class="park-card-header">
                    <div style="font-size:1.1rem;font-weight:700;color:white;margin-bottom:7px;line-height:1.3;">
                        {nome_display}
                    </div>
                    <span class="badge-status" style="background:{cor};color:white;">
                        {status_display}
                    </span>
                </div>
                <div class="park-card-body">
                    <div class="detail-row">
                        <span class="detail-label">🏙️ Município</span>
                        <span class="detail-value">{municipio}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">📅 Ano do Convênio</span>
                        <span class="detail-value">{ano_display}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">💰 Valor Conveniado</span>
                        <span class="detail-value" style="color:#1e3d2f;font-weight:700;font-size:0.95rem;">{conv_display}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">✅ Valor Executado</span>
                        <span class="detail-value" style="font-weight:700;">{exec_display}</span>
                    </div>
{diff_row}
                    <div class="detail-row">
                        <span class="detail-label">📐 Área</span>
                        <span class="detail-value">{area_display}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">👥 Habitantes</span>
                        <span class="detail-value">{hab_display}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">📫 Endereço</span>
                        <span class="detail-value">{end_display}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">📍 Localização</span>
                        <span class="detail-value">{maps_link}</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

# ============================================
# 11. ANÁLISE
# ============================================
elif pagina == "📊 Análise":

    st.title("📊 Análise Estatística")

    df_valid = df_filtrado.dropna(subset=['valor_conveniado', 'ano'])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Conveniado",    formatar_reais(df_valid['valor_conveniado'].sum()) if len(df_valid) else "—")
    c2.metric("Número de Parques",   len(df_filtrado))
    c3.metric("Média por Parque",    formatar_reais(df_valid['valor_conveniado'].mean()) if len(df_valid) else "—")
    c4.metric("Maior Convênio",      formatar_reais(df_valid['valor_conveniado'].max())  if len(df_valid) else "—")

    st.markdown("---")

    col_a, col_b = st.columns([2, 1])

    with col_a:
        inv_ano = df_valid.groupby('ano')['valor_conveniado'].sum().reset_index()
        fig_bar = px.bar(
            inv_ano, x='ano', y='valor_conveniado',
            title="Valor Conveniado por Ano",
            color='valor_conveniado',
            color_continuous_scale=[[0, '#74c69d'], [0.5, '#2e5c3e'], [1, '#1e3d2f']],
            labels={'valor_conveniado': 'Valor Conveniado (R$)', 'ano': 'Ano'}
        )
        fig_bar.update_layout(
            plot_bgcolor='white', paper_bgcolor='white',
            coloraxis_showscale=False,
            font=dict(family='Segoe UI', size=12),
            title_font_size=15, margin=dict(t=40, b=30)
        )
        fig_bar.update_traces(marker_line_width=0)
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_b:
        status_plot = df_filtrado['status'].fillna('Não preenchido')
        status_count = status_plot.value_counts().reset_index()
        status_count.columns = ['status', 'quantidade']

        fig_pie = px.pie(
            status_count, names='status', values='quantidade',
            title="Distribuição por Status",
            color='status',
            color_discrete_map={s: cor_status(s) for s in status_count['status']},
            hole=0.45
        )
        fig_pie.update_layout(
            plot_bgcolor='white', paper_bgcolor='white',
            font=dict(family='Segoe UI', size=11),
            title_font_size=15,
            legend=dict(orientation='h', yanchor='bottom', y=-0.3),
            margin=dict(t=40, b=10)
        )
        fig_pie.update_traces(textinfo='percent+label', showlegend=False)
        st.plotly_chart(fig_pie, use_container_width=True)

    col_c, col_d = st.columns(2)

    with col_c:
        df_comp = df_filtrado.dropna(subset=['ano'])
        g_conv = df_comp.groupby('ano')['valor_conveniado'].sum().reset_index()
        g_exec = df_comp.groupby('ano')['valor_executado'].sum().reset_index()
        g_comp = g_conv.merge(g_exec, on='ano', how='left')

        fig_comp = px.bar(
            g_comp.melt(id_vars='ano',
                        value_vars=['valor_conveniado', 'valor_executado'],
                        var_name='tipo', value_name='valor'),
            x='ano', y='valor', color='tipo', barmode='group',
            title="Conveniado vs Executado por Ano",
            color_discrete_map={
                'valor_conveniado': '#2e5c3e',
                'valor_executado':  '#74c69d'
            },
            labels={'valor': 'R$', 'ano': 'Ano', 'tipo': ''}
        )
        fig_comp.update_layout(
            plot_bgcolor='white', paper_bgcolor='white',
            font=dict(family='Segoe UI', size=11),
            title_font_size=15, margin=dict(t=40, b=30),
            legend=dict(orientation='h', yanchor='bottom', y=-0.25)
        )
        fig_comp.update_traces(marker_line_width=0)
        newnames = {'valor_conveniado': 'Conveniado', 'valor_executado': 'Executado'}
        fig_comp.for_each_trace(lambda t: t.update(name=newnames.get(t.name, t.name)))
        st.plotly_chart(fig_comp, use_container_width=True)

    with col_d:
        top_municipios = (
            df_valid.groupby('município')['valor_conveniado']
            .sum().sort_values(ascending=True).tail(12).reset_index()
        )
        fig_h = px.bar(
            top_municipios, x='valor_conveniado', y='município', orientation='h',
            title="Top 12 Municípios por Valor Conveniado",
            color='valor_conveniado',
            color_continuous_scale=[[0, '#a8d5a2'], [1, '#1e3d2f']],
            labels={'valor_conveniado': 'R$', 'município': ''}
        )
        fig_h.update_layout(
            plot_bgcolor='white', paper_bgcolor='white',
            coloraxis_showscale=False,
            font=dict(family='Segoe UI', size=11),
            title_font_size=15, margin=dict(t=40, b=30)
        )
        fig_h.update_traces(marker_line_width=0)
        st.plotly_chart(fig_h, use_container_width=True)

    col_e, col_f = st.columns(2)

    with col_e:
        fig_hist = px.histogram(
            df_valid, x='valor_conveniado', nbins=20,
            title="Distribuição dos Valores Conveniados",
            color_discrete_sequence=['#2e5c3e'],
            labels={'valor_conveniado': 'Valor Conveniado (R$)', 'count': 'Quantidade'}
        )
        fig_hist.update_layout(
            plot_bgcolor='white', paper_bgcolor='white',
            font=dict(family='Segoe UI', size=11),
            title_font_size=15, bargap=0.08, margin=dict(t=40, b=30)
        )
        st.plotly_chart(fig_hist, use_container_width=True)

    with col_f:
        inv_acum = inv_ano.copy()
        inv_acum['acumulado'] = inv_acum['valor_conveniado'].cumsum()
        fig_line = px.line(
            inv_acum, x='ano', y='acumulado',
            title="Valor Conveniado Acumulado",
            markers=True,
            color_discrete_sequence=['#27ae60'],
            labels={'acumulado': 'Valor Acumulado (R$)', 'ano': 'Ano'}
        )
        fig_line.update_traces(line_width=2.5, marker_size=7)
        fig_line.update_layout(
            plot_bgcolor='white', paper_bgcolor='white',
            font=dict(family='Segoe UI', size=11),
            title_font_size=15, margin=dict(t=40, b=30)
        )
        st.plotly_chart(fig_line, use_container_width=True)

    col_g, col_h = st.columns(2)

    with col_g:
        parques_municipio = (
            df_filtrado.groupby('município').size()
            .sort_values(ascending=False).head(10)
            .reset_index(name='quantidade')
        )
        fig_pc = px.bar(
            parques_municipio, x='município', y='quantidade',
            title="Top 10 Municípios por Nº de Parques",
            color='quantidade',
            color_continuous_scale=[[0, '#a8d5a2'], [1, '#1e3d2f']],
            labels={'quantidade': 'Nº de Parques', 'município': ''}
        )
        fig_pc.update_layout(
            plot_bgcolor='white', paper_bgcolor='white',
            coloraxis_showscale=False,
            font=dict(family='Segoe UI', size=11),
            title_font_size=15, xaxis_tickangle=-35, margin=dict(t=40, b=60)
        )
        fig_pc.update_traces(marker_line_width=0)
        st.plotly_chart(fig_pc, use_container_width=True)

    with col_h:
        df_vph = df_filtrado.dropna(subset=['valor_conveniado', 'habitantes']).copy()
        if len(df_vph) > 0:
            df_vph['valor_por_hab'] = df_vph['valor_conveniado'] / df_vph['habitantes']
            top_vph = df_vph.nlargest(12, 'valor_por_hab')[['município', 'valor_por_hab']].sort_values('valor_por_hab')
            fig_vph = px.bar(
                top_vph, x='valor_por_hab', y='município', orientation='h',
                title="Valor Conveniado por Habitante (Top 12)",
                color='valor_por_hab',
                color_continuous_scale=[[0, '#a8d5a2'], [1, '#1e3d2f']],
                labels={'valor_por_hab': 'R$ / Hab.', 'município': ''}
            )
            fig_vph.update_layout(
                plot_bgcolor='white', paper_bgcolor='white',
                coloraxis_showscale=False,
                font=dict(family='Segoe UI', size=11),
                title_font_size=15, margin=dict(t=40, b=30)
            )
            fig_vph.update_traces(marker_line_width=0)
            st.plotly_chart(fig_vph, use_container_width=True)

    # --- Tabela detalhada ---
    st.markdown("---")
    st.markdown("### 📋 Tabela de Parques")

    cols_map = {
        'nome oficial do parque': 'Nome',
        'município':              'Município',
        'status':                 'Status',
        'ano':                    'Ano',
        'valor_conveniado':       'Valor Conveniado',
        'valor_executado':        'Valor Executado',
        'area_m2':                'Área (m²)',
        'habitantes':             'Habitantes',
    }
    cols_validas = [c for c in cols_map if c in df_filtrado.columns]
    df_tabela = df_filtrado[cols_validas].copy().rename(columns=cols_map)

    for col in ['Valor Conveniado', 'Valor Executado']:
        if col in df_tabela.columns:
            df_tabela[col] = df_tabela[col].apply(
                lambda x: formatar_reais(x) if pd.notna(x) else "—"
            )
    if 'Área (m²)' in df_tabela.columns:
        df_tabela['Área (m²)'] = df_tabela['Área (m²)'].apply(
            lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if pd.notna(x) else "—"
        )
    if 'Habitantes' in df_tabela.columns:
        df_tabela['Habitantes'] = df_tabela['Habitantes'].apply(
            lambda x: f"{int(x):,}".replace(",", ".") if pd.notna(x) else "—"
        )
    if 'Ano' in df_tabela.columns:
        df_tabela['Ano'] = df_tabela['Ano'].apply(
            lambda x: int(x) if pd.notna(x) else "—"
        )
    if 'Status' in df_tabela.columns:
        df_tabela['Status'] = df_tabela['Status'].fillna('—')

    st.dataframe(df_tabela.reset_index(drop=True), use_container_width=True, height=360)
