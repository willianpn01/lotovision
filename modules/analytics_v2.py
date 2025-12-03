"""
LotoVision - Módulo de Análises v2
Suporte para múltiplos jogos: Mega Sena, Quina, Lotofácil
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from itertools import combinations
from collections import Counter

from modules.game_config import GameConfig


def get_kpis(df: pd.DataFrame, game_config: GameConfig) -> Dict:
    """Calcula KPIs principais do dashboard"""
    if df.empty:
        return {}
    
    ball_cols = game_config.ball_columns
    
    # Último sorteio
    ultimo = df.iloc[-1]
    ultimo_concurso = int(ultimo['Concurso'])
    ultimo_data = ultimo['Data'].strftime('%d/%m/%Y') if pd.notna(ultimo['Data']) else 'N/A'
    ultimo_dezenas = sorted([int(ultimo[col]) for col in ball_cols if col in ultimo.index and pd.notna(ultimo[col])])
    
    # Estatísticas gerais
    total_concursos = len(df)
    primeiro_ano = df['Data'].min().year if 'Data' in df.columns and pd.notna(df['Data'].min()) else 'N/A'
    ultimo_ano = df['Data'].max().year if 'Data' in df.columns and pd.notna(df['Data'].max()) else 'N/A'
    
    return {
        'ultimo_concurso': ultimo_concurso,
        'ultimo_data': ultimo_data,
        'ultimo_dezenas': ultimo_dezenas,
        'total_concursos': total_concursos,
        'primeiro_ano': primeiro_ano,
        'ultimo_ano': ultimo_ano,
        'periodo': f"{primeiro_ano} - {ultimo_ano}",
        'game_name': game_config.name,
        'n_balls': game_config.n_balls
    }


def get_frequency_analysis(df_melted: pd.DataFrame, top_n: int = 10) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Analisa frequência das dezenas"""
    if df_melted.empty:
        return pd.DataFrame(), pd.DataFrame()
    
    freq = df_melted['Dezena'].value_counts().reset_index()
    freq.columns = ['Dezena', 'Frequencia']
    
    # Calcula percentual
    total_sorteios = df_melted['Concurso'].nunique()
    freq['Percentual'] = (freq['Frequencia'] / total_sorteios * 100).round(2)
    
    freq = freq.sort_values('Frequencia', ascending=False)
    
    top_mais = freq.head(top_n).copy()
    top_menos = freq.tail(top_n).sort_values('Frequencia', ascending=True).copy()
    
    return top_mais, top_menos


def get_full_frequency(df_melted: pd.DataFrame, game_config: GameConfig) -> pd.DataFrame:
    """Retorna frequência completa de todas as dezenas"""
    if df_melted.empty:
        return pd.DataFrame()
    
    freq = df_melted['Dezena'].value_counts().reset_index()
    freq.columns = ['Dezena', 'Frequencia']
    
    # Adiciona dezenas que nunca saíram
    all_dezenas = pd.DataFrame({'Dezena': range(1, game_config.max_number + 1)})
    freq = all_dezenas.merge(freq, on='Dezena', how='left').fillna(0)
    freq['Frequencia'] = freq['Frequencia'].astype(int)
    
    # Calcula percentual
    total_sorteios = df_melted['Concurso'].nunique()
    freq['Percentual'] = (freq['Frequencia'] / total_sorteios * 100).round(2)
    
    return freq.sort_values('Dezena')


def get_heatmap_data(df_melted: pd.DataFrame, game_config: GameConfig) -> np.ndarray:
    """Prepara dados para heatmap do volante"""
    freq = get_full_frequency(df_melted, game_config)
    
    if freq.empty:
        return np.zeros((1, 1))
    
    max_num = game_config.max_number
    
    # Define grid baseado no jogo
    if max_num == 60:  # Mega Sena
        rows, cols = 6, 10
    elif max_num == 80:  # Quina
        rows, cols = 8, 10
    elif max_num == 25:  # Lotofácil
        rows, cols = 5, 5
    else:
        cols = 10
        rows = (max_num + cols - 1) // cols
    
    heatmap = np.zeros((rows, cols))
    
    for _, row in freq.iterrows():
        dezena = int(row['Dezena'])
        frequencia = row['Frequencia']
        
        if dezena <= max_num:
            linha = (dezena - 1) // cols
            coluna = (dezena - 1) % cols
            if linha < rows and coluna < cols:
                heatmap[linha, coluna] = frequencia
    
    return heatmap


