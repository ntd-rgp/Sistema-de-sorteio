"""Interface gráfica — janela de controles + janela de exibição."""

import tkinter as tk
import tkinter.messagebox as messagebox
from datetime import datetime

import customtkinter as ctk

from sorteio.planilha import (
    caminho_da_planilha,
    ler_inscricoes,
    ler_ganhadores,
    gravar_ganhadores,
)
from sorteio.sorteador import listar_eventos, filtrar_ja_ganhadores, sortear


# ──────────────────────────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────────────────────────
def _cor_fundo():
    """Cor de fundo dos frames CTk no modo atual."""
    try:
        cores = ctk.ThemeManager.theme["CTkFrame"]["fg_color"]
        return cores[1] if ctk.get_appearance_mode() == "Dark" else cores[0]
    except (KeyError, IndexError):
        return "#2b2b2b" if ctk.get_appearance_mode() == "Dark" else "#dbdbdb"


# ──────────────────────────────────────────────────────────────────
# Painel com rolagem automática infinita
# ──────────────────────────────────────────────────────────────────
class PainelRolagem(ctk.CTkFrame):
    """Frame cujo conteúdo rola automaticamente em loop infinito.

    O conteúdo é duplicado internamente; ao atingir o fim da primeira
    cópia, o offset retorna a zero — transição imperceptível.
    """

    def __init__(self, master, velocidade=1, intervalo=40, **kwargs):
        super().__init__(master, **kwargs)

        self._canvas = tk.Canvas(
            self, highlightthickness=0, bd=0, bg=_cor_fundo(),
        )
        self._canvas.pack(fill="both", expand=True)

        self.conteudo = ctk.CTkFrame(self._canvas, fg_color="transparent")
        self._win_id = self._canvas.create_window(
            (0, 0), window=self.conteudo, anchor="nw",
        )

        self._canvas.bind("<Configure>", self._ao_redim_canvas)
        self.conteudo.bind("<Configure>", self._ao_redim_conteudo)

        self._offset = 0.0
        self._altura_bloco = 0
        self._rolando = False
        self._velocidade = velocidade
        self._intervalo = intervalo
        self._after_id = None

    def _ao_redim_canvas(self, event):
        self._canvas.itemconfig(self._win_id, width=event.width)
        self._canvas.configure(bg=_cor_fundo())

    def _ao_redim_conteudo(self, event):
        self._canvas.configure(scrollregion=(0, 0, event.width, event.height))

    def definir_altura_bloco(self, h):
        self._altura_bloco = h

    def limpar(self):
        self.parar()
        for w in self.conteudo.winfo_children():
            w.destroy()
        self._offset = 0.0
        self._altura_bloco = 0
        self._canvas.yview_moveto(0)

    def iniciar(self):
        if not self._rolando:
            self._rolando = True
            self._tick()

    def parar(self):
        self._rolando = False
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None

    def _tick(self):
        if not self._rolando:
            return

        if self._altura_bloco <= 0:
            self._after_id = self.after(self._intervalo, self._tick)
            return

        self._offset += self._velocidade
        if self._offset >= self._altura_bloco:
            self._offset -= self._altura_bloco

        total = self.conteudo.winfo_reqheight()
        if total > 0:
            self._canvas.yview_moveto(self._offset / total)

        self._after_id = self.after(self._intervalo, self._tick)


