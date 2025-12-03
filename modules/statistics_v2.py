"""
LotoVision - Módulo de Estatísticas v2
Suporte para múltiplos jogos: Mega Sena, Quina, Lotofácil
"""

import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, List, Optional
import random
from dataclasses import dataclass

from modules.game_config import GameConfig


@dataclass
class ChiSquareResult:
    """Resultado do teste Chi-Quadrado"""
    chi_statistic: float
    p_value: float
    is_uniform: bool
    interpretation: str
    observed: np.ndarray
    expected: np.ndarray


def chi_square_test(df_melted: pd.DataFrame, game_config: GameConfig) -> Optional[ChiSquareResult]:
    """Executa teste Chi-Quadrado para verificar uniformidade"""
    if df_melted.empty:
        return None
    
    max_num = game_config.max_number
    observed = np.zeros(max_num)
    freq = df_melted['Dezena'].value_counts()
    
    for dezena, count in freq.items():
        if 1 <= dezena <= max_num:
            observed[int(dezena) - 1] = count
    
    total_dezenas = observed.sum()
    expected = np.full(max_num, total_dezenas / max_num)
    
    chi_stat, p_value = stats.chisquare(observed, expected)
    
    is_uniform = p_value > 0.05
    
    if p_value > 0.10:
        interpretation = (
            f"Os dados da {game_config.name} apresentam distribuição estatisticamente uniforme. "
            "Não há evidências de viés nos sorteios."
        )
    elif p_value > 0.05:
        interpretation = (
            "Os dados estão dentro da margem aceitável de aleatoriedade. "
            "Pequenas variações são normais."
        )
    elif p_value > 0.01:
        interpretation = (
            "⚠️ Há uma leve variação na distribuição, mas pode ser explicada "
            "por flutuações naturais."
        )
    else:
        interpretation = (
            "⚠️ A distribuição apresenta desvios significativos. "
            "Isso NÃO significa que você pode prever sorteios futuros."
        )
    
    return ChiSquareResult(
        chi_statistic=round(chi_stat, 2),
        p_value=round(p_value, 4),
        is_uniform=is_uniform,
        interpretation=interpretation,
        observed=observed,
        expected=expected
    )


def sum_normality_test(df: pd.DataFrame, game_config: GameConfig) -> Dict:
    """Testa se a distribuição das somas segue distribuição normal"""
    if df.empty or 'Soma' not in df.columns:
        return {}
    
    somas = df['Soma'].values
    
    if len(somas) < 5000:
        stat, p_value = stats.shapiro(somas[:5000])
        test_name = "Shapiro-Wilk"
    else:
        stat, p_value = stats.normaltest(somas)
        test_name = "D'Agostino-Pearson"
    
    mean = np.mean(somas)
    std = np.std(somas)
    
    lower_68 = mean - std
    upper_68 = mean + std
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
        'range_68': (round(lower_68, 0), round(upper_68, 0)),
        'range_95': (round(lower_95, 0), round(upper_95, 0)),
        'interpretation': (
            f"A soma média dos jogos da {game_config.name} é {mean:.0f} com desvio padrão de {std:.0f}. "
            f"Aproximadamente 68% dos jogos têm soma entre {lower_68:.0f} e {upper_68:.0f}."
        )
    }