def get_heatmap_labels(game_config: GameConfig) -> np.ndarray:
    """Retorna labels para o heatmap"""
    max_num = game_config.max_number
    
    if max_num == 60:
        rows, cols = 6, 10
    elif max_num == 80:
        rows, cols = 8, 10
    elif max_num == 25:
        rows, cols = 5, 5
    else:
        cols = 10
        rows = (max_num + cols - 1) // cols
    
    labels = np.zeros((rows, cols), dtype=int)
    
    for i in range(1, max_num + 1):
        linha = (i - 1) // cols
        coluna = (i - 1) % cols
        if linha < rows and coluna < cols:
            labels[linha, coluna] = i
    
    return labels


def get_parity_distribution(df: pd.DataFrame, game_config: GameConfig) -> pd.DataFrame:
    """Analisa distribuição de pares/ímpares por jogo"""
    if df.empty or 'Pares' not in df.columns:
        return pd.DataFrame()
    
    n_balls = game_config.n_balls
    
    dist = df.groupby('Pares').size().reset_index(name='Quantidade')
    
    all_pares = pd.DataFrame({'Pares': range(0, n_balls + 1)})
    dist = all_pares.merge(dist, on='Pares', how='left').fillna(0)
    dist['Quantidade'] = dist['Quantidade'].astype(int)
    
    total = dist['Quantidade'].sum()
    dist['Percentual'] = (dist['Quantidade'] / total * 100).round(2) if total > 0 else 0
    
    dist['Label'] = dist['Pares'].apply(
        lambda x: f"{x} Par{'es' if x != 1 else ''} / {n_balls-x} Ímpar{'es' if (n_balls-x) != 1 else ''}"
    )
    
    return dist


def get_delay_analysis(df: pd.DataFrame, df_melted: pd.DataFrame, 
                       game_config: GameConfig, top_n: int = 15) -> pd.DataFrame:
    """Analisa atraso das dezenas"""
    if df.empty or df_melted.empty:
        return pd.DataFrame()
    
    ultimo_concurso = df['Concurso'].max()
    
    ultimo_sorteio = df_melted.groupby('Dezena')['Concurso'].max().reset_index()
    ultimo_sorteio.columns = ['Dezena', 'UltimoConcurso']
    
    ultimo_sorteio['Atraso'] = ultimo_concurso - ultimo_sorteio['UltimoConcurso']
    
    def calc_media_atraso(dezena):
        concursos = df_melted[df_melted['Dezena'] == dezena]['Concurso'].sort_values().values
        if len(concursos) < 2:
            return 0, 0
        diffs = np.diff(concursos)
        return round(diffs.mean(), 1), round(diffs.std(), 1)
    
    atrasos_medios = []
    for dezena in range(1, game_config.max_number + 1):
        media, std = calc_media_atraso(dezena)
        atrasos_medios.append({'Dezena': dezena, 'AtrasoMedio': media, 'AtrasoStd': std})
    
    atrasos_df = pd.DataFrame(atrasos_medios)
    resultado = ultimo_sorteio.merge(atrasos_df, on='Dezena')
    
    def get_status(row):
        if row['AtrasoMedio'] == 0:
            return 'normal'
        ratio = row['Atraso'] / row['AtrasoMedio']
        if ratio > 2:
            return 'critico'
        elif ratio > 1.5:
            return 'atencao'
        return 'normal'
    
    resultado['Status'] = resultado.apply(get_status, axis=1)
    resultado = resultado.sort_values('Atraso', ascending=False).head(top_n)
    
    return resultado


def get_frequent_pairs(df: pd.DataFrame, game_config: GameConfig, top_n: int = 10) -> pd.DataFrame:
    """Encontra pares de números mais frequentes"""
    if df.empty:
        return pd.DataFrame()
    
    ball_cols = game_config.ball_columns
    pair_counter = Counter()
    
    for _, row in df.iterrows():
        dezenas = sorted([int(row[col]) for col in ball_cols if col in row.index and pd.notna(row[col])])
        for pair in combinations(dezenas, 2):
            pair_counter[pair] += 1
    
    pairs_data = [
        {'Par': f"{p[0]:02d} - {p[1]:02d}", 'Num1': p[0], 'Num2': p[1], 'Frequencia': count}
        for p, count in pair_counter.most_common(top_n)
    ]
    
    return pd.DataFrame(pairs_data)


