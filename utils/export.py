"""
LotoVision - Módulo de Exportação
Exportação de análises e jogos para PDF e Excel
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime
import io
import base64


def games_to_dataframe(games: List) -> pd.DataFrame:
    """Converte lista de jogos para DataFrame (suporta qualquer quantidade de dezenas)"""
    if not games:
        return pd.DataFrame()
    
    data = []
    for i, game in enumerate(games, 1):
        row = {'Jogo': i}
        
        # Adiciona dezenas dinamicamente
        for j, num in enumerate(game.numbers, 1):
            row[f'Dezena {j}'] = num
        
        row['Soma'] = game.sum_value
        row['Pares'] = game.evens
        row['Ímpares'] = game.odds
        row['Atrasados'] = game.delayed_count
        row['Compatibilidade'] = f"{game.compatibility_score:.0f}%"
        
        data.append(row)
    return pd.DataFrame(data)


def export_games_excel(games: List, analysis_data: Dict = None) -> bytes:
    """
    Exporta jogos para Excel com análise
    
    Returns:
        bytes: Conteúdo do arquivo Excel
    """
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        
        # Formatos
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#6C63FF',
            'font_color': 'white',
            'border': 1,
            'align': 'center'
        })
        
        number_format = workbook.add_format({
            'align': 'center',
            'border': 1
        })
        
        # Aba 1: Jogos Gerados
        df_games = games_to_dataframe(games)
        df_games.to_excel(writer, sheet_name='Jogos Gerados', index=False, startrow=1)
        
        worksheet = writer.sheets['Jogos Gerados']
        
        # Cabeçalho personalizado
        worksheet.write(0, 0, f'LotoVision - Jogos Gerados em {datetime.now().strftime("%d/%m/%Y %H:%M")}', 
                       workbook.add_format({'bold': True, 'font_size': 14}))
        
        # Formata colunas
        for col_num, column in enumerate(df_games.columns):
            worksheet.write(1, col_num, column, header_format)
            worksheet.set_column(col_num, col_num, 12)
        
        # Aba 2: Análise (se fornecida)
        if analysis_data:
            df_analysis = pd.DataFrame([
                {'Métrica': 'Total de Jogos', 'Valor': len(games)},
                {'Métrica': 'Soma Média', 'Valor': f"{np.mean([g.sum_value for g in games]):.1f}"},
                {'Métrica': 'Pares Médios', 'Valor': f"{np.mean([g.evens for g in games]):.1f}"},
                {'Métrica': 'Compatibilidade Média', 'Valor': f"{np.mean([g.compatibility_score for g in games]):.1f}%"},
            ])
            
            df_analysis.to_excel(writer, sheet_name='Análise', index=False)
        
        # Aba 3: Disclaimer
        disclaimer_sheet = workbook.add_worksheet('Aviso Legal')
        disclaimer_format = workbook.add_format({
            'text_wrap': True,
            'valign': 'top'
        })
        
        disclaimer_text = """
AVISO IMPORTANTE - LEIA COM ATENÇÃO

Este documento foi gerado pelo LotoVision, uma ferramenta EDUCACIONAL e ESTATÍSTICA.

SOBRE LOTERIAS:
• Loterias são jogos de PURO ACASO
• A probabilidade de acertar a Mega Sena é de 1 em 50.063.860
• Nenhuma análise histórica aumenta suas chances de ganhar
• Cada sorteio é INDEPENDENTE dos anteriores

SOBRE ESTA FERRAMENTA:
• Objetivo: Educação em estatística e probabilidade
• Os jogos gerados são baseados em critérios estatísticos
• NÃO há garantia de vitória
• Use apenas para entretenimento responsável

JOGUE COM RESPONSABILIDADE
Se você sente que tem problemas com jogos de azar, procure ajuda:
• CVV: 188
• CAPS (Centro de Atenção Psicossocial)

