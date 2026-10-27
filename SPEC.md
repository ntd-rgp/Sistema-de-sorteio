# Sorteio SIPAT 2026 — Especificação (SDD)

> Documento de especificação para desenvolvimento orientado a especificação (Spec-Driven Development).
> Fonte de verdade do projeto: toda implementação deve seguir este documento. Divergências devem ser discutidas e registradas aqui antes de virar código.

---

## 1. Visão geral

### 1.1 Objetivo
Sistema **desktop local em Python** para sortear prêmios entre os inscritos das palestras, atividades e oficinas da **SIPAT 2026** (Petrobras). O sistema lê os inscritos de uma planilha Excel alimentada pelo Microsoft Forms, sorteia os ganhadores entre os elegíveis e grava o resultado de cada sessão num arquivo próprio na pasta `Ganhadores/` ao lado da planilha, que é impresso e usado como lista de assinatura de recebimento.

### 1.2 Contexto
- O participante se inscreve por um **Microsoft Forms**.
- O Forms grava as respostas num **Excel no SharePoint/OneDrive**.
- A pasta desse Excel é sincronizada via **OneDrive** nos computadores que vão rodar o sorteio.
- O **executável** do sistema fica dentro dessa mesma pasta sincronizada, ao lado do Excel.
- Mais de um computador pode rodar o sistema.

### 1.3 Prazo
15 dias a partir de 14/10/2026 (entrega até **29/10/2026**). Escopo deve priorizar o **básico funcional** (seção 12).

### 1.4 Contexto de aprendizado
O autor está usando este projeto para aprender Python. O agente deve:
- implementar em **passos pequenos**, um arquivo/função por vez;
- explicar cada alteração **em português simples**, linha a linha quando for código novo;
- preferir código **simples e legível** a código "esperto";
- **não** introduzir camadas, classes ou bibliotecas além das previstas aqui sem perguntar.

---

## 2. Links e caminhos

