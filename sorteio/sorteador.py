"""Regras de negócio: listar eventos, filtrar elegíveis e sortear."""

import re
import secrets
from datetime import datetime, timedelta

from sorteio.planilha import (
    COL_EMPRESA,
    COL_EVENTO,
    COL_HORA,
    COL_MATRICULA,
    COL_NOME,
    eventos_da_celula,
    normalizar_texto,
)

# Diferença máxima aceita entre a resposta mais recente da planilha e o
# momento considerado pelo sorteio antes de avisar que ela pode estar
# desatualizada (OneDrive ainda não baixou as últimas respostas).
TOLERANCIA_ATRASO = timedelta(minutes=2)

# Nomes que o Forms grava quando a resposta é anônima — não identificam ninguém
NOMES_SEM_IDENTIDADE = {"", "anonymous", "anonimo", "none"}


def _texto_matricula(valor):
    """Matrícula como texto para exibir/gravar (12345.0 do Excel vira "12345")."""
    if valor is None:
        return ""
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    return str(valor).strip()


def normalizar_matricula(valor):
    """Matrícula para comparação (RN-04): só letras e dígitos, maiúsculas;
    se for só número, sem zeros à esquerda ("0012345", 12345 e "12.345"
    são a mesma matrícula)."""
    texto = re.sub(r"[^0-9A-Z]", "", normalizar_texto(_texto_matricula(valor)).upper())
    if texto.isdigit():
        texto = texto.lstrip("0") or "0"
    return texto


def _chaves_pessoa(matricula, nome):
    """Identificadores de uma pessoa: matrícula e nome normalizados.

    Duas linhas são a mesma pessoa se tiverem qualquer chave em comum.
    Matrícula ou nome vazios (ou "anonymous") não contam como chave.
    """
    chaves = set()
    mat = normalizar_matricula(matricula)
    if mat:
        chaves.add(("matricula", mat))
    nome_norm = normalizar_texto(nome)
    if nome_norm not in NOMES_SEM_IDENTIDADE:
        chaves.add(("nome", nome_norm))
    return chaves


def _chaves_inscricao(linha):
    return _chaves_pessoa(linha[COL_MATRICULA], linha[COL_NOME])


# ---------------------------------------------------------------------------
# Listar eventos
# ---------------------------------------------------------------------------
def listar_eventos(inscricoes):
    """Devolve lista ordenada de eventos distintos presentes nas inscrições.

    Eventos que só diferem em acento, maiúsculas ou espaços contam como um
    só (RN-04); fica a grafia da primeira ocorrência.
    """
    eventos = {}
    for linha in inscricoes:
        for evento in eventos_da_celula(linha[COL_EVENTO]):
            eventos.setdefault(normalizar_texto(evento), evento)
    return [eventos[chave] for chave in sorted(eventos)]


# ---------------------------------------------------------------------------
# Filtrar por evento e horário
# ---------------------------------------------------------------------------
def filtrar_inscricoes(inscricoes, evento, horario_limite):
    """Mantém as inscrições do evento até o horário limite (RN-02 itens 1 e 2).

    - evento: comparado sem acento/maiúsculas/espaços extras (RN-04);
      células com várias opções ("A;B;") valem para cada uma delas.
    - horário: hora de conclusão <= horario_limite (só a hora do dia).
    """
    evento_norm = normalizar_texto(evento)
    filtradas = []
    for linha in inscricoes:
        eventos_linha = {normalizar_texto(e) for e in eventos_da_celula(linha[COL_EVENTO])}
        if evento_norm not in eventos_linha:
            continue

        hora = linha[COL_HORA]
        if hora is None or hora.time() > horario_limite:
            continue

        filtradas.append(linha)
    return filtradas


# ---------------------------------------------------------------------------
# Planilha desatualizada
# ---------------------------------------------------------------------------
def resposta_mais_recente(inscricoes):
    """Hora de conclusão mais recente entre todas as inscrições (ou None)."""
    horas = [linha[COL_HORA] for linha in inscricoes if linha[COL_HORA] is not None]
    return max(horas, default=None)