def get_frequent_trios(df: pd.DataFrame, game_config: GameConfig, top_n: int = 10) -> pd.DataFrame:
    """Encontra trios de números mais frequentes"""
    if df.empty:
        return pd.DataFrame()
    
    ball_cols = game_config.ball_columns
    trio_counter = Counter()
    
    for _, row in df.iterrows():
        dezenas = sorted([int(row[col]) for col in ball_cols if col in row.index and pd.notna(row[col])])
        for trio in combinations(dezenas, 3):
            trio_counter[trio] += 1
    
    trios_data = [
        {'Trio': f"{t[0]:02d} - {t[1]:02d} - {t[2]:02d}", 'Frequencia': count}
        for t, count in trio_counter.most_common(top_n)
    ]
    
    return pd.DataFrame(trios_data)


def get_temporal_trend(df: pd.DataFrame, df_melted: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    """Analisa tendência temporal das dezenas mais sorteadas"""
    if df.empty or df_melted.empty or 'Ano' not in df.columns:
        return pd.DataFrame()
    
    top_dezenas = df_melted['Dezena'].value_counts().head(top_n).index.tolist()
    
    df_melted_with_year = df_melted.merge(df[['Concurso', 'Ano']], on='Concurso')
    df_filtered = df_melted_with_year[df_melted_with_year['Dezena'].isin(top_dezenas)]
    
    trend = df_filtered.groupby(['Ano', 'Dezena']).size().reset_index(name='Frequencia')
    trend_pivot = trend.pivot(index='Ano', columns='Dezena', values='Frequencia').fillna(0)
    
    return trend_pivot


def get_sum_analysis(df: pd.DataFrame, game_config: GameConfig) -> Dict:
    """Analisa distribuição da soma das dezenas"""
    if df.empty or 'Soma' not in df.columns:
        return {}
    
    somas = df['Soma']
    
    return {
        'media': round(somas.mean(), 2),
        'mediana': round(somas.median(), 2),
        'std': round(somas.std(), 2),
        'min': int(somas.min()),
        'max': int(somas.max()),
        'q1': round(somas.quantile(0.25), 2),
        'q3': round(somas.quantile(0.75), 2),
        'valores': somas.values,
        'n_balls': game_config.n_balls
    }


def classify_numbers(df_melted: pd.DataFrame, game_config: GameConfig) -> Dict[str, List[int]]:
    """Classifica números em quentes, frios e neutros"""
    if df_melted.empty:
        return {'quentes': [], 'frios': [], 'neutros': []}
    
    freq = df_melted['Dezena'].value_counts()
    media = freq.mean()
    std = freq.std()
    
    quentes = freq[freq > media + std].index.tolist()
    frios = freq[freq < media - std].index.tolist()
    neutros = freq[(freq >= media - std) & (freq <= media + std)].index.tolist()
    
    return {
        'quentes': sorted(quentes),
        'frios': sorted(frios),
        'neutros': sorted(neutros)
    }


def compare_game(game: List[int], df: pd.DataFrame, game_config: GameConfig) -> Dict:
    """Compara um jogo com o histórico"""
    if df.empty:
        return {}
    
    ball_cols = game_config.ball_columns
    game_set = set(game)
    n_balls = game_config.n_balls
    
    exact_matches = 0
    near_matches = 0  # n-1 acertos
    good_matches = 0  # n-2 acertos
    
    for _, row in df.iterrows():
        dezenas = set([int(row[col]) for col in ball_cols if col in row.index and pd.notna(row[col])])
        matches = len(game_set & dezenas)
        
        if matches == n_balls:
            exact_matches += 1
        elif matches == n_balls - 1:
            near_matches += 1
        elif matches == n_balls - 2:
            good_matches += 1
    
    soma = sum(game)
    pares = sum(1 for d in game if d % 2 == 0)
    
    total_jogos = len(df)
    similar_ratio = (near_matches + good_matches) / total_jogos if total_jogos > 0 else 0
    originalidade = round((1 - similar_ratio) * 100, 2)
    
    return {
        'jogo': sorted(game),
        'soma': soma,
        'pares': pares,
        'impares': n_balls - pares,
        'combinacao_exata': exact_matches,
        'quase_acertos': near_matches,
        'bons_acertos': good_matches,
        'originalidade': originalidade
    }