| Item | Valor |
|---|---|
| Planilha (SharePoint) | https://petrobrasbr-my.sharepoint.com/:x:/g/personal/anna_clara_prestserv_petrobras_com_br/IQCw5HRJYPNoR4DkZXr10JYFATp-tIMM-uJGLuAzpI1aMAA |
| Nome do arquivo | `Presença Palestras, Atividades e Oficinas SIPAT 2026.xlsx` |
| Pasta sincronizada (máquina do desenvolvedor) | `C:\Users\FY0E\PETROBRAS\Anna Clara Gomes Silva Sousa - PrestServ - SIPAT 2026\` |
| Caminho completo (desenvolvimento) | `C:\Users\FY0E\PETROBRAS\Anna Clara Gomes Silva Sousa - PrestServ - SIPAT 2026\Presença Palestras, Atividades e Oficinas SIPAT 2026.xlsx` |

O caminho com `FY0E` **só é usado em modo desenvolvimento**. No executável, o caminho é descoberto a partir da pasta do `.exe` (seção 7.2).

### Referências técnicas
- openpyxl: https://openpyxl.readthedocs.io/
- CustomTkinter: https://customtkinter.tomschimansky.com/
- PyInstaller: https://pyinstaller.org/
- Python `secrets`: https://docs.python.org/3/library/secrets.html
- Template `.gitignore` Python: https://github.com/github/gitignore/blob/main/Python.gitignore
- PyPI: https://pypi.org

---

## 3. Fonte de dados

### 3.1 Planilha de inscrições (primeira aba)
Gerada pelo Microsoft Forms. Uma linha = **uma inscrição** (uma pessoa em um evento, num horário).

Colunas de negócio:

| Dado | Uso |
|---|---|
| Nome | exibição e gravação do ganhador |
| Empresa | gravação do ganhador (há terceirizados) |
| Matrícula | identificador único da pessoa; detecção de quem já ganhou |
| Evento | filtro do sorteio |
| Hora | filtro pelo horário limite |

A **posição** de cada coluna é descoberta pelo **cabeçalho** da linha 1 (sem acento, minúsculas), porque o Forms adiciona colunas automáticas ("ID", "Hora de início", "Hora de conclusão", "Email", "Nome", "Hora da última modificação") e a ordem pode variar:

| Dado | Cabeçalho deve conter |
|---|---|
| Hora | "hora de conclusão" (momento do envio) |
| Matrícula | "matrícula" ou "chave" |
| Empresa | "empresa" (opcional) |
| Evento | "evento", "palestra", "atividade" ou "oficina" |
| Nome | "nome" — vale a **última** coluna, para pular o "Nome" automático do Forms |

Se faltar uma coluna obrigatória, o sistema mostra os cabeçalhos encontrados. Em perguntas de múltipla seleção, o Forms grava as opções separadas por `;` — cada uma conta como um evento.

### 3.2 Arquivos de ganhadores (pasta `Ganhadores/`)
A planilha do Forms **não é alterada** pelo sistema (só lida). Cada "Encerrar sorteio" cria um arquivo **novo** na pasta `Ganhadores/`, ao lado da planilha — dentro da pasta sincronizada, portanto enviado ao mesmo SharePoint. Nome do arquivo: `<evento> - <AAAA-MM-DD_HHMMSS> - <computador>.xlsx` (caracteres inválidos no evento viram `-`). Como cada sessão tem seu próprio arquivo, vários computadores podem gravar ao mesmo tempo sem conflito.

Aba "Ganhadores" de cada arquivo. Colunas, nesta ordem:

| A | B | C | D | E | F |
|---|---|---|---|---|---|
| Evento | Nome | Matrícula | Empresa | Prêmio | Assinatura |

- Cada arquivo tem um único cabeçalho na linha 1.
- "Assinatura" é gravada **vazia**, para preenchimento à mão após impressão.
- A aba não contém semente nem data/hora do sorteio (decisão: aba limpa para impressão).

---

## 4. Regras de negócio

### RN-01 — Entradas do organizador
Antes de sortear, o organizador informa:
1. **Evento** (lista suspensa com os eventos existentes na planilha)
2. **Quantidade** de sorteados na rodada (inteiro ≥ 1)
3. **Horário limite** de inscrição (formato `dd/mm/aaaa HH:MM`)
4. **Prêmio** (texto)

### RN-02 — Elegibilidade
Uma inscrição é **elegível** se, e somente se:
1. o **evento** da inscrição é igual ao evento escolhido; **e**
2. a **hora** da inscrição é **menor ou igual** ao horário limite; **e**
3. a **matrícula** não consta como ganhadora **no mesmo evento**, considerando:
   - os arquivos da pasta `Ganhadores/` (e a aba "Ganhadores" da planilha principal, se existir, de versões antigas); **e**
   - a lista de ganhadores da **sessão atual** ainda não salva (RN-06).

Inscritos depois do horário limite **não são elegíveis**.

### RN-03 — Ganhar mais de uma vez
- **Proibido** ganhar duas vezes **no mesmo evento**.
- **Permitido** ganhar em **eventos diferentes**.

### RN-04 — Normalização
Para comparações, a matrícula é normalizada: sem espaços nas pontas e em maiúsculas (`str(valor).strip().upper()`). O nome do evento também deve ser comparado sem espaços nas pontas.

### RN-05 — Sorteio
- Sorteio **sem repetição** entre os elegíveis, usando `secrets.SystemRandom().sample(...)` (aleatoriedade criptográfica do sistema operacional, imprevisível).
- Se a quantidade pedida for **maior** que o número de elegíveis, o sistema **não sorteia** e exibe mensagem clara (ex.: "Há apenas 4 inscritos elegíveis; reduza a quantidade.").
- Se não houver elegíveis, exibe mensagem e não sorteia.
- Linhas totalmente vazias da planilha são ignoradas.

### RN-06 — Sessão de sorteio e salvamento
1. Ao iniciar a sessão de um evento, o **evento fica travado** (não pode ser trocado).
2. O organizador pode fazer **várias rodadas** no mesmo evento (cada rodada com sua quantidade e prêmio).
3. Os ganhadores de cada rodada são **acumulados** numa lista em memória (`ganhadores.extend(ganhadores_da_rodada)`).
4. Botão **"Encerrar sorteio"**:
   - grava todos os ganhadores da sessão num arquivo novo em `Ganhadores/` (seção 3.2);
   - esvazia a lista da sessão;
   - **destrava** a escolha de evento.
5. Se o usuário tentar **fechar a janela** com ganhadores não salvos, o sistema pergunta se deseja salvar antes de sair.

> Alternativa registrada (não adotada): gravar a cada rodada e usar "Encerrar" só para destravar. Mais segura contra perda de dados; pode ser adotada se surgirem problemas.

### RN-07 — Momento da leitura
A planilha é lida **no momento do play** (não ao abrir o programa), para considerar inscrições e ganhadores gravados por outros computadores.

### RN-08 — Estrutura de um ganhador
Cada ganhador é **uma tupla** com 5 valores, na mesma ordem das colunas da aba:

```python
(evento, nome, matricula, empresa, premio)
```

A lista `ganhadores` é uma lista dessas tuplas. Um ganhador = um item da lista.

---

## 5. Arquitetura

### 5.1 Princípios
- **Separação de responsabilidades:** cada arquivo cuida de uma coisa.
- **`planilha.py` não decide nada:** só abre, lê e grava o Excel.
- **`sorteador.py` não abre arquivos:** só aplica regras a dados já lidos.
- **`telas.py` não tem regra de negócio:** só coleta entradas, chama as funções e exibe resultados.
- Dependência num sentido só: `telas` → `sorteador` / `planilha`. Nunca o contrário (evita importação circular).
- Dados passam entre arquivos por **parâmetros e retornos**, nunca por import de variáveis.

### 5.2 Estrutura de pastas (flat layout)

```
sorteio-sipat/
├── .venv/                 # ambiente virtual (fora do git)
├── sorteio/               # pacote do programa
│   ├── __init__.py        # vazio; marca a pasta como pacote
│   ├── __main__.py        # porta de entrada: python -m sorteio
│   ├── planilha.py        # leitura e gravação do Excel
│   ├── sorteador.py       # regras: eventos, elegíveis, sorteio
│   └── telas.py           # interface (CustomTkinter)
├── data/
│   └── exemplo/           # cópias de teste (dados fictícios)
├── .gitignore
├── README.md
├── SPEC.md                # este documento
└── requirements.txt
```

### 5.3 Fluxo do play

```
telas.py      → organizador escolhe evento/horário/quantidade/prêmio e aperta Play
                        ↓
