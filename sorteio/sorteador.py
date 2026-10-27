"""Regras de negócio: listar eventos, filtrar elegíveis e sortear."""

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


def _normalizar_matricula(valor):
    """Normaliza matrícula: sem espaços nas pontas e em maiúsculas (RN-04)."""
    return str(valor).strip().upper()


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

    Parâmetros:
        inscricoes: lista de tuplas (saída de filtrar_inscricoes).
        ganhadores_planilha: lista de tuplas já gravadas (saída de ler_ganhadores).
        ganhadores_sessao: lista de tuplas (evento, nome, matricula, empresa, premio) da sessão atual.
        evento: nome do evento sendo sorteado.

    Retorna lista de inscrições elegíveis.
    """
    # Monta o conjunto de matrículas que já ganharam NESTE evento.
    # Nos ganhadores gravados: coluna 0 = Evento, coluna 2 = Matrícula
    matriculas_ganhadoras = set()

    evento_norm = normalizar_texto(evento)

    for g in list(ganhadores_planilha) + list(ganhadores_sessao):
        if len(g) > 2 and normalizar_texto(g[0]) == evento_norm:
            matriculas_ganhadoras.add(_normalizar_matricula(g[2]))

    # Filtra inscrições: mantém quem NÃO está no conjunto de ganhadores
    elegiveis = []
    for linha in inscricoes:
        matricula = _normalizar_matricula(linha[COL_MATRICULA])
        if matricula not in matriculas_ganhadoras:
            elegiveis.append(linha)

    return elegiveis


# ---------------------------------------------------------------------------
# Sortear
# ---------------------------------------------------------------------------
def sortear(elegiveis, quantidade, evento, premio):
    """Sorteia *quantidade* inscritos entre os elegíveis (RN-05).

    Usa secrets.SystemRandom().sample() — aleatoriedade criptográfica.

    Retorna lista de tuplas no formato RN-08:
        (evento, nome, matricula, empresa, premio)

    Levanta ValueError se quantidade > len(elegiveis).
    Levanta ValueError se não houver elegíveis.
    """
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
            _normalizar_matricula(linha[COL_MATRICULA]),
            str(linha[COL_EMPRESA]).strip() if linha[COL_EMPRESA] is not None else "",
            premio.strip(),
        )
        resultado.append(ganhador)

    return resultado
