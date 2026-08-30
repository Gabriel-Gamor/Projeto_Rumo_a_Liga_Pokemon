"""Regras de XP, evolução, saúde e recuperação.

XP é acumulado, sem zerar: as transições ocorrem em 1000 e 2000 XP.
O bônus de evolução é registrado no instante da transição; XP posterior
continua acrescentando exatamente 10% de seu valor a AP e DP.
"""

from dataclasses import dataclass

from nucleo.tipos import Especie


@dataclass
class Pokemon:
    codigo: str
    especie: Especie
    ap_inicial: int
    dp_inicial: int
    xp: int = 0
    hp: float = 100.0
    fase: int = 0
    bonus_batalhas: int = 0
    bonus_evolucao_ap: float = 0.0
    bonus_evolucao_dp: float = 0.0
    inconsciente_ate: int | None = None
    resto_distancia: int = 0
    resto_tempo_hp: int = 0

    @property
    def nome(self):
        return self.especie.fases[self.fase].nome

    @property
    def tipos(self):
        return self.especie.fases[self.fase].tipos

    @property
    def ataques(self):
        return self.especie.ataques_ate(self.fase)

    @property
    def ap(self):
        return self.ap_inicial + self.xp * 0.1 + self.bonus_batalhas + self.bonus_evolucao_ap

    @property
    def dp(self):
        return self.dp_inicial + self.xp * 0.1 + self.bonus_batalhas + self.bonus_evolucao_dp

    @property
    def grave(self):
        return self.hp < 5

    @property
    def consciente(self):
        return self.hp >= 20 and self.inconsciente_ate is None

    def ganhar_xp(self, pontos):
        if type(pontos) is not int or pontos < 0:
            raise ValueError("O ganho de XP deve ser inteiro não negativo.")
        alvo = self.xp + pontos
        evolucoes = []
        while self.fase + 1 < len(self.especie.fases):
            limiar = (self.fase + 1) * 1000
            if alvo < limiar:
                break
            # Aplica o salto na fronteira, mesmo quando se ganham muitos XP.
            self.xp = limiar
            ap_anterior, dp_anterior = self.ap, self.dp
            self.bonus_evolucao_ap += ap_anterior * 0.3
            self.bonus_evolucao_dp += dp_anterior * 0.3
            self.fase += 1
            evolucoes.append(self.nome)
        self.xp = alvo
        return evolucoes

    def percorrer(self, distancia):
        if type(distancia) is not int or distancia < 0:
            raise ValueError("Distância deve ser inteira não negativa.")
        pontos, self.resto_distancia = divmod(self.resto_distancia + distancia, 100)
        return self.ganhar_xp(pontos)

    def vencer_duelo(self, xp_adversario_antes, xp_proprio_antes):
        if xp_adversario_antes >= xp_proprio_antes:
            self.bonus_batalhas += 1
        return self.ganhar_xp(10)

    def receber_dano(self, dano, agora, rng):
        """Nunca deixa HP abaixo de 1; uma nova queda agenda repouso uma vez."""
        if dano < 0:
            raise ValueError("Dano não pode ser negativo.")
        antes = self.consciente
        self.hp = max(1.0, self.hp - dano)
        if antes and self.hp < 20:
            self.inconsciente_ate = agora + rng.randint(10, 50)

    def passar_tempo(self, unidades, agora_final):
        if unidades < 0:
            raise ValueError("Tempo não pode retroceder.")
        if self.grave:
            return  # Ferimento grave não se cura por espera ou erva.
        # Divide no fim do repouso para o resultado não depender do tamanho dos
        # saltos do relógio. Durante o repouso HP não atinge 20; ao acordar
        # chega a pelo menos 20, conciliando o prazo de 10..50 com o limiar de HP.
        if self.inconsciente_ate is not None:
            inicio = agora_final - unidades
            repouso = min(unidades, max(0, self.inconsciente_ate - inicio))
            cura, self.resto_tempo_hp = divmod(self.resto_tempo_hp + repouso, 10)
            self.hp = min(max(19.0, self.hp), self.hp + cura)
            unidades -= repouso
            if agora_final < self.inconsciente_ate:
                return
            self.inconsciente_ate = None
            self.hp = max(20.0, self.hp)
        cura, self.resto_tempo_hp = divmod(self.resto_tempo_hp + unidades, 10)
        self.hp = min(100.0, self.hp + cura)

    def tomar_erva(self):
        if not self.consciente:
            return False
        self.hp = min(100.0, self.hp + 10)
        return True

    def tratar_pmc(self):
        self.hp = 100.0
        self.inconsciente_ate = None
        self.resto_tempo_hp = 0

    def resumo(self):
        estado = "grave" if self.grave else "consciente" if self.consciente else "inconsciente"
        return {"codigo": self.codigo, "nome": self.nome, "tipos": list(self.tipos),
                "fase": self.fase + 1, "xp": self.xp, "hp": round(self.hp, 2),
                "ap": round(self.ap, 2), "dp": round(self.dp, 2), "estado": estado,
                "repouso_ate": self.inconsciente_ate}
