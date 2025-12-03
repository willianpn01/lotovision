"""
LotoVision - Carregador de Dados JSON
Gerencia histórico de sorteios em arquivos JSON
"""

import json
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from datetime import datetime
import streamlit as st

from modules.game_config import GameConfig, GAMES


def get_json_path(game_slug: str) -> Path:
    """Retorna o caminho do arquivo JSON para cada jogo"""
    base_path = Path(__file__).parent.parent / "data"
    return base_path / f"{game_slug}.json"


def load_json_data(game_slug: str) -> Dict:
    """Carrega dados do arquivo JSON"""
    path = get_json_path(game_slug)
    
    if not path.exists():
        return {
            "game": game_slug,
            "last_update": None,
            "total_contests": 0,
            "results": []
        }
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.warning(f"Erro ao carregar JSON: {e}")
        return {"game": game_slug, "results": []}


def save_json_data(game_slug: str, data: Dict) -> bool:
    """Salva dados no arquivo JSON"""
    path = get_json_path(game_slug)
    
    try:
        # Atualiza metadados
        data["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        data["total_contests"] = len(data.get("results", []))
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar JSON: {e}")
        return False


def json_to_dataframe(data: Dict, game_config: GameConfig) -> pd.DataFrame:
    """Converte dados JSON para DataFrame"""
    results = data.get("results", [])
    
    if not results:
        return pd.DataFrame()
    
    rows = []
    for r in results:
        row = {
            'Concurso': r.get('concurso'),
            'Data': r.get('data'),
        }
        # Adiciona bolas
        dezenas = r.get('dezenas', [])
        for i, d in enumerate(dezenas[:game_config.n_balls], 1):
            row[f'Bola_{i}'] = int(d)
        rows.append(row)
    
    df = pd.DataFrame(rows)
    
    # Converte data
    if 'Data' in df.columns:
        df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
    
    # Ordena por concurso
    df = df.sort_values('Concurso').reset_index(drop=True)
    
    return df


def dataframe_to_json_results(df: pd.DataFrame, game_config: GameConfig) -> List[Dict]:
    """Converte DataFrame para lista de resultados JSON"""
    results = []
    
    ball_cols = [f'Bola_{i}' for i in range(1, game_config.n_balls + 1)]
    
    for _, row in df.iterrows():
        # Trata a data de forma segura
        data_val = row.get('Data')
        if pd.notna(data_val):
            if hasattr(data_val, 'strftime'):
                data_str = data_val.strftime('%d/%m/%Y')
            else:
                data_str = str(data_val)
        else:
            data_str = None
        
        result = {
            "concurso": int(row['Concurso']),
            "data": data_str,
            "dezenas": [int(row[col]) for col in ball_cols if col in row]
        }
        results.append(result)
    
    return results


def add_result(game_slug: str, concurso: int, data: str, dezenas: List[int]) -> bool:
    """
    Adiciona um novo resultado ao histórico
    Evita duplicatas verificando o número do concurso
    """
    json_data = load_json_data(game_slug)
    results = json_data.get("results", [])
    
    # Verifica se já existe
    existing = [r for r in results if r.get('concurso') == concurso]
    if existing:
        return False  # Já existe
    
    # Adiciona novo resultado
    new_result = {
        "concurso": concurso,
        "data": data,
        "dezenas": dezenas
    }
    results.append(new_result)
    
    # Ordena por concurso
    results.sort(key=lambda x: x.get('concurso', 0))
    
    json_data["results"] = results
    return save_json_data(game_slug, json_data)


def get_last_contest(game_slug: str) -> Optional[int]:
    """Retorna o número do último concurso no histórico"""
    data = load_json_data(game_slug)
    results = data.get("results", [])
    
    if not results:
        return None
    
    return max(r.get('concurso', 0) for r in results)


def get_json_stats(game_slug: str) -> Dict:
    """Retorna estatísticas do arquivo JSON"""
    data = load_json_data(game_slug)
    results = data.get("results", [])
    
    if not results:
        return {
            "total": 0,
            "primeiro": None,
            "ultimo": None,
            "atualizado": data.get("last_update")
        }
    
    concursos = [r.get('concurso', 0) for r in results]
    
    return {
        "total": len(results),
        "primeiro": min(concursos),
        "ultimo": max(concursos),
        "atualizado": data.get("last_update")
    }


def import_from_excel(game_slug: str, excel_path: str) -> Tuple[bool, str]:
    """
    Importa dados de um arquivo Excel para JSON
    Útil para migração inicial dos dados demo
    """
    game_config = GAMES.get(game_slug)
    if not game_config:
        return False, "Jogo não encontrado"
    
    try:
        df = pd.read_excel(excel_path, engine='openpyxl')
        
        # Normaliza colunas
        df.columns = df.columns.str.strip().str.lower()
        
        # Renomeia colunas
        col_map = {'concurso': 'Concurso', 'data do sorteio': 'Data', 'data sorteio': 'Data', 'data': 'Data'}
        for i in range(1, game_config.n_balls + 1):
            col_map[f'bola {i}'] = f'Bola_{i}'
            col_map[f'bola{i}'] = f'Bola_{i}'
        
        df = df.rename(columns=col_map)
        
        # Converte para JSON
        results = dataframe_to_json_results(df, game_config)
        
        json_data = {
            "game": game_slug,
            "results": results
        }
        
        if save_json_data(game_slug, json_data):
            return True, f"Importados {len(results)} concursos"
        return False, "Erro ao salvar"
        
    except Exception as e:
        return False, f"Erro: {e}"


@st.cache_data(ttl=60)
def load_game_from_json(game_slug: str) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], str]:
    """
    Carrega dados do jogo a partir do JSON
    Retorna: (df_main, df_melted, status_message)
    """
    game_config = GAMES.get(game_slug)
    if not game_config:
        return None, None, "Jogo não configurado"
    
    data = load_json_data(game_slug)
    
    if not data.get("results"):
        return None, None, "Nenhum dado disponível. Importe dados ou sincronize com a API."
    
    df = json_to_dataframe(data, game_config)
    
    if df.empty:
        return None, None, "Erro ao processar dados"
    
    # Cria df_melted
    ball_cols = [f'Bola_{i}' for i in range(1, game_config.n_balls + 1)]
    df_melted = df.melt(
        id_vars=['Concurso', 'Data'],
        value_vars=ball_cols,
        var_name='Posicao',
        value_name='Dezena'
    )
    
    stats = get_json_stats(game_slug)
    status = f"✅ {stats['total']} concursos (#{stats['primeiro']} a #{stats['ultimo']})"
    
    return df, df_melted, status
