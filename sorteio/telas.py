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
    normalizar_texto,
)
from sorteio.sorteador import (
    filtrar_inscricoes,
    filtrar_ja_ganhadores,
    listar_eventos,
    planilha_pode_estar_desatualizada,
    resposta_mais_recente,
    sortear,
)


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
# Eventos SIPAT 2026  (label curto, texto da opção no Forms)
# A lista suspensa mostra os eventos que existem na planilha; quando o
# texto da planilha bate com um destes (ignorando acento, maiúsculas e
# espaços), aparece o label curto. Eventos fora desta lista aparecem
# com o texto da planilha.
# ──────────────────────────────────────────────────────────────────
EVENTOS_SIPAT = [
    ("Abertura + Denison/Fabi",            "Abertura, Palestra do Denison e Fabi"),
    ("Palestra Josué + Teatro Educa Vida", "Palestra Josue, Teatro educa vida"),
    ("Game Show Porta Refeitório",         "Game Show porta refeitório"),
    ("Palestra Josué Refeitório",          "Palestra Josue no refeitório"),
    ("Game Show C3",                       "Game Show C3"),
    ("Game Show Gramo",                    "Game Show Gramo"),
    ("Encerramento + Rodrigo/Peralta",     "Encerramento, Palestra Rodrigo, Palestra Peralta"),
    ("14h — Oficina Marmita 1",            "Oficina de marmita 1 - 14h"),
    ("15h — Oficina Marmita 2",            "Oficina de marmita 2 - 15h"),
    ("14h — Plantio Mudas 1",              "Plantio de mudas 1 - 14"),
    ("15h — Plantio Mudas 2",              "Plantio de mudas 2 - 15"),
    ("11/11 — GA: Oficina Marmita",        "Turno GA: Oficina de marmita 11/11"),
    ("12/11 — GA: Geral",                  "Turno GA: Geral 12/11"),
    ("13/11 — GB: Oficina Marmita",        "Turno GB: Oficina de marmita 13/11"),
    ("14/11 — GB: Geral",                  "Turno GB: Geral 14/11"),
    ("14/11 — GC: Oficina Marmita",        "Turno GC: Oficina de marmita 14/11"),
    ("16/11 — GC: Geral",                  "Turno GC: Geral 16/11"),
    ("06/11 — GD: Oficina Marmita",        "Turno GD: Oficina de marmita 06/11"),
    ("18/11 — GD: Geral",                  "Turno GD: Geral 18/11"),
    ("09/11 — GE: Oficina Marmita",        "Turno GE: Oficina de marmita 09/11"),
    ("11/11 — GE: Geral",                  "Turno GE: Geral 11/11"),
]

SEM_EVENTOS = "(nenhum evento — clique em Recarregar)"


def _rotulos_eventos(eventos):
    """Monta {label exibido: texto do evento na planilha}.

    Eventos conhecidos (EVENTOS_SIPAT) vêm primeiro, na ordem da lista,
    com o label curto; os demais vêm depois, com o texto da planilha.
    """
    por_texto = {normalizar_texto(e): e for e in eventos}
    rotulos = {}
    for label, texto in EVENTOS_SIPAT:
        evento = por_texto.pop(normalizar_texto(texto), None)
        if evento is not None:
            rotulos[label] = evento
    for evento in por_texto.values():
        rotulos[evento] = evento
    return rotulos


# ──────────────────────────────────────────────────────────────────
# Cores da janela de exibição — sempre clara (fundo branco),
# independente do modo escuro da janela de controles.
# ──────────────────────────────────────────────────────────────────
EXIB_FUNDO = "#ffffff"
EXIB_CARD = "#f3f5f7"
EXIB_BORDA = "#d5dae0"
EXIB_TEXTO = "#1a1a1a"
EXIB_TEXTO_SEC = "#5f6368"
EXIB_PREMIO_FUNDO = "#d10c56"
EXIB_PREMIO_TEXTO = "#ffffff"


