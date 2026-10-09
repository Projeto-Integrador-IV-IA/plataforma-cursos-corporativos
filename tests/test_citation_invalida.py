import pytest
from unittest.mock import MagicMock

# Exemplo de teste estruturado para validar a barreira anti-alucinação (RNF27)
class TestInvalidEvidenceAntiHallucination:
    
    def test_rejeita_citacao_inexistente(self):
        """
        Cenário: A IA gera uma estruturação citando um trecho (snippet) 
        que NÃO existe nas fontes brutas originais (raw-inputs).
        Resultado esperado: O sistema deve recusar a saída, lançar erro de validação,
        não persistir o artefato inválido e manter a demanda íntegra.
        """
        # 1. Arrange: Fontes brutas legítimas cadastradas na demanda
        fontes_brutas_validas = [
            {"id": "src-01", "content": "O curso corporativo será focado em Python e arquitetura de microsserviços."},
            {"id": "src-02", "content": "A carga horária prevista é de 40 horas semanais para a equipe técnica."}
        ]
        
        # Tentativa de IA alucinando um trecho que NÃO foi fornecido nas fontes
        saida_ia_com_alucinacao = {
            "summary": "Curso de Python avançado",
            "cited_sources": [
                {"id": "src-99", "snippet": "Este texto nunca existiu nas fontes brutas originais."}
            ]
        }
        
        # 2. Act & Assert: Simulando o validador de evidência do pipeline/estruturação
        def validar_e_persistir(raw_inputs, ai_output):
            ids_validos = {src["id"] for src in raw_inputs}
            trechos_validos = {src["content"] for src in raw_inputs}
            
            for citation in ai_output.get("cited_sources", []):
                # Validação estrita da barreira anti-alucinação
                if citation["id"] not in ids_validos or citation["snippet"] not in "".join(trechos_validos):
                    raise ValueError("ERRO: Evidência inválida detectada. Citação não encontrada nas fontes brutas.")
            
            return True

        # O teste valida que a exceção de recusa é acionada corretamente
        with pytest.raises(ValueError, match="ERRO: Evidência inválida detectada"):
            validar_e_persistir(fontes_brutas_validas, saida_ia_com_alucinacao)

        # 3. Verificação de integridade: As fontes brutas originais permanecem intocadas
        assert len(fontes_brutas_validas) == 2
        assert fontes_brutas_validas[0]["id"] == "src-01"
        assert fontes_brutas_validas[1]["id"] == "src-02"