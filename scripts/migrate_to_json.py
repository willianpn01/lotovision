"""
Script para migrar dados dos arquivos Excel para JSON
Execute uma vez para popular os arquivos JSON iniciais
"""

import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.json_loader import import_from_excel, get_json_stats

def migrate_all():
    """Migra todos os arquivos Excel para JSON"""
    
    base_path = Path(__file__).parent.parent
    
    migrations = [
        ("mega_sena", base_path / "data" / "mega_sena_demo.xlsx"),
        ("quina", base_path / "data" / "quina_demo.xlsx"),
        ("lotofacil", base_path / "data" / "lotofacil_demo.xlsx"),
    ]
    
    for game_slug, excel_path in migrations:
        print(f"\n{'='*50}")
        print(f"Migrando {game_slug}...")
        
        if not excel_path.exists():
            print(f"  ⚠️  Arquivo não encontrado: {excel_path}")
            continue
        
        success, msg = import_from_excel(game_slug, str(excel_path))
        
        if success:
            stats = get_json_stats(game_slug)
            print(f"  ✅ {msg}")
            print(f"  📊 Total: {stats['total']} concursos")
            print(f"  📅 Primeiro: #{stats['primeiro']}")
            print(f"  📅 Último: #{stats['ultimo']}")
        else:
            print(f"  ❌ {msg}")

if __name__ == "__main__":
    print("="*50)
    print("LotoVision - Migração Excel → JSON")
    print("="*50)
    
    migrate_all()
    
    print("\n" + "="*50)
    print("Migração concluída!")
    print("="*50)
