"""
LotoVision - Módulo Gerador de Jogos
Geração inteligente de jogos com filtros e estratégias
"""

import pandas as pd
import numpy as np
import random
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


BOLA_COLUMNS = [f'Bola_{i}' for i in range(1, 7)]


class Strategy(Enum):
    RANDOM = "random"
    BALANCED = "balanced"
    CONTRARIAN = "contrarian"


@dataclass
class GameFilters:
    """Filtros para geração de jogos"""
    exclude_last_draw: bool = False
    exclude_most_drawn: bool = False
    min_evens: int = 0
    max_evens: int = 6
    min_sum: int = 21  # Soma mínima possível: 1+2+3+4+5+6 = 21
    max_sum: int = 345  # Soma máxima possível: 55+56+57+58+59+60 = 345
    fixed_numbers: List[int] = field(default_factory=list)
    strategy: Strategy = Strategy.RANDOM


@dataclass 
class GeneratedGame:
    """Jogo gerado com metadados"""
    numbers: List[int]
    sum_value: int
    evens: int
    odds: int
    delayed_count: int
    hot_count: int
    cold_count: int
    compatibility_score: float
    metadata: Dict = field(default_factory=dict)


class GameGenerator:
    """Gerador de jogos da Mega Sena"""
    
    def __init__(self, df: pd.DataFrame, df_melted: pd.DataFrame):
        self.df = df
        self.df_melted = df_melted
        self._analyze_data()
    
    def _analyze_data(self):
        """Pré-analisa dados para otimizar geração"""
        if self.df.empty or self.df_melted.empty:
            self.hot_numbers = set()
            self.cold_numbers = set()
            self.delayed_numbers = set()
            self.last_draw = set()
            self.top_10_drawn = set()
            self.frequency = {}
            self.avg_sum = 180
            self.avg_evens = 3
            return
        
        # Frequência de cada dezena
        freq = self.df_melted['Dezena'].value_counts()
        self.frequency = freq.to_dict()
        
        # Classifica números
        mean_freq = freq.mean()
        std_freq = freq.std()
        
        self.hot_numbers = set(freq[freq > mean_freq + std_freq / 2].index.tolist())
        self.cold_numbers = set(freq[freq < mean_freq - std_freq / 2].index.tolist())
        
        # Top 10 mais sorteados
        self.top_10_drawn = set(freq.head(10).index.tolist())
        
        # Números atrasados (acima da média de atraso)
        ultimo_concurso = self.df['Concurso'].max()
        ultimo_sorteio = self.df_melted.groupby('Dezena')['Concurso'].max()
        atraso = ultimo_concurso - ultimo_sorteio
        atraso_medio = atraso.mean()
        self.delayed_numbers = set(atraso[atraso > atraso_medio * 1.5].index.tolist())
        
        # Último sorteio
        ultimo_row = self.df.iloc[-1]
        self.last_draw = set([int(ultimo_row[col]) for col in BOLA_COLUMNS])
        
        # Médias históricas
        self.avg_sum = self.df['Soma'].mean() if 'Soma' in self.df.columns else 180
        self.avg_evens = self.df['Pares'].mean() if 'Pares' in self.df.columns else 3
    
    def _get_valid_pool(self, filters: GameFilters) -> Set[int]:
        """Retorna pool de números válidos baseado nos filtros"""
        pool = set(range(1, 61))
        
        # Remove números do último sorteio
        if filters.exclude_last_draw:
            pool -= self.last_draw
        
        # Remove números mais sorteados
        if filters.exclude_most_drawn:
            pool -= self.top_10_drawn
        
        # Garante que números fixos estejam no pool
        for num in filters.fixed_numbers:
            pool.add(num)
        
        return pool
    
    def _validate_game(self, game: List[int], filters: GameFilters) -> bool:
        """Valida se um jogo atende aos filtros"""
        if len(game) != 6:
            return False
        
        if len(set(game)) != 6:  # Sem duplicatas
            return False
        
        # Validação de range
        if not all(1 <= n <= 60 for n in game):
            return False
        
        # Validação de paridade
        evens = sum(1 for n in game if n % 2 == 0)
        if evens < filters.min_evens or evens > filters.max_evens:
            return False
        
        # Validação de soma
        total = sum(game)
        if total < filters.min_sum or total > filters.max_sum:
            return False
        
        # Números fixos devem estar presentes
        for num in filters.fixed_numbers:
            if num not in game:
                return False
        
        return True
    
    def _apply_strategy(self, pool: List[int], needed: int, 
                        strategy: Strategy) -> List[int]:
        """Aplica estratégia de seleção"""
        if strategy == Strategy.RANDOM:
            return random.sample(pool, needed)
        
        elif strategy == Strategy.BALANCED:
            # 50% quentes, 50% frios
            hot_pool = [n for n in pool if n in self.hot_numbers]
            cold_pool = [n for n in pool if n in self.cold_numbers]
            neutral_pool = [n for n in pool if n not in self.hot_numbers and n not in self.cold_numbers]
            
            selected = []
            hot_needed = needed // 2
            cold_needed = needed - hot_needed
            
            # Seleciona quentes
            if hot_pool:
                hot_count = min(hot_needed, len(hot_pool))
                selected.extend(random.sample(hot_pool, hot_count))
            
            # Seleciona frios
            if cold_pool:
                cold_count = min(cold_needed, len(cold_pool))
                selected.extend(random.sample(cold_pool, cold_count))
            
            # Completa com neutros se necessário
            remaining = needed - len(selected)
            if remaining > 0 and neutral_pool:
                available = [n for n in neutral_pool if n not in selected]
                selected.extend(random.sample(available, min(remaining, len(available))))
            
            # Se ainda falta, pega qualquer um
            remaining = needed - len(selected)
            if remaining > 0:
                available = [n for n in pool if n not in selected]
                selected.extend(random.sample(available, min(remaining, len(available))))
            
            return selected
        
        elif strategy == Strategy.CONTRARIAN:
            # Prioriza números atrasados
            delayed_pool = [n for n in pool if n in self.delayed_numbers]
            other_pool = [n for n in pool if n not in self.delayed_numbers]
            
            selected = []
            
            # Tenta pegar maioria de atrasados
            delayed_count = min(4, len(delayed_pool), needed)
            if delayed_pool:
                selected.extend(random.sample(delayed_pool, delayed_count))
            
            # Completa com outros
            remaining = needed - len(selected)
            if remaining > 0 and other_pool:
                available = [n for n in other_pool if n not in selected]
                selected.extend(random.sample(available, min(remaining, len(available))))
            
            return selected
        
        return random.sample(pool, needed)
    
    def _calculate_score(self, game: List[int]) -> float:
        """
        Calcula score de compatibilidade baseado em padrões históricos
        NOTA: Isso é puramente educacional, não aumenta chances de ganhar
        """
        score = 100.0
        
        # Penaliza soma muito fora da média
        game_sum = sum(game)
        sum_diff = abs(game_sum - self.avg_sum)
        if sum_diff > 50:
            score -= min(20, sum_diff / 5)
        
        # Penaliza paridade muito desequilibrada
        evens = sum(1 for n in game if n % 2 == 0)
        if evens in [0, 6]:
            score -= 15
        elif evens in [1, 5]:
            score -= 5
        
        # Bônus por ter números atrasados
        delayed = sum(1 for n in game if n in self.delayed_numbers)
        score += delayed * 2
        
        # Bônus por balanceamento quente/frio
        hot = sum(1 for n in game if n in self.hot_numbers)
        cold = sum(1 for n in game if n in self.cold_numbers)
        if 2 <= hot <= 4 and 1 <= cold <= 3:
            score += 10
        
        return min(100, max(0, score))
    
    def _create_game_metadata(self, game: List[int]) -> GeneratedGame:
        """Cria objeto de jogo com metadados"""
        sorted_game = sorted(game)
        
        evens = sum(1 for n in sorted_game if n % 2 == 0)
        delayed = sum(1 for n in sorted_game if n in self.delayed_numbers)
        hot = sum(1 for n in sorted_game if n in self.hot_numbers)
        cold = sum(1 for n in sorted_game if n in self.cold_numbers)
        
        return GeneratedGame(
            numbers=sorted_game,
            sum_value=sum(sorted_game),
            evens=evens,
            odds=6 - evens,
            delayed_count=delayed,
            hot_count=hot,
            cold_count=cold,
            compatibility_score=self._calculate_score(sorted_game),
            metadata={
                'delayed_numbers': [n for n in sorted_game if n in self.delayed_numbers],
                'hot_numbers': [n for n in sorted_game if n in self.hot_numbers],
                'cold_numbers': [n for n in sorted_game if n in self.cold_numbers]
            }
        )
    
    def generate_single(self, filters: GameFilters, 
                        max_attempts: int = 1000) -> Optional[GeneratedGame]:
        """Gera um único jogo"""
        pool = self._get_valid_pool(filters)
        
        if len(pool) < 6:
            return None
        
        pool_list = list(pool)
        
        for _ in range(max_attempts):
            # Começa com números fixos
            game = list(filters.fixed_numbers)
            needed = 6 - len(game)
            
            if needed > 0:
                # Remove fixos do pool disponível
                available = [n for n in pool_list if n not in game]
                
                if len(available) < needed:
                    continue
                
                # Aplica estratégia
                selected = self._apply_strategy(available, needed, filters.strategy)
                game.extend(selected)
            
            if self._validate_game(game, filters):
                return self._create_game_metadata(game)
        
        return None
    
    def generate_multiple(self, n_games: int, filters: GameFilters,
                          allow_duplicates: bool = False,
                          progress_callback=None) -> List[GeneratedGame]:
        """Gera múltiplos jogos"""
        games = []
        seen_combinations = set()
        attempts = 0
        max_total_attempts = n_games * 1000
        
        while len(games) < n_games and attempts < max_total_attempts:
            game = self.generate_single(filters)
            
            if game:
                combo = tuple(game.numbers)
                
                if allow_duplicates or combo not in seen_combinations:
                    games.append(game)
                    seen_combinations.add(combo)
                    
                    if progress_callback:
                        progress_callback(len(games) / n_games)
            
            attempts += 1
        
        return games


