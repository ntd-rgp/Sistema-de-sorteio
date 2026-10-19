# Sistema de Sorteio SIPAT 2026

Aplicação desktop em Python para sortear prêmios entre inscritos de palestras, atividades e oficinas da SIPAT (Petrobras). O sistema lê inscrições de uma planilha Excel gerada pelo Microsoft Forms, filtra os participantes elegíveis, sorteia os ganhadores e grava o resultado em uma aba `Ganhadores` na mesma planilha.

## Visão geral

- Leitura da planilha Excel com `openpyxl`
- Interface desktop com `CustomTkinter`
- Seleção de evento, quantidade, horário limite e prêmio
- Validação de elegibilidade conforme regras de negócio do projeto
- Backup automático antes de salvar os resultados
- Suporte a execução local em Windows e empacotamento em `.exe`

## Requisitos

- Python 3.13+
- Windows 10/11 (aplicação desktop local)
- Microsoft Excel instalado para abrir a planilha em uso

## Instalação

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Execução

```powershell
python -m sorteio
```

## Estrutura do projeto

```text
Sistema_de_sorteio/
├── sorteio/
│   ├── __init__.py
│   ├── __main__.py
│   ├── planilha.py
│   ├── sorteador.py
│   └── telas.py
├── data/
│   └── exemplo/
│       └── teste.xlsx
├── README.md
├── SPEC.md
├── requirements.txt
└── .gitignore
```

## Observações importantes

- A especificação completa do projeto está em [SPEC.md](SPEC.md).
- A planilha real não deve ser enviada para o repositório; use a cópia de teste em `data/exemplo/teste.xlsx` para validações manuais.
- O projeto usa regras de negócio específicas do SIPAT, especialmente quanto ao filtro por evento, horário limite e prevenção de repetição na mesma matrícula.
- O arquivo Excel real é localizado por caminho de desenvolvimento ou pela pasta do executável, conforme a lógica em `sorteio/planilha.py`.

## Build do executável

```powershell
python -m pip install pyinstaller
pyinstaller --onefile --windowed --name SorteioSIPAT sorteio/__main__.py
```

O executável gerado fica na pasta `dist/`.

## Validação manual

Para testes manuais, utilize sempre a cópia de teste e siga a checklist da seção 11 de [SPEC.md](SPEC.md). Não use a planilha real em ambiente de desenvolvimento ou teste.
