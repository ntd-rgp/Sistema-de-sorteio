"""Leitura e gravação da planilha Excel (inscrições e ganhadores)."""

import shutil
import sys
from datetime import datetime
from pathlib import Path

from openpyxl import load_workbook

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
# Cabeçalho da aba "Ganhadores"
# ---------------------------------------------------------------------------
CABECALHO_GANHADORES = ["Evento", "Nome", "Matrícula", "Empresa", "Prêmio", "Assinatura"]

ABA_GANHADORES = "Ganhadores"


# ---------------------------------------------------------------------------
# Caminho da planilha
# ---------------------------------------------------------------------------
def caminho_da_planilha() -> Path:
    """Retorna o Path do arquivo Excel.

    Se rodando como .exe (frozen), procura na pasta do executável.
    Senão, usa o caminho de desenvolvimento.
    Plano B: se o arquivo não existir, abre seletor de arquivos.
    """
    if getattr(sys, "frozen", False):
        pasta = Path(sys.executable).parent
    else:
        pasta = Path(
            r"C:\Users\FY0E\PETROBRAS"
            r"\Anna Clara Gomes Silva Sousa - PrestServ - SIPAT 2026"
        )

    caminho = pasta / NOME_ARQUIVO
    if caminho.exists():
        return caminho

    # Plano B: seletor de arquivos
    from tkinter import filedialog
    arquivo = filedialog.askopenfilename(
        title="Escolher planilha",
        filetypes=[("Excel", "*.xlsx")],
    )
    if arquivo:
        return Path(arquivo)

    return caminho


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
    wb = load_workbook(arquivo_excel, read_only=True, data_only=True)
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
def ler_ganhadores(arquivo_excel):
    """Lê a aba 'Ganhadores' e devolve lista de tuplas.

    Se a aba não existir, devolve lista vazia.
    """
    wb = load_workbook(arquivo_excel, read_only=True, data_only=True)

    if ABA_GANHADORES not in wb.sheetnames:
        wb.close()
        return []

    ws = wb[ABA_GANHADORES]
    ganhadores = []
    primeira_linha = True
    for row in ws.iter_rows(min_row=1):
        if primeira_linha:
            primeira_linha = False
            continue

        valores = tuple(cell.value for cell in row)
        if all(v is None for v in valores):
            continue

        ganhadores.append(valores)

    wb.close()
    return ganhadores


# ---------------------------------------------------------------------------
# Gravação de ganhadores
# ---------------------------------------------------------------------------
def _fazer_backup(arquivo_excel):
    """Copia o arquivo para a pasta backup/ com data/hora no nome."""
    caminho = Path(arquivo_excel)
    pasta_backup = caminho.parent / "backup"
    pasta_backup.mkdir(exist_ok=True)

    agora = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_backup = f"{caminho.stem}_{agora}{caminho.suffix}"
    shutil.copy2(caminho, pasta_backup / nome_backup)


def gravar_ganhadores(arquivo_excel, ganhadores):
    """Grava a lista de ganhadores na aba 'Ganhadores'.

    - Cria a aba com cabeçalho se não existir.
    - Cada ganhador é uma tupla (evento, nome, matricula, empresa, premio).
    - Adiciona coluna "Assinatura" vazia ao final de cada linha.
    - Faz backup antes de salvar.
    - Trata PermissionError (planilha aberta no Excel).

    Retorna None em caso de sucesso.
    Levanta PermissionError com mensagem amigável se o arquivo estiver aberto.
    """
    _fazer_backup(arquivo_excel)

    wb = load_workbook(arquivo_excel)

    if ABA_GANHADORES not in wb.sheetnames:
        ws = wb.create_sheet(ABA_GANHADORES)
        ws.append(CABECALHO_GANHADORES)
    else:
        ws = wb[ABA_GANHADORES]

    for ganhador in ganhadores:
        ws.append(list(ganhador) + [""])

    try:
        wb.save(arquivo_excel)
    except PermissionError:
        wb.close()
        raise PermissionError(
            "Não foi possível salvar a planilha. "
            "Feche a planilha no Excel e tente novamente."
        )

    wb.close()
