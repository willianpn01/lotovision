"""
LotoVision - Módulo de Análises
KPIs, frequências, atrasos e análises visuais
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from itertools import combinations
from collections import Counter


BOLA_COLUMNS = [f'Bola_{i}' for i in range(1, 7)]


def get_kpis(df: pd.DataFrame) -> Dict:
    """
    Calcula KPIs principais do dashboard
    """
    if df.empty:
        return {}
    
    # Último sorteio
    ultimo = df.iloc[-1]
    ultimo_concurso = int(ultimo['Concurso'])
    ultimo_data = ultimo['Data'].strftime('%d/%m/%Y') if pd.notna(ultimo['Data']) else 'N/A'
    ultimo_dezenas = sorted([int(ultimo[col]) for col in BOLA_COLUMNS if col in ultimo.index])
    
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
        'periodo': f"{primeiro_ano} - {ultimo_ano}"
    }


def get_frequency_analysis(df_melted: pd.DataFrame, top_n: int = 10) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Analisa frequência das dezenas
    
    Returns:
        Tuple: (top_mais_sorteadas, top_menos_sorteadas)
    """
    if df_melted.empty:
        return pd.DataFrame(), pd.DataFrame()
    
    # Conta frequência de cada dezena
    freq = df_melted['Dezena'].value_counts().reset_index()
    freq.columns = ['Dezena', 'Frequencia']
    
    # Calcula percentual (total de sorteios = total de dezenas / 6)
    total_sorteios = len(df_melted) / 6
    freq['Percentual'] = (freq['Frequencia'] / total_sorteios * 100).round(2)
    
    # Ordena
    freq = freq.sort_values('Frequencia', ascending=False)
    
    # Top mais e menos sorteadas
    top_mais = freq.head(top_n).copy()
    top_menos = freq.tail(top_n).sort_values('Frequencia', ascending=True).copy()
    
    return top_mais, top_menos


def get_full_frequency(df_melted: pd.DataFrame) -> pd.DataFrame:
    """
    Retorna frequência completa de todas as 60 dezenas
    """
    if df_melted.empty:
        return pd.DataFrame()
    
    # Conta frequência
    freq = df_melted['Dezena'].value_counts().reset_index()
    freq.columns = ['Dezena', 'Frequencia']
    
    # Adiciona dezenas que nunca saíram (se houver)
    all_dezenas = pd.DataFrame({'Dezena': range(1, 61)})
    freq = all_dezenas.merge(freq, on='Dezena', how='left').fillna(0)
    freq['Frequencia'] = freq['Frequencia'].astype(int)
    
    # Calcula percentual
    total_sorteios = len(df_melted) / 6
    freq['Percentual'] = (freq['Frequencia'] / total_sorteios * 100).round(2)
    
    return freq.sort_values('Dezena')


def get_heatmap_data(df_melted: pd.DataFrame) -> np.ndarray:
    """
    Prepara dados para heatmap do volante (6x10)
    """
    freq = get_full_frequency(df_melted)
    
    if freq.empty:
        return np.zeros((6, 10))
    
    # Cria matriz 6x10
    heatmap = np.zeros((6, 10))
    
    for _, row in freq.iterrows():
        dezena = int(row['Dezena'])
        frequencia = row['Frequencia']
        
        # Calcula posição na matriz (1-10 na primeira linha, 11-20 na segunda, etc.)
        linha = (dezena - 1) // 10
        coluna = (dezena - 1) % 10
        heatmap[linha, coluna] = frequencia
    
    return heatmap


def get_parity_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """
    Analisa distribuição de pares/ímpares por jogo
    """
    if df.empty or 'Pares' not in df.columns:
        return pd.DataFrame()
    
    # Conta distribuição
    dist = df.groupby('Pares').size().reset_index(name='Quantidade')
    
    # Adiciona categorias faltantes
    all_pares = pd.DataFrame({'Pares': range(0, 7)})
    dist = all_pares.merge(dist, on='Pares', how='left').fillna(0)
    dist['Quantidade'] = dist['Quantidade'].astype(int)
    
    # Calcula percentual
    total = dist['Quantidade'].sum()
    dist['Percentual'] = (dist['Quantidade'] / total * 100).round(2)
    
    # Adiciona labels
    dist['Label'] = dist['Pares'].apply(
        lambda x: f"{x} Par{'es' if x != 1 else ''} / {6-x} Ímpar{'es' if (6-x) != 1 else ''}"
    )
    
    return dist