© LotoVision - Ferramenta Educacional
        """
        
        disclaimer_sheet.set_column(0, 0, 80)
        disclaimer_sheet.write(0, 0, disclaimer_text, disclaimer_format)
    
    output.seek(0)
    return output.read()


def export_analysis_summary(df: pd.DataFrame, df_melted: pd.DataFrame, 
                           kpis: Dict, frequency_data: tuple) -> bytes:
    """
    Exporta resumo de análise para Excel
    """
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        
        # KPIs
        kpi_data = [
            {'Indicador': 'Total de Concursos', 'Valor': kpis.get('total_concursos', 'N/A')},
            {'Indicador': 'Período', 'Valor': kpis.get('periodo', 'N/A')},
            {'Indicador': 'Último Concurso', 'Valor': kpis.get('ultimo_concurso', 'N/A')},
            {'Indicador': 'Data Último Sorteio', 'Valor': kpis.get('ultimo_data', 'N/A')},
        ]
        df_kpis = pd.DataFrame(kpi_data)
        df_kpis.to_excel(writer, sheet_name='Resumo', index=False)
        
        # Frequência
        if frequency_data and len(frequency_data) == 2:
            top_mais, top_menos = frequency_data
            if not top_mais.empty:
                top_mais.to_excel(writer, sheet_name='Mais Sorteadas', index=False)
            if not top_menos.empty:
                top_menos.to_excel(writer, sheet_name='Menos Sorteadas', index=False)
        
        # Dados brutos (amostra)
        if not df.empty:
            df.tail(100).to_excel(writer, sheet_name='Últimos 100 Sorteios', index=False)
    
    output.seek(0)
    return output.read()


def format_games_text(games: List) -> str:
    """
    Formata jogos para texto (copiar/colar)
    """
    lines = ["=" * 50]
    lines.append("LOTTOANALYTICS - JOGOS GERADOS")
    lines.append(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    lines.append("=" * 50)
    lines.append("")
    
    for i, game in enumerate(games, 1):
        numbers = " - ".join([f"{n:02d}" for n in game.numbers])
        lines.append(f"Jogo {i:02d}: {numbers}")
        lines.append(f"         Soma: {game.sum_value} | {game.evens}P/{game.odds}I | Score: {game.compatibility_score:.0f}%")
        lines.append("")
    
    lines.append("=" * 50)
    lines.append("⚠️ AVISO: Jogos gerados para fins educacionais.")
    lines.append("Loterias são jogos de puro acaso.")
    lines.append("=" * 50)
    
    return "\n".join(lines)


def create_download_link(data: bytes, filename: str, mime_type: str) -> str:
    """
    Cria link de download para Streamlit
    """
    b64 = base64.b64encode(data).decode()
    return f'<a href="data:{mime_type};base64,{b64}" download="{filename}">📥 Baixar {filename}</a>'


def export_to_pdf(games: List = None, analysis_data: Dict = None) -> bytes:
    """
    Exporta para PDF usando fpdf2
    """
    from fpdf import FPDF
    
    class PDF(FPDF):
        def header(self):
            self.set_font('Helvetica', 'B', 16)
            self.cell(0, 10, 'LotoVision - Relatorio', align='C', new_x='LMARGIN', new_y='NEXT')
            self.set_font('Helvetica', '', 10)
            self.cell(0, 5, f'Gerado em: {datetime.now().strftime("%d/%m/%Y %H:%M")}', align='C', new_x='LMARGIN', new_y='NEXT')
            self.ln(5)
        
        def footer(self):
            self.set_y(-15)
            self.set_font('Helvetica', 'I', 8)
            self.cell(0, 10, f'Pagina {self.page_no()}', align='C')
    
    pdf = PDF()
    pdf.add_page()
    
    # Jogos
    if games:
        pdf.set_font('Helvetica', 'B', 14)
        pdf.cell(0, 10, 'Jogos Gerados', new_x='LMARGIN', new_y='NEXT')
        pdf.ln(3)
        
        pdf.set_font('Helvetica', '', 11)
        for i, game in enumerate(games, 1):
            numbers = " - ".join([f"{n:02d}" for n in game.numbers])
            pdf.cell(0, 7, f'Jogo {i:02d}: {numbers}', new_x='LMARGIN', new_y='NEXT')
            pdf.set_font('Helvetica', '', 9)
            pdf.cell(0, 5, f'   Soma: {game.sum_value} | Pares: {game.evens} | Score: {game.compatibility_score:.0f}%', 
                    new_x='LMARGIN', new_y='NEXT')
            pdf.set_font('Helvetica', '', 11)
            pdf.ln(2)
    
    # Disclaimer
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 10, 'AVISO LEGAL', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('Helvetica', '', 10)
    
    disclaimer = (
        "Este documento foi gerado pelo LotoVision, uma ferramenta EDUCACIONAL. "
        "Loterias sao jogos de PURO ACASO. A probabilidade de acertar a Mega Sena e de 1 em 50.063.860. "
        "Nenhuma analise historica aumenta suas chances de ganhar. Jogue com responsabilidade."
    )
    pdf.multi_cell(0, 6, disclaimer)
    
    return bytes(pdf.output())
