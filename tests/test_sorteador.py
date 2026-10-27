"""Regras de negócio: filtros, quem já ganhou, sorteio."""

import unittest
from datetime import datetime, time

from sorteio.planilha import COL_NOME
from sorteio.sorteador import (
    filtrar_inscricoes,
    filtrar_ja_ganhadores,
    listar_eventos,
    normalizar_matricula,
    planilha_pode_estar_desatualizada,
    remover_inscricoes_repetidas,
    sortear,
)
from tests.apoio import inscricao

EVENTO = "Game Show C3"
OUTRO_EVENTO = "Palestra Josué, Teatro Educa Vida"


def nomes(linhas):
    return [l[COL_NOME] for l in linhas]


class TesteMatricula(unittest.TestCase):
    def test_variacoes_da_mesma_matricula(self):
        iguais = ["0012345", 12345, 12345.0, " 12345 ", "12.345", "12 345"]
        self.assertEqual({normalizar_matricula(m) for m in iguais}, {"12345"})

    def test_chave_alfanumerica(self):
        self.assertEqual(normalizar_matricula(" fy0e "), "FY0E")
        self.assertEqual(normalizar_matricula("AB-12"), normalizar_matricula("ab12"))
        # letra O e dígito 0 continuam diferentes
        self.assertNotEqual(normalizar_matricula("FYOE"), normalizar_matricula("FY0E"))

    def test_vazia(self):
        self.assertEqual(normalizar_matricula(None), "")
        self.assertEqual(normalizar_matricula("  "), "")


class TesteFiltros(unittest.TestCase):
    def test_evento_ignora_acento_maiusculas_e_espacos(self):
        linhas = [
            inscricao("A", "1", "palestra josue,  teatro educa vida "),
            inscricao("B", "2", EVENTO),
        ]
        self.assertEqual(nomes(filtrar_inscricoes(linhas, OUTRO_EVENTO, time(23, 59))), ["A"])

    def test_multipla_selecao(self):
        linhas = [inscricao("A", "1", f"{EVENTO};{OUTRO_EVENTO};")]
        self.assertEqual(len(filtrar_inscricoes(linhas, EVENTO, time(23, 59))), 1)
        self.assertEqual(len(filtrar_inscricoes(linhas, OUTRO_EVENTO, time(23, 59))), 1)

    def test_horario_limite_inclusivo(self):
        linhas = [
            inscricao("No limite", "1", EVENTO, hora=datetime(2026, 11, 10, 9, 0)),
            inscricao("Depois", "2", EVENTO, hora=datetime(2026, 11, 10, 9, 0, 1)),
            inscricao("Sem hora", "3", EVENTO, hora=None),
        ]
        self.assertEqual(nomes(filtrar_inscricoes(linhas, EVENTO, time(9, 0))), ["No limite"])

    def test_listar_eventos_sem_duplicar_grafias(self):
        linhas = [inscricao("A", "1", "Game Show C3"), inscricao("B", "2", "game show  c3 ")]
        self.assertEqual(listar_eventos(linhas), ["Game Show C3"])


class TesteJaGanhou(unittest.TestCase):
    def setUp(self):
        self.linhas = [
            inscricao("Maria Souza", "0012345", EVENTO),
            inscricao("Pedro Lima", "AB12", EVENTO),
        ]

    def test_matricula_escrita_diferente(self):
        ganhadores = [(EVENTO, "Outro Nome", 12345.0, "X", "Caneca")]
        self.assertEqual(nomes(filtrar_ja_ganhadores(self.linhas, ganhadores, [], EVENTO)),
                         ["Pedro Lima"])

    def test_mesmo_nome_com_matricula_diferente(self):
        sessao = [(EVENTO, "MARIA  SOUZA", "99999", "X", "Caneca")]
        self.assertEqual(nomes(filtrar_ja_ganhadores(self.linhas, [], sessao, EVENTO)),
                         ["Pedro Lima"])

    def test_evento_com_grafia_diferente_no_arquivo_de_ganhadores(self):
        ganhadores = [("game show c3 ", "Pedro Lima", "ab12", "X", "Caneca")]
        self.assertEqual(nomes(filtrar_ja_ganhadores(self.linhas, ganhadores, [], EVENTO)),
                         ["Maria Souza"])

    def test_ganhar_em_outro_evento_nao_impede(self):
        ganhadores = [(OUTRO_EVENTO, "Maria Souza", "0012345", "X", "Caneca")]
        self.assertEqual(len(filtrar_ja_ganhadores(self.linhas, ganhadores, [], EVENTO)), 2)

    def test_nome_anonimo_nao_bloqueia_todo_mundo(self):
        linhas = [inscricao("anonymous", "1", EVENTO), inscricao("anonymous", "2", EVENTO)]
        sessao = [(EVENTO, "anonymous", "1", "X", "P")]
        self.assertEqual(len(filtrar_ja_ganhadores(linhas, [], sessao, EVENTO)), 1)

    def test_linhas_antigas_ou_curtas_nos_ganhadores_nao_quebram(self):
        ganhadores = [(EVENTO,), (None, None, None), (EVENTO, None, None, None, None)]
        self.assertEqual(len(filtrar_ja_ganhadores(self.linhas, ganhadores, [], EVENTO)), 2)


