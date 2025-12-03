"""
LotoVision - Módulo Gerador de Jogos v2
Suporte para múltiplos jogos: Mega Sena, Quina, Lotofácil
"""

import pandas as pd
import numpy as np
import random
from typing import List, Dict, Set, Optional
from dataclasses import dataclass, field
from enum import Enum

from modules.game_config import GameConfig


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
    max_evens: int = 100
    min_sum: int = 0
    max_sum: int = 10000
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
    game_type: str = ""
    metadata: Dict = field(default_factory=dict)


class GameGenerator:
    """Gerador de jogos para qualquer loteria"""
    
    def __init__(self, df: pd.DataFrame, df_melted: pd.DataFrame, game_config: GameConfig):
        self.df = df
        self.df_melted = df_melted
        self.config = game_config
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
            self.avg_sum = 0
            self.avg_evens = self.config.n_balls // 2
            return
        
        ball_cols = self.config.ball_columns
        
        freq = self.df_melted['Dezena'].value_counts()
        self.frequency = freq.to_dict()
        
        mean_freq = freq.mean()
        std_freq = freq.std()
        
        self.hot_numbers = set(freq[freq > mean_freq + std_freq / 2].index.tolist())
        self.cold_numbers = set(freq[freq < mean_freq - std_freq / 2].index.tolist())
        
        self.top_10_drawn = set(freq.head(10).index.tolist())
        
        ultimo_concurso = self.df['Concurso'].max()
        ultimo_sorteio = self.df_melted.groupby('Dezena')['Concurso'].max()
        atraso = ultimo_concurso - ultimo_sorteio
        atraso_medio = atraso.mean()
        self.delayed_numbers = set(atraso[atraso > atraso_medio * 1.5].index.tolist())
        
        ultimo_row = self.df.iloc[-1]
        self.last_draw = set([int(ultimo_row[col]) for col in ball_cols 
                              if col in ultimo_row.index and pd.notna(ultimo_row[col])])
        
        self.avg_sum = self.df['Soma'].mean() if 'Soma' in self.df.columns else 0
        self.avg_evens = self.df['Pares'].mean() if 'Pares' in self.df.columns else self.config.n_balls // 2
    
    def _get_valid_pool(self, filters: GameFilters) -> Set[int]:
        """Retorna pool de números válidos baseado nos filtros"""
        pool = set(range(1, self.config.max_number + 1))
        
        if filters.exclude_last_draw:
            pool -= self.last_draw
        
        if filters.exclude_most_drawn:
            pool -= self.top_10_drawn
        
        for num in filters.fixed_numbers:
            pool.add(num)
        
        return pool
    
    def _validate_game(self, game: List[int], filters: GameFilters) -> bool:
        """Valida se um jogo atende aos filtros"""
        n_balls = self.config.n_balls
        
        if len(game) != n_balls:
            return False
        
        if len(set(game)) != n_balls:
            return False
        
        if not all(1 <= n <= self.config.max_number for n in game):
            return False
        
        evens = sum(1 for n in game if n % 2 == 0)
        if evens < filters.min_evens or evens > filters.max_evens:
            return False
        
        total = sum(game)
        if total < filters.min_sum or total > filters.max_sum:
            return False
        
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
            hot_pool = [n for n in pool if n in self.hot_numbers]
            cold_pool = [n for n in pool if n in self.cold_numbers]
            neutral_pool = [n for n in pool if n not in self.hot_numbers and n not in self.cold_numbers]
            
            selected = []
            hot_needed = needed // 2
            cold_needed = needed - hot_needed
            
            if hot_pool:
                hot_count = min(hot_needed, len(hot_pool))
                selected.extend(random.sample(hot_pool, hot_count))
            
            if cold_pool:
                cold_count = min(cold_needed, len(cold_pool))
                selected.extend(random.sample(cold_pool, cold_count))
            
            remaining = needed - len(selected)
            if remaining > 0 and neutral_pool:
                available = [n for n in neutral_pool if n not in selected]
                selected.extend(random.sample(available, min(remaining, len(available))))
            
            remaining = needed - len(selected)
            if remaining > 0:
                available = [n for n in pool if n not in selected]
                selected.extend(random.sample(available, min(remaining, len(available))))
            
            return selected
        
        elif strategy == Strategy.CONTRARIAN:
            delayed_pool = [n for n in pool if n in self.delayed_numbers]
            other_pool = [n for n in pool if n not in self.delayed_numbers]
            
            selected = []
            
            delayed_count = min(needed * 2 // 3, len(delayed_pool), needed)
            if delayed_pool:
                selected.extend(random.sample(delayed_pool, delayed_count))
            
            remaining = needed - len(selected)
            if remaining > 0 and other_pool:
                available = [n for n in other_pool if n not in selected]
                selected.extend(random.sample(available, min(remaining, len(available))))
            
            return selected
        
        return random.sample(pool, needed)
    
    def _calculate_score(self, game: List[int]) -> float:
        """Calcula score de compatibilidade"""
        score = 100.0
        
        game_sum = sum(game)
        if self.avg_sum > 0:
            sum_diff = abs(game_sum - self.avg_sum)
            if sum_diff > self.avg_sum * 0.3:
                score -= min(20, sum_diff / self.avg_sum * 30)
        
        evens = sum(1 for n in game if n % 2 == 0)
        n_balls = self.config.n_balls
        
        if evens == 0 or evens == n_balls:
            score -= 15
        elif evens == 1 or evens == n_balls - 1:
            score -= 5
        
        delayed = sum(1 for n in game if n in self.delayed_numbers)
        score += delayed * 2
        
        hot = sum(1 for n in game if n in self.hot_numbers)
        cold = sum(1 for n in game if n in self.cold_numbers)
        if hot > 0 and cold > 0:
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
            odds=self.config.n_balls - evens,
            delayed_count=delayed,
            hot_count=hot,
            cold_count=cold,
            compatibility_score=self._calculate_score(sorted_game),
            game_type=self.config.name,
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
        
        if len(pool) < self.config.n_balls:
            return None
        
        pool_list = list(pool)
        
        for _ in range(max_attempts):
            game = list(filters.fixed_numbers)
            needed = self.config.n_balls - len(game)
            
            if needed > 0:
                available = [n for n in pool_list if n not in game]
                
                if len(available) < needed:
                    continue
                
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
                   game_config: GameConfig,
                   n_games: int = 1,
                   strategy: str = "random",
                   exclude_last: bool = False,
                   exclude_top: bool = False,
                   min_evens: int = 0,
                   max_evens: int = 100,
                   min_sum: int = 0,
                   max_sum: int = 10000,
                   fixed_numbers: List[int] = None) -> List[GeneratedGame]:
    """Função de conveniência para geração rápida de jogos"""
    generator = GameGenerator(df, df_melted, game_config)
    
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
**Jogo #{index} ({game.game_type}):** {numbers_str}
- 📊 Soma: {game.sum_value}
- ⚖️ Paridade: {game.evens} Pares / {game.odds} Ímpares
- ⏳ Atrasados: {game.delayed_count}
- ⭐ Compatibilidade: {game.compatibility_score:.0f}%
"""
