"""Interface: tela de exibição e fluxo do operador (Play / Encerrar).

Precisam de uma tela (Tk); são pulados se não houver.
"""

import tempfile
import tkinter as tk
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

import customtkinter as ctk

from sorteio import telas
from sorteio.planilha import ler_ganhadores
from tests.apoio import criar_planilha_forms

EVENTO = "Game Show C3"


def textos(widget):
    """Textos de todos os CTkLabel dentro de *widget*."""
    achados = []
    for filho in widget.winfo_children():
        if isinstance(filho, ctk.CTkLabel):
            achados.append(filho.cget("text"))
        achados.extend(textos(filho))
    return achados


def esperar(janela, ms):
    """Deixa a interface rodar por *ms* milissegundos."""
    fim = datetime.now() + timedelta(milliseconds=ms)
    while datetime.now() < fim:
        janela.update()


class TesteTk(unittest.TestCase):
    def setUp(self):
        try:
            self.raiz = ctk.CTk()
        except tk.TclError as e:
            self.skipTest(f"sem tela disponível: {e}")
        self.raiz.withdraw()

    def tearDown(self):
        self.raiz.destroy()


class TesteExibicao(TesteTk):
    def setUp(self):
        super().setUp()
        self.tela = telas.JanelaExibicao(self.raiz)
        self.tela.geometry("1400x800+0+0")
        esperar(self.tela, 300)

    def test_um_ganhador_aparece_uma_vez(self):
        # Caso relatado: quantidade = 1 mostrava o mesmo nome duas vezes
        self.tela.adicionar_rodada([(EVENTO, "Maria Souza", "123", "X", "Caneca")], EVENTO, "Caneca")
        esperar(self.tela, 500)
        self.assertEqual(textos(self.tela._painel_rodada.conteudo).count("Maria Souza"), 1)
        self.assertEqual(textos(self.tela._painel_todos.conteudo).count("• Maria Souza"), 1)

    def test_rodadas_seguidas_com_um_ganhador(self):
        for i in range(3):
            self.tela.adicionar_rodada([(EVENTO, f"Pessoa {i}", str(i), "X", "P")], EVENTO, "P")
            esperar(self.tela, 300)
            self.assertEqual(textos(self.tela._painel_rodada.conteudo).count(f"Pessoa {i}"), 1)
        todos = textos(self.tela._painel_todos.conteudo)
        for i in range(3):
            self.assertEqual(todos.count(f"• Pessoa {i}"), 1)

    def test_lista_que_nao_cabe_rola_em_loop(self):
        ganhadores = [(EVENTO, f"Pessoa {i}", str(i), "X", "P") for i in range(30)]
        self.tela.adicionar_rodada(ganhadores, EVENTO, "P")
        esperar(self.tela, 500)
        painel = self.tela._painel_rodada
        self.assertIsNotNone(painel._copia)  # segunda cópia só para o loop
        self.assertGreater(painel._offset, 0)


class TesteFluxoOperador(unittest.TestCase):
    """O App é a janela principal — sem outra raiz Tk junto."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        hora = datetime.now() - timedelta(minutes=1)
        respostas = [(hora, f"Pessoa {n}", "X", f"M{n}", EVENTO) for n in range(6)]
        respostas.append((hora, "PESSOA 0", "X", "m0", EVENTO))  # inscrição repetida
        self.arq = criar_planilha_forms(Path(self._tmp.name) / "forms.xlsx", respostas)

        self.avisos = []
        alvo = telas.messagebox
        self._patches = [
            mock.patch.object(telas, "caminho_da_planilha", lambda: self.arq),
            mock.patch.object(alvo, "showwarning", lambda t, m, **k: self.avisos.append(m)),
            mock.patch.object(alvo, "showerror", lambda t, m, **k: self.avisos.append(m)),
            mock.patch.object(alvo, "showinfo", lambda t, m, **k: None),
            mock.patch.object(alvo, "askyesno", lambda t, m, **k: True),
        ]
        for p in self._patches:
            p.start()
        self.addCleanup(self._limpar)

        try:
            self.app = telas.App()
        except tk.TclError as e:
            self.skipTest(f"sem tela disponível: {e}")
        self.app.withdraw()
        self.app._carregar_eventos()

    def _limpar(self):
        app = getattr(self, "app", None)
        if app is not None:
            if app._display is not None:
                app._display.destroy()
            app.destroy()
        for p in self._patches:
            p.stop()
        self._tmp.cleanup()

    def _play(self, quantidade):
        self.app.combo_evento.set(EVENTO)
        self.app.entry_horario.delete(0, "end")
        self.app.entry_horario.insert(0, "2359")
        self.app.entry_quantidade.delete(0, "end")
        self.app.entry_quantidade.insert(0, str(quantidade))
        self.app.entry_premio.delete(0, "end")
        self.app.entry_premio.insert(0, "Caneca")
        self.app._ao_clicar_play()

    def test_play_quantidade_1_ate_esgotar(self):
        for _ in range(6):
            self._play(1)
        nomes = [g[1] for g in self.app.ganhadores_sessao]
        self.assertEqual(sorted(nomes), [f"Pessoa {n}" for n in range(6)], self.avisos)

        self._play(1)  # ninguém mais elegível
        self.assertIn("Não há inscritos elegíveis", self.avisos[-1])
        self.assertEqual(len(self.app.ganhadores_sessao), 6)

    def test_nova_sessao_respeita_ganhadores_gravados(self):
        for _ in range(3):
            self._play(1)
        primeira = {g[1] for g in self.app.ganhadores_sessao}
        self.app._ao_clicar_encerrar()
        self.assertEqual(len(ler_ganhadores(self.arq)), 3)
        self.assertFalse(self.app.evento_travado)

        for _ in range(3):
            self._play(1)
        segunda = {g[1] for g in self.app.ganhadores_sessao}
        self.assertEqual(primeira & segunda, set())
        self._play(1)
        self.assertIn("Não há inscritos elegíveis", self.avisos[-1])


if __name__ == "__main__":
    unittest.main()
