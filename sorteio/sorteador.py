"""Regras de negócio: listar eventos, filtrar elegíveis e sortear."""

import secrets

from sorteio.planilha import COL_EVENTO, COL_MATRICULA, COL_NOME, COL_EMPRESA


def _normalizar_matricula(valor):
    """Normaliza matrícula: sem espaços nas pontas e em maiúsculas (RN-04)."""
    return str(valor).strip().upper()


# ---------------------------------------------------------------------------
# Listar eventos
# ---------------------------------------------------------------------------
def listar_eventos(inscricoes):
    """Devolve lista ordenada de eventos distintos presentes nas inscrições.

    Cada evento é comparado com strip() (RN-04).
    """
    eventos = set()
    for linha in inscricoes:
        valor = linha[COL_EVENTO]
        if valor is not None:
            eventos.add(str(valor).strip())
    return sorted(eventos)


# ---------------------------------------------------------------------------
# Filtrar quem já ganhou
# ---------------------------------------------------------------------------
def filtrar_ja_ganhadores(inscricoes, ganhadores_planilha, ganhadores_sessao, evento):
    """Remove dos inscritos quem já ganhou no mesmo evento (RN-02 item 3, RN-03).

    Parâmetros:
        inscricoes: lista de tuplas (saída de ler_inscricoes, já filtrada por evento/horário).
        ganhadores_planilha: lista de tuplas já gravadas (saída de ler_ganhadores).
        ganhadores_sessao: lista de tuplas (evento, nome, matricula, empresa, premio) da sessão atual.
        evento: nome do evento sendo sorteado.

    Retorna lista de inscrições elegíveis.
    """
    # Monta o conjunto de matrículas que já ganharam NESTE evento.
    # Nos ganhadores gravados: coluna 0 = Evento, coluna 2 = Matrícula
    matriculas_ganhadoras = set()

    evento_norm = evento.strip()

    for g in ganhadores_planilha:
        evento_g = str(g[0]).strip() if g[0] is not None else ""
        if evento_g == evento_norm:
            matriculas_ganhadoras.add(_normalizar_matricula(g[2]))

    for g in ganhadores_sessao:
        evento_g = str(g[0]).strip() if g[0] is not None else ""
        if evento_g == evento_norm:
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