# ──────────────────────────────────────────────────────────────────
# Janela de exibição (projetor)
# ──────────────────────────────────────────────────────────────────
class JanelaExibicao(ctk.CTkToplevel):
    """Dois painéis lado a lado: rodada atual (esquerda) e acumulado (direita)."""

    def __init__(self, master):
        super().__init__(master)
        self.title("Sorteio SIPAT 2026 — Ganhadores")
        self.geometry("1400x800")
        self.minsize(900, 600)

        self._rodada_num = 0
        self._rodadas = []

        self._criar_layout()
        self.protocol("WM_DELETE_WINDOW", self._esconder)

    def _esconder(self):
        self.withdraw()

    # ── Layout ────────────────────────────────────────────────────

    def _criar_layout(self):
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=10, pady=10)
        container.grid_columnconfigure(0, weight=1)
        container.grid_columnconfigure(1, weight=1)
        container.grid_rowconfigure(0, weight=1)

        # Painel esquerdo — rodada atual
        esq = ctk.CTkFrame(container)
        esq.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        ctk.CTkLabel(
            esq, text="Ganhadores da Rodada",
            font=("Segoe UI", 26, "bold"),
        ).pack(padx=15, pady=(15, 5))

        self._lbl_rodada = ctk.CTkLabel(esq, text="", font=("Segoe UI", 15))
        self._lbl_rodada.pack(padx=15, pady=(0, 10))

        self._painel_rodada = PainelRolagem(esq, velocidade=1, intervalo=40)
        self._painel_rodada.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Painel direito — acumulado
        dire = ctk.CTkFrame(container)
        dire.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        ctk.CTkLabel(
            dire, text="Todos os Ganhadores",
            font=("Segoe UI", 26, "bold"),
        ).pack(padx=15, pady=(15, 10))

        self._painel_todos = PainelRolagem(dire, velocidade=1, intervalo=40)
        self._painel_todos.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    # ── API pública ───────────────────────────────────────────────

    def adicionar_rodada(self, resultado, evento, premio):
        self._rodada_num += 1
        ganhadores = [(g[1], g[2], g[3], g[4]) for g in resultado]
        self._rodadas.append((premio, evento, ganhadores))

        self._atualizar_esquerda(ganhadores, evento, premio)
        self._atualizar_direita()
        self.deiconify()

    def limpar_tudo(self):
        self._rodada_num = 0
        self._rodadas.clear()
        self._painel_rodada.limpar()
        self._painel_todos.limpar()
        self._lbl_rodada.configure(text="")

    # ── Painel esquerdo ───────────────────────────────────────────

    def _atualizar_esquerda(self, ganhadores, evento, premio):
        self._painel_rodada.parar()
        self._painel_rodada.limpar()
        self._lbl_rodada.configure(
            text=f"Rodada {self._rodada_num} — {premio} ({evento})",
        )

        frame = self._painel_rodada.conteudo
        self._criar_cards(frame, ganhadores)

        frame.update_idletasks()
        bloco_h = frame.winfo_reqheight()

        self._criar_cards(frame, ganhadores)

        self._painel_rodada.definir_altura_bloco(bloco_h)
        self._painel_rodada.iniciar()

    @staticmethod
    def _criar_cards(parent, ganhadores):
        for nome, mat, empresa, premio in ganhadores:
            card = ctk.CTkFrame(parent, corner_radius=12)
            card.pack(fill="x", padx=8, pady=6)

            ctk.CTkLabel(
                card, text=nome,
                font=("Segoe UI", 22, "bold"), anchor="w",
            ).pack(padx=15, pady=(12, 2), anchor="w")

            ctk.CTkLabel(
                card, text=f"Matrícula: {mat}  ·  {empresa}",
                font=("Segoe UI", 15), anchor="w",
            ).pack(padx=15, pady=(0, 2), anchor="w")

            ctk.CTkLabel(
                card, text=f"Prêmio: {premio}",
                font=("Segoe UI", 15), anchor="w",
                text_color=("#1b5e20", "#66bb6a"),
            ).pack(padx=15, pady=(0, 12), anchor="w")

    # ── Painel direito ────────────────────────────────────────────

    def _atualizar_direita(self):
        self._painel_todos.parar()
        self._painel_todos.limpar()

        frame = self._painel_todos.conteudo
        self._criar_blocos(frame, self._rodadas)

        frame.update_idletasks()
        bloco_h = frame.winfo_reqheight()

        self._criar_blocos(frame, self._rodadas)

        self._painel_todos.definir_altura_bloco(bloco_h)
        self._painel_todos.iniciar()

    @staticmethod
    def _criar_blocos(parent, rodadas):
        for i, (premio, evento, ganhadores) in enumerate(rodadas, 1):
            caixa = ctk.CTkFrame(
                parent, corner_radius=12,
                border_width=2, border_color=("#999999", "#555555"),
            )
            caixa.pack(fill="x", padx=8, pady=8)

            ctk.CTkLabel(
                caixa, text=f"Rodada {i} — {premio}",
                font=("Segoe UI", 17, "bold"), anchor="w",
            ).pack(padx=12, pady=(10, 3), anchor="w")

            ctk.CTkLabel(
                caixa, text=evento,
                font=("Segoe UI", 12), anchor="w",
                text_color=("gray50", "gray60"),
            ).pack(padx=12, pady=(0, 6), anchor="w")

            for nome, mat, empresa, pr in ganhadores:
                linha = ctk.CTkFrame(caixa, fg_color="transparent")
                linha.pack(fill="x", padx=12, pady=3)

                ctk.CTkLabel(
                    linha, text=f"• {nome}",
                    font=("Segoe UI", 14, "bold"), anchor="w",
                ).pack(anchor="w")

                ctk.CTkLabel(
                    linha,
                    text=f"   Mat: {mat}  ·  {empresa}  ·  Prêmio: {pr}",
                    font=("Segoe UI", 12), anchor="w",
                ).pack(anchor="w")

            ctk.CTkFrame(caixa, height=5, fg_color="transparent").pack()