class TesteRepetidas(unittest.TestCase):
    def test_inscricao_dupla_vira_uma(self):
        linhas = [
            inscricao("Maria", "0012345", EVENTO),
            inscricao("Maria", "12345", EVENTO),       # mesma matrícula
            inscricao("maria ", "77777", EVENTO),      # mesmo nome
            inscricao("Pedro", "AB12", EVENTO),
        ]
        self.assertEqual(nomes(remover_inscricoes_repetidas(linhas)), ["Maria", "Pedro"])

    def test_matricula_vazia_nao_junta_pessoas_diferentes(self):
        linhas = [inscricao("A", None, EVENTO), inscricao("B", "", EVENTO)]
        self.assertEqual(len(remover_inscricoes_repetidas(linhas)), 2)


class TesteSortear(unittest.TestCase):
    def test_formato_rn08(self):
        [g] = sortear([inscricao(" Maria ", 12345.0, EVENTO, empresa=" X ")], 1, EVENTO, " Caneca ")
        self.assertEqual(g, (EVENTO, "Maria", "12345", "X", "Caneca"))

    def test_nunca_repete_na_mesma_rodada_mesmo_com_inscricao_dupla(self):
        linhas = [inscricao("Maria", "1", EVENTO)] * 5 + [inscricao("Pedro", "2", EVENTO)]
        for _ in range(200):
            resultado = sortear(linhas, 2, EVENTO, "P")
            self.assertEqual(sorted(g[1] for g in resultado), ["Maria", "Pedro"])

    def test_quantidade_maior_que_pessoas(self):
        linhas = [inscricao("Maria", "1", EVENTO)] * 3
        with self.assertRaises(ValueError) as erro:
            sortear(linhas, 2, EVENTO, "P")
        self.assertIn("apenas 1", str(erro.exception))

    def test_sem_elegiveis(self):
        with self.assertRaises(ValueError):
            sortear([], 1, EVENTO, "P")

    def test_inscricao_dupla_nao_aumenta_a_chance(self):
        # Maria inscrita 9 vezes, Pedro 1: com uma chance cada, ~50% / 50%
        linhas = [inscricao("Maria", "1", EVENTO)] * 9 + [inscricao("Pedro", "2", EVENTO)]
        vezes_maria = sum(sortear(linhas, 1, EVENTO, "P")[0][1] == "Maria" for _ in range(2000))
        self.assertTrue(800 < vezes_maria < 1200, vezes_maria)


class TesteDesatualizada(unittest.TestCase):
    def setUp(self):
        self.linhas = [inscricao("A", "1", EVENTO, hora=datetime(2026, 11, 10, 10, 0))]
        self.agora = datetime(2026, 11, 10, 11, 0)

    def test_avisa_quando_ultima_resposta_e_bem_anterior_ao_limite(self):
        self.assertTrue(planilha_pode_estar_desatualizada(self.linhas, time(10, 30), self.agora))

    def test_nao_avisa_dentro_da_tolerancia(self):
        self.assertFalse(planilha_pode_estar_desatualizada(self.linhas, time(10, 1), self.agora))

    def test_limite_no_futuro_compara_com_agora(self):
        agora = datetime(2026, 11, 10, 10, 1)
        self.assertFalse(planilha_pode_estar_desatualizada(self.linhas, time(23, 0), agora))

    def test_planilha_vazia(self):
        self.assertTrue(planilha_pode_estar_desatualizada([], time(9, 0), self.agora))


if __name__ == "__main__":
    unittest.main()