def _etiqueta_premio(parent, premio, tamanho):
    """Etiqueta do prêmio: texto branco em negrito sobre fundo destacado."""
    return ctk.CTkLabel(
        parent, text=premio,
        font=("Segoe UI", tamanho, "bold"),
        fg_color=EXIB_PREMIO_FUNDO, text_color=EXIB_PREMIO_TEXTO,
        corner_radius=8, padx=14, pady=2,
    )


# ──────────────────────────────────────────────────────────────────
# Painel com rolagem automática infinita
# ──────────────────────────────────────────────────────────────────
class PainelRolagem(ctk.CTkFrame):
    """Frame cujo conteúdo rola automaticamente em loop infinito.

    O conteúdo é duplicado internamente; ao atingir o fim da primeira
    cópia, o offset retorna a zero — transição imperceptível.
    """

    def __init__(self, master, velocidade=1, intervalo=40, cor_fundo=None, **kwargs):
        super().__init__(master, **kwargs)

        self._cor_fundo = cor_fundo
        self._canvas = tk.Canvas(
            self, highlightthickness=0, bd=0, bg=cor_fundo or _cor_fundo(),
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
        self._canvas.configure(bg=self._cor_fundo or _cor_fundo())

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
        self.configure(fg_color=EXIB_FUNDO)
        # Abre maximizada para ocupar toda a tela do projetor
        self.after(100, lambda: self.state("zoomed"))

        self._rodada_num = 0
        self._rodadas = []

        self._criar_layout()
        self.protocol("WM_DELETE_WINDOW", self._esconder)

    def _esconder(self):
        self.withdraw()

    # ── Layout ────────────────────────────────────────────────────

    def _criar_layout(self):
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=6, pady=6)
        container.grid_columnconfigure(0, weight=1)
        container.grid_columnconfigure(1, weight=1)
        container.grid_rowconfigure(0, weight=1)

        # Painel esquerdo — rodada atual
        esq = ctk.CTkFrame(
            container, fg_color=EXIB_FUNDO,
            border_width=1, border_color=EXIB_BORDA,
        )
        esq.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        ctk.CTkLabel(
            esq, text="Ganhadores da Rodada",
            font=("Segoe UI", 34, "bold"), text_color=EXIB_TEXTO,
        ).pack(padx=10, pady=(12, 2))

        self._lbl_rodada = ctk.CTkLabel(
            esq, text="", font=("Segoe UI", 20), text_color=EXIB_TEXTO_SEC,
        )
        self._lbl_rodada.pack(padx=10, pady=(0, 8))

        self._painel_rodada = PainelRolagem(
            esq, velocidade=1, intervalo=40,
            cor_fundo=EXIB_FUNDO, fg_color=EXIB_FUNDO,
        )
        self._painel_rodada.pack(fill="both", expand=True, padx=4, pady=(0, 6))

        # Painel direito — acumulado
        dire = ctk.CTkFrame(
            container, fg_color=EXIB_FUNDO,
            border_width=1, border_color=EXIB_BORDA,
        )
        dire.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        ctk.CTkLabel(
            dire, text="Todos os Ganhadores",
            font=("Segoe UI", 34, "bold"), text_color=EXIB_TEXTO,
        ).pack(padx=10, pady=(12, 8))

        self._painel_todos = PainelRolagem(
            dire, velocidade=1, intervalo=40,
            cor_fundo=EXIB_FUNDO, fg_color=EXIB_FUNDO,
        )
        self._painel_todos.pack(fill="both", expand=True, padx=4, pady=(0, 6))

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
            card = ctk.CTkFrame(parent, corner_radius=12, fg_color=EXIB_CARD)
            card.pack(fill="x", padx=4, pady=5)

            ctk.CTkLabel(
                card, text=nome,
                font=("Segoe UI", 38, "bold"), anchor="w",
                text_color=EXIB_TEXTO,
            ).pack(padx=16, pady=(10, 0), anchor="w")

            ctk.CTkLabel(
                card, text=f"Matrícula: {mat}  ·  {empresa}",
                font=("Segoe UI", 24), anchor="w",
                text_color=EXIB_TEXTO_SEC,
            ).pack(padx=16, pady=(0, 6), anchor="w")

            _etiqueta_premio(card, premio, 30).pack(
                padx=16, pady=(0, 12), anchor="w",
            )

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
                parent, corner_radius=12, fg_color=EXIB_CARD,
                border_width=1, border_color=EXIB_BORDA,
            )
            caixa.pack(fill="x", padx=4, pady=6)

            cabecalho = ctk.CTkFrame(caixa, fg_color="transparent")
            cabecalho.pack(fill="x", padx=14, pady=(12, 0))

            ctk.CTkLabel(
                cabecalho, text=f"Rodada {i}",
                font=("Segoe UI", 28, "bold"), anchor="w",
                text_color=EXIB_TEXTO,
            ).pack(side="left")

            _etiqueta_premio(cabecalho, premio, 26).pack(
                side="left", padx=(14, 0),
            )

            ctk.CTkLabel(
                caixa, text=evento,
                font=("Segoe UI", 18), anchor="w",
                text_color=EXIB_TEXTO_SEC,
            ).pack(padx=14, pady=(2, 6), anchor="w")

            for nome, mat, empresa, pr in ganhadores:
                linha = ctk.CTkFrame(caixa, fg_color="transparent")
                linha.pack(fill="x", padx=14, pady=4)

                ctk.CTkLabel(
                    linha, text=f"• {nome}",
                    font=("Segoe UI", 28, "bold"), anchor="w",
                    text_color=EXIB_TEXTO,
                ).pack(anchor="w")

                ctk.CTkLabel(
                    linha,
                    text=f"   Matrícula: {mat}  ·  {empresa}",
                    font=("Segoe UI", 20), anchor="w",
                    text_color=EXIB_TEXTO_SEC,
                ).pack(anchor="w")

            ctk.CTkFrame(caixa, height=5, fg_color="transparent").pack()


