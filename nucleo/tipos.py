"""Espécies, fases e ataques definidos no arquivo da região."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Ataque:
    nome: str
    tipo: str


@dataclass(frozen=True)
class Fase:
    nome: str
    tipos: tuple
    ataques: tuple


@dataclass(frozen=True)
class Especie:
    codigo: str
    fases: tuple

    def ataques_ate(self, fase):
        """Evoluir preserva ataques antigos e acrescenta os da nova fase."""
        ataques = {}
        for forma in self.fases[:fase + 1]:
            for ataque in forma.ataques:
                ataques[ataque.nome] = ataque
        return tuple(ataques.values())


TIPOS = ("normal", "fogo", "agua", "eletrico", "planta", "gelo",
         "lutador", "venenoso", "terra", "voador", "psiquico", "inseto",
         "pedra", "fantasma", "dragao", "sombrio", "aco", "fada")


class TabelaTipos:
    """A tabela usa [tipo do ataque][tipo do defensor]."""

    def __init__(self, tabela=None, habilitada=False):
        self.tabela = tabela or {}
        self.habilitada = habilitada

    def multiplicador(self, ataque, defensores):
        if not self.habilitada:
            return 1.0
        valor = 1.0
        for tipo in defensores:
            valor *= self.tabela.get(ataque, {}).get(tipo, 1.0)
        return valor