# ──────────────────────────────────────────────────────────────────
# Janela de controles (operador)
# ──────────────────────────────────────────────────────────────────
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Sorteio SIPAT 2026 — Controles")
        self.geometry("560x500")
        self.minsize(450, 420)

        self.ganhadores_sessao = []
        self.evento_travado = False

        self._criar_widgets()
        self._display = JanelaExibicao(self)
        self._carregar_eventos()
        self.protocol("WM_DELETE_WINDOW", self._ao_fechar_janela)

    # ── Widgets ───────────────────────────────────────────────────

    def _criar_widgets(self):
        ctk.CTkLabel(
            self, text="Controles do Sorteio",
            font=("Segoe UI", 22, "bold"),
        ).pack(padx=20, pady=(20, 10))

        frame_cfg = ctk.CTkFrame(self)
        frame_cfg.pack(padx=20, pady=10, fill="x")

        ctk.CTkLabel(frame_cfg, text="Evento:").grid(
            row=0, column=0, padx=10, pady=8, sticky="w",
        )
        self.combo_evento = ctk.CTkOptionMenu(
            frame_cfg, values=["Carregando..."], width=300,
        )
        self.combo_evento.grid(row=0, column=1, padx=10, pady=8, sticky="w")
        self.btn_recarregar = ctk.CTkButton(
            frame_cfg, text="Recarregar", width=100,
            command=self._carregar_eventos,
        )
        self.btn_recarregar.grid(row=0, column=2, padx=10, pady=8)

        ctk.CTkLabel(frame_cfg, text="Horário limite:").grid(
            row=1, column=0, padx=10, pady=8, sticky="w",
        )
        self.entry_horario = ctk.CTkEntry(
            frame_cfg, placeholder_text="dd/mm/aaaa HH:MM", width=220,
        )
        self.entry_horario.grid(row=1, column=1, padx=10, pady=8, sticky="w")

        ctk.CTkLabel(frame_cfg, text="Quantidade:").grid(
            row=2, column=0, padx=10, pady=8, sticky="w",
        )
        self.entry_quantidade = ctk.CTkEntry(
            frame_cfg, placeholder_text="Ex: 3", width=100,
        )
        self.entry_quantidade.grid(row=2, column=1, padx=10, pady=8, sticky="w")

        ctk.CTkLabel(frame_cfg, text="Prêmio:").grid(
            row=3, column=0, padx=10, pady=8, sticky="w",
        )
        self.entry_premio = ctk.CTkEntry(
            frame_cfg, placeholder_text="Ex: Caneca Térmica", width=300,
        )
        self.entry_premio.grid(row=3, column=1, padx=10, pady=8, sticky="w")

        frame_btn = ctk.CTkFrame(self)
        frame_btn.pack(padx=20, pady=10, fill="x")

        self.btn_play = ctk.CTkButton(
            frame_btn, text="Play — Sortear", command=self._ao_clicar_play,
            fg_color="#2e7d32", hover_color="#1b5e20", height=40,
        )
        self.btn_play.pack(side="left", padx=10, pady=10, expand=True, fill="x")

        self.btn_encerrar = ctk.CTkButton(
            frame_btn, text="Encerrar Sorteio", command=self._ao_clicar_encerrar,
            fg_color="#c62828", hover_color="#8e0000", height=40, state="disabled",
        )
        self.btn_encerrar.pack(side="left", padx=10, pady=10, expand=True, fill="x")

        self.label_sessao = ctk.CTkLabel(
            self, text="Sessão: 0 ganhadores acumulados",
        )
        self.label_sessao.pack(padx=20, pady=(5, 20))

    # ── Carregar eventos ──────────────────────────────────────────

    def _carregar_eventos(self):
        arquivo = caminho_da_planilha()
        if not arquivo.exists():
            messagebox.showerror(
                "Arquivo não encontrado",
                f"Planilha não encontrada em:\n{arquivo}\n\n"
                "Verifique se a pasta está sincronizada.",
            )
            self.combo_evento.configure(values=["(nenhum)"])
            self.combo_evento.set("(nenhum)")
            return

        try:
            todas = ler_inscricoes(arquivo)
            eventos = listar_eventos(todas)
        except Exception as e:
            messagebox.showerror("Erro ao ler planilha", str(e))
            return

        if not eventos:
            self.combo_evento.configure(values=["(nenhum evento)"])
            self.combo_evento.set("(nenhum evento)")
            return

        self.combo_evento.configure(values=eventos)
        self.combo_evento.set(eventos[0])

    # ── Play ──────────────────────────────────────────────────────

    def _ao_clicar_play(self):
        evento = self.combo_evento.get()
        if evento in ("Carregando...", "(nenhum)", "(nenhum evento)"):
            messagebox.showwarning("Evento", "Selecione um evento válido.")
            return

        texto_horario = self.entry_horario.get().strip()
        if not texto_horario:
            messagebox.showwarning("Horário", "Informe o horário limite.")
            return
        try:
            horario_limite = datetime.strptime(texto_horario, "%d/%m/%Y %H:%M")
        except ValueError:
            messagebox.showwarning(
                "Horário inválido",
                "Use o formato dd/mm/aaaa HH:MM\nExemplo: 20/10/2026 08:30",
            )
            return

        texto_qtd = self.entry_quantidade.get().strip()
        if not texto_qtd:
            messagebox.showwarning("Quantidade", "Informe a quantidade de sorteados.")
            return
        try:
            quantidade = int(texto_qtd)
            if quantidade < 1:
                raise ValueError
        except ValueError:
            messagebox.showwarning(
                "Quantidade inválida",
                "Informe um número inteiro >= 1.",
            )
            return

        premio = self.entry_premio.get().strip()
        if not premio:
            messagebox.showwarning("Prêmio", "Informe o prêmio da rodada.")
            return

        if not self.evento_travado:
            self.evento_travado = True
            self.combo_evento.configure(state="disabled")
            self.btn_recarregar.configure(state="disabled")

        arquivo = caminho_da_planilha()
        try:
            inscricoes = ler_inscricoes(
                arquivo, evento=evento, horario_limite=horario_limite,
            )
            ganhadores_planilha = ler_ganhadores(arquivo)
        except Exception as e:
            messagebox.showerror("Erro ao ler planilha", str(e))
            return

        elegiveis = filtrar_ja_ganhadores(
            inscricoes, ganhadores_planilha, self.ganhadores_sessao, evento,
        )

        try:
            resultado = sortear(elegiveis, quantidade, evento, premio)
        except ValueError as e:
            messagebox.showwarning("Sorteio", str(e))
            return

        self.ganhadores_sessao.extend(resultado)
        self._atualizar_contador()
        self.btn_encerrar.configure(state="normal")

        self._display.adicionar_rodada(resultado, evento, premio)

    # ── Contador ──────────────────────────────────────────────────

    def _atualizar_contador(self):
        n = len(self.ganhadores_sessao)
        self.label_sessao.configure(
            text=f"Sessão: {n} ganhador(es) acumulado(s)",
        )

    # ── Encerrar ──────────────────────────────────────────────────

    def _ao_clicar_encerrar(self):
        if not self.ganhadores_sessao:
            return

        arquivo = caminho_da_planilha()
        try:
            gravar_ganhadores(arquivo, self.ganhadores_sessao)
        except PermissionError as e:
            messagebox.showerror("Erro ao salvar", str(e))
            return
        except Exception as e:
            messagebox.showerror("Erro ao salvar", str(e))
            return

        n = len(self.ganhadores_sessao)
        messagebox.showinfo(
            "Sorteio encerrado",
            f"{n} ganhador(es) gravado(s) na aba 'Ganhadores'.",
        )

        self.ganhadores_sessao.clear()
        self._atualizar_contador()
        self.evento_travado = False
        self.combo_evento.configure(state="normal")
        self.btn_recarregar.configure(state="normal")
        self.btn_encerrar.configure(state="disabled")

        self._display.limpar_tudo()

    # ── Fechar janela ─────────────────────────────────────────────

    def _ao_fechar_janela(self):
        if self.ganhadores_sessao:
            resposta = messagebox.askyesnocancel(
                "Ganhadores não salvos",
                f"Há {len(self.ganhadores_sessao)} ganhador(es) não salvo(s).\n\n"
                "Deseja salvar antes de sair?",
            )
            if resposta is None:
                return
            if resposta:
                self._ao_clicar_encerrar()
                if self.ganhadores_sessao:
                    return

        self.destroy()


def iniciar():
    """Cria e executa a aplicação."""
    ctk.set_appearance_mode("dark")
    app = App()
    app.mainloop()
