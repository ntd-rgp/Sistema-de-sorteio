"""Interface gráfica (CustomTkinter) — versão funcional para testes."""

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


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Sorteio SIPAT 2026")
        self.geometry("900x650")
        self.minsize(700, 500)

        self.ganhadores_sessao = []
        self.evento_travado = False

        self._criar_widgets()
        self._carregar_eventos()
        self.protocol("WM_DELETE_WINDOW", self._ao_fechar_janela)

    # ------------------------------------------------------------------
    # Construção da interface
    # ------------------------------------------------------------------
    def _criar_widgets(self):
        # --- Frame de configuração ---
        frame_config = ctk.CTkFrame(self)
        frame_config.pack(padx=20, pady=(20, 10), fill="x")

        # Evento
        ctk.CTkLabel(frame_config, text="Evento:").grid(
            row=0, column=0, padx=10, pady=8, sticky="w"
        )
        self.combo_evento = ctk.CTkOptionMenu(frame_config, values=["Carregando..."], width=350)
        self.combo_evento.grid(row=0, column=1, padx=10, pady=8, sticky="w")

        self.btn_recarregar = ctk.CTkButton(
            frame_config, text="Recarregar", width=100, command=self._carregar_eventos
        )
        self.btn_recarregar.grid(row=0, column=2, padx=10, pady=8)

        # Horário limite
        ctk.CTkLabel(frame_config, text="Horário limite:").grid(
            row=1, column=0, padx=10, pady=8, sticky="w"
        )
        self.entry_horario = ctk.CTkEntry(
            frame_config, placeholder_text="dd/mm/aaaa HH:MM", width=250
        )
        self.entry_horario.grid(row=1, column=1, padx=10, pady=8, sticky="w")

        # Quantidade
        ctk.CTkLabel(frame_config, text="Quantidade:").grid(
            row=2, column=0, padx=10, pady=8, sticky="w"
        )
        self.entry_quantidade = ctk.CTkEntry(
            frame_config, placeholder_text="Ex: 3", width=100
        )
        self.entry_quantidade.grid(row=2, column=1, padx=10, pady=8, sticky="w")

        # Prêmio
        ctk.CTkLabel(frame_config, text="Prêmio:").grid(
            row=3, column=0, padx=10, pady=8, sticky="w"
        )
        self.entry_premio = ctk.CTkEntry(
            frame_config, placeholder_text="Ex: Caneca Térmica", width=350
        )
        self.entry_premio.grid(row=3, column=1, padx=10, pady=8, sticky="w")

        # --- Frame de botões ---
        frame_botoes = ctk.CTkFrame(self)
        frame_botoes.pack(padx=20, pady=5, fill="x")

        self.btn_play = ctk.CTkButton(
            frame_botoes, text="Play — Sortear", command=self._ao_clicar_play,
            fg_color="#2e7d32", hover_color="#1b5e20", height=40
        )
        self.btn_play.pack(side="left", padx=10, pady=10, expand=True, fill="x")

        self.btn_encerrar = ctk.CTkButton(
            frame_botoes, text="Encerrar Sorteio", command=self._ao_clicar_encerrar,
            fg_color="#c62828", hover_color="#8e0000", height=40, state="disabled"
        )
        self.btn_encerrar.pack(side="left", padx=10, pady=10, expand=True, fill="x")

        # --- Label do contador da sessão ---
        self.label_sessao = ctk.CTkLabel(self, text="Sessão: 0 ganhadores acumulados")
        self.label_sessao.pack(padx=20, pady=(5, 0))

        # --- Área de exibição dos ganhadores ---
        ctk.CTkLabel(self, text="Ganhadores:", anchor="w").pack(
            padx=20, pady=(10, 0), anchor="w"
        )

        self.textbox = ctk.CTkTextbox(self, font=("Consolas", 20), state="disabled")
        self.textbox.pack(padx=20, pady=(5, 20), fill="both", expand=True)

    # ------------------------------------------------------------------
    # Carregar eventos da planilha
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Play — sortear
    # ------------------------------------------------------------------
    def _ao_clicar_play(self):
        # Validar evento
        evento = self.combo_evento.get()
        if evento in ("Carregando...", "(nenhum)", "(nenhum evento)"):
            messagebox.showwarning("Evento", "Selecione um evento válido.")
            return

        # Validar horário
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

        # Validar quantidade
        texto_qtd = self.entry_quantidade.get().strip()
        if not texto_qtd:
            messagebox.showwarning("Quantidade", "Informe a quantidade de sorteados.")
            return
        try:
            quantidade = int(texto_qtd)
            if quantidade < 1:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Quantidade inválida", "Informe um número inteiro maior ou igual a 1.")
            return

        # Validar prêmio
        premio = self.entry_premio.get().strip()
        if not premio:
            messagebox.showwarning("Prêmio", "Informe o prêmio da rodada.")
            return

        # --- Travar evento na primeira rodada (RN-06) ---
        if not self.evento_travado:
            self.evento_travado = True
            self.combo_evento.configure(state="disabled")
            self.btn_recarregar.configure(state="disabled")

        # --- Ler planilha no momento do play (RN-07) ---
        arquivo = caminho_da_planilha()
        try:
            inscricoes = ler_inscricoes(arquivo, evento=evento, horario_limite=horario_limite)
            ganhadores_planilha = ler_ganhadores(arquivo)
        except Exception as e:
            messagebox.showerror("Erro ao ler planilha", str(e))
            return

        # --- Filtrar quem já ganhou ---
        elegiveis = filtrar_ja_ganhadores(
            inscricoes, ganhadores_planilha, self.ganhadores_sessao, evento
        )

        # --- Sortear ---
        try:
            resultado = sortear(elegiveis, quantidade, evento, premio)
        except ValueError as e:
            messagebox.showwarning("Sorteio", str(e))
            return

        # --- Acumular na sessão (RN-06) ---
        self.ganhadores_sessao.extend(resultado)
        self._atualizar_contador()

        # --- Habilitar botão Encerrar ---
        self.btn_encerrar.configure(state="normal")

        # --- Exibir resultado ---
        self._exibir_resultado(resultado, evento, premio)

    # ------------------------------------------------------------------
    # Exibir ganhadores no textbox
    # ------------------------------------------------------------------
    def _exibir_resultado(self, resultado, evento, premio):
        self.textbox.configure(state="normal")

        self.textbox.insert("end", f"--- Rodada: {premio} ({evento}) ---\n")
        for i, g in enumerate(resultado, 1):
            # g = (evento, nome, matricula, empresa, premio)
            self.textbox.insert("end", f"  {i}. {g[1]}  |  {g[3]}  |  Mat: {g[2]}\n")
        self.textbox.insert("end", "\n")

        self.textbox.configure(state="disabled")
        self.textbox.see("end")

    # ------------------------------------------------------------------
    # Atualizar contador
    # ------------------------------------------------------------------
    def _atualizar_contador(self):
        n = len(self.ganhadores_sessao)
        self.label_sessao.configure(text=f"Sessão: {n} ganhador(es) acumulado(s)")

    # ------------------------------------------------------------------
    # Encerrar sorteio — gravar e destravar
    # ------------------------------------------------------------------
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

        # Limpar sessão e destravar evento
        self.ganhadores_sessao.clear()
        self._atualizar_contador()
        self.evento_travado = False
        self.combo_evento.configure(state="normal")
        self.btn_recarregar.configure(state="normal")
        self.btn_encerrar.configure(state="disabled")

        # Limpar textbox
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.configure(state="disabled")

    # ------------------------------------------------------------------
    # Fechar janela com confirmação (RN-06.5)
    # ------------------------------------------------------------------
    def _ao_fechar_janela(self):
        if self.ganhadores_sessao:
            resposta = messagebox.askyesnocancel(
                "Ganhadores não salvos",
                f"Há {len(self.ganhadores_sessao)} ganhador(es) não salvo(s).\n\n"
                "Deseja salvar antes de sair?",
            )
            if resposta is None:  # Cancelar
                return
            if resposta:  # Sim — salvar
                self._ao_clicar_encerrar()
                if self.ganhadores_sessao:
                    return  # falhou ao salvar, não fecha

        self.destroy()


def iniciar():
    """Cria e executa a janela principal."""
    ctk.set_appearance_mode("dark")
    app = App()
    app.mainloop()