planilha.py   → lê inscrições (já filtradas por evento e horário)
              → lê ganhadores da pasta "Ganhadores/"
                        ↓
sorteador.py  → remove quem já ganhou (aba + sessão)
              → sorteia a quantidade pedida
                        ↓
telas.py      → mostra os ganhadores; acumula na lista da sessão
                        ↓
[Encerrar]    → planilha.py grava a sessão num arquivo novo em "Ganhadores/"
```

### 5.4 Contratos das funções

#### `planilha.py`

| Função | Entrada | Saída | Regras |
|---|---|---|---|
| `caminho_da_planilha()` | — | `Path` do Excel | Se `sys.frozen`: pasta do `.exe` + `NOME_ARQUIVO`. Senão: caminho de desenvolvimento. |
| `ler_inscricoes(arquivo_excel)` | caminho | lista de tuplas `(hora, nome, empresa, matricula, evento)` | Lê a primeira aba; localiza as colunas pelo cabeçalho (3.1); ignora linhas vazias; hora vira `datetime`. Lê o arquivo inteiro para a memória antes de abrir (não segura o arquivo do OneDrive). |
| `ler_ganhadores(arquivo_excel)` | caminho | lista de tuplas | Junta a aba "Ganhadores" da planilha (se existir) e a primeira aba de cada `.xlsx` em `Ganhadores/` (ignora `~$*`). Lê a partir da linha 2, ignorando vazias. |
| `gravar_ganhadores(arquivo_excel, ganhadores)` | caminho, lista de tuplas (RN-08) | `Path` do arquivo criado | Cria arquivo novo em `Ganhadores/` com cabeçalho; para cada ganhador, `append(list(ganhador) + [""])`; **um único `save` no final**. Nunca altera a planilha nem arquivos existentes. Trata `PermissionError`. |

Convenção: o **caminho do arquivo é sempre o primeiro parâmetro**.

#### `sorteador.py`

| Função | Entrada | Saída | Regras |
|---|---|---|---|
| `listar_eventos(inscricoes)` | lista de inscrições | lista ordenada de eventos distintos | Para popular a lista suspensa. |
| `filtrar_inscricoes(inscricoes, evento, horario_limite)` | lista + evento + hora | lista filtrada | RN-02 itens 1 e 2, com RN-04. |
| `planilha_pode_estar_desatualizada(inscricoes, horario_limite)` | lista + hora | bool | Resposta mais recente anterior ao horário limite (ou a agora) por mais de 2 min → aviso antes de sortear. |
| `filtrar_ja_ganhadores(inscricoes, ganhadores_planilha, ganhadores_sessao, evento)` | listas + evento | lista de elegíveis | RN-02 item 3, com RN-04. |
| `sortear(elegiveis, quantidade, evento, premio)` | elegíveis, int, str, str | lista de tuplas (RN-08) | RN-05. Lança erro claro se `quantidade` > elegíveis. |

#### `telas.py`
| Função | Responsabilidade |
|---|---|
| `iniciar()` | Cria a janela, os componentes e liga os gatilhos (`command=`) aos callbacks. |
| `ao_clicar_play()` | Lê os campos (`.get()`), converte o horário com `datetime.strptime(texto, "%d/%m/%Y %H:%M")`, chama leitura → filtro → sorteio, exibe e acumula. |
| `ao_clicar_encerrar()` | Chama `gravar_ganhadores`, limpa a lista da sessão, destrava o evento. |
| `ao_fechar_janela()` | Se houver ganhadores não salvos, pergunta antes de sair. |

#### `__main__.py`
```python
from sorteio.telas import iniciar

