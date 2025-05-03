import streamlit as st
from typing import Dict, Any

class FeatureFlags:
    """Gerenciador de feature flags"""

    def __init__(self):
        self._flags: Dict[str, bool] = {
            'NOVO_SISTEMA_AGENDAMENTO': False,
            'INTEGRACAO_WHATSAPP': False,
            'PAGAMENTO_ONLINE': False,
            'GALERIA_FOTOS': True,
            'PREVISAO_TEMPO': True
        }

        # Carregar flags do secrets
        self._load_flags()

    def _load_flags(self) -> None:
        """Carrega as flags do st.secrets"""
        for flag in self._flags:
            try:
                self._flags[flag] = st.secrets.get(f"FEATURE_{flag}", self._flags[flag])
            except:
                # Se não conseguir carregar do secrets, mantém o valor padrão
                pass

    def is_enabled(self, flag: str) -> bool:
        """Verifica se uma feature está habilitada"""
        return self._flags.get(flag, False)

    def get_all_flags(self) -> Dict[str, bool]:
        """Retorna todas as flags e seus estados"""
        return self._flags.copy()

# Instância global do gerenciador de flags
feature_flags = FeatureFlags()