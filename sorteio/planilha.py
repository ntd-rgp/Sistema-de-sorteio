"""Leitura e gravação da planilha Excel (inscrições e ganhadores)."""

import re
import socket
import sys
import time
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook, load_workbook

# ---------------------------------------------------------------------------
# Nome do arquivo Excel (gerado pelo Microsoft Forms)
# ---------------------------------------------------------------------------
NOME_ARQUIVO = "Presença Palestras, Atividades e Oficinas SIPAT 2026.xlsx"

# ---------------------------------------------------------------------------
# Índices das colunas na aba de inscrições (linha 2 em diante).
# ⚠️ PENDÊNCIA: confirmar contra a planilha real (seção 3.1 da SPEC).
# Valores provisórios baseados na estrutura típica do Forms:
#   A=ID  B=Hora início  C=Hora conclusão  D=Email  E=Nome  F=Empresa
#   G=Matrícula  H=Evento
# ---------------------------------------------------------------------------
COL_NOME = 4        # coluna E (índice 0-based)
COL_EMPRESA = 5     # coluna F
COL_MATRICULA = 6   # coluna G
COL_EVENTO = 7      # coluna H
COL_HORA = 2        # coluna C — hora de conclusão (momento do envio)

# ---------------------------------------------------------------------------
# Ganhadores
# Cada sessão encerrada gera um arquivo próprio na pasta "Ganhadores/" ao lado
# da planilha (sincronizada pelo OneDrive). A planilha do Forms nunca é
# reescrita, então vários computadores podem gravar ao mesmo tempo sem
# conflito de sincronização.
# ---------------------------------------------------------------------------
CABECALHO_GANHADORES = ["Evento", "Nome", "Matrícula", "Empresa", "Prêmio", "Assinatura"]

ABA_GANHADORES = "Ganhadores"
PASTA_GANHADORES = "Ganhadores"

# Tentativas de abrir um arquivo bloqueado (ex.: OneDrive sincronizando)
TENTATIVAS_LEITURA = 3
ESPERA_ENTRE_TENTATIVAS = 1.0  # segundos


# ---------------------------------------------------------------------------
# Caminho da planilha
# ---------------------------------------------------------------------------
def caminho_esperado() -> Path:
    """Caminho esperado da planilha (sem abrir seletor)."""
    if getattr(sys, "frozen", False):
        pasta = Path(sys.executable).parent
    else:
        pasta = Path(
            r"C:\Users\FY0E\PETROBRAS"
            r"\Anna Clara Gomes Silva Sousa - PrestServ - SIPAT 2026"
        )
    return pasta / NOME_ARQUIVO


def caminho_da_planilha() -> Path:
    """Retorna o Path do arquivo Excel.

    Tenta o caminho esperado; se não existir, abre seletor de arquivos.
    """
    caminho = caminho_esperado()
    if caminho.exists():
        return caminho

    from tkinter import filedialog
    arquivo = filedialog.askopenfilename(
        title="Escolher planilha",
        filetypes=[("Excel", "*.xlsx")],
    )
    if arquivo:
        return Path(arquivo)

    return caminho


def pasta_ganhadores(arquivo_excel) -> Path:
    """Pasta onde ficam os arquivos de ganhadores (ao lado da planilha)."""
    return Path(arquivo_excel).parent / PASTA_GANHADORES


# ---------------------------------------------------------------------------
# Abertura com nova tentativa
# ---------------------------------------------------------------------------
def _abrir_para_leitura(arquivo_excel):
    """Abre o Excel em modo leitura, tentando de novo se estiver bloqueado.

    O OneDrive bloqueia o arquivo por alguns instantes enquanto sincroniza;
    nesse caso o Windows devolve PermissionError (Errno 13).
    """
    for tentativa in range(TENTATIVAS_LEITURA):
        try:
            return load_workbook(arquivo_excel, read_only=True, data_only=True)
        except PermissionError:
            if tentativa < TENTATIVAS_LEITURA - 1:
                time.sleep(ESPERA_ENTRE_TENTATIVAS)

    raise PermissionError(
        f"Não foi possível abrir o arquivo:\n{Path(arquivo_excel).name}\n\n"
        "Verifique se:\n"
        "• o OneDrive terminou de sincronizar a pasta;\n"
        "• a pasta está marcada como \"Sempre manter neste dispositivo\";\n"
        "• você tem acesso à pasta compartilhada.\n\n"
        "Depois tente novamente."
    )