iniciar()
```

### 5.5 Acesso às colunas
As linhas são tuplas (sem nome de coluna). Os **índices** de cada campo ficam definidos **num único lugar** em `planilha.py` (constantes `COL_HORA`, `COL_NOME`, `COL_EMPRESA`, `COL_MATRICULA`, `COL_EVENTO`). São posições na tupla montada por `ler_inscricoes`, não na planilha — a posição na planilha vem do cabeçalho (3.1). Nunca usar índices "soltos" (`linha[2]`) espalhados pelo código.

---

## 6. Interface e design system

### 6.1 Estrutura
**Uma única tela** (`telas.py`) com dois modos:

- **Modo configuração:** seleção de evento, horário limite, quantidade, prêmio; botões **Play** e **Encerrar sorteio**; contador da sessão.
- **Modo amostragem:** exibição dos ganhadores em destaque para o telão. Os controles ficam ocultos ou discretos, para não poluir a projeção.

### 6.2 Componentes (CustomTkinter)

| Elemento | Componente |
|---|---|
| Evento | `CTkOptionMenu` (lista suspensa, populada por `listar_eventos`) |
| Horário limite | `CTkEntry` com dica do formato `dd/mm/aaaa HH:MM` |
| Quantidade | `CTkEntry` numérico |
| Prêmio | `CTkEntry` |
| Play / Encerrar | `CTkButton` |
| Ganhadores | `CTkLabel` / `CTkTextbox` com fonte grande |
| Mensagens | `CTkMessagebox` ou `tkinter.messagebox` |

### 6.3 Diretrizes visuais
- **Legibilidade no telão:** nomes dos ganhadores com fonte grande (≥ 36 pt), alto contraste.
- Paleta e logo: seguir a identidade visual da SIPAT 2026 (**a definir**; colocar assets na pasta do pacote para entrarem no `.exe`).
- Estados visuais claros: evento travado (desabilitado) durante a sessão; botão Encerrar habilitado só com ganhadores na sessão.
- Mensagens de erro em português, dizendo **o que fazer** (ex.: "Feche a planilha no Excel e tente novamente.").

---

## 7. Ambiente, execução e distribuição

### 7.1 Ambiente de desenvolvimento (Windows / PowerShell)

```powershell
mkdir sorteio-sipat
cd sorteio-sipat
python -m venv .venv
.venv\Scripts\activate
python -m pip install openpyxl customtkinter
python -m pip freeze > requirements.txt
git init
```

Executar: `python -m sorteio` (a partir da raiz do projeto).
Recriar ambiente: `python -m pip install -r requirements.txt`.
Atualizar `requirements.txt` após instalar/remover bibliotecas.

### 7.2 Localização da planilha no executável

```python
def caminho_da_planilha():
    if getattr(sys, "frozen", False):
        pasta = Path(sys.executable).parent
    else:
        pasta = Path(r"C:\Users\FY0E\PETROBRAS\Anna Clara Gomes Silva Sousa - PrestServ - SIPAT 2026")
    return pasta / NOME_ARQUIVO
