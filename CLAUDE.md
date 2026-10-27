# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Sistema de Sorteio SIPAT 2026 — aplicação desktop local em Python para sortear prêmios entre inscritos de palestras, atividades e oficinas da SIPAT (Petrobras). Lê inscrições de uma planilha Excel gerada pelo Microsoft Forms e grava os ganhadores de cada sessão num arquivo próprio na pasta `Ganhadores/` ao lado da planilha.

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

# Testes automatizados (unittest, sem dependência extra)
python -m unittest discover -s tests -t . -v
python -m unittest tests.test_auditoria      # só a auditoria de ponta a ponta

# Testes manuais — usar cópia de teste, nunca a planilha real
# Arquivo de teste: data/exemplo/teste.xlsx
# Lista de critérios de aceite: seção 11 do SPEC.md
```

Testes em `tests/` (dados fictícios gerados em pasta temporária por `tests/apoio.py`, no formato do Forms):
- `test_planilha.py` — leitura pelo cabeçalho, erros de arquivo, gravar/ler ganhadores.
- `test_sorteador.py` — filtros, normalização, quem já ganhou, sorteio sem repetição.
- `test_auditoria.py` — várias sessões gravando/relendo em disco até esgotar os elegíveis; verifica que ninguém repete no mesmo evento e que pode ganhar em outro.
- `test_telas.py` — tela de exibição (cada ganhador aparece uma vez) e fluxo Play/Encerrar; pulado sem tela (Tk).

Rodar a suíte antes de gerar um `.exe` novo.

## Architecture

Flat layout com separação de responsabilidades estrita:

- `sorteio/planilha.py` — leitura e gravação do Excel (openpyxl). Não decide regras de negócio.
- `sorteio/sorteador.py` — regras: listar eventos, filtrar elegíveis, sortear. Não abre arquivos.
- `sorteio/telas.py` — interface (CustomTkinter). Implementada como classe `App(ctk.CTk)`. Não tem regra de negócio.
- `sorteio/__main__.py` — ponto de entrada (`python -m sorteio`).

Dependência num sentido só: `telas` → `sorteador` / `planilha`. Nunca o contrário.
Dados passam entre módulos **por parâmetros e retornos**, nunca por importação de variáveis de estado.

### Dois tipos de tupla — não confundir

`ler_inscricoes` devolve tuplas de **5 campos** `(hora, nome, empresa, matricula, evento)` nas posições das constantes `COL_*` de `planilha.py` (importadas por `sorteador.py`). A posição de cada coluna **na planilha** é descoberta pelo cabeçalho (`_mapear_colunas`, palavras-chave em `CABECALHOS_ESPERADOS`) — o Forms adiciona colunas automáticas ("Nome", "Hora da última modificação") que deslocam as perguntas. `hora` já vem como `datetime` (ou `None`).

`sortear` e `gravar_ganhadores` trabalham com tuplas de **5 elementos fixos** (RN-08):
```python
(evento, nome, matricula, empresa, premio)
```
Essa estrutura é o único formato aceito por `gravar_ganhadores` e é o que `App.ganhadores_sessao` acumula.

### Fluxo de leitura

`ler_inscricoes(arquivo)` só lê; as regras ficam em `sorteador.py`:

```python
inscricoes = ler_inscricoes(arquivo)
listar_eventos(inscricoes)                                        # _carregar_eventos (início e botão Recarregar)
planilha_pode_estar_desatualizada(inscricoes, horario_limite)     # aviso antes de sortear (OneDrive atrasado)
filtrar_inscricoes(inscricoes, evento, horario_limite)            # RN-02 itens 1 e 2
```

Eventos são comparados com `normalizar_texto` (sem acento, minúsculas, espaços simples); células de múltipla seleção do Forms (`"A;B;"`) são separadas por `eventos_da_celula`. A lista suspensa mostra os eventos **da planilha**; `EVENTOS_SIPAT` em `telas.py` só dá o label curto quando o texto bate.

### Estado da sessão (App em telas.py)

```python
self.ganhadores_sessao: list  # tuplas RN-08 acumuladas; esvaziado após gravar
self.evento_travado: bool     # True durante a sessão; trava CTkOptionMenu e btn_recarregar
```

`Encerrar` chama `gravar_ganhadores`, esvazia a lista e desfaz a trava. Fechar a janela com ganhadores não salvos pergunta antes de sair.

### Gravação de ganhadores (vários computadores ao mesmo tempo)

A planilha do Forms **nunca é reescrita** — o sistema só a lê. Isso evita conflito de sincronização do OneDrive quando vários computadores sorteiam ao mesmo tempo.

- `gravar_ganhadores` cria um arquivo **novo** a cada sessão em `Ganhadores/` (ao lado da planilha, sincronizado para o SharePoint): `<evento> - <AAAA-MM-DD_HHMMSS> - <computador>.xlsx`. Nunca altera arquivos existentes. Retorna o `Path` criado. Se não conseguir gravar, lança `PermissionError` com mensagem amigável — os ganhadores ficam na sessão para nova tentativa.
- `ler_ganhadores` junta a aba "Ganhadores" da planilha principal (legado, se existir) + a primeira aba de cada `.xlsx` em `Ganhadores/` (ignora `~$*`).
- Leituras copiam o arquivo inteiro para a memória (`read_bytes` + `BytesIO`) e tentam de novo (6x, 1 s) em caso de `OSError` ou ZIP pela metade (OneDrive sincronizando) antes de mostrar mensagem amigável com o detalhe técnico. Arquivo criptografado (assinatura OLE) tem mensagem própria.
- Limitação: dois computadores sorteando o **mesmo evento** ao mesmo tempo só enxergam os ganhadores um do outro depois que o OneDrive sincroniza — RN-03 entre máquinas depende desse atraso.

## Key rules

- Aleatoriedade com `secrets.SystemRandom().sample()`, nunca `random`.
- Planilhas reais nunca vão para o git (LGPD). Testes sempre em `data/exemplo/teste.xlsx`.
- A planilha é lida no momento do play (não ao abrir o programa) — RN-07.
- Normalização de matrícula: `normalizar_matricula` em `sorteador.py` — só letras/dígitos, maiúsculas, sem zeros à esquerda se for numérica (`"0012345"`, `12345`, `12345.0`, `"12.345"` são iguais) — RN-04.
- Mesma pessoa = mesma matrícula **ou** mesmo nome normalizado (nome "anonymous"/vazio não conta). Vale para RN-03 (`filtrar_ja_ganhadores`) e para inscrições repetidas, que contam uma vez só no sorteio (`remover_inscricoes_repetidas`, chamada dentro de `sortear`).
- `PainelRolagem` (tela de exibição) só cria a segunda cópia do conteúdo — usada no loop da rolagem — quando ele não cabe na tela; senão o ganhador apareceria duplicado.
- Constantes de índice dos campos (`COL_NOME`, `COL_EMPRESA`, `COL_MATRICULA`, `COL_EVENTO`, `COL_HORA`) ficam em `planilha.py`. Nunca usar índices soltos espalhados pelo código.
- Se a planilha real tiver um cabeçalho que as palavras-chave não reconhecem, ajustar `CABECALHOS_ESPERADOS` em `planilha.py` (a mensagem de erro lista os cabeçalhos encontrados) — seção 3.1 do SPEC.