# ---------------------------------------------------------------------------
# Leitura de inscrições
# ---------------------------------------------------------------------------
def ler_inscricoes(arquivo_excel, evento=None, horario_limite=None):
    """Lê a primeira aba da planilha e devolve lista de tuplas.

    Cada tupla contém todos os valores da linha (uma célula por posição).
    Linhas totalmente vazias são ignoradas.

    Se *evento* e/ou *horario_limite* forem informados, filtra conforme
    RN-02 itens 1 e 2:
      - evento da inscrição == evento escolhido (comparação strip)
      - hora de conclusão <= horario_limite
    Com ambos None, devolve tudo (usado para listar eventos).
    """
    wb = _abrir_para_leitura(arquivo_excel)
    ws = wb.worksheets[0]  # sempre a primeira aba (nunca active)

    inscricoes = []
    primeira_linha = True
    for row in ws.iter_rows(min_row=1):
        # Pula o cabeçalho (primeira linha)
        if primeira_linha:
            primeira_linha = False
            continue

        valores = tuple(cell.value for cell in row)

        # Ignora linhas totalmente vazias
        if all(v is None for v in valores):
            continue

        # --- Filtro por evento (RN-02 item 1) ---
        if evento is not None:
            evento_celula = str(valores[COL_EVENTO]).strip() if valores[COL_EVENTO] is not None else ""
            if evento_celula != evento.strip():
                continue

        # --- Filtro por horário limite (RN-02 item 2) ---
        if horario_limite is not None:
            hora_celula = valores[COL_HORA]
            if hora_celula is None:
                continue
            if isinstance(hora_celula, datetime):
                hora_celula = hora_celula.time()
            elif isinstance(hora_celula, str):
                hora_celula = datetime.strptime(hora_celula, "%H:%M").time()
            if hora_celula > horario_limite:
                continue

        inscricoes.append(valores)

    wb.close()
    return inscricoes


# ---------------------------------------------------------------------------
# Leitura de ganhadores
# ---------------------------------------------------------------------------
def _linhas_da_aba(ws):
    """Linhas da aba a partir da linha 2, ignorando as totalmente vazias."""
    linhas = []
    primeira_linha = True
    for row in ws.iter_rows(min_row=1):
        if primeira_linha:
            primeira_linha = False
            continue

        valores = tuple(cell.value for cell in row)
        if all(v is None for v in valores):
            continue

        linhas.append(valores)
    return linhas


def ler_ganhadores(arquivo_excel):
    """Lê todos os ganhadores já gravados e devolve lista de tuplas.

    Junta:
      - a aba 'Ganhadores' da planilha principal, se existir (versões antigas
        do sistema gravavam lá);
      - a primeira aba de cada arquivo .xlsx da pasta 'Ganhadores/'.
    """
    ganhadores = []

    wb = _abrir_para_leitura(arquivo_excel)
    if ABA_GANHADORES in wb.sheetnames:
        ganhadores.extend(_linhas_da_aba(wb[ABA_GANHADORES]))
    wb.close()

    pasta = pasta_ganhadores(arquivo_excel)
    if pasta.is_dir():
        for arquivo in sorted(pasta.glob("*.xlsx")):
            # "~$..." são arquivos temporários do Excel (arquivo aberto)
            if arquivo.name.startswith("~$"):
                continue
            wb = _abrir_para_leitura(arquivo)
            ganhadores.extend(_linhas_da_aba(wb.worksheets[0]))
            wb.close()

    return ganhadores


# ---------------------------------------------------------------------------
# Gravação de ganhadores
# ---------------------------------------------------------------------------
def _nome_arquivo_sessao(evento) -> str:
    """Nome único do arquivo da sessão: evento + data/hora + computador."""
    evento_limpo = re.sub(r'[<>:"/\\|?*]', "-", str(evento)).strip(" .")
    agora = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    computador = socket.gethostname()
    return f"{evento_limpo} - {agora} - {computador}.xlsx"


def gravar_ganhadores(arquivo_excel, ganhadores):
    """Grava os ganhadores da sessão num arquivo novo em 'Ganhadores/'.

    - Cada ganhador é uma tupla (evento, nome, matricula, empresa, premio).
    - Adiciona coluna "Assinatura" vazia ao final de cada linha.
    - Nunca altera a planilha do Forms nem arquivos de outras sessões.

    Retorna o Path do arquivo criado.
    Levanta PermissionError com mensagem amigável se não conseguir gravar.
    """
    pasta = pasta_ganhadores(arquivo_excel)
    destino = pasta / _nome_arquivo_sessao(ganhadores[0][0])

    wb = Workbook()
    ws = wb.active
    ws.title = ABA_GANHADORES
    ws.append(CABECALHO_GANHADORES)
    for ganhador in ganhadores:
        ws.append(list(ganhador) + [""])

    try:
        pasta.mkdir(exist_ok=True)
        wb.save(destino)
    except PermissionError:
        raise PermissionError(
            "Não foi possível salvar os ganhadores na pasta:\n"
            f"{pasta}\n\n"
            "Verifique se você tem permissão de edição na pasta "
            "compartilhada e tente novamente."
        )
    finally:
        wb.close()

    return destino