```

**Plano B:** se o arquivo não existir no caminho calculado, a tela abre o seletor de arquivos ("Escolher planilha").

### 7.3 Build e distribuição
- Build com PyInstaller **na pasta do projeto** (nunca dentro da pasta sincronizada):
  ```powershell
  python -m pip install pyinstaller
  pyinstaller --onefile --windowed --name SorteioSIPAT sorteio/__main__.py
  ```
- Copiar **apenas** o `.exe` gerado em `dist/` para a pasta sincronizada, ao lado do Excel.
- O OneDrive distribui o `.exe` para todos que sincronizam a pasta.

### 7.4 Configuração em cada computador
1. A pasta deve estar compartilhada com o usuário com permissão de **edição** (o OneDrive só sincroniza **pastas** compartilhadas, não arquivos soltos).
2. No OneDrive web → **Compartilhado** → pasta → **Adicionar atalho a Meus arquivos**.
3. No Explorador de Arquivos → botão direito na pasta → **Sempre manter neste dispositivo**.
4. Executar o `.exe` de dentro da pasta.

---

## 8. Segurança e privacidade (LGPD)

- **Planilhas reais nunca vão para o git** (nomes e matrículas de funcionários). Ver `.gitignore`.
- **Testes de gravação sempre em cópia** (`data/exemplo/teste.xlsx`), nunca no arquivo real do SharePoint.
- **Não mover** o Excel ligado ao Forms (pode quebrar a ligação); apenas compartilhar a pasta.
- Ao colar saídas de teste em conversas/documentos, **substituir dados reais** por fictícios.
- Somente o desenvolvedor atualiza o `.exe` na pasta compartilhada; combinar com a organização que ninguém mais o substitui.
- Aleatoriedade com `secrets` (não `random`), para o resultado ser imprevisível e defensável.

---

## 9. Robustez e riscos conhecidos

| Risco | Mitigação |
|---|---|
| Arquivo bloqueado (OneDrive sincronizando) → `PermissionError` (Errno 13) ao ler | Ler o arquivo inteiro para a memória e fechar na hora; tentar de novo 6x com 1 s de intervalo (também se vier pela metade); depois, mensagem amigável com o detalhe técnico do erro. Manter os ganhadores na sessão para nova tentativa. |
| Planilha protegida (senha / rótulo de confidencialidade com criptografia) | Detectado pela assinatura do arquivo; mensagem pedindo para remover a proteção. |
| OneDrive demora a baixar as respostas novas do Forms → sorteio com planilha desatualizada | Status mostra a hora da última resposta; antes de sortear, se ela for mais de 2 min anterior ao horário limite (ou a agora), o sistema avisa e pergunta se quer sortear mesmo assim. |
| openpyxl reescreveria o arquivo inteiro, perdendo respostas do Forms / quebrando a ligação | **Resolvido:** a planilha do Forms nunca é gravada; ganhadores vão para arquivos separados (seção 3.2). |
| Conflito de sincronização do OneDrive (vários computadores gravando) | **Resolvido:** cada sessão grava um arquivo com nome único (evento + data/hora + computador). |
| Dois computadores sorteando o **mesmo evento** ao mesmo tempo | Um só enxerga os ganhadores do outro depois que o OneDrive sincroniza; evitar, ou aguardar a sincronização entre sessões. |
| Programa fechado antes de "Encerrar" → perda da sessão | Confirmação ao fechar a janela (RN-06.5). Alternativa: gravar a cada rodada. |
| Leitura da **aba ativa**: se alguém salvar o arquivo com "Ganhadores" selecionada, o sistema leria a aba errada | **Recomendado:** ler a aba de inscrições por `worksheets[0]` (primeira aba) ou pelo nome, em vez de `active`. |
| Cabeçalho pulado duas vezes (`min_row=2` + `next`) exclui o primeiro inscrito | Usar **apenas um** dos dois. |
| Arquivo não sincronizado (só na nuvem) sem internet | "Sempre manter neste dispositivo" em cada computador. |
| Executável bloqueado por política/antivírus | Testar o `.exe` em um computador que não seja o do desenvolvedor antes do evento. |
| Nome do evento digitado de formas diferentes no Forms | Usar campo de **múltipla escolha** no Forms; a lista suspensa é montada com os eventos da própria planilha; comparação sem acento, maiúsculas ou espaços extras. |
| Atualizar o `.exe` com alguém usando | Atualizar apenas fora dos horários de sorteio. |

---

## 10. Arquivos de apoio

### 10.1 `.gitignore`

```gitignore
# Ambiente virtual
.venv/

