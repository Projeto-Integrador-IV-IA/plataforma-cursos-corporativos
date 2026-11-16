"""Calculo das metricas de qualidade e persistencia da rodada (RNF04).

O que estes testes protegem, em uma frase: metrica nao medida sai como ``None`` e
nunca como zero. Reportar 0% de alucinacao num conjunto que nao tem campo sem
base afirmaria algo que ninguem mediu, e e o tipo de numero que passa por uma
banca sem ser questionado.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from app.domain.course import StructuredCourse, validar_curso_estruturado
from app.evaluation.dataset import CasoDeAvaliacao, Procedencia
from app.evaluation.metrics import (
    CAMPOS_AUTOMATICOS,
    CAMPOS_DE_JULGAMENTO,
    Criterio,
    Execucao,
    comparar,
    comparar_modelos,
    estabilidade,
    medir,
)
from app.evaluation.runner import Rodada, carregar, salvar

MODELO = "vendor/modelo-a"


def curso(**sobrescreve: Any) -> StructuredCourse:
    """Monta um curso valido pela propria validacao canonica do dominio."""

    base: dict[str, Any] = {
        "tema": "lideranca",
        "nicho": "industrial",
        "publico_alvo": "coordenadores",
        "numero_participantes": 12,
        "carga_horaria": 16,
        "formato": "presencial",
        "objetivos_aprendizagem": ["dar feedback"],
        "ementa": [{"titulo": "Feedback", "topicos": ["escuta"], "carga_horaria": 16}],
        "campos_ausentes": [],
        "procedencia": {
            "tema": "extraido",
            "nicho": "extraido",
            "publico_alvo": "extraido",
            "numero_participantes": "extraido",
            "carga_horaria": "extraido",
            "formato": "extraido",
            "objetivos_aprendizagem": "extraido",
            "ementa": "inferido",
        },
        "evidencias": {
            "tema": [1],
            "nicho": [1],
            "publico_alvo": [1],
            "numero_participantes": [1],
            "carga_horaria": [1],
            "formato": [1],
            "objetivos_aprendizagem": [1],
            "ementa": [1],
        },
        "observacoes": [],
    }
    base.update(sobrescreve)
    return validar_curso_estruturado(base)


def caso(identificador: str = "c1", **sobrescreve: Any) -> CasoDeAvaliacao:
    dados: dict[str, Any] = {
        "identificador": identificador,
        "canal": "emails",
        "procedencia": Procedencia.SINTETICO,
        "texto": "texto",
        "esperado": {"carga_horaria": 16, "numero_participantes": 12, "formato": "presencial"},
        "sem_base": frozenset(),
    }
    dados.update(sobrescreve)
    return CasoDeAvaliacao(**dados)


def execucao(**sobrescreve: Any) -> Execucao:
    dados: dict[str, Any] = {
        "caso": "c1",
        "modelo": MODELO,
        "curso": curso(),
        "valida_de_primeira": True,
        "tentativas": 1,
    }
    dados.update(sobrescreve)
    return Execucao(**dados)


class TestCriterios:
    def test_so_tres_campos_sao_automatizaveis(self) -> None:
        """O resto exige julgamento humano, pelo criterio do proprio projeto."""

        assert set(CAMPOS_AUTOMATICOS) == {"numero_participantes", "carga_horaria", "formato"}
        assert "tema" in CAMPOS_DE_JULGAMENTO
        assert "ementa" in CAMPOS_DE_JULGAMENTO

    def test_campo_numerico_compara_por_igualdade(self) -> None:
        assert comparar("carga_horaria", 16, 16) is True
        assert comparar("carga_horaria", 16, 40) is False

    def test_formato_compara_sobre_vocabulario_fechado_ignorando_caixa(self) -> None:
        assert comparar("formato", "PRESENCIAL", "presencial") is True
        assert comparar("formato", "presencial", "online") is False

    def test_campo_de_texto_livre_nao_e_decidido_por_maquina(self) -> None:
        """Igualdade de string aqui produziria acuracia artificialmente baixa."""

        assert comparar("tema", "lideranca para coordenadores", "lideranca") is None

    def test_criterio_por_campo_cobre_todo_campo_inferivel(self) -> None:
        from app.domain.course import CAMPOS_INFERIVEIS
        from app.evaluation.metrics import CRITERIO_POR_CAMPO

        assert set(CRITERIO_POR_CAMPO) == set(CAMPOS_INFERIVEIS)
        assert all(isinstance(c, Criterio) for c in CRITERIO_POR_CAMPO.values())


class TestMedicao:
    def test_sem_execucao_do_modelo_devolve_medicao_vazia(self) -> None:
        d = medir(MODELO, {"c1": caso()}, [])

        assert d.casos == 0
        assert d.acuracia_global is None
        assert d.pendentes_de_julgamento == CAMPOS_DE_JULGAMENTO

    def test_ignora_execucao_de_outro_modelo(self) -> None:
        d = medir(MODELO, {"c1": caso()}, [execucao(modelo="outro/modelo")])

        assert d.casos == 0

    def test_acerto_em_todos_os_campos_automaticos(self) -> None:
        d = medir(MODELO, {"c1": caso()}, [execucao()])

        assert d.acuracia_global == pytest.approx(1.0)
        assert d.acuracia_por_campo["carga_horaria"] == pytest.approx(1.0)

    def test_erro_em_um_campo_derruba_a_acuracia_daquele_campo(self) -> None:
        d = medir(MODELO, {"c1": caso()}, [execucao(curso=curso(carga_horaria=40))])

        assert d.acuracia_por_campo["carga_horaria"] == pytest.approx(0.0)
        assert d.acuracia_por_campo["formato"] == pytest.approx(1.0)

    def test_campo_sem_gabarito_nao_entra_na_acuracia(self) -> None:
        d = medir(MODELO, {"c1": caso(esperado={"carga_horaria": 16})}, [execucao()])

        assert d.acuracia_por_campo["carga_horaria"] == pytest.approx(1.0)
        assert d.acuracia_por_campo["formato"] is None

    def test_cobertura_conta_campo_preenchido_quando_a_informacao_existe(self) -> None:
        d = medir(MODELO, {"c1": caso()}, [execucao()])

        assert d.cobertura == pytest.approx(1.0)

    def test_campo_vazio_conta_como_ausencia_nao_como_valor(self) -> None:
        d = medir(MODELO, {"c1": caso()}, [execucao(curso=curso(objetivos_aprendizagem=[]))])

        assert d.cobertura is not None
        assert d.cobertura < 1.0

    def test_preencher_campo_sem_base_e_alucinacao(self) -> None:
        sem_base = caso(sem_base=frozenset({"nicho"}), esperado={"carga_horaria": 16})

        d = medir(MODELO, {"c1": sem_base}, [execucao()])

        assert d.taxa_de_alucinacao == pytest.approx(1.0)
        assert d.reconhecimento_de_ausencia == pytest.approx(0.0)

    def test_declarar_ausencia_de_campo_sem_base_e_acerto(self) -> None:
        sem_base = caso(sem_base=frozenset({"nicho"}), esperado={"carga_horaria": 16})
        honesto = curso(
            nicho=None,
            campos_ausentes=[{"campo": "nicho", "tipo": "ausente", "motivo": "nao dito"}],
        )

        d = medir(MODELO, {"c1": sem_base}, [execucao(curso=honesto)])

        assert d.taxa_de_alucinacao == pytest.approx(0.0)
        assert d.reconhecimento_de_ausencia == pytest.approx(1.0)

    def test_conjunto_sem_campo_sem_base_nao_tem_taxa_de_alucinacao(self) -> None:
        """None, nunca zero: 0% afirmaria uma medicao que nao aconteceu."""

        d = medir(MODELO, {"c1": caso()}, [execucao()])

        assert d.taxa_de_alucinacao is None
        assert d.reconhecimento_de_ausencia is None

    def test_conformidade_de_schema_e_taxa_de_falha(self) -> None:
        d = medir(
            MODELO,
            {"c1": caso(), "c2": caso("c2")},
            [
                execucao(),
                execucao(caso="c2", curso=None, valida_de_primeira=False, erro="invalido"),
            ],
        )

        assert d.conformidade_de_schema == pytest.approx(0.5)
        assert d.taxa_de_falha == pytest.approx(0.5)

    def test_percentil_de_latencia_com_uma_amostra(self) -> None:
        d = medir(MODELO, {"c1": caso()}, [execucao(latencia_ms=120.0)])

        assert d.latencia_p50_ms == pytest.approx(120.0)
        assert d.latencia_p95_ms == pytest.approx(120.0)

    def test_percentil_interpola_entre_amostras(self) -> None:
        execucoes = [
            execucao(latencia_ms=100.0),
            execucao(latencia_ms=200.0),
            execucao(latencia_ms=300.0),
        ]

        d = medir(MODELO, {"c1": caso()}, execucoes)

        assert d.latencia_p50_ms == pytest.approx(200.0)

    def test_tokens_por_demanda_soma_entrada_e_saida(self) -> None:
        d = medir(MODELO, {"c1": caso()}, [execucao(tokens_entrada=800, tokens_saida=200)])

        assert d.tokens_por_demanda == pytest.approx(1000.0)

    def test_cobertura_de_evidencia_e_cem_por_cento_para_curso_validado(self) -> None:
        """A barreira dos cards #153-#156 so deixa passar campo preenchido com
        citacao - por isso o numero tende a 100% para execucao que nao falhou."""

        d = medir(MODELO, {"c1": caso()}, [execucao()])

        assert d.cobertura_de_evidencia == pytest.approx(1.0)
        assert d.cobertura_de_evidencia_por_campo["carga_horaria"] == pytest.approx(1.0)

    def test_cobertura_de_evidencia_despreza_campo_que_nao_foi_preenchido(self) -> None:
        """Campo ausente nunca tem evidencia (e nao deveria ter) - fica fora da conta."""

        sem_ementa = curso(
            ementa=[],
            campos_ausentes=[{"campo": "ementa", "tipo": "ausente", "motivo": "nao descrito"}],
        )

        d = medir(MODELO, {"c1": caso()}, [execucao(curso=sem_ementa)])

        assert d.cobertura_de_evidencia_por_campo["ementa"] is None
        assert d.cobertura_de_evidencia == pytest.approx(1.0)

    def test_sem_execucao_do_modelo_nao_tem_cobertura_de_evidencia(self) -> None:
        d = medir(MODELO, {"c1": caso()}, [])

        assert d.cobertura_de_evidencia is None
        assert d.taxa_de_citacao_invalida is None

    def test_taxa_de_citacao_invalida_conta_so_a_recusa_por_essa_causa(self) -> None:
        """Falha de outra origem (schema, timeout) nao e citacao invalida."""

        d = medir(
            MODELO,
            {"c1": caso(), "c2": caso("c2"), "c3": caso("c3")},
            [
                execucao(),
                execucao(
                    caso="c2",
                    curso=None,
                    valida_de_primeira=False,
                    erro="LLMInvalidResponseError: Resposta cita trecho que nao foi enviado "
                    "nesta chamada.",
                ),
                execucao(
                    caso="c3",
                    curso=None,
                    valida_de_primeira=False,
                    erro="LLMInvalidResponseError: Resposta do modelo nao corresponde ao "
                    "schema do curso estruturado.",
                ),
            ],
        )

        assert d.taxa_de_citacao_invalida == pytest.approx(1 / 3)

    def test_citacao_a_trecho_real_sem_suporte_semantico_nao_e_citacao_invalida(self) -> None:
        """Limite documentado no modulo (RNF30, card #224): so existencia e
        checada, nunca se o trecho citado realmente sustenta o campo.

        ``nicho`` esta em ``sem_base`` - o gabarito diz que a informacao nao
        esta no texto. O curso ainda assim preenche ``nicho`` citando o
        trecho [1], que existe e passaria pela barreira dos cards #153-#156
        sem ressalva. ``taxa_de_citacao_invalida`` fica em zero porque a
        citacao existe; e ``taxa_de_alucinacao`` - metrica diferente, que usa
        o gabarito, nao a existencia do trecho - e que capta o problema real.
        """

        sem_base = caso(sem_base=frozenset({"nicho"}), esperado={"carga_horaria": 16})
        cita_trecho_real_mas_sem_relacao = curso(nicho="industrial pesado")

        d = medir(MODELO, {"c1": sem_base}, [execucao(curso=cita_trecho_real_mas_sem_relacao)])

        assert d.taxa_de_citacao_invalida == pytest.approx(0.0)
        assert d.taxa_de_alucinacao == pytest.approx(1.0)

    @pytest.mark.parametrize(
        ("metrica", "valor", "esperado"),
        [
            ("cobertura", 0.90, True),
            ("cobertura", 0.50, False),
            ("taxa_de_alucinacao", 0.01, True),
            ("taxa_de_alucinacao", 0.40, False),
            ("cobertura_de_evidencia", 0.99, True),
            ("cobertura_de_evidencia", 0.50, False),
            ("taxa_de_citacao_invalida", 0.01, True),
            ("taxa_de_citacao_invalida", 0.40, False),
        ],
    )
    def test_atende_compara_com_a_meta_do_documento(
        self, metrica: str, valor: float, esperado: bool
    ) -> None:
        """Na taxa de alucinacao menor e melhor; nas demais, maior."""

        from app.evaluation.metrics import Medicao

        d = Medicao(modelo=MODELO, casos=1, **{metrica: valor})

        assert d.atende(metrica) is esperado

    def test_atende_devolve_none_para_metrica_nao_medida(self) -> None:
        from app.evaluation.metrics import Medicao

        assert Medicao(modelo=MODELO, casos=0).atende("cobertura") is None


class TestEstabilidade:
    def test_exige_mais_de_uma_repeticao(self) -> None:
        assert estabilidade([execucao()]) is None

    def test_saida_identica_nas_repeticoes_e_estabilidade_total(self) -> None:
        assert estabilidade([execucao(), execucao()]) == pytest.approx(1.0)

    def test_um_campo_que_varia_reduz_a_estabilidade(self) -> None:
        valor = estabilidade([execucao(), execucao(curso=curso(carga_horaria=40))])

        assert valor is not None
        assert valor < 1.0

    def test_ignora_execucao_que_falhou(self) -> None:
        assert estabilidade([execucao(), execucao(curso=None)]) is None


class TestComparacaoDeModelos:
    """Card #218: comparar completude, acuracia e cobertura de evidencia."""

    def test_compara_por_modelo_reaproveitando_medir(self) -> None:
        execucoes = [
            execucao(modelo="vendor/a"),
            execucao(modelo="vendor/b", curso=curso(carga_horaria=40)),
        ]

        c = comparar_modelos(["vendor/a", "vendor/b"], {"c1": caso()}, execucoes)

        assert [m.modelo for m in c.medicoes] == ["vendor/a", "vendor/b"]
        assert c.medicoes[0].acuracia_por_campo["carga_horaria"] == pytest.approx(1.0)
        assert c.medicoes[1].acuracia_por_campo["carga_horaria"] == pytest.approx(0.0)

    def test_modelo_sem_execucao_entra_com_medicao_vazia(self) -> None:
        c = comparar_modelos(
            ["vendor/a", "vendor/sem-execucao"], {"c1": caso()}, [execucao(modelo="vendor/a")]
        )

        assert c.medicoes[1].casos == 0

    def test_por_campo_pareia_modelo_e_acuracia_naquele_campo(self) -> None:
        execucoes = [
            execucao(modelo="vendor/a"),
            execucao(modelo="vendor/b", curso=curso(carga_horaria=40)),
        ]

        c = comparar_modelos(["vendor/a", "vendor/b"], {"c1": caso()}, execucoes)

        assert c.por_campo("carga_horaria") == {
            "vendor/a": pytest.approx(1.0),
            "vendor/b": pytest.approx(0.0),
        }

    def test_ranking_poe_o_melhor_primeiro_quando_maior_e_melhor(self) -> None:
        execucoes = [
            execucao(modelo="vendor/pior", curso=curso(carga_horaria=40)),
            execucao(modelo="vendor/melhor"),
        ]

        c = comparar_modelos(["vendor/pior", "vendor/melhor"], {"c1": caso()}, execucoes)

        ranking = c.ranking("acuracia_global")
        assert [modelo for modelo, _ in ranking] == ["vendor/melhor", "vendor/pior"]

    def test_ranking_poe_o_melhor_primeiro_quando_menor_e_melhor(self) -> None:
        """taxa_de_falha: menor e melhor, igual a atende()."""

        execucoes = [
            execucao(modelo="vendor/falha", curso=None),
            execucao(modelo="vendor/sucesso"),
        ]

        c = comparar_modelos(["vendor/falha", "vendor/sucesso"], {"c1": caso()}, execucoes)

        ranking = c.ranking("taxa_de_falha")
        assert [modelo for modelo, _ in ranking] == ["vendor/sucesso", "vendor/falha"]

    def test_ranking_manda_metrica_nao_medida_para_o_final(self) -> None:
        c = comparar_modelos(
            ["vendor/a", "vendor/sem-execucao"], {"c1": caso()}, [execucao(modelo="vendor/a")]
        )

        ranking = c.ranking("acuracia_global")
        assert ranking[-1] == ("vendor/sem-execucao", None)

    def test_estabilidade_agrega_por_caso_nao_por_execucao_do_modelo_inteiro(self) -> None:
        """Casos diferentes tem campos diferentes por natureza - comparar entre
        eles mediria variacao de conteudo, nao reprodutibilidade (RNF03)."""

        caso_2 = caso("c2", esperado={"carga_horaria": 40})
        execucoes = [
            # c1: duas repeticoes identicas - estavel.
            execucao(caso="c1"),
            execucao(caso="c1"),
            # c2: uma repeticao so - nao entra na media.
            execucao(caso="c2", curso=curso(carga_horaria=40)),
        ]

        c = comparar_modelos([MODELO], {"c1": caso(), "c2": caso_2}, execucoes)

        assert c.estabilidade_por_modelo[MODELO] == pytest.approx(1.0)

    def test_estabilidade_none_quando_nenhum_caso_tem_repeticao(self) -> None:
        c = comparar_modelos([MODELO], {"c1": caso()}, [execucao()])

        assert c.estabilidade_por_modelo[MODELO] is None

    def test_violam_meta_isola_quem_reprova_so_nessa_metrica(self) -> None:
        """RNF30, card #224: "quais modelos nao servem para producao por este
        numero" - sem misturar com as demais metricas de ``Medicao``."""

        casos = {f"c{n}": caso(f"c{n}") for n in range(1, 11)}
        execucoes_dentro_da_meta = [
            execucao(modelo="vendor/dentro-da-meta", caso=ident) for ident in casos
        ]
        # 2 em 10 == 0.20, acima da meta de 0.02: viola.
        execucoes_fora_da_meta = [
            execucao(
                modelo="vendor/fora-da-meta",
                caso=ident,
                curso=None,
                valida_de_primeira=False,
                erro="LLMInvalidResponseError: Resposta cita trecho que nao foi enviado "
                "nesta chamada.",
            )
            if ident in ("c1", "c2")
            else execucao(modelo="vendor/fora-da-meta", caso=ident)
            for ident in casos
        ]

        c = comparar_modelos(
            ["vendor/dentro-da-meta", "vendor/fora-da-meta"],
            casos,
            execucoes_dentro_da_meta + execucoes_fora_da_meta,
        )

        assert c.medicoes[0].taxa_de_citacao_invalida == pytest.approx(0.0)
        assert c.medicoes[1].taxa_de_citacao_invalida == pytest.approx(0.2)
        assert c.violam_meta("taxa_de_citacao_invalida") == ["vendor/fora-da-meta"]

    def test_violam_meta_ignora_modelo_sem_a_metrica_medida(self) -> None:
        c = comparar_modelos(
            ["vendor/a", "vendor/sem-execucao"], {"c1": caso()}, [execucao(modelo="vendor/a")]
        )

        assert c.violam_meta("acuracia_global") == []


class TestPersistenciaDaRodada:
    def test_grava_e_le_de_volta_sem_perder_o_que_as_metricas_usam(self, tmp_path: Path) -> None:
        rodada = Rodada(
            iniciada_em=datetime(2026, 10, 16, 12, 0, tzinfo=UTC),
            prompt_version="v3",
            schema_version="v1",
            modelos=(MODELO,),
            casos=("c1",),
            execucoes=(
                execucao(
                    latencia_ms=150.0,
                    tokens_entrada=800,
                    tokens_saida=200,
                    modelo_reportado="vendor/modelo-a-20261016",
                ),
            ),
        )

        destino = salvar(rodada, tmp_path / "sub" / "rodada.json")
        lida = carregar(destino)

        assert destino.exists(), "o diretorio de destino e criado quando falta"
        assert lida.prompt_version == "v3"
        assert lida.schema_version == "v1"
        assert lida.modelos == (MODELO,)
        e = lida.execucoes[0]
        assert e.modelo == MODELO
        assert e.modelo_reportado == "vendor/modelo-a-20261016"
        assert e.latencia_ms == pytest.approx(150.0)
        assert e.tokens_entrada == 800

    def test_a_saida_bruta_do_curso_vai_para_o_arquivo(self, tmp_path: Path) -> None:
        """Reanalise nao pode exigir nova chamada de API."""

        import json

        rodada = Rodada(
            iniciada_em=datetime(2026, 10, 16, tzinfo=UTC),
            prompt_version="v3",
            schema_version="v1",
            modelos=(MODELO,),
            casos=("c1",),
            execucoes=(execucao(),),
        )

        destino = salvar(rodada, tmp_path / "rodada.json")
        bruto = json.loads(destino.read_text(encoding="utf-8"))

        assert bruto["execucoes"][0]["curso"]["tema"] == "lideranca"

    def test_execucao_que_falhou_grava_curso_nulo(self, tmp_path: Path) -> None:
        import json

        rodada = Rodada(
            iniciada_em=datetime(2026, 10, 16, tzinfo=UTC),
            prompt_version="v3",
            schema_version="v1",
            modelos=(MODELO,),
            casos=("c1",),
            execucoes=(execucao(curso=None, erro="LLMTimeoutError: estourou"),),
        )

        bruto = json.loads(salvar(rodada, tmp_path / "r.json").read_text(encoding="utf-8"))

        assert bruto["execucoes"][0]["curso"] is None
        assert "estourou" in bruto["execucoes"][0]["erro"]

    def test_le_rodada_antiga_sem_versao_de_schema(self, tmp_path: Path) -> None:
        """Arquivo gravado antes do campo existir nao pode virar erro de leitura."""

        import json

        rodada = Rodada(
            iniciada_em=datetime(2026, 10, 16, tzinfo=UTC),
            prompt_version="v3",
            schema_version="v1",
            modelos=(MODELO,),
            casos=("c1",),
            execucoes=(execucao(),),
        )
        destino = salvar(rodada, tmp_path / "r.json")
        bruto = json.loads(destino.read_text(encoding="utf-8"))
        del bruto["schema_version"]
        destino.write_text(json.dumps(bruto, ensure_ascii=False), encoding="utf-8")

        lida = carregar(destino)

        assert lida.schema_version == "desconhecida"