def quick_generate(df: pd.DataFrame, df_melted: pd.DataFrame,
                   n_games: int = 1,
                   strategy: str = "random",
                   exclude_last: bool = False,
                   exclude_top: bool = False,
                   min_evens: int = 0,
                   max_evens: int = 6,
                   min_sum: int = 21,
                   max_sum: int = 345,
                   fixed_numbers: List[int] = None) -> List[GeneratedGame]:
    """
    Função de conveniência para geração rápida de jogos
    """
    generator = GameGenerator(df, df_melted)
    
    strategy_map = {
        "random": Strategy.RANDOM,
        "balanced": Strategy.BALANCED,
        "contrarian": Strategy.CONTRARIAN
    }
    
    filters = GameFilters(
        exclude_last_draw=exclude_last,
        exclude_most_drawn=exclude_top,
        min_evens=min_evens,
        max_evens=max_evens,
        min_sum=min_sum,
        max_sum=max_sum,
        fixed_numbers=fixed_numbers or [],
        strategy=strategy_map.get(strategy, Strategy.RANDOM)
    )
    
    return generator.generate_multiple(n_games, filters)


def format_game_display(game: GeneratedGame, index: int = 1) -> str:
    """Formata jogo para exibição"""
    numbers_str = " - ".join([f"{n:02d}" for n in game.numbers])
    
    return f"""
**Jogo #{index}:** {numbers_str}
- 📊 Soma: {game.sum_value} {'(Média)' if 150 <= game.sum_value <= 210 else '(Fora da média)'}
- ⚖️ Paridade: {game.evens} Pares / {game.odds} Ímpares
- ⏳ Números atrasados: {game.delayed_count} ({', '.join(map(str, game.metadata.get('delayed_numbers', []))) if game.metadata.get('delayed_numbers') else 'nenhum'})
- ⭐ Compatibilidade: {game.compatibility_score:.0f}%
"""
