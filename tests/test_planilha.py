"""Leitura da planilha do Forms e gravação/leitura dos ganhadores."""

import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook

from sorteio import planilha
from sorteio.planilha import (
    COL_EVENTO, COL_HORA, COL_MATRICULA, COL_NOME,
    eventos_da_celula, gravar_ganhadores, ler_ganhadores, ler_inscricoes,
    normalizar_texto,
)
from tests.apoio import criar_planilha_forms

RAIZ = Path(__file__).resolve().parent.parent


class TesteLeitura(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.pasta = Path(self._tmp.name)
        planilha.ESPERA_ENTRE_TENTATIVAS = 0.01

    def tearDown(self):
        self._tmp.cleanup()

    def test_colunas_achadas_pelo_cabecalho_do_forms(self):
        hora = datetime(2026, 11, 10, 8, 5)
        arq = criar_planilha_forms(self.pasta / "f.xlsx", [
            (hora, "João Silva", "Petrobras", "AB12", "Game Show C3"),
        ])
        [linha] = ler_inscricoes(arq)
        # "Nome completo" (pergunta), não o "Nome" automático ("anonymous")
        self.assertEqual(linha[COL_NOME], "João Silva")
        self.assertEqual(linha[COL_MATRICULA], "AB12")
        self.assertEqual(linha[COL_EVENTO], "Game Show C3")
        self.assertEqual(linha[COL_HORA], hora)

    def test_primeiro_inscrito_nao_e_pulado_e_linhas_vazias_sao(self):
        arq = self.pasta / "f.xlsx"
        criar_planilha_forms(arq, [
            (datetime(2026, 11, 10, 8, i), f"Pessoa {i}", "X", f"M{i}", "E")
            for i in range(3)
        ])
        nomes = [l[COL_NOME] for l in ler_inscricoes(arq)]
        self.assertEqual(nomes, ["Pessoa 0", "Pessoa 1", "Pessoa 2"])

    def test_hora_em_texto(self):
        arq = criar_planilha_forms(self.pasta / "f.xlsx", [
            ("10/11/2026 09:15:00", "A", "X", "1", "E"),
        ])
        self.assertEqual(ler_inscricoes(arq)[0][COL_HORA], datetime(2026, 11, 10, 9, 15))

    def test_planilha_de_exemplo_do_repositorio(self):
        inscricoes = ler_inscricoes(RAIZ / "data" / "exemplo" / "teste.xlsx")
        self.assertGreater(len(inscricoes), 0)

    def test_coluna_faltando_lista_cabecalhos(self):
        wb = Workbook()
        wb.active.append(["ID", "Hora de conclusão", "Nome", "Matrícula", "Pergunta X"])
        wb.save(self.pasta / "f.xlsx")
        with self.assertRaises(ValueError) as erro:
            ler_inscricoes(self.pasta / "f.xlsx")
        self.assertIn("Pergunta X", str(erro.exception))

    def test_arquivo_criptografado(self):
        arq = self.pasta / "f.xlsx"
        arq.write_bytes(planilha.ASSINATURA_OLE + b"\0" * 64)
        with self.assertRaises(PermissionError) as erro:
            ler_inscricoes(arq)
        self.assertIn("protegida", str(erro.exception))

    def test_arquivo_pela_metade_mostra_detalhe_tecnico(self):
        criar_planilha_forms(self.pasta / "ok.xlsx", [])
        arq = self.pasta / "f.xlsx"
        arq.write_bytes((self.pasta / "ok.xlsx").read_bytes()[:300])
        with self.assertRaises(PermissionError) as erro:
            ler_inscricoes(arq)
        self.assertIn("Detalhe técnico", str(erro.exception))


class TesteGanhadores(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.arq = criar_planilha_forms(Path(self._tmp.name) / "f.xlsx", [])

    def tearDown(self):
        self._tmp.cleanup()

    def test_gravar_e_ler_de_volta(self):
        ganhadores = [("Game Show C3", "Maria", "0012345", "TechServ", "Caneca")]
        destino = gravar_ganhadores(self.arq, ganhadores)
        self.assertTrue(destino.name.startswith("Game Show C3 - "))
        lidos = ler_ganhadores(self.arq)
        self.assertEqual([g[:5] for g in lidos], ganhadores)

    def test_cada_sessao_gera_arquivo_novo(self):
        gravar_ganhadores(self.arq, [("E1", "A", "1", "X", "P")])
        gravar_ganhadores(self.arq, [("E2", "B", "2", "X", "P")])
        self.assertEqual(len(ler_ganhadores(self.arq)), 2)

    def test_arquivo_temporario_do_excel_e_ignorado(self):
        gravar_ganhadores(self.arq, [("E1", "A", "1", "X", "P")])
        (self.arq.parent / "Ganhadores" / "~$aberto.xlsx").write_bytes(b"lixo")
        self.assertEqual(len(ler_ganhadores(self.arq)), 1)


class TesteTexto(unittest.TestCase):
    def test_normalizar_texto(self):
        self.assertEqual(normalizar_texto("  Palestra  JOSUÉ "), "palestra josue")
        self.assertEqual(normalizar_texto(None), "")

    def test_eventos_da_celula_multipla_selecao(self):
        self.assertEqual(eventos_da_celula("A;B, C;"), ["A", "B, C"])
        self.assertEqual(eventos_da_celula(None), [])


if __name__ == "__main__":
    unittest.main()