def monte_carlo_simulation(game_config: GameConfig, n_simulations: int = 10000, 
                           progress_callback=None) -> Dict:
    """Simulação Monte Carlo para demonstrar aleatoriedade"""
    
    n_balls = game_config.n_balls
    max_num = game_config.max_number
    total_combinations = game_config.total_combinations
    
    results = {
        'acerto_total': 0,
        'acerto_menos_1': 0,
        'acerto_menos_2': 0,
        'acerto_menos_3': 0,
        'poucos_acertos': 0,
        'nada': 0
    }
    
    for i in range(n_simulations):
        jogo = set(random.sample(range(1, max_num + 1), n_balls))
        sorteio = set(random.sample(range(1, max_num + 1), n_balls))
        
        acertos = len(jogo & sorteio)
        
        if acertos == n_balls:
            results['acerto_total'] += 1
        elif acertos == n_balls - 1:
            results['acerto_menos_1'] += 1
        elif acertos == n_balls - 2:
            results['acerto_menos_2'] += 1
        elif acertos == n_balls - 3:
            results['acerto_menos_3'] += 1
        elif acertos > 0:
            results['poucos_acertos'] += 1
        else:
            results['nada'] += 1
        
        if progress_callback and i % 1000 == 0:
            progress_callback(i / n_simulations)
    
    # Calcula proporções
    for key in list(results.keys()):
        results[f'{key}_pct'] = round(results[key] / n_simulations * 100, 4)
    
    results['n_simulations'] = n_simulations
    results['total_combinations'] = total_combinations
    results['game_name'] = game_config.name
    
    # Labels específicos por jogo
    if game_config.slug == "mega_sena":
        labels = {'acerto_total': 'Sena', 'acerto_menos_1': 'Quina', 'acerto_menos_2': 'Quadra'}
    elif game_config.slug == "quina":
        labels = {'acerto_total': 'Quina', 'acerto_menos_1': 'Quadra', 'acerto_menos_2': 'Terno'}
    else:  # lotofacil
        labels = {'acerto_total': '15 Pts', 'acerto_menos_1': '14 Pts', 'acerto_menos_2': '13 Pts'}
    
    results['labels'] = labels
    
    results['interpretation'] = (
        f"Em {n_simulations:,} jogos simulados da {game_config.name}:\n"
        f"• {labels['acerto_total']}: {results['acerto_total']} ({results['acerto_total_pct']:.2f}%)\n"
        f"• {labels['acerto_menos_1']}: {results['acerto_menos_1']} ({results['acerto_menos_1_pct']:.2f}%)\n"
        f"• {labels['acerto_menos_2']}: {results['acerto_menos_2']} ({results['acerto_menos_2_pct']:.2f}%)\n\n"
        f"Probabilidade real de acertar: 1 em {total_combinations:,}"
    )
    
    return results


def runs_test(df_melted: pd.DataFrame, game_config: GameConfig) -> Dict:
    """Teste de runs para verificar aleatoriedade"""
    if df_melted.empty:
        return {}
    
    dezenas = df_melted.sort_values('Concurso')['Dezena'].values
    mediana = np.median(dezenas)
    
    binary = ['A' if d > mediana else 'B' for d in dezenas]
    
    runs = 1
    for i in range(1, len(binary)):
        if binary[i] != binary[i-1]:
            runs += 1
    
    n1 = sum(1 for b in binary if b == 'A')
    n2 = sum(1 for b in binary if b == 'B')
    n = n1 + n2
    
    expected_runs = (2 * n1 * n2) / n + 1
    variance = (2 * n1 * n2 * (2 * n1 * n2 - n)) / (n * n * (n - 1))
    
    z = (runs - expected_runs) / np.sqrt(variance) if variance > 0 else 0
    p_value = 2 * (1 - stats.norm.cdf(abs(z)))
    
    is_random = p_value > 0.05
    
    return {
        'runs_observed': runs,
        'runs_expected': round(expected_runs, 2),
        'z_score': round(z, 4),
        'p_value': round(p_value, 4),
        'is_random': is_random,
        'interpretation': (
            f"A sequência de sorteios da {game_config.name} apresenta aleatoriedade adequada."
            if is_random else
            "A sequência pode apresentar algum padrão, mas isso não permite previsões."
        )
    }


def get_statistical_summary(df: pd.DataFrame, df_melted: pd.DataFrame, 
                           game_config: GameConfig) -> Dict:
    """Retorna resumo completo das análises estatísticas"""
    chi_result = chi_square_test(df_melted, game_config)
    sum_result = sum_normality_test(df, game_config)
    runs_result = runs_test(df_melted, game_config)
    
    return {
        'chi_square': chi_result,
        'sum_normality': sum_result,
        'runs_test': runs_result,
        'game_name': game_config.name
    }
