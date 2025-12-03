"""
LotoVision - Módulo de Carregamento de Dados v2
Suporte para múltiplos jogos: Mega Sena, Quina, Lotofácil
"""

import pandas as pd
import numpy as np
import streamlit as st
from pathlib import Path
from typing import Tuple, Optional
import os

from modules.game_config import GameConfig, GAMES, detect_game_type, validate_game_file


def get_demo_path(game_slug: str) -> Path:
    """Retorna o caminho do arquivo demo para cada jogo"""
    demo_files = {
        "mega_sena": ["data/mega_sena_demo.xlsx", "data/demo.xlsx", "Mega-Sena.xlsx"],
        "quina": ["data/quina_demo.xlsx", "Quina.xlsx"],
        "lotofacil": ["data/lotofacil_demo.xlsx", "Lotofacil.xlsx", "LotoFacil.xlsx"],
    }
    
    base_path = Path(__file__).parent.parent
    
    for filename in demo_files.get(game_slug, []):
        path = base_path / filename
        if path.exists():
            return path
    
    return base_path / f"data/{game_slug}_demo.xlsx"


@st.cache_data(ttl=3600, show_spinner=False)
def load_excel_cached(file_content: bytes, filename: str) -> pd.DataFrame:
    """Carrega arquivo Excel de bytes (cached)"""
    import io
    return pd.read_excel(io.BytesIO(file_content), engine='openpyxl')


def normalize_columns(df: pd.DataFrame, game_config: GameConfig) -> pd.DataFrame:
    """
    Normaliza nomes das colunas para o padrão esperado
    Adaptado para diferentes quantidades de bolas
    """
    df = df.copy()
    
    # Mapeamento base
    column_aliases = {
        'concurso': 'Concurso',
        'data do sorteio': 'Data',
        'data sorteio': 'Data',
        'data': 'Data',
    }
    
    # Adiciona mapeamentos para bolas (vários formatos)
    for i in range(1, game_config.n_balls + 1):
        column_aliases[f'bola {i}'] = f'Bola_{i}'
        column_aliases[f'bola{i}'] = f'Bola_{i}'
        column_aliases[f'{i}ª dezena'] = f'Bola_{i}'
        column_aliases[f'{i}ª bola'] = f'Bola_{i}'
        column_aliases[f'dezena {i}'] = f'Bola_{i}'
        column_aliases[f'dezena{i}'] = f'Bola_{i}'
    
    # Se colunas são numéricas (índices), renomeia por posição
    if all(isinstance(col, int) for col in df.columns[:2]):
        new_cols = ['Concurso', 'Data']
        for i in range(game_config.n_balls):
            if i + 2 < len(df.columns):
                new_cols.append(f'Bola_{i+1}')
        # Adiciona colunas extras se existirem
        for i in range(len(new_cols), len(df.columns)):
            new_cols.append(f'Extra_{i}')
        df.columns = new_cols[:len(df.columns)]
    else:
        # Renomeia por alias
        new_columns = {}
        for col in df.columns:
            col_lower = str(col).lower().strip()
            if col_lower in column_aliases:
                new_columns[col] = column_aliases[col_lower]
        
        if new_columns:
            df = df.rename(columns=new_columns)
        
        # Se ainda não tem as colunas de bola, tenta mapear por posição
        has_ball_cols = any(f'Bola_{i}' in df.columns for i in range(1, game_config.n_balls + 1))
        
        if not has_ball_cols:
            cols = list(df.columns)
            new_cols = {}
            ball_idx = 1
            
            for i, col in enumerate(cols):
                if i == 0 and 'Concurso' not in str(col):
                    new_cols[col] = 'Concurso'
                elif i == 1 and 'Data' not in str(col):
                    new_cols[col] = 'Data'
                elif i >= 2 and ball_idx <= game_config.n_balls:
                    # Verifica se é coluna numérica
                    if pd.api.types.is_numeric_dtype(df[col]) or df[col].dtype == object:
                        new_cols[col] = f'Bola_{ball_idx}'
                        ball_idx += 1
            
            if new_cols:
                df = df.rename(columns=new_cols)
    
    return df


def clean_data(df: pd.DataFrame, game_config: GameConfig) -> pd.DataFrame:
    """Limpa e prepara os dados"""
    df = df.copy()
    
    # Remove linhas completamente vazias
    df = df.dropna(how='all')
    
    # Garante que Concurso é inteiro
    if 'Concurso' in df.columns:
        df['Concurso'] = pd.to_numeric(df['Concurso'], errors='coerce').astype('Int64')
        df = df.dropna(subset=['Concurso'])
    
    # Converte Data para datetime
    if 'Data' in df.columns:
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce', dayfirst=True)
    
    # Garante que dezenas são inteiros
    for col in game_config.ball_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')
    
    # Ordena por concurso
    if 'Concurso' in df.columns:
        df = df.sort_values('Concurso', ascending=True).reset_index(drop=True)
    
    return df


