"""
LotoVision - Módulo de Validação de Dados
Validações de integridade para dados da Mega Sena
"""

import pandas as pd
import numpy as np
from typing import Tuple, List, Dict
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Resultado de uma validação"""
    is_valid: bool
    message: str
    severity: str  # 'error', 'warning', 'info'
    details: Dict = None


class DataValidator:
    """Validador de dados da Mega Sena"""
    
    MIN_DEZENA = 1
    MAX_DEZENA = 60
    DEZENAS_POR_JOGO = 6
    
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.bola_columns = [f'Bola_{i}' for i in range(1, 7)]
        self.validation_results: List[ValidationResult] = []
    
    def validate_all(self) -> Tuple[bool, List[ValidationResult]]:
        """Executa todas as validações"""
        self.validation_results = []
        
        # Validações estruturais
        self._validate_required_columns()
        self._validate_data_types()
        
        # Validações de regras de negócio
        self._validate_dezena_range()
        self._validate_no_duplicates_per_row()
        self._validate_concurso_sequence()
        self._validate_date_order()
        
        # Determina se passou em todas validações críticas
        has_errors = any(r.severity == 'error' for r in self.validation_results)
        
        return not has_errors, self.validation_results
    
    def _validate_required_columns(self):
        """Verifica se todas as colunas necessárias existem"""
        required = ['Concurso', 'Data'] + self.bola_columns
        missing = [col for col in required if col not in self.df.columns]
        
        if missing:
            self.validation_results.append(ValidationResult(
                is_valid=False,
                message=f"Colunas ausentes: {', '.join(missing)}",
                severity='error',
                details={'missing_columns': missing}
            ))
        else:
            self.validation_results.append(ValidationResult(
                is_valid=True,
                message="Todas as colunas necessárias presentes",
                severity='info'
            ))
    
    def _validate_data_types(self):
        """Verifica tipos de dados"""
        errors = []
        
        # Verificar se Concurso é numérico
        if 'Concurso' in self.df.columns:
            if not pd.api.types.is_numeric_dtype(self.df['Concurso']):
                errors.append("Coluna 'Concurso' deve ser numérica")
        
        # Verificar se dezenas são numéricas
        for col in self.bola_columns:
            if col in self.df.columns:
                if not pd.api.types.is_numeric_dtype(self.df[col]):
                    errors.append(f"Coluna '{col}' deve ser numérica")
        
        if errors:
            self.validation_results.append(ValidationResult(
                is_valid=False,
                message="Tipos de dados inválidos",
                severity='error',
                details={'errors': errors}
            ))
        else:
            self.validation_results.append(ValidationResult(
                is_valid=True,
                message="Tipos de dados corretos",
                severity='info'
            ))
    
    def _validate_dezena_range(self):
        """Verifica se todas as dezenas estão no range 1-60"""
        invalid_rows = []
        
        for col in self.bola_columns:
            if col in self.df.columns:
                mask = (self.df[col] < self.MIN_DEZENA) | (self.df[col] > self.MAX_DEZENA)
                invalid = self.df[mask]['Concurso'].tolist() if 'Concurso' in self.df.columns else self.df[mask].index.tolist()
                invalid_rows.extend(invalid)
        
        invalid_rows = list(set(invalid_rows))
        
        if invalid_rows:
            self.validation_results.append(ValidationResult(
                is_valid=False,
                message=f"{len(invalid_rows)} concurso(s) com dezenas fora do range 1-60",
                severity='error',
                details={'invalid_concursos': invalid_rows[:10]}  # Limita a 10
            ))
        else:
            self.validation_results.append(ValidationResult(
                is_valid=True,
                message="Todas as dezenas no range válido (1-60)",
                severity='info'
            ))
    
    def _validate_no_duplicates_per_row(self):
        """Verifica se não há dezenas duplicadas no mesmo concurso"""
        duplicated_rows = []
        
        if all(col in self.df.columns for col in self.bola_columns):
            for idx, row in self.df.iterrows():
                dezenas = [row[col] for col in self.bola_columns]
                if len(dezenas) != len(set(dezenas)):
                    concurso = row['Concurso'] if 'Concurso' in self.df.columns else idx
                    duplicated_rows.append(concurso)
        
        if duplicated_rows:
            self.validation_results.append(ValidationResult(
                is_valid=False,
                message=f"{len(duplicated_rows)} concurso(s) com dezenas duplicadas",
                severity='error',
                details={'duplicated_concursos': duplicated_rows[:10]}
            ))
        else:
            self.validation_results.append(ValidationResult(
                is_valid=True,
                message="Sem dezenas duplicadas nos concursos",
                severity='info'
            ))
    
    def _validate_concurso_sequence(self):
        """Verifica gaps na sequência de concursos"""
        if 'Concurso' not in self.df.columns:
            return
        
        concursos = self.df['Concurso'].sort_values()
        gaps = []
        
        for i in range(1, len(concursos)):
            diff = concursos.iloc[i] - concursos.iloc[i-1]
            if diff > 1:
                gaps.append({
                    'after': int(concursos.iloc[i-1]),
                    'before': int(concursos.iloc[i]),
                    'missing': int(diff - 1)
                })
        
        if gaps:
            total_missing = sum(g['missing'] for g in gaps)
            self.validation_results.append(ValidationResult(
                is_valid=True,  # Warning, não erro
                message=f"{total_missing} concurso(s) faltando na sequência",
                severity='warning',
                details={'gaps': gaps[:5]}  # Limita a 5 gaps
            ))
        else:
            self.validation_results.append(ValidationResult(
                is_valid=True,
                message="Sequência de concursos completa",
                severity='info'
            ))
    
    def _validate_date_order(self):
        """Verifica se datas estão em ordem cronológica"""
        if 'Data' not in self.df.columns or 'Concurso' not in self.df.columns:
            return
        
        df_sorted = self.df.sort_values('Concurso')
        
        try:
            dates = pd.to_datetime(df_sorted['Data'])
            out_of_order = []
            
            for i in range(1, len(dates)):
                if dates.iloc[i] < dates.iloc[i-1]:
                    out_of_order.append({
                        'concurso': int(df_sorted.iloc[i]['Concurso']),
                        'date': str(dates.iloc[i].date())
                    })
            
            if out_of_order:
                self.validation_results.append(ValidationResult(
                    is_valid=True,
                    message=f"{len(out_of_order)} data(s) fora de ordem cronológica",
                    severity='warning',
                    details={'out_of_order': out_of_order[:5]}
                ))
            else:
                self.validation_results.append(ValidationResult(
                    is_valid=True,
                    message="Datas em ordem cronológica",
                    severity='info'
                ))
        except Exception as e:
            self.validation_results.append(ValidationResult(
                is_valid=False,
                message=f"Erro ao processar datas: {str(e)}",
                severity='error'
            ))
    
    def get_summary(self) -> Dict:
        """Retorna resumo das validações"""
        errors = sum(1 for r in self.validation_results if r.severity == 'error')
        warnings = sum(1 for r in self.validation_results if r.severity == 'warning')
        info = sum(1 for r in self.validation_results if r.severity == 'info')
        
        return {
            'total_validations': len(self.validation_results),
            'errors': errors,
            'warnings': warnings,
            'info': info,
            'passed': errors == 0
        }


def quick_validate(df: pd.DataFrame) -> Tuple[bool, str]:
    """Validação rápida - retorna True/False e mensagem resumida"""
    validator = DataValidator(df)
    is_valid, results = validator.validate_all()
    
    if is_valid:
        return True, "✅ Dados validados com sucesso"
    else:
        errors = [r.message for r in results if r.severity == 'error']
        return False, f"❌ Erros encontrados: {'; '.join(errors)}"


def validate_game_data(df: pd.DataFrame, game_config) -> Tuple[bool, str]:
    """
    Validação de dados específica para cada jogo
    
    Args:
        df: DataFrame com os dados
        game_config: Configuração do jogo (GameConfig)
    
    Returns:
        (is_valid, message)
    """
    errors = []
    warnings = []
    
    # Verifica colunas de bolas
    ball_cols = game_config.ball_columns
    missing_cols = [col for col in ball_cols if col not in df.columns]
    
    if missing_cols:
        errors.append(f"Colunas faltando: {', '.join(missing_cols)}")
    
    # Verifica range dos números
    for col in ball_cols:
        if col in df.columns:
            min_val = df[col].min()
            max_val = df[col].max()
            
            if min_val < game_config.min_number:
                errors.append(f"Número abaixo do mínimo ({game_config.min_number}) em {col}")
            if max_val > game_config.max_number:
                errors.append(f"Número acima do máximo ({game_config.max_number}) em {col}")
    
    # Verifica duplicatas no mesmo concurso
    for idx, row in df.iterrows():
        dezenas = [row[col] for col in ball_cols if col in row.index and pd.notna(row[col])]
        if len(dezenas) != len(set(dezenas)):
            warnings.append(f"Dezenas duplicadas no concurso {row.get('Concurso', idx)}")
            if len(warnings) > 5:
                warnings.append("... e mais")
                break
    
    if errors:
        return False, f"❌ {'; '.join(errors)}"
    elif warnings:
        return True, f"⚠️ {'; '.join(warnings[:3])}"
    else:
        return True, "✅ Dados validados"
