# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Sistema de Sorteio SIPAT 2026 — aplicação desktop local em Python para sortear prêmios entre inscritos de palestras, atividades e oficinas da SIPAT (Petrobras). Lê inscrições de uma planilha Excel gerada pelo Microsoft Forms e grava ganhadores na mesma planilha.

A especificação completa está em `SPEC.md` (fonte de verdade do projeto).

## Language

O dono do projeto se comunica em português (Brasil). Strings de UI e mensagens de erro devem ser em pt-BR.

## Architecture

Flat layout com separação de responsabilidades:

- `sorteio/planilha.py` — leitura e gravação do Excel (openpyxl). Não decide regras de negócio.
- `sorteio/sorteador.py` — regras: listar eventos, filtrar elegíveis, sortear. Não abre arquivos.
- `sorteio/telas.py` — interface (CustomTkinter). Não tem regra de negócio. **Ainda não implementada** (aguardando design Figma).
- `sorteio/__main__.py` — ponto de entrada (`python -m sorteio`).

Dependência num sentido só: `telas` → `sorteador` / `planilha`. Nunca o contrário.

Constantes de índice das colunas do Excel ficam definidas em `planilha.py` (COL_NOME, COL_EMPRESA, etc). Nunca usar índices soltos espalhados pelo código.

## Commands

```powershell
# Criar/ativar ambiente virtual
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt

# Executar
python -m sorteio

# Build .exe
python -m pip install pyinstaller
pyinstaller --onefile --windowed --name SorteioSIPAT sorteio/__main__.py
```

## Key rules

- Aleatoriedade com `secrets.SystemRandom().sample()`, nunca `random`.
- Planilhas reais nunca vão para o git (LGPD). Testes sempre em `data/exemplo/teste.xlsx`.
- A planilha é lida no momento do play (não ao abrir o programa) — RN-07.
- Ganhadores são tuplas: `(evento, nome, matricula, empresa, premio)` — RN-08.
- Normalização de matrícula: `str(valor).strip().upper()` — RN-04.
- Pendência: índices de coluna são provisórios; confirmar contra a planilha real do Forms (seção 3.1 da SPEC).
