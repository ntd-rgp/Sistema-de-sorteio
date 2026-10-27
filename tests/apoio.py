"""Apoio aos testes: planilhas no formato do Microsoft Forms (dados fictícios)."""

from datetime import datetime

from openpyxl import Workbook

from sorteio.planilha import COL_EMPRESA, COL_EVENTO, COL_HORA, COL_MATRICULA, COL_NOME

# Cabeçalho como o Forms exporta hoje: colunas automáticas ("Nome" da conta e
# "Hora da última modificação") antes das perguntas do formulário.
CABECALHO_FORMS = [
    "ID", "Hora de início", "Hora de conclusão", "Email", "Nome",
    "Hora da última modificação", "Nome completo", "Empresa",
    "Matrícula / Chave", "Qual palestra/atividade você está participando?",
]


HORA_PADRAO = datetime(2026, 11, 10, 8, 0)


def inscricao(nome, matricula, evento, hora=HORA_PADRAO, empresa="Petrobras"):
    """Tupla no formato devolvido por ler_inscricoes."""
    linha = [None] * 5
    linha[COL_HORA] = hora
    linha[COL_NOME] = nome
    linha[COL_EMPRESA] = empresa
    linha[COL_MATRICULA] = matricula
    linha[COL_EVENTO] = evento
    return tuple(linha)


def criar_planilha_forms(caminho, respostas):
    """Grava uma planilha do Forms. *respostas*: lista de
    (hora, nome, empresa, matricula, evento)."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Form1"
    ws.append(CABECALHO_FORMS)
    for i, (hora, nome, empresa, matricula, evento) in enumerate(respostas, 1):
        ws.append([i, hora, hora, f"p{i}@teste.com", "anonymous", None,
                   nome, empresa, matricula, evento])
    wb.save(caminho)
    return caminho