def get_delay_analysis(df: pd.DataFrame, df_melted: pd.DataFrame, top_n: int = 15) -> pd.DataFrame:
    """
    Analisa atraso das dezenas (quantos concursos desde última aparição)
    """
    if df.empty or df_melted.empty:
        return pd.DataFrame()
    
    ultimo_concurso = df['Concurso'].max()
    
    # Encontra último sorteio de cada dezena
    ultimo_sorteio = df_melted.groupby('Dezena')['Concurso'].max().reset_index()
    ultimo_sorteio.columns = ['Dezena', 'UltimoConcurso']
    
    # Calcula atraso atual
    ultimo_sorteio['Atraso'] = ultimo_concurso - ultimo_sorteio['UltimoConcurso']
    
    # Calcula atraso médio histórico (intervalo médio entre aparições)
    def calc_media_atraso(dezena):
        concursos = df_melted[df_melted['Dezena'] == dezena]['Concurso'].sort_values().values
        if len(concursos) < 2:
            return 0, 0
        diffs = np.diff(concursos)
        return round(diffs.mean(), 1), round(diffs.std(), 1)
    
    atrasos_medios = []
    for dezena in range(1, 61):
        media, std = calc_media_atraso(dezena)
        atrasos_medios.append({'Dezena': dezena, 'AtrasoMedio': media, 'AtrasoStd': std})
    
    atrasos_df = pd.DataFrame(atrasos_medios)
    
    # Junta dados
    resultado = ultimo_sorteio.merge(atrasos_df, on='Dezena')
    
    # Classifica status
    def get_status(row):
        if row['AtrasoMedio'] == 0:
            return 'normal'
        ratio = row['Atraso'] / row['AtrasoMedio']
        if ratio > 2:
            return 'critico'
        elif ratio > 1.5:
            return 'atencao'
        else:
            return 'normal'
    
    resultado['Status'] = resultado.apply(get_status, axis=1)
    
    # Ordena por atraso (maior primeiro) e retorna top N
    resultado = resultado.sort_values('Atraso', ascending=False).head(top_n)
    
    return resultado


def get_frequent_pairs(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """
    Encontra pares de números mais frequentes
    """
    if df.empty:
        return pd.DataFrame()
    
    pair_counter = Counter()
    
    for _, row in df.iterrows():
        dezenas = sorted([int(row[col]) for col in BOLA_COLUMNS if col in row.index])
        # Gera todos os pares possíveis
        for pair in combinations(dezenas, 2):
            pair_counter[pair] += 1
    
    # Converte para DataFrame
    pairs_data = [
        {'Par': f"{p[0]:02d} - {p[1]:02d}", 'Num1': p[0], 'Num2': p[1], 'Frequencia': count}
        for p, count in pair_counter.most_common(top_n)
    ]
    
    return pd.DataFrame(pairs_data)


def get_frequent_trios(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """
    Encontra trios de números mais frequentes (mais pesado computacionalmente)
    """
    if df.empty:
        return pd.DataFrame()
    
    trio_counter = Counter()
    
    for _, row in df.iterrows():
        dezenas = sorted([int(row[col]) for col in BOLA_COLUMNS if col in row.index])
        # Gera todos os trios possíveis
        for trio in combinations(dezenas, 3):
            trio_counter[trio] += 1
    
    # Converte para DataFrame
    trios_data = [
        {'Trio': f"{t[0]:02d} - {t[1]:02d} - {t[2]:02d}", 'Frequencia': count}
        for t, count in trio_counter.most_common(top_n)
    ]
    
    return pd.DataFrame(trios_data)


def get_temporal_trend(df: pd.DataFrame, df_melted: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    """
    Analisa tendência temporal das dezenas mais sorteadas
    """
    if df.empty or df_melted.empty or 'Ano' not in df.columns:
        return pd.DataFrame()
    
    # Identifica top N dezenas mais sorteadas
    top_dezenas = df_melted['Dezena'].value_counts().head(top_n).index.tolist()
    
    # Adiciona ano ao melted
    df_melted_with_year = df_melted.merge(df[['Concurso', 'Ano']], on='Concurso')
    
    # Filtra apenas top dezenas
    df_filtered = df_melted_with_year[df_melted_with_year['Dezena'].isin(top_dezenas)]
    
    # Agrupa por ano e dezena
    trend = df_filtered.groupby(['Ano', 'Dezena']).size().reset_index(name='Frequencia')
    
    # Pivot para ter dezenas como colunas
    trend_pivot = trend.pivot(index='Ano', columns='Dezena', values='Frequencia').fillna(0)
    
    return trend_pivot


def get_sum_analysis(df: pd.DataFrame) -> Dict:
    """
    Analisa distribuição da soma das dezenas
    """
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
        'valores': somas.values
    }


def classify_numbers(df_melted: pd.DataFrame) -> Dict[str, List[int]]:
    """
    Classifica números em quentes, frios e neutros
    """
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


def compare_game(game: List[int], df: pd.DataFrame) -> Dict:
    """
    Compara um jogo com o histórico
    """
    if df.empty:
        return {}
    
    game_set = set(game)
    
    # Verifica se a combinação exata já saiu
    exact_matches = 0
    five_matches = 0
    four_matches = 0
    
    for _, row in df.iterrows():
        dezenas = set([int(row[col]) for col in BOLA_COLUMNS if col in row.index])
        matches = len(game_set & dezenas)
        
        if matches == 6:
            exact_matches += 1
        elif matches == 5:
            five_matches += 1
        elif matches == 4:
            four_matches += 1
    
    # Calcula soma e paridade
    soma = sum(game)
    pares = sum(1 for d in game if d % 2 == 0)
    
    # Score de originalidade (baseado em combinações similares)
    total_jogos = len(df)
    similar_ratio = (five_matches + four_matches) / total_jogos if total_jogos > 0 else 0
    originalidade = round((1 - similar_ratio) * 100, 2)
    
    return {
        'jogo': sorted(game),
        'soma': soma,
        'pares': pares,
        'impares': 6 - pares,
        'combinacao_exata': exact_matches,
        'cinco_acertos': five_matches,
        'quatro_acertos': four_matches,
        'originalidade': originalidade
    }
