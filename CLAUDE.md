# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Sistema de Sorteio SIPAT 2026 — aplicação desktop local em Python para sortear prêmios entre inscritos de palestras, atividades e oficinas da SIPAT (Petrobras). Lê inscrições de uma planilha Excel gerada pelo Microsoft Forms e grava ganhadores na mesma planilha.

A especificação completa está em `SPEC.md` (fonte de verdade do projeto).

## Language

O dono do projeto se comunica em português (Brasil). Strings de UI e mensagens de erro devem ser em pt-BR.

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

# Testes manuais — usar cópia de teste, nunca a planilha real
# Arquivo de teste: data/exemplo/teste.xlsx
# Lista de critérios de aceite: seção 11 do SPEC.md
```

Não há suite de testes automatizados (pytest está listado como opcional no SPEC). Testes são feitos manualmente conforme a checklist da seção 11 do SPEC.

## Architecture

Flat layout com separação de responsabilidades estrita:

- `sorteio/planilha.py` — leitura e gravação do Excel (openpyxl). Não decide regras de negócio.
- `sorteio/sorteador.py` — regras: listar eventos, filtrar elegíveis, sortear. Não abre arquivos.
- `sorteio/telas.py` — interface (CustomTkinter). Implementada como classe `App(ctk.CTk)`. Não tem regra de negócio.
- `sorteio/__main__.py` — ponto de entrada (`python -m sorteio`).

Dependência num sentido só: `telas` → `sorteador` / `planilha`. Nunca o contrário.
Dados passam entre módulos **por parâmetros e retornos**, nunca por importação de variáveis de estado.

### Dois tipos de tupla — não confundir

`ler_inscricoes` devolve tuplas com **todos os campos da linha da planilha** (tamanho varia conforme a planilha do Forms). Os índices de cada campo são as constantes `COL_*` definidas em `planilha.py` e importadas por `sorteador.py`.

`sortear` e `gravar_ganhadores` trabalham com tuplas de **5 elementos fixos** (RN-08):
```python
(evento, nome, matricula, empresa, premio)
```
Essa estrutura é o único formato aceito por `gravar_ganhadores` e é o que `App.ganhadores_sessao` acumula.

### Dual-use de `ler_inscricoes`

```python
# Sem filtros → devolve tudo; usado por _carregar_eventos para popular o CTkOptionMenu
ler_inscricoes(arquivo)

# Com filtros → aplica RN-02 itens 1 e 2; usado por _ao_clicar_play no momento do play
ler_inscricoes(arquivo, evento=evento, horario_limite=horario_limite)
```

### Estado da sessão (App em telas.py)

```python
self.ganhadores_sessao: list  # tuplas RN-08 acumuladas; esvaziado após gravar
self.evento_travado: bool     # True durante a sessão; trava CTkOptionMenu e btn_recarregar
```

`Encerrar` chama `gravar_ganhadores`, esvazia a lista e desfaz a trava. Fechar a janela com ganhadores não salvos pergunta antes de sair.

### Backup automático

`gravar_ganhadores` **sempre** faz backup antes de salvar, copiando o arquivo para `backup/` (ao lado da planilha) com data/hora no nome. Se o arquivo estiver aberto no Excel, lança `PermissionError` com mensagem amigável — os ganhadores ficam na sessão para nova tentativa.

## Key rules

- Aleatoriedade com `secrets.SystemRandom().sample()`, nunca `random`.
- Planilhas reais nunca vão para o git (LGPD). Testes sempre em `data/exemplo/teste.xlsx`.
- A planilha é lida no momento do play (não ao abrir o programa) — RN-07.
- Normalização de matrícula: `str(valor).strip().upper()` — RN-04.
- Constantes de índice das colunas (`COL_NOME`, `COL_EMPRESA`, `COL_MATRICULA`, `COL_EVENTO`, `COL_HORA`) ficam em `planilha.py`. Nunca usar índices soltos espalhados pelo código.
- **Pendência crítica:** os índices de coluna são provisórios (baseados na estrutura típica do Forms). Devem ser confirmados contra a planilha real antes de usar em produção — seção 3.1 do SPEC.
