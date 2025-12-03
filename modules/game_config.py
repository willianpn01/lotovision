"""
LotoVision - Configurações dos Jogos
Define as regras e parâmetros de cada tipo de loteria
"""

from dataclasses import dataclass
from typing import List, Dict


@dataclass
class GameConfig:
    """Configuração de um jogo de loteria"""
    name: str
    slug: str
    n_balls: int
    min_number: int
    max_number: int
    total_combinations: int
    icon: str
    color_primary: str
    color_secondary: str
    description: str
    
    @property
    def ball_columns(self) -> List[str]:
        """Retorna lista de colunas das bolas"""
        return [f'Bola_{i}' for i in range(1, self.n_balls + 1)]
    
    @property
    def excel_columns(self) -> List[str]:
        """Retorna letras das colunas no Excel (C em diante)"""
        # C = 2 (0-indexed), então Bola_1 = C, Bola_2 = D, etc.
        return [chr(ord('C') + i) for i in range(self.n_balls)]


# Configurações dos jogos suportados
MEGA_SENA = GameConfig(
    name="Mega Sena",
    slug="mega_sena",
    n_balls=6,
    min_number=1,
    max_number=60,
    total_combinations=50_063_860,
    icon="🎰",
    color_primary="#209869",
    color_secondary="#1a7a54",
    description="Escolha 6 números de 1 a 60"
)

QUINA = GameConfig(
    name="Quina",
    slug="quina",
    n_balls=5,
    min_number=1,
    max_number=80,
    total_combinations=24_040_016,
    icon="⭐",
    color_primary="#260085",
    color_secondary="#1a005c",
    description="Escolha 5 números de 1 a 80"
)

LOTOFACIL = GameConfig(
    name="Lotofácil",
    slug="lotofacil",
    n_balls=15,
    min_number=1,
    max_number=25,
    total_combinations=3_268_760,
    icon="🍀",
    color_primary="#930089",
    color_secondary="#6b0064",
    description="Escolha 15 números de 1 a 25"
)

# Dicionário de todos os jogos
GAMES: Dict[str, GameConfig] = {
    "mega_sena": MEGA_SENA,
    "quina": QUINA,
    "lotofacil": LOTOFACIL
}

# Lista ordenada para exibição
GAMES_LIST: List[GameConfig] = [MEGA_SENA, QUINA, LOTOFACIL]


def detect_game_type(df) -> str:
    """
    Detecta o tipo de jogo baseado no número de colunas de bolas
    
    Returns:
        slug do jogo detectado ou None se não reconhecido
    """
    # Conta colunas que parecem ser de bolas (numéricas após as 2 primeiras)
    ball_cols = 0
    
    # Verifica colunas existentes que são de bolas
    for col in df.columns:
        col_lower = str(col).lower()
        if 'bola' in col_lower or col_lower.startswith('bola'):
            ball_cols += 1
    
    # Se não encontrou por nome, tenta por posição (colunas C em diante)
    if ball_cols == 0:
        # Assume que primeiras 2 colunas são Concurso e Data
        # Conta colunas numéricas restantes
        numeric_cols = df.select_dtypes(include=['number']).columns
        # Remove 'Concurso' se existir
        numeric_cols = [c for c in numeric_cols if 'concurso' not in str(c).lower()]
        ball_cols = len(numeric_cols)
    
    # Mapeia para o jogo
    if ball_cols == 6:
        return "mega_sena"
    elif ball_cols == 5:
        return "quina"
    elif ball_cols >= 15:
        return "lotofacil"
    
    return None


def validate_game_file(df, expected_game: str) -> tuple:
    """
    Valida se o arquivo corresponde ao jogo esperado
    
    Returns:
        (is_valid, message)
    """
    detected = detect_game_type(df)
    
    if detected is None:
        return False, "❌ Não foi possível identificar o tipo de jogo no arquivo"
    
    if detected != expected_game:
        detected_config = GAMES.get(detected)
        expected_config = GAMES.get(expected_game)
        
        if detected_config and expected_config:
            return False, (
                f"❌ Arquivo incompatível! "
                f"Esperado: {expected_config.name} ({expected_config.n_balls} bolas). "
                f"Detectado: {detected_config.name} ({detected_config.n_balls} bolas)."
            )
        return False, "❌ Tipo de jogo não corresponde ao esperado"
    
    return True, f"✅ Arquivo válido para {GAMES[expected_game].name}"