def create_melted_df(df: pd.DataFrame, game_config: GameConfig) -> pd.DataFrame:
    """Cria DataFrame no formato melted (long format)"""
    id_vars = ['Concurso', 'Data'] if 'Data' in df.columns else ['Concurso']
    
    # Filtra apenas as colunas de bola que existem
    ball_cols = [col for col in game_config.ball_columns if col in df.columns]
    
    df_melted = df.melt(
        id_vars=id_vars,
        value_vars=ball_cols,
        var_name='Posicao',
        value_name='Dezena'
    )
    
    # Remove valores nulos
    df_melted = df_melted.dropna(subset=['Dezena'])
    df_melted['Dezena'] = df_melted['Dezena'].astype(int)
    
    # Ordena por concurso e dezena
    df_melted = df_melted.sort_values(['Concurso', 'Dezena']).reset_index(drop=True)
    
    return df_melted


def add_computed_columns(df: pd.DataFrame, game_config: GameConfig) -> pd.DataFrame:
    """Adiciona colunas calculadas úteis para análises"""
    df = df.copy()
    
    ball_cols = [col for col in game_config.ball_columns if col in df.columns]
    
    # Soma das dezenas
    if ball_cols:
        df['Soma'] = df[ball_cols].sum(axis=1)
    
    # Contagem de pares
    def count_even(row):
        dezenas = [row[col] for col in ball_cols if col in row.index and pd.notna(row[col])]
        return sum(1 for d in dezenas if int(d) % 2 == 0)
    
    df['Pares'] = df.apply(count_even, axis=1)
    df['Impares'] = len(ball_cols) - df['Pares']
    
    # Ano (para análises temporais)
    if 'Data' in df.columns:
        df['Ano'] = df['Data'].dt.year
        df['Mes'] = df['Data'].dt.month
    
    return df


def load_game_data(
    game_config: GameConfig,
    uploaded_file=None, 
    use_demo: bool = False
) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], str]:
    """
    Função principal de carregamento de dados para um jogo específico
    
    Args:
        game_config: Configuração do jogo
        uploaded_file: Arquivo enviado pelo usuário
        use_demo: Se True, carrega arquivo demo
    
    Returns:
        Tuple: (df_main, df_melted, mensagem_status)
    """
    df = None
    source = ""
    
    try:
        if uploaded_file is not None:
            # Carrega arquivo do usuário
            df = load_excel_cached(uploaded_file.read(), uploaded_file.name)
            source = f"Arquivo: {uploaded_file.name}"
            
            # Valida se o arquivo corresponde ao jogo
            is_valid, validation_msg = validate_game_file(df, game_config.slug)
            if not is_valid:
                return None, None, validation_msg
            
        elif use_demo:
            # Carrega arquivo demo
            demo_path = get_demo_path(game_config.slug)
            if demo_path.exists():
                with open(demo_path, 'rb') as f:
                    df = load_excel_cached(f.read(), demo_path.name)
                source = "Dados de demonstração"
            else:
                return None, None, f"❌ Arquivo demo não encontrado para {game_config.name}"
        else:
            return None, None, "📁 Aguardando upload de arquivo..."
        
        # Normaliza colunas
        df = normalize_columns(df, game_config)
        
        # Limpa dados
        df = clean_data(df, game_config)
        
        # Adiciona colunas calculadas
        df = add_computed_columns(df, game_config)
        
        # Cria versão melted
        df_melted = create_melted_df(df, game_config)
        
        # Validação básica
        from utils.validators import validate_game_data
        is_valid, validation_msg = validate_game_data(df, game_config)
        
        n_concursos = len(df)
        status_msg = f"✅ {n_concursos:,} concursos carregados | {source}"
        
        if not is_valid:
            status_msg = f"⚠️ {n_concursos:,} concursos carregados (com avisos) | {source}"
        
        return df, df_melted, status_msg
        
    except Exception as e:
        return None, None, f"❌ Erro ao carregar dados: {str(e)}"


def filter_by_date_range(
    df: pd.DataFrame, 
    df_melted: pd.DataFrame, 
    start_date, 
    end_date
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Filtra DataFrames por intervalo de datas"""
    if 'Data' not in df.columns:
        return df, df_melted
    
    mask = (df['Data'] >= pd.Timestamp(start_date)) & (df['Data'] <= pd.Timestamp(end_date))
    df_filtered = df[mask].copy()
    
    # Filtra melted também
    concursos_validos = df_filtered['Concurso'].unique()
    df_melted_filtered = df_melted[df_melted['Concurso'].isin(concursos_validos)].copy()
    
    return df_filtered, df_melted_filtered


def get_date_range(df: pd.DataFrame) -> Tuple[Optional[pd.Timestamp], Optional[pd.Timestamp]]:
    """Retorna range de datas do DataFrame"""
    if 'Data' not in df.columns or df.empty:
        return None, None
    
    return df['Data'].min(), df['Data'].max()
