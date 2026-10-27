"""Auditoria de ponta a ponta: planilha real em disco, várias sessões,
ganhadores gravados e relidos a cada sessão, até esgotar os elegíveis.

Invariantes verificadas:
  1. ninguém ganha duas vezes no mesmo evento (nem entre sessões);
  2. todas as pessoas do evento acabam sorteadas (ninguém fica de fora);
  3. ganhar num evento não impede de ganhar em outro;
  4. inscrição repetida (matrícula/nome escritos de outro jeito) não
     vira uma segunda pessoa.
"""

import secrets
import tempfile
import unittest
from collections import Counter
from datetime import datetime, time
from pathlib import Path

from sorteio.planilha import gravar_ganhadores, ler_ganhadores, ler_inscricoes, normalizar_texto
from sorteio.sorteador import filtrar_inscricoes, filtrar_ja_ganhadores, sortear
from tests.apoio import criar_planilha_forms

EVENTO_A = "Game Show C3"
EVENTO_B = "Palestra Josué, Teatro Educa Vida"
HORA = datetime(2026, 11, 10, 8, 0)
RODADAS = 20  # repetições da auditoria completa


def montar_respostas():
    """20 pessoas no evento A, as 10 primeiras também no B, com repetições."""
    respostas = []
    for n in range(20):
        nome, mat = f"Pessoa {n:02d}", f"00{1000 + n}"
        respostas.append((HORA, nome, "Petrobras", mat, EVENTO_A))
        if n < 10:
            # B escrito com outra grafia, como pode vir do Forms
            respostas.append((HORA, nome, "Petrobras", mat, "palestra josue, teatro educa vida"))
    for n in range(5):
        # mesma pessoa de novo: matrícula como número e nome em maiúsculas
        respostas.append((HORA, f"PESSOA {n:02d}", "Petrobras", 1000 + n, EVENTO_A))
    # mesmo nome, matrícula digitada errada
    respostas.append((HORA, "Pessoa 05", "Petrobras", "99999", EVENTO_A))
    return respostas


def pessoa(ganhador):
    return normalizar_texto(ganhador[1])


def sortear_ate_esgotar(arq, evento):
    """Simula sessões de 1 a 4 rodadas (quantidade 1 a 3) gravando ao fim
    de cada uma, como o botão Encerrar. Devolve os ganhadores do evento."""
    while True:
        sessao = []
        for _ in range(secrets.randbelow(4) + 1):
            inscricoes = filtrar_inscricoes(ler_inscricoes(arq), evento, time(23, 59))
            elegiveis = filtrar_ja_ganhadores(inscricoes, ler_ganhadores(arq), sessao, evento)
            try:
                sessao.extend(sortear(elegiveis, secrets.randbelow(3) + 1, evento, "Prêmio"))
            except ValueError:
                try:
                    # sobrou menos gente que a quantidade pedida
                    sessao.extend(sortear(elegiveis, 1, evento, "Prêmio"))
                except ValueError:
                    break
        if not sessao:
            break
        gravar_ganhadores(arq, sessao)

    evento_norm = normalizar_texto(evento)
    return [g for g in ler_ganhadores(arq) if normalizar_texto(g[0]) == evento_norm]


class TesteAuditoria(unittest.TestCase):
    def test_auditoria_completa(self):
        for rodada in range(RODADAS):
            with self.subTest(rodada=rodada), tempfile.TemporaryDirectory() as pasta:
                arq = criar_planilha_forms(Path(pasta) / "forms.xlsx", montar_respostas())
                ganhadores_a = sortear_ate_esgotar(arq, EVENTO_A)
                ganhadores_b = sortear_ate_esgotar(arq, EVENTO_B)

                repetidos_a = [p for p, n in Counter(map(pessoa, ganhadores_a)).items() if n > 1]
                repetidos_b = [p for p, n in Counter(map(pessoa, ganhadores_b)).items() if n > 1]
                self.assertEqual(repetidos_a, [], "repetiu no evento A")
                self.assertEqual(repetidos_b, [], "repetiu no evento B")

                # 20 pessoas no A (as repetições não viram pessoas novas)
                self.assertEqual(len(ganhadores_a), 20)
                # as 10 do B ganham de novo, mesmo já tendo ganhado no A
                self.assertEqual(
                    sorted(map(pessoa, ganhadores_b)),
                    [f"pessoa {n:02d}" for n in range(10)],
                )


if __name__ == "__main__":
    unittest.main()