# ──────────────────────────────────────────────────────────────────
# Janela de controles (operador)
# ──────────────────────────────────────────────────────────────────
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Sorteio SIPAT 2026 — Controles")
        self.geometry("620x540")
        self.minsize(450, 420)

        self.ganhadores_sessao = []
        self.evento_travado = False

        self._display = None
        self._arquivo = None   # Path da planilha, resolvido na primeira leitura
        self._eventos = {}     # {label exibido: texto do evento na planilha}

        self._criar_widgets()
        self.protocol("WM_DELETE_WINDOW", self._ao_fechar_janela)
        self.after(200, self._carregar_eventos)

    def _garantir_display(self):
        """Cria a janela de exibição se ainda não existe, ou reexibe se oculta."""
        if self._display is None or not self._display.winfo_exists():
            self._display = JanelaExibicao(self)
        else:
            self._display.deiconify()
            self._display.lift()

    # ── Widgets ───────────────────────────────────────────────────

    def _criar_widgets(self):
        ctk.CTkLabel(
            self, text="Controles do Sorteio",
            font=("Segoe UI", 22, "bold"),
        ).pack(padx=20, pady=(20, 5))

        # Indicador de status da planilha (atualizado a cada leitura)
        self.label_status = ctk.CTkLabel(
            self, text="Lendo planilha…", text_color="#ffb74d",
            font=("Segoe UI", 12), justify="center",
        )
        self.label_status.pack(padx=20, pady=(0, 10))

        frame_cfg = ctk.CTkFrame(self)
        frame_cfg.pack(padx=20, pady=10, fill="x")

        ctk.CTkLabel(frame_cfg, text="Evento:").grid(
            row=0, column=0, padx=10, pady=8, sticky="w",
        )
        self.combo_evento = ctk.CTkOptionMenu(
            frame_cfg, values=[SEM_EVENTOS], width=300,
            dynamic_resizing=False,
        )
        self.combo_evento.set(SEM_EVENTOS)
        self.combo_evento.grid(row=0, column=1, padx=10, pady=8, sticky="w")

        self.btn_recarregar = ctk.CTkButton(
            frame_cfg, text="Recarregar", width=90,
            command=self._carregar_eventos,
        )
        self.btn_recarregar.grid(row=0, column=2, padx=(0, 10), pady=8, sticky="w")

        ctk.CTkLabel(frame_cfg, text="Horário limite:").grid(
            row=1, column=0, padx=10, pady=8, sticky="w",
        )
        self._var_horario = tk.StringVar()
        self._var_horario.trace_add("write", self._formatar_horario)
        self._formatando_horario = False
        self.entry_horario = ctk.CTkEntry(
            frame_cfg, textvariable=self._var_horario,
            placeholder_text="HHMM", width=120,
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

        self.btn_tela = ctk.CTkButton(
            self, text="Abrir Tela de Exibição",
            command=self._garantir_display, height=36,
        )
        self.btn_tela.pack(padx=20, pady=5, fill="x")

        self.label_sessao = ctk.CTkLabel(
            self, text="Sessão: 0 ganhadores acumulados",
        )
        self.label_sessao.pack(padx=20, pady=(5, 20))

    # ── Leitura da planilha ───────────────────────────────────────

    def _arquivo_planilha(self):
        """Path da planilha; abre o seletor só se ainda não houver um válido."""
        if self._arquivo is None or not self._arquivo.exists():
            self._arquivo = caminho_da_planilha()
        return self._arquivo

    def _ler_inscricoes(self):
        """Lê a planilha agora e atualiza o status. Devolve None se falhar."""
        arquivo = self._arquivo_planilha()
        self.label_status.configure(text="Lendo planilha…", text_color="#ffb74d")
        self.configure(cursor="watch")
        self.update_idletasks()
        try:
            inscricoes = ler_inscricoes(arquivo)
        except Exception as e:
            self.label_status.configure(
                text=f"Erro ao ler a planilha — {arquivo.name}",
                text_color="#ef5350",
            )
            messagebox.showerror("Erro ao ler planilha", str(e))
            return None
        finally:
            self.configure(cursor="")

        ultima = resposta_mais_recente(inscricoes)
        txt_ultima = ultima.strftime("%d/%m %H:%M:%S") if ultima else "—"
        self.label_status.configure(
            text=(
                f"{arquivo.name}\n"
                f"Lida às {datetime.now():%H:%M:%S} · {len(inscricoes)} inscrições"
                f" · última resposta: {txt_ultima}"
            ),
            text_color="#66bb6a",
        )
        return inscricoes

    def _carregar_eventos(self):
        """Preenche a lista suspensa com os eventos que existem na planilha."""
        if self.evento_travado:
            return

        inscricoes = self._ler_inscricoes()
        if inscricoes is None:
            return

        selecionado = self._eventos.get(self.combo_evento.get())
        self._eventos = _rotulos_eventos(listar_eventos(inscricoes))
        labels = list(self._eventos) or [SEM_EVENTOS]
        self.combo_evento.configure(values=labels)

        # Mantém o evento que estava escolhido, se ainda existir
        atual = next(
            (label for label, evento in self._eventos.items() if evento == selecionado),
            labels[0],
        )
        self.combo_evento.set(atual)

    # ── Auto-formatação do horário (4 dígitos → HH:MM) ─────────

    def _formatar_horario(self, *_args):
        if self._formatando_horario:
            return
        self._formatando_horario = True

        digitos = "".join(c for c in self._var_horario.get() if c.isdigit())[:4]

        if len(digitos) > 2:
            formatado = digitos[:2] + ":" + digitos[2:]
        else:
            formatado = digitos

        self._var_horario.set(formatado)
        self._formatando_horario = False

    # ── Play ──────────────────────────────────────────────────────

    def _ao_clicar_play(self):
        evento_label = self.combo_evento.get()
        evento = self._eventos.get(evento_label)
        if not evento:
            messagebox.showwarning(
                "Evento",
                "Selecione um evento válido.\n\n"
                "Se a lista estiver vazia, clique em Recarregar.",
            )
            return

        texto_horario = self.entry_horario.get().strip()
        if not texto_horario:
            messagebox.showwarning("Horário", "Informe o horário limite.")
            return
        try:
            horario_limite = datetime.strptime(texto_horario, "%H:%M").time()
        except ValueError:
            messagebox.showwarning(
                "Horário inválido",
                "Use o formato HH:MM\nExemplo: 08:30",
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

        # A planilha é lida no momento do play (RN-07)
        inscricoes = self._ler_inscricoes()
        if inscricoes is None:
            return
        try:
            ganhadores_planilha = ler_ganhadores(self._arquivo)
        except Exception as e:
            messagebox.showerror("Erro ao ler ganhadores", str(e))
            return

        # O OneDrive pode demorar a baixar as respostas mais novas do Forms
        if planilha_pode_estar_desatualizada(inscricoes, horario_limite):
            ultima = resposta_mais_recente(inscricoes)
            txt_ultima = ultima.strftime("%d/%m/%Y %H:%M:%S") if ultima else "nenhuma"
            continuar = messagebox.askyesno(
                "Planilha pode estar desatualizada",
                "A planilha neste computador pode ainda não ter todas as "
                "inscrições.\n\n"
                f"Última resposta recebida: {txt_ultima}\n"
                f"Horário limite do sorteio: {texto_horario}\n\n"
                "O OneDrive pode estar demorando para baixar as respostas "
                "mais recentes do Forms. Aguarde a sincronização (ícone do "
                "OneDrive sem setas azuis) e clique em Play de novo.\n\n"
                "Sortear mesmo assim?",
                icon="warning", default="no",
            )
            if not continuar:
                return

        inscricoes = filtrar_inscricoes(inscricoes, evento, horario_limite)
        elegiveis = filtrar_ja_ganhadores(
            inscricoes, ganhadores_planilha, self.ganhadores_sessao, evento,
        )

        try:
            resultado = sortear(elegiveis, quantidade, evento, premio)
        except ValueError as e:
            messagebox.showwarning("Sorteio", str(e))
            return

        if not self.evento_travado:
            self.evento_travado = True
            self.combo_evento.configure(state="disabled")
            self.btn_recarregar.configure(state="disabled")

        self.ganhadores_sessao.extend(resultado)
        self._atualizar_contador()
        self.btn_encerrar.configure(state="normal")

        self._garantir_display()
        self._display.adicionar_rodada(resultado, evento_label, premio)

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

        try:
            destino = gravar_ganhadores(self._arquivo_planilha(), self.ganhadores_sessao)
        except PermissionError as e:
            messagebox.showerror("Erro ao salvar", str(e))
            return
        except Exception as e:
            messagebox.showerror("Erro ao salvar", str(e))
            return

        n = len(self.ganhadores_sessao)
        messagebox.showinfo(
            "Sorteio encerrado",
            f"{n} ganhador(es) gravado(s) em:\n"
            f"{destino.parent.name}\\{destino.name}",
        )

        self.ganhadores_sessao.clear()
        self._atualizar_contador()
        self.evento_travado = False
        self.combo_evento.configure(state="normal")
        self.btn_recarregar.configure(state="normal")
        self.btn_encerrar.configure(state="disabled")

        if self._display and self._display.winfo_exists():
            self._display.limpar_tudo()

    # ── Fechar janela ─────────────────────────────────────────────

    def _ao_fechar_janela(self):
        if self.ganhadores_sessao:
            messagebox.showwarning(
                "Sorteio em andamento",
                f"Há {len(self.ganhadores_sessao)} ganhador(es) não salvo(s).\n\n"
                "Clique em 'Encerrar Sorteio' para salvar os ganhadores "
                "antes de fechar o programa.",
            )
            return

        self.destroy()


def iniciar():
    """Cria e executa a aplicação."""
    ctk.set_appearance_mode("dark")
    app = App()
    app.mainloop()
