"""
LotoVision - Módulo de Carregamento de Dados
Upload e processamento de arquivos Excel da Mega Sena
"""

import pandas as pd
import numpy as np
import streamlit as st
from pathlib import Path
from typing import Tuple, Optional
import os


# Colunas padrão do arquivo
COLUMN_MAPPING = {
    0: 'Concurso',
    1: 'Data',
    2: 'Bola_1',
    3: 'Bola_2',
    4: 'Bola_3',
    5: 'Bola_4',
    6: 'Bola_5',
    7: 'Bola_6'
}

BOLA_COLUMNS = [f'Bola_{i}' for i in range(1, 7)]


def get_demo_path() -> Path:
    """Retorna o caminho do arquivo demo"""
    # Tenta encontrar o arquivo demo em vários locais possíveis
    possible_paths = [
        Path(__file__).parent.parent / 'data' / 'demo.xlsx',
        Path(__file__).parent.parent / 'Mega-Sena.xlsx',
        Path('data/demo.xlsx'),
        Path('Mega-Sena.xlsx'),
    ]
    
    for path in possible_paths:
        if path.exists():
            return path
    
    return possible_paths[0]  # Retorna o padrão mesmo se não existir


@st.cache_data(ttl=3600, show_spinner=False)
def load_excel(file_content: bytes, filename: str) -> pd.DataFrame:
    """
    Carrega arquivo Excel de bytes
    Cached para evitar reprocessamento
    """
    import io
    return pd.read_excel(io.BytesIO(file_content), engine='openpyxl')


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza nomes das colunas para o padrão esperado
    """
    # Se as colunas são numéricas (índices), renomeia
    if all(isinstance(col, int) for col in df.columns):
        df.columns = [COLUMN_MAPPING.get(i, f'Col_{i}') for i in range(len(df.columns))]
    
    # Tenta mapear nomes comuns
    column_aliases = {
        'concurso': 'Concurso',
        'data do sorteio': 'Data',
        'data': 'Data',
        'bola 1': 'Bola_1',
        'bola 2': 'Bola_2',
        'bola 3': 'Bola_3',
        'bola 4': 'Bola_4',
        'bola 5': 'Bola_5',
        'bola 6': 'Bola_6',
        'bola1': 'Bola_1',
        'bola2': 'Bola_2',
        'bola3': 'Bola_3',
        'bola4': 'Bola_4',
        'bola5': 'Bola_5',
        'bola6': 'Bola_6',
        '1ª dezena': 'Bola_1',
        '2ª dezena': 'Bola_2',
        '3ª dezena': 'Bola_3',
        '4ª dezena': 'Bola_4',
        '5ª dezena': 'Bola_5',
        '6ª dezena': 'Bola_6',
    }
    
    new_columns = {}
    for col in df.columns:
        col_lower = str(col).lower().strip()
        if col_lower in column_aliases:
            new_columns[col] = column_aliases[col_lower]
    
    if new_columns:
        df = df.rename(columns=new_columns)
    
    return df


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpa e prepara os dados
    """
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
    for col in BOLA_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')
    
    # Ordena por concurso
    if 'Concurso' in df.columns:
        df = df.sort_values('Concurso', ascending=True).reset_index(drop=True)
    
    return df


def create_melted_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cria DataFrame no formato melted (long format)
    Cada linha representa uma dezena sorteada
    """
    id_vars = ['Concurso', 'Data'] if 'Data' in df.columns else ['Concurso']
    
    df_melted = df.melt(
        id_vars=id_vars,
        value_vars=BOLA_COLUMNS,
        var_name='Posicao',
        value_name='Dezena'
    )
    
    # Remove valores nulos
    df_melted = df_melted.dropna(subset=['Dezena'])
    df_melted['Dezena'] = df_melted['Dezena'].astype(int)
    
    # Ordena por concurso e dezena
    df_melted = df_melted.sort_values(['Concurso', 'Dezena']).reset_index(drop=True)
    
    return df_melted


def add_computed_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adiciona colunas calculadas úteis para análises
    """
    df = df.copy()
    
    # Soma das dezenas
    if all(col in df.columns for col in BOLA_COLUMNS):
        df['Soma'] = df[BOLA_COLUMNS].sum(axis=1)
    
    # Contagem de pares
    def count_even(row):
        dezenas = [row[col] for col in BOLA_COLUMNS if col in row.index]
        return sum(1 for d in dezenas if d % 2 == 0)
    
    df['Pares'] = df.apply(count_even, axis=1)
    df['Impares'] = 6 - df['Pares']
    
    # Ano (para análises temporais)
    if 'Data' in df.columns:
        df['Ano'] = df['Data'].dt.year
        df['Mes'] = df['Data'].dt.month
    
    return df


def load_data(uploaded_file=None, use_demo: bool = False) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], str]:
    """
    Função principal de carregamento de dados
    
    Args:
        uploaded_file: Arquivo enviado pelo usuário (UploadedFile do Streamlit)
        use_demo: Se True, carrega arquivo demo
    
    Returns:
        Tuple: (df_main, df_melted, mensagem_status)
    """
    df = None
    source = ""
    
    try:
        if uploaded_file is not None:
            # Carrega arquivo do usuário
            df = load_excel(uploaded_file.read(), uploaded_file.name)
            source = f"Arquivo: {uploaded_file.name}"
            
        elif use_demo:
            # Carrega arquivo demo
            demo_path = get_demo_path()
            if demo_path.exists():
                with open(demo_path, 'rb') as f:
                    df = load_excel(f.read(), demo_path.name)
                source = "Dados de demonstração"
            else:
                return None, None, f"❌ Arquivo demo não encontrado em {demo_path}"
        else:
            return None, None, "📁 Aguardando upload de arquivo..."
        
        # Normaliza colunas
        df = normalize_columns(df)
        
        # Limpa dados
        df = clean_data(df)
        
        # Adiciona colunas calculadas
        df = add_computed_columns(df)
        
        # Cria versão melted
        df_melted = create_melted_df(df)
        
        # Validação básica
        from utils.validators import quick_validate
        is_valid, validation_msg = quick_validate(df)
        
        n_concursos = len(df)
        status_msg = f"✅ {n_concursos:,} concursos carregados | {source}"
        
        if not is_valid:
            status_msg = f"⚠️ {n_concursos:,} concursos carregados (com avisos) | {source}"
        
        return df, df_melted, status_msg
        
    except Exception as e:
        return None, None, f"❌ Erro ao carregar dados: {str(e)}"


def filter_by_date_range(df: pd.DataFrame, df_melted: pd.DataFrame, 
                         start_date, end_date) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Filtra DataFrames por intervalo de datas
    """
    if 'Data' not in df.columns:
        return df, df_melted
    
    mask = (df['Data'] >= pd.Timestamp(start_date)) & (df['Data'] <= pd.Timestamp(end_date))
    df_filtered = df[mask].copy()
    
    # Filtra melted também
    concursos_validos = df_filtered['Concurso'].unique()
    df_melted_filtered = df_melted[df_melted['Concurso'].isin(concursos_validos)].copy()
    
    return df_filtered, df_melted_filtered


def get_date_range(df: pd.DataFrame) -> Tuple[Optional[pd.Timestamp], Optional[pd.Timestamp]]:
    """
    Retorna range de datas do DataFrame
    """
    if 'Data' not in df.columns or df.empty:
        return None, None
    
    return df['Data'].min(), df['Data'].max()