# Python
__pycache__/
*.py[cod]

# Planilhas reais - nunca versionar (LGPD)
*.xlsx
!data/exemplo/*.xlsx

# Backups e logs
backup/
*.log

# Build do PyInstaller
build/
dist/
*.spec
```

### 10.2 README
Deve conter: descrição, requisitos, instalação, como usar no dia do evento, formato da planilha, regras de elegibilidade, estrutura do projeto e como testar.

---

## 11. Testes e critérios de aceite

Testes manuais (no terminal, com a cópia de teste):

- [ ] `ler_inscricoes` devolve todas as linhas não vazias, **incluindo o primeiro inscrito**, com nome/matrícula/evento das colunas certas mesmo com as colunas automáticas do Forms.
- [ ] `filtrar_inscricoes` devolve só inscrições daquele evento (ignorando acento/maiúsculas) até o horário limite.
- [ ] Com a planilha antiga (última resposta antes do horário limite), o Play avisa que ela pode estar desatualizada.
- [ ] `ler_ganhadores` devolve `[]` quando a aba não existe.
- [ ] `gravar_ganhadores` cria um arquivo novo em `Ganhadores/` com cabeçalho a cada sessão.
- [ ] Dois computadores encerrando ao mesmo tempo geram dois arquivos, sem perder nenhum ganhador.
- [ ] A planilha do Forms não é alterada após "Encerrar".
- [ ] Sem permissão de gravação, "Encerrar" exibe mensagem amigável e não perde a sessão.
- [ ] Quem ganhou na rodada 1 não é sorteado na rodada 2 do mesmo evento.
- [ ] Quem ganhou no evento A pode ser sorteado no evento B.
- [ ] Inscrito após o horário limite nunca é sorteado.
- [ ] Quantidade maior que elegíveis gera mensagem e não sorteia.
- [ ] Evento fica travado durante a sessão e é liberado após "Encerrar".
- [ ] Fechar a janela com ganhadores não salvos pede confirmação.
- [ ] `.exe` encontra a planilha ao lado dele em outro computador.
- [ ] A pasta `Ganhadores/` aparece no SharePoint após a sincronização.

---

## 12. Plano de implementação e prioridades

### Obrigatório (MVP)
1. ✅ Estrutura do projeto, venv, git, `.gitignore`
2. 🟡 `planilha.py`: `caminho_da_planilha`, `ler_inscricoes` (com filtros), `ler_ganhadores`
3. ⬜ `planilha.py`: `gravar_ganhadores` (arquivo por sessão em `Ganhadores/` e `PermissionError`)
4. ⬜ Confirmar colunas reais e definir constantes de índice (5.5)
5. ⬜ `sorteador.py`: `listar_eventos`, `filtrar_ja_ganhadores`, `sortear`
6. ⬜ `telas.py`: tela única, Play, Encerrar, trava de evento, confirmação ao fechar
7. ⬜ `__main__.py` ligando a tela
8. ⬜ Build `.exe`, cópia para a pasta sincronizada, teste em outro computador
9. ⬜ Teste com Forms de teste (seção 9)

### Se sobrar tempo
- Modo amostragem caprichado (animação, identidade visual SIPAT)
- Log de auditoria com semente, data/hora e total de elegíveis (arquivo `.log` ao lado da planilha)
- Contador "N inscritos elegíveis" ao trocar de evento
- Testes automatizados com `pytest`

---

## 13. Pendências em aberto

1. Nomes exatos e posição das colunas na exportação real do Forms.
2. Formato da coluna de hora (confirmar se chega como `datetime`).
3. Campo "Evento" no Forms é múltipla escolha ou texto livre?
4. ~~Quantos computadores vão sortear~~ — vários ao mesmo tempo (resolvido com arquivos por sessão, seção 3.2).
5. Identidade visual (cores, logo) da SIPAT 2026.
6. Lista de pessoas que precisam de acesso de edição à pasta.
