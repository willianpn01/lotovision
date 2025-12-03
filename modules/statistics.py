"""
LotoVision - Módulo de Estatísticas
Validações estatísticas: Chi-Quadrado, Monte Carlo, etc.
"""

import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, List, Tuple, Optional
import random
from dataclasses import dataclass


BOLA_COLUMNS = [f'Bola_{i}' for i in range(1, 7)]


@dataclass
class ChiSquareResult:
    """Resultado do teste Chi-Quadrado"""
    chi_statistic: float
    p_value: float
    is_uniform: bool
    interpretation: str
    observed: np.ndarray
    expected: np.ndarray


def chi_square_test(df_melted: pd.DataFrame) -> Optional[ChiSquareResult]:
    """
    Executa teste Chi-Quadrado para verificar se a distribuição é uniforme
    
    Hipótese Nula (H0): A distribuição das dezenas é uniforme (aleatória)
    Se p-value > 0.05: Não rejeitamos H0 (distribuição uniforme)
    Se p-value <= 0.05: Rejeitamos H0 (distribuição não uniforme)
    """
    if df_melted.empty:
        return None
    
    # Frequência observada de cada número (1-60)
    observed = np.zeros(60)
    freq = df_melted['Dezena'].value_counts()
    
    for dezena, count in freq.items():
        if 1 <= dezena <= 60:
            observed[int(dezena) - 1] = count
    
    # Frequência esperada (uniforme)
    total_dezenas = observed.sum()
    expected = np.full(60, total_dezenas / 60)
    
    # Teste Chi-Quadrado
    chi_stat, p_value = stats.chisquare(observed, expected)
    
    # Interpretação
    is_uniform = p_value > 0.05
    
    if p_value > 0.10:
        interpretation = (
            "Os dados apresentam uma distribuição estatisticamente uniforme. "
            "Não há evidências de viés nos sorteios. "
            "Isso é esperado em uma loteria justa."
        )
    elif p_value > 0.05:
        interpretation = (
            "Os dados estão dentro da margem aceitável de aleatoriedade. "
            "Pequenas variações são normais em qualquer amostra finita."
        )
    elif p_value > 0.01:
        interpretation = (
            "⚠️ Há uma leve variação na distribuição, mas pode ser explicada "
            "por flutuações naturais. Recomenda-se analisar com mais dados."
        )
    else:
        interpretation = (
            "⚠️ A distribuição apresenta desvios significativos da aleatoriedade. "
            "Isso pode indicar padrões nos dados ou problemas na amostra. "
            "Note que isso NÃO significa que você pode prever sorteios futuros."
        )
    
    return ChiSquareResult(
        chi_statistic=round(chi_stat, 2),
        p_value=round(p_value, 4),
        is_uniform=is_uniform,
        interpretation=interpretation,
        observed=observed,
        expected=expected
    )


def sum_normality_test(df: pd.DataFrame) -> Dict:
    """
    Testa se a distribuição das somas segue uma distribuição normal
    """
    if df.empty or 'Soma' not in df.columns:
        return {}
    
    somas = df['Soma'].values
    
    # Teste de normalidade (Shapiro-Wilk para amostras menores, D'Agostino para maiores)
    if len(somas) < 5000:
        stat, p_value = stats.shapiro(somas[:5000])  # Shapiro tem limite
        test_name = "Shapiro-Wilk"
    else:
        stat, p_value = stats.normaltest(somas)
        test_name = "D'Agostino-Pearson"
    
    # Estatísticas descritivas
    mean = np.mean(somas)
    std = np.std(somas)
    skewness = stats.skew(somas)
    kurtosis = stats.kurtosis(somas)
    
    # Intervalo onde 68% dos jogos caem (média ± 1 std)
    lower_68 = mean - std
    upper_68 = mean + std
    
    # Intervalo onde 95% dos jogos caem (média ± 2 std)
    lower_95 = mean - 2 * std
    upper_95 = mean + 2 * std
    
    is_normal = p_value > 0.05
    
    return {
        'test_name': test_name,
        'statistic': round(stat, 4),
        'p_value': round(p_value, 4),
        'is_normal': is_normal,
        'mean': round(mean, 2),
        'std': round(std, 2),
        'skewness': round(skewness, 4),
        'kurtosis': round(kurtosis, 4),
        'range_68': (round(lower_68, 0), round(upper_68, 0)),
        'range_95': (round(lower_95, 0), round(upper_95, 0)),
        'interpretation': (
            f"A soma média dos jogos é {mean:.0f} com desvio padrão de {std:.0f}. "
            f"Aproximadamente 68% dos jogos têm soma entre {lower_68:.0f} e {upper_68:.0f}. "
            f"Jogos com soma abaixo de {lower_95:.0f} ou acima de {upper_95:.0f} são estatisticamente raros."
        )
    }


