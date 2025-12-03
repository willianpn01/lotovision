"""
LotoVision - Carregador de Dados via API
Busca resultados diretamente da API da Caixa e sincroniza com JSON local
"""

import requests
import streamlit as st
from typing import Optional, Dict, Tuple
from datetime import datetime

from modules.game_config import GAMES
from modules.json_loader import (
    load_json_data, save_json_data, add_result, 
    get_last_contest, get_json_stats
)


# URLs da API da Caixa (não oficial, mas pública)
API_URLS = {
    "mega_sena": "https://servicebus2.caixa.gov.br/portaldeloterias/api/megasena",
    "quina": "https://servicebus2.caixa.gov.br/portaldeloterias/api/quina",
    "lotofacil": "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil",
}


@st.cache_data(ttl=3600, show_spinner="Buscando dados da Caixa...")
def fetch_latest_result(game_slug: str) -> Optional[Dict]:
    """
    Busca o último resultado de um jogo via API da Caixa
    Cache de 1 hora para não sobrecarregar
    """
    url = API_URLS.get(game_slug)
    if not url:
        return None
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.warning(f"Não foi possível buscar dados online: {e}")
        return None


@st.cache_data(ttl=3600, show_spinner="Buscando concurso...")
def fetch_specific_result(game_slug: str, concurso: int) -> Optional[Dict]:
    """Busca um concurso específico"""
    url = API_URLS.get(game_slug)
    if not url:
        return None
    
    try:
        response = requests.get(f"{url}/{concurso}", timeout=10)
        response.raise_for_status()
        return response.json()
    except:
        return None


def parse_api_result(data: Dict) -> Optional[Dict]:
    """
    Extrai dados do resultado da API no formato para JSON
    """
    if not data:
        return None
    
    # Extrai dezenas (campo varia por jogo)
    dezenas_field = "listaDezenas" if "listaDezenas" in data else "dezenasSorteadasOrdemSorteio"
    dezenas = data.get(dezenas_field, [])
    
    if not dezenas:
        return None
    
    return {
        "concurso": data.get('numero', 0),
        "data": data.get('dataApuracao', ''),
        "dezenas": [int(d) for d in dezenas]
    }


def sync_with_api(game_slug: str) -> Tuple[int, str]:
    """
    Sincroniza dados locais com a API da Caixa
    Busca apenas concursos que ainda não temos
    Retorna: (quantidade_novos, mensagem)
    """
    # Último concurso local
    last_local = get_last_contest(game_slug) or 0
    
    # Último concurso online
    latest = fetch_latest_result(game_slug)
    if not latest:
        return 0, "❌ Não foi possível conectar à API"
    
    last_online = latest.get('numero', 0)
    
    if last_local >= last_online:
        return 0, "✅ Dados já estão atualizados"
    
    # Busca concursos faltantes
    novos = 0
    faltantes = last_online - last_local
    
    progress = st.progress(0, text="Sincronizando...")
    
    for i, num in enumerate(range(last_local + 1, last_online + 1)):
        result = fetch_specific_result(game_slug, num)
        if result:
            parsed = parse_api_result(result)
            if parsed:
                add_result(
                    game_slug,
                    parsed['concurso'],
                    parsed['data'],
                    parsed['dezenas']
                )
                novos += 1
        
        progress.progress((i + 1) / faltantes, text=f"Concurso {num}...")
    
    progress.empty()
    
    if novos > 0:
        # Limpa cache para recarregar dados
        st.cache_data.clear()
        return novos, f"✅ {novos} novos concursos adicionados"
    
    return 0, "Nenhum concurso novo encontrado"


def sync_full_history(game_slug: str, start_from: int = 1) -> Tuple[int, str]:
    """
    Sincroniza histórico completo (usar com cuidado - muitas requisições)
    """
    latest = fetch_latest_result(game_slug)
    if not latest:
        return 0, "❌ Não foi possível conectar à API"
    
    last_online = latest.get('numero', 0)
    total = last_online - start_from + 1
    novos = 0
    
    progress = st.progress(0, text="Baixando histórico completo...")
    
    for i, num in enumerate(range(start_from, last_online + 1)):
        # Verifica se já existe
        if get_last_contest(game_slug) and num <= get_last_contest(game_slug):
            continue
            
        result = fetch_specific_result(game_slug, num)
        if result:
            parsed = parse_api_result(result)
            if parsed:
                add_result(
                    game_slug,
                    parsed['concurso'],
                    parsed['data'],
                    parsed['dezenas']
                )
                novos += 1
        
        if i % 10 == 0:  # Atualiza a cada 10
            progress.progress((i + 1) / total, text=f"Concurso {num} de {last_online}...")
    
    progress.empty()
    st.cache_data.clear()
    
    return novos, f"✅ {novos} concursos importados"


def get_data_freshness(game_slug: str) -> str:
    """Retorna informação sobre atualização dos dados"""
    latest = fetch_latest_result(game_slug)
    if latest:
        data = latest.get('dataApuracao', 'N/A')
        concurso = latest.get('numero', 'N/A')
        return f"Último sorteio: Concurso {concurso} ({data})"
    return "Dados offline"
