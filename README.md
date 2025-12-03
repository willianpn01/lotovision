# 🎰 LotoVision

**Análise Estatística Avançada de Loterias Brasileiras**

Uma aplicação web interativa para análise estatística de resultados de loterias, com geração inteligente de palpites e validação científica dos dados.

> ⚠️ **AVISO IMPORTANTE**: Esta é uma ferramenta EDUCACIONAL. Loterias são jogos de PURO ACASO. Nenhuma análise histórica aumenta suas chances de ganhar.

## 🎮 Jogos Suportados

| Jogo | Dezenas | Range | Combinações |
|------|---------|-------|-------------|
| 🎰 **Mega Sena** | 6 | 1-60 | 50.063.860 |
| ⭐ **Quina** | 5 | 1-80 | 24.040.016 |
| 🍀 **Lotofácil** | 15 | 1-25 | 3.268.760 |

## 📸 Screenshots

### Dashboard Principal
- KPIs do último sorteio
- Heatmap do volante (frequência visual adaptativa)
- Gráficos de frequência
- Análise par/ímpar

### Estatísticas
- Teste Chi-Quadrado
- Distribuição de somas
- Simulação Monte Carlo

### Gerador de Jogos
- Múltiplas estratégias
- Filtros avançados
- Exportação Excel/PDF

## 🚀 Instalação

### Requisitos
- Python 3.10+
- pip

### Setup

```bash
# Clonar repositório
git clone https://github.com/seu-usuario/lottoanalytics.git
cd lottoanalytics

# Instalar dependências
pip install -r requirements.txt

# Executar
streamlit run app.py
```

## 📁 Estrutura do Projeto

```
lottoanalytics/
├── app.py                     # Aplicação principal Streamlit
├── data/
│   ├── mega_sena_demo.xlsx    # Dados Mega Sena
│   ├── quina_demo.xlsx        # Dados Quina
│   └── lotofacil_demo.xlsx    # Dados Lotofácil
├── modules/
│   ├── game_config.py         # Configurações dos jogos
│   ├── data_loader_v2.py      # Upload e processamento (multi-jogo)
│   ├── analytics_v2.py        # Análises e KPIs (multi-jogo)
│   ├── statistics_v2.py       # Validações estatísticas (multi-jogo)
│   └── generator_v2.py        # Gerador de jogos (multi-jogo)
├── utils/
│   ├── validators.py          # Validações de integridade
│   └── export.py              # Exportação PDF/Excel
├── requirements.txt
└── README.md
```

## 📊 Funcionalidades

### Dashboard
- **KPIs Principais**: Último sorteio, total de concursos, período
- **Heatmap do Volante**: Visualização da frequência (grid adaptativo por jogo)
- **Frequência de Dezenas**: Top 10 mais e menos sorteadas
- **Distribuição Par/Ímpar**: Análise de paridade dos sorteios
- **Análise de Atraso**: Dezenas há mais tempo sem aparecer
- **Pares Frequentes**: Combinações de números mais sorteadas
- **Tendência Temporal**: Evolução das dezenas ao longo dos anos

### Estatísticas
- **Teste Chi-Quadrado**: Verifica uniformidade da distribuição
- **Análise de Somas**: Distribuição e normalidade
- **Simulação Monte Carlo**: Demonstração de probabilidades

### Gerador de Jogos
- **Estratégias**:
  - Aleatório Puro
  - Balanceado (quentes/frios)
  - Contrarian (prioriza atrasados)
- **Filtros**:
  - Excluir último sorteio
  - Excluir top 10 mais sorteados
  - Range de pares
  - Range de soma
  - Números fixos

### Exportação
- Excel com análise completa
- PDF com relatório
- Texto para copiar/colar

## 📋 Formato dos Dados

O arquivo Excel deve conter:

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| Concurso | Integer | ID do sorteio |
| Data | Date | Data do sorteio |
| Bola1-BolaN | Integer | Dezenas sorteadas |

### Colunas por Jogo

| Jogo | Colunas | Range |
|------|---------|-------|
| Mega Sena | Bola1-Bola6 | 1-60 |
| Quina | Bola1-Bola5 | 1-80 |
| Lotofácil | Bola1-Bola15 | 1-25 |

> O sistema detecta automaticamente o tipo de jogo pelo número de colunas de bolas.

> **Validação**: Ao selecionar um jogo, o sistema rejeita arquivos incompatíveis.

## 🛠️ Stack Tecnológica

- **Framework**: Streamlit
- **Dados**: Pandas, NumPy
- **Estatística**: SciPy
- **Visualização**: Plotly
- **Exportação**: fpdf2, xlsxwriter

## ⚖️ Disclaimer

```
Este sistema é uma ferramenta EDUCACIONAL e ESTATÍSTICA.

Loterias são jogos de PURO ACASO. Nenhuma análise histórica
aumenta suas chances de ganhar.

Probabilidades:
• Mega Sena:  1 em 50.063.860
• Quina:      1 em 24.040.016
• Lotofácil:  1 em 3.268.760

Jogue com responsabilidade. Este software não incentiva
apostas compulsivas.
```

## � Links Úteis

**Loterias Caixa**: [https://loterias.caixa.gov.br](https://loterias.caixa.gov.br/Paginas/default.aspx)

Todas as informações oficiais sobre os jogos, resultados, regras e premiações podem ser encontradas no site oficial da Caixa Econômica Federal.

## �📄 Licença

MIT License

## 👤 Autor

LotoVision Team - Ferramenta Educacional

---

**Versão**: 2.0 (Multi-Jogos)  
**Última Atualização**: Dezembro 2024
