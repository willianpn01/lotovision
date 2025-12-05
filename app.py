"""
LotoVision v2.0 - Análise Estatística de Loterias
Suporta: Mega Sena, Quina, Lotofácil

Ferramenta educacional para compreensão de padrões em jogos de loteria
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import sys
from pathlib import Path

# Adiciona diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

from modules.game_config import GameConfig, GAMES, GAMES_LIST, MEGA_SENA, QUINA, LOTOFACIL
from modules.data_loader_v2 import get_date_range, filter_by_date_range
from modules.analytics_v2 import (
    get_kpis, get_frequency_analysis, get_full_frequency, get_heatmap_data,
    get_heatmap_labels, get_parity_distribution, get_delay_analysis, 
    get_frequent_pairs, get_frequent_trios, get_temporal_trend, 
    get_sum_analysis, classify_numbers, compare_game
)
from modules.statistics_v2 import (
    chi_square_test, sum_normality_test, monte_carlo_simulation,
    get_statistical_summary
)
from modules.generator_v2 import quick_generate, format_game_display
from modules.api_loader import fetch_latest_result, get_data_freshness, sync_with_api
from modules.json_loader import load_game_from_json, get_json_stats
from utils.export import export_games_excel, format_games_text, export_to_pdf

# ============================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================
st.set_page_config(
    page_title="LotoVision - Análise de Loterias",
    page_icon="🎰",
    layout="wide",
    initial_sidebar_state="auto"  # Auto-collapse on mobile
)

# ============================================
# CSS PERSONALIZADO
# ============================================
st.markdown("""
<style>
    /* Mobile-first responsive design */
    .main-header {
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 15px;
        color: white;
        text-align: center;
    }
    
    .mega-sena-header { background: linear-gradient(135deg, #209869 0%, #1a7a54 100%); }
    .quina-header { background: linear-gradient(135deg, #260085 0%, #1a005c 100%); }
    .lotofacil-header { background: linear-gradient(135deg, #930089 0%, #6b0064 100%); }
    
    .kpi-card {
        background: #1E2130;
        padding: 15px;
        border-radius: 10px;
        border-left: 4px solid #6C63FF;
        margin-bottom: 10px;
    }
    
    .disclaimer-box {
        background: #2D1F1F;
        border: 1px solid #FF4444;
        padding: 12px;
        border-radius: 8px;
        margin: 15px 0;
    }
    
    .game-card {
        background: #1E2130;
        padding: 12px;
        border-radius: 10px;
        margin: 8px 0;
        border: 1px solid #333;
    }
    
    .number-ball {
        display: inline-block;
        width: 32px;
        height: 32px;
        border-radius: 50%;
        color: white;
        text-align: center;
        line-height: 32px;
        font-weight: bold;
        margin: 2px;
        font-size: 13px;
    }
    
    .ball-mega { background: linear-gradient(135deg, #209869 0%, #1a7a54 100%); }
    .ball-quina { background: linear-gradient(135deg, #260085 0%, #1a005c 100%); }
    .ball-lotofacil { background: linear-gradient(135deg, #930089 0%, #6b0064 100%); }
    
    .game-tab {
        padding: 8px 15px;
        border-radius: 8px;
        margin: 2px;
    }
    
    /* Mobile menu hint - subtle text */
    .mobile-menu-hint {
        display: none;
        color: #FAEF2D;
        font-size: 13px;
        text-align: center;
        padding: 8px;
        margin-bottom: 10px;
    }
    
    /* Mobile optimizations */
    @media (max-width: 768px) {
        .mobile-menu-hint {
            display: block;
        }
        .main-header {
            padding: 10px;
            margin-bottom: 10px;
        }
        .main-header h1 {
            font-size: 1.4rem !important;
        }
        .kpi-card {
            padding: 10px;
        }
        .number-ball {
            width: 28px;
            height: 28px;
            line-height: 28px;
            font-size: 12px;
            margin: 1px;
        }
        .game-card {
            padding: 10px;
            margin: 5px 0;
        }
        /* Reduce sidebar width on mobile */
        section[data-testid="stSidebar"] {
            width: 280px !important;
        }
        /* Better touch targets */
        button {
            min-height: 44px !important;
        }
        /* Compact tables */
        .stDataFrame {
            font-size: 12px !important;
        }
    }
    
    /* Tablet */
    @media (min-width: 769px) and (max-width: 1024px) {
        .number-ball {
            width: 30px;
            height: 30px;
            line-height: 30px;
            font-size: 13px;
        }
    }
</style>
""", unsafe_allow_html=True)


# ============================================
# SESSION STATE
# ============================================
def init_session_state():
    """Inicializa variáveis de sessão"""
    for game in GAMES_LIST:
        key_df = f'{game.slug}_df'
        key_melted = f'{game.slug}_df_melted'
        key_loaded = f'{game.slug}_loaded'
        key_games = f'{game.slug}_generated_games'
        
        if key_df not in st.session_state:
            st.session_state[key_df] = None
        if key_melted not in st.session_state:
            st.session_state[key_melted] = None
        if key_loaded not in st.session_state:
            st.session_state[key_loaded] = False
        if key_games not in st.session_state:
            st.session_state[key_games] = []
    
    if 'first_visit' not in st.session_state:
        st.session_state.first_visit = True
    if 'selected_game' not in st.session_state:
        st.session_state.selected_game = 'mega_sena'

init_session_state()


# ============================================
# MODAL DE BOAS-VINDAS
# ============================================
def show_welcome_modal():
    """Mostra modal de boas-vindas apenas na primeira visita"""
    # Verifica se já aceitou (via query param persistente)
    params = st.query_params
    already_accepted = params.get("accepted") == "1"
    
    if already_accepted:
        st.session_state.first_visit = False
        return
    
    if st.session_state.first_visit:
        with st.expander("👋 Bem-vindo ao LotoVision!", expanded=True):
            st.markdown("""
            ### Ferramenta de análise estatística para loterias brasileiras
            
            **Jogos suportados:**
            - 🎰 **Mega Sena** - 6 dezenas de 1 a 60
            - ⭐ **Quina** - 5 dezenas de 1 a 80
            - 🍀 **Lotofácil** - 15 dezenas de 1 a 25
            
            ---
            
            🎲 **Cada sorteio é INDEPENDENTE e ALEATÓRIO**
            
            **Use para:** ✅ Aprender estatística | ✅ Visualizar dados | ✅ Entender probabilidades
            
            **Não use para:** ❌ "Garantir" vitórias | ❌ Fazer apostas irresponsáveis
            """)
            
            if st.button("✅ Li e Concordo", type="primary", key="welcome_btn"):
                st.session_state.first_visit = False
                st.query_params["accepted"] = "1"  # Persiste na URL
                st.rerun()


# ============================================
# SIDEBAR COM SELEÇÃO DE JOGO
# ============================================
def render_sidebar():
    """Renderiza sidebar com seleção de jogo e upload"""
    with st.sidebar:
        st.markdown("## 🎰 LotoVision")
        st.markdown("---")
        
        # Seleção do jogo
        st.markdown("### 🎮 Selecionar Jogo")
        
        game_options = {g.slug: f"{g.icon} {g.name}" for g in GAMES_LIST}
        selected = st.radio(
            "Escolha o jogo",
            options=list(game_options.keys()),
            format_func=lambda x: game_options[x],
            key="game_selector",
            label_visibility="collapsed"
        )
        st.session_state.selected_game = selected
        
        game_config = GAMES[selected]
        
        # Carrega dados automaticamente se ainda não carregou
        if not st.session_state.get(f'{selected}_loaded', False):
            df, df_melted, status = load_game_from_json(selected)
            if df is not None:
                st.session_state[f'{selected}_df'] = df
                st.session_state[f'{selected}_df_melted'] = df_melted
                st.session_state[f'{selected}_loaded'] = True
        
        st.markdown("---")
        
        # Status dos dados
        st.markdown(f"### 📁 {game_config.name}")
        json_stats = get_json_stats(selected)
        if json_stats['total'] > 0:
            st.success(f"✅ {json_stats['total']:,} concursos")
            st.caption(f"#{json_stats['primeiro']} a #{json_stats['ultimo']}")
        else:
            st.warning("Nenhum dado disponível")
        
        # Sincronização com API
        st.markdown("---")
        st.markdown("### 🌐 Sincronizar")
        freshness = get_data_freshness(selected)
        st.caption(freshness)
        
        if st.button("⬇️ Atualizar da Caixa", key=f"sync_{selected}", width="stretch"):
            novos, msg = sync_with_api(selected)
            if novos > 0:
                st.success(msg)
                # Recarrega dados
                df, df_melted, _ = load_game_from_json(selected)
                if df is not None:
                    st.session_state[f'{selected}_df'] = df
                    st.session_state[f'{selected}_df_melted'] = df_melted
                    st.session_state[f'{selected}_loaded'] = True
                st.rerun()
            else:
                st.info(msg)
        
        # Status dos dados
        if st.session_state[f'{selected}_loaded'] and st.session_state[f'{selected}_df'] is not None:
            n_concursos = len(st.session_state[f'{selected}_df'])
            st.success(f"✅ {n_concursos:,} concursos")
            
            # Filtro temporal
            st.markdown("---")
            st.markdown("### 📅 Período")
            
            df = st.session_state[f'{selected}_df']
            min_date, max_date = get_date_range(df)
            
            if min_date and max_date:
                date_range = st.slider(
                    "Filtrar por data",
                    min_value=min_date.to_pydatetime(),
                    max_value=max_date.to_pydatetime(),
                    value=(min_date.to_pydatetime(), max_date.to_pydatetime()),
                    format="DD/MM/YYYY",
                    key=f"date_{selected}"
                )
                st.session_state[f'{selected}_date_filter'] = date_range
        
        # Info do jogo
        st.markdown("---")
        st.markdown("### ℹ️ Informações")
        st.markdown(f"""
        **{game_config.name}**
        - Dezenas: {game_config.n_balls}
        - Range: 1 a {game_config.max_number}
        - Combinações: {game_config.total_combinations:,}
        """)


# ============================================
# HEADER COM KPIs
# ============================================
def render_header(df: pd.DataFrame, game_config: GameConfig):
    """Renderiza header com KPIs do jogo"""
    kpis = get_kpis(df, game_config)
    
    if not kpis:
        return
    
    header_class = f"{game_config.slug.replace('_', '-')}-header"
    
    dezenas_str = ' - '.join([f'{d:02d}' for d in kpis['ultimo_dezenas']])
    
    st.markdown(f"""
    <div class="main-header {header_class}">
        <h2>{game_config.icon} {game_config.name}</h2>
        <h3>Último Sorteio: #{kpis['ultimo_concurso']} | {kpis['ultimo_data']}</h3>
        <p style="font-size: 1.2em; font-weight: bold;">{dezenas_str}</p>
        <p>Total: {kpis['total_concursos']:,} concursos | Período: {kpis['periodo']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Concursos", f"{kpis['total_concursos']:,}")
    with col2:
        soma_media = df['Soma'].mean() if 'Soma' in df.columns else 0
        st.metric("Soma Média", f"{soma_media:.0f}")
    with col3:
        pares_media = df['Pares'].mean() if 'Pares' in df.columns else 0
        st.metric("Pares Médios", f"{pares_media:.1f}")
    with col4:
        prob = f"1:{game_config.total_combinations:,}"
        st.metric("Probabilidade", prob)


# ============================================
# GRÁFICOS DE FREQUÊNCIA
# ============================================
def render_frequency_charts(df_melted: pd.DataFrame, game_config: GameConfig):
    """Renderiza gráficos de frequência"""
    st.markdown("### 📊 Frequência de Dezenas")
    st.caption("Top 10 dezenas mais e menos sorteadas no período selecionado.")
    
    top_mais, top_menos = get_frequency_analysis(df_melted)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🔥 Mais Sorteadas")
        if not top_mais.empty:
            fig = px.bar(
                top_mais,
                x='Frequencia',
                y='Dezena',
                orientation='h',
                color='Frequencia',
                color_continuous_scale=['#FFAA00', game_config.color_primary],
                text='Frequencia'
            )
            fig.update_traces(textposition='outside')
            fig.update_layout(
                height=400,
                showlegend=False,
                yaxis={'categoryorder': 'total ascending'}
            )
            st.plotly_chart(fig, width="stretch")
    
    with col2:
        st.markdown("#### ❄️ Menos Sorteadas")
        if not top_menos.empty:
            fig = px.bar(
                top_menos,
                x='Frequencia',
                y='Dezena',
                orientation='h',
                color='Frequencia',
                color_continuous_scale=['#4444FF', '#88CCFF'],
                text='Frequencia'
            )
            fig.update_traces(textposition='outside')
            fig.update_layout(
                height=400,
                showlegend=False,
                yaxis={'categoryorder': 'total descending'}
            )
            st.plotly_chart(fig, width="stretch")


# ============================================
# HEATMAP DO VOLANTE
# ============================================
def render_heatmap(df_melted: pd.DataFrame, game_config: GameConfig):
    """Renderiza heatmap do volante"""
    st.markdown("### 🔥 Heatmap do Volante")
    st.caption("Visualização da frequência de cada dezena no formato do volante oficial.")
    
    heatmap_data = get_heatmap_data(df_melted, game_config)
    labels = get_heatmap_labels(game_config)
    
    # Texto para hover
    rows, cols = heatmap_data.shape
    text_labels = [[f"Dezena {labels[i,j]:02d}<br>Frequência: {int(heatmap_data[i,j])}" 
                    for j in range(cols)] for i in range(rows)]
    
    fig = go.Figure(data=go.Heatmap(
        z=heatmap_data,
        text=labels,
        texttemplate="%{text}",
        textfont={"size": 11, "color": "white"},
        customdata=text_labels,
        hovertemplate="%{customdata}<extra></extra>",
        colorscale=[
            [0, '#4444FF'],
            [0.5, '#FFAA00'],
            [1, game_config.color_primary]
        ],
        showscale=True,
        colorbar=dict(title="Freq")
    ))
    
    fig.update_layout(
        height=max(250, rows * 45),
        xaxis=dict(showticklabels=False, showgrid=False),
        yaxis=dict(showticklabels=False, showgrid=False, autorange="reversed"),
        margin=dict(l=20, r=20, t=20, b=20)
    )
    
    n_concursos = df_melted['Concurso'].nunique()
    st.plotly_chart(fig, width="stretch")
    st.caption(f"Baseado em {n_concursos:,} sorteios")


# ============================================
# DISTRIBUIÇÃO PAR/ÍMPAR
# ============================================
def render_parity_chart(df: pd.DataFrame, game_config: GameConfig):
    """Renderiza gráfico de paridade"""
    st.markdown("### ⚖️ Distribuição Par/Ímpar")
    st.caption("Proporção de números pares e ímpares em cada sorteio.")
    
    parity = get_parity_distribution(df, game_config)
    
    if not parity.empty:
        fig = px.pie(
            parity,
            values='Quantidade',
            names='Label',
            color_discrete_sequence=px.colors.sequential.Viridis,
            hole=0.4
        )
        fig.update_traces(textposition='outside', textinfo='percent+label')
        fig.update_layout(height=400)
        st.plotly_chart(fig, width="stretch")


# ============================================
# ANÁLISE DE ATRASO
# ============================================
def render_delay_analysis(df: pd.DataFrame, df_melted: pd.DataFrame, game_config: GameConfig):
    """Renderiza tabela de atrasos"""
    st.markdown("### ⏱️ Análise de Atraso")
    st.caption("Dezenas há mais tempo sem aparecer. Atraso acima da média não indica maior chance.")
    
    delays = get_delay_analysis(df, df_melted, game_config)
    
    if not delays.empty:
        display_df = delays[['Dezena', 'UltimoConcurso', 'Atraso', 'AtrasoMedio', 'Status']].copy()
        display_df.columns = ['Dezena', 'Último Concurso', 'Atraso', 'Média', 'Status']
        
        def color_status(val):
            if val == 'critico':
                return 'background-color: #FF4444; color: white'
            elif val == 'atencao':
                return 'background-color: #FFAA00; color: black'
            return 'background-color: #00CC66; color: white'
        
        styled_df = display_df.style.map(color_status, subset=['Status'])
        st.dataframe(styled_df, width="stretch")


# ============================================
# PARES FREQUENTES
# ============================================
def render_frequent_pairs(df: pd.DataFrame, game_config: GameConfig):
    """Renderiza pares frequentes"""
    st.markdown("### 🔗 Duplas Frequentes")
    st.caption("Combinações de duas dezenas que mais aparecem juntas nos sorteios.")
    
    pairs = get_frequent_pairs(df, game_config)
    
    if not pairs.empty:
        fig = px.bar(
            pairs,
            x='Frequencia',
            y='Par',
            orientation='h',
            color='Frequencia',
            color_continuous_scale='Purples',
            text='Frequencia'
        )
        fig.update_traces(textposition='outside')
        fig.update_layout(
            height=400,
            showlegend=False,
            yaxis={'categoryorder': 'total ascending'}
        )
        st.plotly_chart(fig, width="stretch")


# ============================================
# TENDÊNCIA TEMPORAL
# ============================================
def render_temporal_trend(df: pd.DataFrame, df_melted: pd.DataFrame, game_config: GameConfig):
    """Renderiza tendência temporal"""
    st.markdown("### 📈 Tendência Temporal")
    
    trend = get_temporal_trend(df, df_melted)
    
    if not trend.empty:
        fig = go.Figure()
        
        for col in trend.columns:
            fig.add_trace(go.Scatter(
                x=trend.index,
                y=trend[col],
                mode='lines+markers',
                name=f'Dezena {col:02d}',
                line=dict(width=2)
            ))
        
        fig.update_layout(
            height=400,
            xaxis_title="Ano",
            yaxis_title="Frequência",
            legend_title="Dezenas",
            hovermode='x unified'
        )
        st.plotly_chart(fig, width="stretch")


# ============================================
# DOCUMENTAÇÃO CURVA NORMAL
# ============================================
def render_normal_curve_docs(game_config: GameConfig):
    """Renderiza documentação da Curva Normal da Soma"""
    
    st.markdown("## 📈 Curva Normal da Soma: Guia Completo")
    
    st.markdown("### 🎯 O que é?")
    st.markdown(f"""
    A **Análise da Curva Normal da Soma** examina o padrão de distribuição das 
    **somas das dezenas** sorteadas em cada jogo da {game_config.name}.
    
    Em termos simples: **somamos os {game_config.n_balls} números de cada sorteio e verificamos 
    se essas somas formam um padrão previsível** (a famosa "curva em forma de sino").
    """)
    
    st.divider()
    
    st.markdown("### 📊 A Curva Normal (Distribuição Gaussiana)")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        **Características:**
        - **μ (Média)**: Centro da curva - valor mais provável
        - **σ (Desvio Padrão)**: Largura da curva - mede a dispersão
        - **Simetria**: Mesma probabilidade de estar acima ou abaixo da média
        """)
    
    with col2:
        st.code("""
        📈
       /  \\
      /    \\
     /      \\
____/        \\____
   μ-σ   μ   μ+σ
        """, language=None)
    
    st.markdown("### 📏 Regra 68-95-99.7")
    st.info("""
    Em uma distribuição normal:
    - **68%** dos dados estão entre μ - 1σ e μ + 1σ
    - **95%** dos dados estão entre μ - 2σ e μ + 2σ
    - **99.7%** dos dados estão entre μ - 3σ e μ + 3σ
    """)
    
    st.divider()
    
    st.markdown(f"### 🔢 Limites Teóricos - {game_config.name}")
    
    # Cálculo dinâmico baseado no jogo
    n = game_config.n_balls
    max_num = game_config.max_number
    soma_min = sum(range(1, n + 1))
    soma_max = sum(range(max_num - n + 1, max_num + 1))
    soma_media = n * (max_num + 1) / 2
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Soma Mínima", f"{soma_min}")
    col2.metric("Soma Média Teórica", f"{soma_media:.0f}")
    col3.metric("Soma Máxima", f"{soma_max}")
    
    with st.expander("**Ver cálculo detalhado**"):
        st.markdown(f"""
        **Soma Mínima**: {' + '.join(str(i) for i in range(1, n+1))} = **{soma_min}**
        
        **Soma Máxima**: {' + '.join(str(i) for i in range(max_num - n + 1, max_num + 1))} = **{soma_max}**
        
        **Soma Média Teórica**: {n} × ({max_num} + 1) / 2 = **{soma_media:.0f}**
        """)
    
    st.divider()
    
    st.markdown("### 🎲 Por que a Soma Segue uma Distribuição Normal?")
    
    with st.expander("**Teorema Central do Limite**"):
        st.markdown("""
        Quando somamos várias variáveis aleatórias independentes, o resultado 
        tende a seguir uma distribuição normal, **independentemente** da distribuição original.
        
        **Aplicação:**
        - Cada número sorteado é uma variável aleatória
        - Somamos eles em cada concurso
        - Repetimos milhares de vezes
        
        **Resultado**: As somas se concentram ao redor da média e formam uma curva em sino.
        """)
    
    st.divider()
    
    st.markdown("### 📊 Zonas de Probabilidade")
    
    st.markdown("""
    | Zona | Frequência Esperada | Interpretação |
    |------|---------------------|---------------|
    | 🟦 Muito Baixa (< μ-2σ) | ~2.5% | Extremamente raro |
    | 🟨 Baixa (μ-2σ a μ-1σ) | ~13.5% | Incomum |
    | 🟩 Normal (μ-1σ a μ+1σ) | ~68% | Comum |
    | 🟨 Alta (μ+1σ a μ+2σ) | ~13.5% | Incomum |
    | 🟦 Muito Alta (> μ+2σ) | ~2.5% | Extremamente raro |
    """)
    
    st.divider()
    
    st.markdown("### ⚠️ Equívocos Comuns")
    
    with st.expander("❌ Mito 1: 'Devo sempre jogar com soma próxima da média'"):
        st.error("""
        **Realidade**: Embora seja a soma mais comum, **não aumenta suas chances de ganhar**. 
        Você apenas está escolhendo dentro do conjunto mais populoso de combinações.
        """)
    
    with st.expander("❌ Mito 2: 'Somas extremas nunca saem'"):
        st.warning("""
        **Realidade**: São raras (~2.5% cada cauda), mas **acontecem**. 
        Em 2.000 sorteios, esperamos ~50 jogos com somas extremas.
        """)
    
    with st.expander("❌ Mito 3: 'Se a última soma foi X, a próxima será próxima'"):
        st.warning("""
        **Realidade**: Cada sorteio é **independente**. 
        A soma anterior não influencia a próxima.
        """)
    
    with st.expander("✅ Verdade: A distribuição é previsível, os resultados não"):
        st.success("""
        A **distribuição geral** (curva) é previsível estatisticamente, 
        mas o **resultado específico** de cada sorteio permanece totalmente aleatório.
        """)
    
    st.divider()
    
    st.markdown("### 🔗 Por que Somas Centrais São Mais Comuns?")
    
    st.markdown("""
    Há **muitas maneiras** de chegar em somas centrais, mas **poucas maneiras** de chegar em somas extremas.
    
    **Analogia com 2 dados:**
    - Há **1 forma** de somar 2 (1+1)
    - Há **6 formas** de somar 7 (1+6, 2+5, 3+4, 4+3, 5+2, 6+1)
    - Há **1 forma** de somar 12 (6+6)
    
    Por isso, somar 7 é mais provável que somar 2 ou 12.
    """)
    
    st.divider()
    
    st.markdown("### ❓ Perguntas Frequentes")
    
    with st.expander("Posso usar isso para escolher meus números?"):
        st.markdown("""
        Você pode **preferir** jogar em determinada zona de soma, mas saiba que isso 
        **não aumenta suas chances de ganhar**. É apenas uma preferência pessoal.
        """)
    
    with st.expander("Se a curva não é perfeita, há fraude?"):
        st.markdown("""
        **Não necessariamente.** Pequenos desvios são normais, especialmente com amostras menores. 
        Use testes estatísticos (como o Chi-Quadrado) para verificar.
        """)
    
    with st.expander("Qual é a soma mais 'sortuda'?"):
        st.markdown("""
        **Não existe.** A soma mais **frequente** é a média, mas cada combinação específica 
        tem a mesma probabilidade de sair.
        """)
    
    st.caption("📖 Leitura adicional: Khan Academy (Normal Distribution), StatQuest, 3Blue1Brown")


# ============================================
# DOCUMENTAÇÃO CHI-QUADRADO
# ============================================
def render_chi_square_docs():
    """Renderiza documentação do teste Chi-Quadrado"""
    
    st.markdown("## 📊 Teste Chi-Quadrado (χ²): Guia Completo")
    
    st.markdown("### 🎯 O que é?")
    st.markdown("""
    O **Teste Chi-Quadrado** (pronuncia-se "qui-quadrado") é um teste estatístico que verifica 
    se existe uma diferença significativa entre frequências observadas e frequências esperadas.
    
    Em termos simples: ele responde à pergunta **"Esses dados são diferentes do que esperaríamos por acaso?"**
    """)
    
    st.divider()
    
    st.markdown("### 🎲 Aplicação nas Loterias")
    st.markdown("""
    Em uma loteria verdadeiramente aleatória, esperamos que:
    - Todos os números tenham a **mesma chance** de serem sorteados
    - Ao longo de muitos sorteios, todos os números devem aparecer **aproximadamente a mesma quantidade de vezes**
    
    **Pergunta que o teste responde:**
    > "A frequência com que cada número foi sorteado está dentro do esperado para um processo aleatório?"
    """)
    
    st.divider()
    
    st.markdown("### 📐 Como Funciona?")
    
    with st.expander("**Passo 1: Coletar Frequências Observadas**"):
        st.markdown("""
        Contamos quantas vezes cada número foi sorteado ao longo de todos os concursos.
        
        **Exemplo** (dados hipotéticos de 1000 concursos):
        | Número | Vezes Sorteado |
        |--------|----------------|
        | 01 | 98 |
        | 02 | 103 |
        | 03 | 95 |
        | ... | ... |
        """)
    
    with st.expander("**Passo 2: Calcular Frequência Esperada**"):
        st.markdown("""
        Se o sorteio é aleatório, cada número deveria aparecer com frequência igual.
        
        ```
        Frequência Esperada = (Total de Sorteios × Dezenas por jogo) / Total de números
        ```
        
        **Exemplo Mega Sena**: Em 1000 concursos → (1000 × 6) / 60 = **100 vezes** por número
        """)
    
    with st.expander("**Passo 3: Calcular a Estatística χ²**"):
        st.code("""
χ² = Σ [(Observado - Esperado)² / Esperado]

Para cada número:
• Calcula a diferença entre o que ocorreu e o esperado
• Eleva ao quadrado (elimina valores negativos)
• Divide pelo esperado (normaliza)
• Soma tudo
        """, language=None)
    
    with st.expander("**Passo 4: Interpretar com P-Value**"):
        st.markdown("""
        O **P-Value** é a probabilidade de observarmos um χ² tão grande **se a loteria fosse realmente aleatória**.
        
        | P-Value | Significado | Interpretação |
        |---------|-------------|---------------|
        | **> 0.05** | Não há evidência de anomalia | ✅ Distribuição normal |
        | **0.01 a 0.05** | Evidência fraca | ⚠️ Leve desvio, variação natural |
        | **< 0.01** | Evidência forte | 🚨 Padrão incomum - investigar |
        """)
    
    st.divider()
    
    st.markdown("### 🧪 Hipóteses do Teste")
    
    col1, col2 = st.columns(2)
    with col1:
        st.info("""
        **Hipótese Nula (H₀)**
        
        "A loteria é aleatória e todos os números têm a mesma chance."
        """)
    with col2:
        st.warning("""
        **Hipótese Alternativa (H₁)**
        
        "Há algo diferente - alguns números são favorecidos."
        """)
    
    st.markdown("""
    **Decisão:**
    - Se **P-Value > 0.05**: Não rejeitamos H₀ (loteria aparenta ser aleatória)
    - Se **P-Value < 0.05**: Rejeitamos H₀ (há indícios de não-aleatoriedade)
    """)
    
    st.divider()
    
    st.markdown("### ⚠️ Limitações e Cuidados")
    
    st.markdown("""
    | Limitação | Explicação |
    |-----------|------------|
    | **Tamanho da amostra** | Com poucos sorteios, variações são normais. O teste funciona melhor com 500+ concursos |
    | **Não explica causas** | Se detectar anomalia, pode ser erro nos dados, período curto, ou coincidência |
    | **Aleatoriedade ≠ Previsibilidade** | Confirmar aleatoriedade NÃO ajuda a prever próximos sorteios |
    """)
    
    st.divider()
    
    st.markdown("### ❓ Perguntas Frequentes")
    
    with st.expander("Se o teste diz que é aleatório, posso usar isso para ganhar?"):
        st.error("""
        **Não.** Aleatoriedade significa exatamente o oposto: **imprevisibilidade total**. 
        O teste confirma que não há padrões exploráveis.
        """)
    
    with st.expander("Por que usamos 0.05 como limiar?"):
        st.markdown("""
        É uma **convenção científica** (5% de risco de erro). Em contextos críticos 
        (medicina, por exemplo), usa-se 0.01 (1%).
        """)
    
    with st.expander("O teste pode dar falso positivo?"):
        st.markdown("""
        **Sim.** Em 5% das vezes (se usamos α = 0.05), rejeitaremos H₀ mesmo quando 
        ela é verdadeira. É o chamado **erro Tipo I**.
        """)
    
    st.divider()
    
    st.markdown("### 🎓 Glossário")
    st.markdown("""
    | Termo | Definição |
    |-------|-----------|
    | **χ² (Chi-Quadrado)** | Estatística que mede o desvio total entre observado e esperado |
    | **P-Value** | Probabilidade de observar os dados se H₀ for verdadeira |
    | **H₀ (Hipótese Nula)** | Suposição de que não há diferença/efeito |
    | **Graus de Liberdade** | Número de valores que podem variar (n-1) |
    | **Nível de Significância** | Limiar para rejeitar H₀ (geralmente 0.05) |
    """)
    
    st.caption("📖 Leitura adicional: Khan Academy, StatQuest (YouTube), scipy.stats.chisquare")


# ============================================
# VALIDAÇÃO ESTATÍSTICA
# ============================================
def render_statistics(df: pd.DataFrame, df_melted: pd.DataFrame, game_config: GameConfig):
    """Renderiza validações estatísticas"""
    st.markdown("## 🧪 Validação Estatística")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Teste Chi-Quadrado")
        
        chi_result = chi_square_test(df_melted, game_config)
        
        if chi_result:
            status = "✅" if chi_result.is_uniform else "⚠️"
            
            st.markdown(f"""
            **{status} P-Value: {chi_result.p_value}**
            
            Chi²: {chi_result.chi_statistic}
            
            {chi_result.interpretation}
            """)
            
            # Botão para documentação
            if st.button("📚 Entenda o Chi-Quadrado", key="chi_docs_btn"):
                st.session_state.show_chi_docs = True
    
    # Modal de documentação
    if st.session_state.get('show_chi_docs', False):
        with st.expander("📊 Documentação Chi-Quadrado", expanded=True):
            render_chi_square_docs()
            if st.button("✖️ Fechar", key="close_chi_docs"):
                st.session_state.show_chi_docs = False
                st.rerun()
    
    with col2:
        st.markdown("### Distribuição das Somas")
        
        sum_data = get_sum_analysis(df, game_config)
        
        if sum_data:
            fig = px.histogram(
                x=sum_data['valores'],
                nbins=30,
                color_discrete_sequence=[game_config.color_primary]
            )
            fig.add_vline(x=sum_data['media'], line_dash="dash", 
                         line_color="red", annotation_text=f"Média: {sum_data['media']:.0f}")
            fig.update_layout(height=300, xaxis_title="Soma", yaxis_title="Frequência")
            st.plotly_chart(fig, width="stretch")
            
            # Estatísticas resumidas
            st.caption(f"μ = {sum_data['media']:.0f} | σ = {sum_data['std']:.0f} | 68% entre {sum_data['media']-sum_data['std']:.0f} e {sum_data['media']+sum_data['std']:.0f}")
            
            # Botão para documentação
            if st.button("📚 Entenda a Curva Normal", key="normal_docs_btn"):
                st.session_state.show_normal_docs = True
    
    # Modal de documentação Curva Normal
    if st.session_state.get('show_normal_docs', False):
        with st.expander("📈 Documentação Curva Normal", expanded=True):
            render_normal_curve_docs(game_config)
            if st.button("✖️ Fechar", key="close_normal_docs"):
                st.session_state.show_normal_docs = False
                st.rerun()
    
    # Monte Carlo
    st.markdown("### 🎲 Simulação Monte Carlo")
    
    if st.button(f"▶️ Simular 10.000 jogos de {game_config.name}", type="primary"):
        progress = st.progress(0)
        status_text = st.empty()
        
        def update(pct):
            progress.progress(pct)
            status_text.text(f"Simulando... {pct*100:.0f}%")
        
        results = monte_carlo_simulation(game_config, 10000, update)
        progress.progress(1.0)
        status_text.text("Concluído!")
        
        labels = results.get('labels', {})
        col1, col2, col3 = st.columns(3)
        col1.metric(labels.get('acerto_total', 'Total'), results['acerto_total'])
        col2.metric(labels.get('acerto_menos_1', 'N-1'), results['acerto_menos_1'])
        col3.metric(labels.get('acerto_menos_2', 'N-2'), results['acerto_menos_2'])
        
        st.info(results['interpretation'])


# ============================================
# GERADOR DE JOGOS
# ============================================
def render_generator(df: pd.DataFrame, df_melted: pd.DataFrame, game_config: GameConfig):
    """Renderiza gerador de jogos"""
    st.markdown(f"## 🎲 Gerador de Jogos - {game_config.name}")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### ⚙️ Configurações")
        
        n_jogos = st.number_input("Quantidade", min_value=1, max_value=100, value=5,
                                   key=f"gen_qty_{game_config.slug}")
        
        # Exclusões - só mostra se fizer sentido para o jogo
        # Lotofácil tem 15 de 25, excluir muito não deixa números suficientes
        exclude_last = False
        exclude_top = False
        
        if game_config.max_number - game_config.n_balls >= 20:  # Mega Sena, Quina
            st.markdown("#### 🚫 Exclusões")
            exclude_last = st.checkbox("Excluir último sorteio", 
                                       help=f"Remove as {game_config.n_balls} dezenas do último concurso",
                                       key=f"gen_last_{game_config.slug}")
            exclude_top = st.checkbox("Excluir top 10 números", 
                                       help="Remove os 10 números mais sorteados",
                                       key=f"gen_top_{game_config.slug}")
        
        st.markdown("#### ⚖️ Balanceamento")
        n_balls = game_config.n_balls
        min_p, max_p = st.slider("Pares", 0, n_balls, (n_balls//3, n_balls*2//3),
                                  key=f"gen_pares_{game_config.slug}")
        
        # Range de soma baseado no jogo
        min_possible = sum(range(1, n_balls + 1))
        max_possible = sum(range(game_config.max_number - n_balls + 1, game_config.max_number + 1))
        default_min = int(min_possible + (max_possible - min_possible) * 0.3)
        default_max = int(min_possible + (max_possible - min_possible) * 0.7)
        
        min_s, max_s = st.slider("Soma", min_possible, max_possible, 
                                  (default_min, default_max),
                                  key=f"gen_soma_{game_config.slug}")
        
        st.markdown("#### 📌 Fixos (opcional)")
        fixed_input = st.text_input("Números fixos", placeholder="Ex: 7, 13, 25",
                                     key=f"gen_fixed_{game_config.slug}")
        fixed = []
        if fixed_input:
            try:
                fixed = [int(n.strip()) for n in fixed_input.split(',') if n.strip()]
                fixed = [n for n in fixed if 1 <= n <= game_config.max_number]
            except:
                st.warning("Formato inválido")
        
        st.markdown("#### 🎯 Estratégia")
        strategy = st.radio(
            "Escolha a estratégia",
            options=["random", "balanced", "contrarian"],
            format_func=lambda x: {
                "random": "🎲 Aleatório", 
                "balanced": "⚖️ Balanceado", 
                "contrarian": "🔄 Atrasados"
            }[x],
            key=f"gen_strat_{game_config.slug}",
            label_visibility="collapsed"
        )
        
        # Tooltip explicativo da estratégia selecionada
        strategy_help = {
            "random": "Seleção puramente aleatória, sem nenhum critério estatístico.",
            "balanced": "Mistura números 'quentes' (frequentes) e 'frios' (raros) de forma equilibrada.",
            "contrarian": "Prioriza números atrasados (há mais tempo sem sair). Não aumenta chances reais."
        }
        st.caption(f"ℹ️ {strategy_help[strategy]}")
        
        gen_btn = st.button("🎯 GERAR", type="primary", width="stretch",
                            key=f"gen_btn_{game_config.slug}")
    
    with col2:
        st.markdown("### 🎰 Jogos Gerados")
        
        games_key = f'{game_config.slug}_generated_games'
        
        if gen_btn:
            with st.spinner("Gerando..."):
                games = quick_generate(
                    df, df_melted, game_config,
                    n_games=n_jogos,
                    strategy=strategy,
                    exclude_last=exclude_last,
                    exclude_top=exclude_top,
                    min_evens=min_p,
                    max_evens=max_p,
                    min_sum=min_s,
                    max_sum=max_s,
                    fixed_numbers=fixed
                )
                if games:
                    st.session_state[games_key] = games
                else:
                    st.warning("Não foi possível gerar jogos com os filtros selecionados. Tente ajustar os parâmetros.")
        
        if st.session_state[games_key]:
            games = st.session_state[games_key]
            
            # Mapeia slug para classe CSS correta
            ball_class_map = {
                "mega_sena": "ball-mega",
                "quina": "ball-quina", 
                "lotofacil": "ball-lotofacil"
            }
            ball_class = ball_class_map.get(game_config.slug, "ball-mega")
            
            for i, game in enumerate(games, 1):
                numbers_html = " ".join([f'<span class="number-ball {ball_class}">{n:02d}</span>' 
                                         for n in game.numbers])
                
                st.markdown(f"""
                <div class="game-card">
                    <strong>Jogo #{i}:</strong> {numbers_html}
                    <br><small>Soma: {game.sum_value} | {game.evens}P/{game.odds}I | Score: {game.compatibility_score:.0f}%</small>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
            col_a, col_b = st.columns(2)
            
            with col_a:
                text = format_games_text(games)
                st.download_button("📋 Texto", text, f"jogos_{game_config.slug}.txt", 
                                   key=f"dl_txt_{game_config.slug}")
            
            with col_b:
                excel = export_games_excel(games)
                st.download_button("📊 Excel", excel, f"jogos_{game_config.slug}.xlsx",
                                   key=f"dl_xlsx_{game_config.slug}")


# ============================================
# COMPARADOR
# ============================================
def render_comparator(df: pd.DataFrame, game_config: GameConfig):
    """Renderiza comparador de jogos"""
    st.markdown(f"## 🔍 Comparador - {game_config.name}")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        n_balls = game_config.n_balls
        st.markdown(f"### Digite {n_balls} números")
        
        numbers_input = st.text_input(
            f"{n_balls} números separados por vírgula",
            placeholder=f"Ex: {', '.join(str(i) for i in range(1, n_balls+1))}",
            key=f"comp_input_{game_config.slug}"
        )
        
        compare_btn = st.button("🔎 Analisar", type="primary", key=f"comp_btn_{game_config.slug}")
    
    with col2:
        if compare_btn and numbers_input:
            try:
                numbers = [int(n.strip()) for n in numbers_input.split(',')]
                
                if len(numbers) != n_balls:
                    st.error(f"Digite exatamente {n_balls} números")
                elif len(set(numbers)) != n_balls:
                    st.error("Números não podem se repetir")
                elif not all(1 <= n <= game_config.max_number for n in numbers):
                    st.error(f"Números devem estar entre 1 e {game_config.max_number}")
                else:
                    result = compare_game(numbers, df, game_config)
                    
                    st.markdown("### Resultado")
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Soma", result['soma'])
                    c2.metric("Pares/Ímpares", f"{result['pares']}/{result['impares']}")
                    c3.metric("Originalidade", f"{result['originalidade']}%")
                    
                    st.markdown(f"""
                    - **Exato:** {'Nunca saiu!' if result['combinacao_exata'] == 0 else result['combinacao_exata']}
                    - **{n_balls-1} acertos:** {result['quase_acertos']} vez(es)
                    - **{n_balls-2} acertos:** {result['bons_acertos']} vez(es)
                    """)
            except Exception as e:
                st.error(f"Erro: {e}")


# ============================================
# FAQ
# ============================================
def render_faq(game_config: GameConfig):
    """Renderiza seção de FAQ"""
    st.markdown("## ❓ Perguntas Frequentes")
    
    with st.expander("Por que meus jogos não ganham?"):
        st.markdown(f"""
        A {game_config.name} tem **{game_config.total_combinations:,}** combinações possíveis. 
        A probabilidade de acertar é de aproximadamente **1 em {game_config.total_combinations:,}**, 
        independentemente de qualquer estratégia ou análise histórica.
        
        **Cada sorteio é independente** - o que saiu antes não influencia o próximo.
        """)
    
    with st.expander("O que é p-value?"):
        st.markdown("""
        O p-value é uma medida estatística que indica a probabilidade de obter 
        resultados tão extremos quanto os observados, assumindo que a hipótese 
        nula (no nosso caso, que os sorteios são aleatórios) é verdadeira.
        
        - **p > 0.05**: Não há evidência significativa contra a aleatoriedade
        - **p < 0.05**: Pode haver algum padrão, mas isso não significa previsibilidade
        """)
    
    with st.expander("Qual a melhor estratégia?"):
        st.markdown("""
        **Não existe estratégia vencedora em loteria.** Matematicamente, todas as 
        combinações têm exatamente a mesma probabilidade de serem sorteadas.
        
        Esta ferramenta é **educacional** - ajuda a entender estatística e 
        probabilidade, não a prever sorteios.
        """)
    
    with st.expander("Os números 'quentes' têm mais chance?"):
        st.markdown("""
        **Não.** O fato de um número ter saído mais vezes no passado não aumenta 
        nem diminui sua probabilidade de sair no próximo sorteio.
        
        Isso é conhecido como a **Falácia do Jogador**. Cada sorteio é independente.
        """)
    
    with st.expander("O que significa 'atrasado'?"):
        st.markdown("""
        Um número "atrasado" é aquele que não sai há muitos sorteios. Porém, isso 
        **não significa** que ele tem mais chance de sair.
        
        É apenas uma curiosidade estatística, não uma previsão.
        """)
    
    with st.expander("Posso confiar no gerador de jogos?"):
        st.markdown("""
        O gerador cria jogos **matematicamente válidos** com base em filtros estatísticos. 
        Porém, ele **não aumenta suas chances de ganhar**.
        
        Todos os jogos gerados têm a mesma probabilidade de qualquer outro jogo aleatório.
        """)


# ============================================
# DISCLAIMER
# ============================================
def render_disclaimer():
    """Renderiza disclaimer"""
    st.markdown("---")
    st.markdown("""
    <div class="disclaimer-box">
        <h4>⚖️ AVISO IMPORTANTE</h4>
        <p>Este sistema é uma ferramenta <strong>EDUCACIONAL</strong>. 
        Loterias são jogos de <strong>PURO ACASO</strong>. 
        Nenhuma análise aumenta suas chances de ganhar. 
        <strong>Jogue com responsabilidade.</strong></p>
    </div>
    """, unsafe_allow_html=True)


# ============================================
# MAIN
# ============================================
def main():
    """Função principal"""
    show_welcome_modal()
    render_sidebar()
    
    # Obtém jogo selecionado
    selected = st.session_state.selected_game
    game_config = GAMES[selected]
    
    df = st.session_state.get(f'{selected}_df')
    df_melted = st.session_state.get(f'{selected}_df_melted')
    loaded = st.session_state.get(f'{selected}_loaded', False)
    
    if not loaded or df is None:
        st.markdown(f"""
        <div style="text-align: center; padding: 100px 20px;">
            <h1>{game_config.icon} LotoVision</h1>
            <h3>Análise Estatística - {game_config.name}</h3>
            <p>⏳ Carregando dados...</p>
        </div>
        """, unsafe_allow_html=True)
        st.rerun()  # Recarrega para pegar os dados
        return
    
    # Dica para abrir menu no mobile
    st.markdown("""
    <div class="mobile-menu-hint">
        ☰ Menu no canto superior esquerdo
    </div>
    """, unsafe_allow_html=True)
    
    # Aplica filtro de data
    date_key = f'{selected}_date_filter'
    if date_key in st.session_state:
        start, end = st.session_state[date_key]
        df, df_melted = filter_by_date_range(df, df_melted, start, end)
    
    # Tabs do jogo
    tabs = st.tabs(["📊 Dashboard", "📈 Estatísticas", "🎲 Gerador", "🔍 Comparador", "❓ FAQ"])
    
    with tabs[0]:
        render_header(df, game_config)
        
        col1, col2 = st.columns(2)
        with col1:
            render_heatmap(df_melted, game_config)
        with col2:
            render_parity_chart(df, game_config)
        
        render_frequency_charts(df_melted, game_config)
        render_delay_analysis(df, df_melted, game_config)
        render_frequent_pairs(df, game_config)
    
    with tabs[1]:
        render_statistics(df, df_melted, game_config)
    
    with tabs[2]:
        render_generator(df, df_melted, game_config)
    
    with tabs[3]:
        render_comparator(df, game_config)
    
    with tabs[4]:
        render_faq(game_config)
    
    render_disclaimer()


if __name__ == "__main__":
    main()