def monte_carlo_simulation(n_simulations: int = 10000, 
                           progress_callback=None) -> Dict:
    """
    Simulação Monte Carlo para demonstrar aleatoriedade
    
    Gera jogos aleatórios e compara com probabilidades teóricas
    """
    # Probabilidades teóricas da Mega Sena
    # Total de combinações: C(60,6) = 50.063.860
    total_combinations = 50063860
    
    results = {
        'sena': 0,
        'quina': 0,
        'quadra': 0,
        'terno': 0,
        'duque': 0,
        'nada': 0
    }
    
    # Simula jogos
    for i in range(n_simulations):
        # Gera um jogo "apostado"
        jogo = set(random.sample(range(1, 61), 6))
        
        # Gera um "sorteio"
        sorteio = set(random.sample(range(1, 61), 6))
        
        # Conta acertos
        acertos = len(jogo & sorteio)
        
        if acertos == 6:
            results['sena'] += 1
        elif acertos == 5:
            results['quina'] += 1
        elif acertos == 4:
            results['quadra'] += 1
        elif acertos == 3:
            results['terno'] += 1
        elif acertos == 2:
            results['duque'] += 1
        else:
            results['nada'] += 1
        
        # Callback de progresso
        if progress_callback and i % 1000 == 0:
            progress_callback(i / n_simulations)
    
    # Calcula proporções observadas
    for key in list(results.keys()):
        results[f'{key}_pct'] = round(results[key] / n_simulations * 100, 4)
    
    # Probabilidades teóricas
    theoretical = {
        'sena_prob': 1 / total_combinations,
        'quina_prob': 258 / total_combinations,  # C(6,5) * C(54,1) = 6 * 54 / C(60,6)
        'quadra_prob': 21.945 / total_combinations * 1000,  # Aproximado
    }
    
    results['n_simulations'] = n_simulations
    results['theoretical'] = theoretical
    results['interpretation'] = (
        f"Em {n_simulations:,} jogos simulados:\n"
        f"• Senas: {results['sena']} (esperado: ~0)\n"
        f"• Quinas: {results['quina']} ({results['quina_pct']:.2f}%)\n"
        f"• Quadras: {results['quadra']} ({results['quadra_pct']:.2f}%)\n\n"
        f"Isso demonstra que a loteria é um jogo de puro azar. "
        f"Estratégias baseadas em histórico não alteram estas probabilidades."
    )
    
    return results


def analyze_sequences(df: pd.DataFrame) -> Dict:
    """
    Analisa padrões de sequências consecutivas nos jogos
    """
    if df.empty:
        return {}
    
    sequences = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0}  # 0 = sem sequência
    
    for _, row in df.iterrows():
        dezenas = sorted([int(row[col]) for col in BOLA_COLUMNS if col in row.index])
        
        # Conta sequências consecutivas
        max_seq = 1
        current_seq = 1
        
        for i in range(1, len(dezenas)):
            if dezenas[i] == dezenas[i-1] + 1:
                current_seq += 1
                max_seq = max(max_seq, current_seq)
            else:
                current_seq = 1
        
        seq_key = min(max_seq - 1, 5)  # max_seq - 1 porque 1 número sozinho não é sequência
        sequences[seq_key] = sequences.get(seq_key, 0) + 1
    
    total = sum(sequences.values())
    
    result = {
        'distribution': sequences,
        'percentages': {k: round(v/total*100, 2) for k, v in sequences.items()},
        'total_games': total
    }
    
    return result


def correlation_analysis(df_melted: pd.DataFrame) -> pd.DataFrame:
    """
    Analisa correlação entre posições das dezenas
    Verifica se há padrões entre qual dezena sai em qual posição
    """
    if df_melted.empty:
        return pd.DataFrame()
    
    # Pivot: Concurso x Posição -> Dezena
    pivot = df_melted.pivot(index='Concurso', columns='Posicao', values='Dezena')
    
    # Calcula correlação entre posições
    correlation = pivot.corr()
    
    return correlation


def runs_test(df_melted: pd.DataFrame) -> Dict:
    """
    Teste de runs para verificar aleatoriedade nas sequências
    Verifica se a alternância entre números acima/abaixo da mediana é aleatória
    """
    if df_melted.empty:
        return {}
    
    # Ordena por concurso
    dezenas = df_melted.sort_values('Concurso')['Dezena'].values
    
    mediana = np.median(dezenas)
    
    # Converte para binário (acima/abaixo da mediana)
    binary = ['A' if d > mediana else 'B' for d in dezenas]
    
    # Conta runs (sequências de mesmo tipo)
    runs = 1
    for i in range(1, len(binary)):
        if binary[i] != binary[i-1]:
            runs += 1
    
    # Contagem de cada tipo
    n1 = sum(1 for b in binary if b == 'A')
    n2 = sum(1 for b in binary if b == 'B')
    n = n1 + n2
    
    # Média e variância esperadas para distribuição de runs
    expected_runs = (2 * n1 * n2) / n + 1
    variance = (2 * n1 * n2 * (2 * n1 * n2 - n)) / (n * n * (n - 1))
    
    # Z-score
    z = (runs - expected_runs) / np.sqrt(variance) if variance > 0 else 0
    
    # P-value (bilateral)
    p_value = 2 * (1 - stats.norm.cdf(abs(z)))
    
    is_random = p_value > 0.05
    
    return {
        'runs_observed': runs,
        'runs_expected': round(expected_runs, 2),
        'z_score': round(z, 4),
        'p_value': round(p_value, 4),
        'is_random': is_random,
        'interpretation': (
            "A sequência de sorteios apresenta aleatoriedade adequada."
            if is_random else
            "A sequência de sorteios pode apresentar algum padrão, mas isso não permite previsões."
        )
    }


def get_statistical_summary(df: pd.DataFrame, df_melted: pd.DataFrame) -> Dict:
    """
    Retorna resumo completo das análises estatísticas
    """
    chi_result = chi_square_test(df_melted)
    sum_result = sum_normality_test(df)
    runs_result = runs_test(df_melted)
    
    return {
        'chi_square': chi_result,
        'sum_normality': sum_result,
        'runs_test': runs_result,
        'overall_assessment': (
            "Os dados apresentam características consistentes com sorteios aleatórios. "
            "Não foram encontradas evidências de padrões exploráveis."
            if (chi_result and chi_result.is_uniform and runs_result.get('is_random', True))
            else
            "Algumas variações foram detectadas, mas são consistentes com flutuações naturais."
        )
    }