def planilha_pode_estar_desatualizada(inscricoes, horario_limite, agora=None):
    """True se a resposta mais recente é bem anterior ao horário limite de
    hoje (ou a agora, se o limite ainda não chegou).

    Sinal de que o OneDrive ainda não trouxe as últimas respostas do Forms.
    Não é certeza: pode só não ter havido inscrições nesse intervalo.
    """
    agora = agora or datetime.now()
    ultima = resposta_mais_recente(inscricoes)
    if ultima is None:
        return True
    referencia = min(datetime.combine(agora.date(), horario_limite), agora)
    return ultima < referencia - TOLERANCIA_ATRASO


# ---------------------------------------------------------------------------
# Filtrar quem já ganhou
# ---------------------------------------------------------------------------
def filtrar_ja_ganhadores(inscricoes, ganhadores_planilha, ganhadores_sessao, evento):
    """Remove dos inscritos quem já ganhou no mesmo evento (RN-02 item 3, RN-03).

    Quem ganhou é reconhecido pela matrícula OU pelo nome (normalizados),
    para pegar também quem se inscreveu duas vezes com a matrícula
    digitada de outro jeito. Ganhar em outro evento não impede.

    Parâmetros:
        inscricoes: lista de tuplas (saída de filtrar_inscricoes).
        ganhadores_planilha: lista de tuplas já gravadas (saída de ler_ganhadores).
        ganhadores_sessao: lista de tuplas (evento, nome, matricula, empresa, premio) da sessão atual.
        evento: nome do evento sendo sorteado.

    Retorna lista de inscrições elegíveis.
    """
    # Chaves de quem já ganhou NESTE evento.
    # Nos ganhadores (RN-08): coluna 0 = Evento, 1 = Nome, 2 = Matrícula
    chaves_ganhadoras = set()

    evento_norm = normalizar_texto(evento)

    for g in list(ganhadores_planilha) + list(ganhadores_sessao):
        if len(g) > 2 and normalizar_texto(g[0]) == evento_norm:
            chaves_ganhadoras |= _chaves_pessoa(g[2], g[1])

    # Mantém quem NÃO tem nenhuma chave em comum com os ganhadores
    return [
        linha for linha in inscricoes
        if not (_chaves_inscricao(linha) & chaves_ganhadoras)
    ]


def remover_inscricoes_repetidas(inscricoes):
    """Deixa uma inscrição por pessoa (a primeira), para que se inscrever
    duas vezes não dê duas chances nem permita sair duas vezes na rodada."""
    vistas = set()
    unicas = []
    for linha in inscricoes:
        chaves = _chaves_inscricao(linha)
        if chaves & vistas:
            continue
        vistas |= chaves
        unicas.append(linha)
    return unicas


# ---------------------------------------------------------------------------
# Sortear
# ---------------------------------------------------------------------------
def sortear(elegiveis, quantidade, evento, premio):
    """Sorteia *quantidade* pessoas entre os elegíveis (RN-05).

    Inscrições repetidas da mesma pessoa contam uma vez só.
    Usa secrets.SystemRandom().sample() — aleatoriedade criptográfica.

    Retorna lista de tuplas no formato RN-08:
        (evento, nome, matricula, empresa, premio)

    Levanta ValueError se quantidade > número de pessoas elegíveis.
    Levanta ValueError se não houver elegíveis.
    """
    elegiveis = remover_inscricoes_repetidas(elegiveis)

    if len(elegiveis) == 0:
        raise ValueError("Não há inscritos elegíveis para este sorteio.")

    if quantidade > len(elegiveis):
        raise ValueError(
            f"Há apenas {len(elegiveis)} inscritos elegíveis; "
            f"reduza a quantidade (você pediu {quantidade})."
        )

    rng = secrets.SystemRandom()
    sorteados = rng.sample(elegiveis, quantidade)

    resultado = []
    for linha in sorteados:
        ganhador = (
            evento.strip(),
            str(linha[COL_NOME]).strip() if linha[COL_NOME] is not None else "",
            _texto_matricula(linha[COL_MATRICULA]),
            str(linha[COL_EMPRESA]).strip() if linha[COL_EMPRESA] is not None else "",
            premio.strip(),
        )
        resultado.append(ganhador)

    return resultado
