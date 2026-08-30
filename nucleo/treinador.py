"""Inventário: até seis ativos e até sete posições contando ovos e espera."""

from dataclasses import dataclass, field

from nucleo.pokemon import Pokemon
from nucleo.erros import AcaoInvalida


@dataclass
class Ovo:
    codigo: str
    filhote: Pokemon
    choca_em: int


@dataclass
class Treinador:
    codigo: str
    nome: str
    posicao: str | None
    equipe: list = field(default_factory=list)
    xp: int = 0
    insignias: set = field(default_factory=set)
    ovos: list = field(default_factory=list)
    deposito: list = field(default_factory=list)
    pendente: Pokemon | None = None
    incubadora: bool = True
    pokebolas: int = 7

    @property
    def ocupacao(self):
        return len(self.equipe) + len(self.ovos) + (self.pendente is not None)

    @property
    def conscientes(self):
        return [p for p in self.equipe if p.consciente]

    def conferir_limites(self):
        if len(self.equipe) > 6 or self.ocupacao > 7:
            raise AcaoInvalida("Limite: seis ativos e sete posições incluindo ovos.")
        ids = [p.codigo for p in self.equipe + self.deposito]
        ids += [ovo.filhote.codigo for ovo in self.ovos]
        if self.pendente:
            ids.append(self.pendente.codigo)
        if len(ids) != len(set(ids)):
            raise AcaoInvalida("Pokémon duplicado no inventário.")

    def receber(self, pokemon):
        self._exigir_novo(pokemon)
        if self.ocupacao >= 7:
            raise AcaoInvalida("Não há posição livre na sétima pokébola.")
        if len(self.equipe) < 6:
            self.equipe.append(pokemon)
            destino = "equipe"
        elif self.pendente is None:
            self.pendente = pokemon
            destino = "selecao_pendente"
        else:
            raise AcaoInvalida("Resolva a seleção pendente antes de outra captura.")
        self.conferir_limites()
        return destino

    def pegar_ovo(self, codigo, filhote, agora):
        self._exigir_novo(filhote)
        if any(o.codigo == codigo for o in self.ovos):
            raise AcaoInvalida("Ovo duplicado no inventário.")
        if not self.incubadora or self.ocupacao >= 7:
            raise AcaoInvalida("Não há incubadora ou posição disponível para o ovo.")
        self.ovos.append(Ovo(codigo, filhote, agora + 100))
        self.conferir_limites()

    def _exigir_novo(self, pokemon):
        existentes = self.equipe + self.deposito + [o.filhote for o in self.ovos]
        if self.pendente:
            existentes.append(self.pendente)
        if any(p.codigo == pokemon.codigo for p in existentes):
            raise AcaoInvalida("Pokémon duplicado no inventário.")

    def chocar(self, agora):
        nascidos = []
        for ovo in list(self.ovos):
            if ovo.choca_em <= agora:
                self.ovos.remove(ovo)
                self.receber(ovo.filhote)
                nascidos.append(ovo.filhote)
        return nascidos

    def enviar_ao_professor(self, codigo):
        """O jogador escolhe quem sai; nenhum ativo é descartado implicitamente."""
        if self.pendente and self.pendente.codigo == codigo:
            pokemon, self.pendente = self.pendente, None
        else:
            pokemon = next((p for p in self.equipe if p.codigo == codigo), None)
            if pokemon is None:
                raise AcaoInvalida("Escolha um Pokémon ativo ou pendente; ovos não podem ser abandonados.")
            self.equipe.remove(pokemon)
        self.deposito.append(pokemon)
        if self.pendente and len(self.equipe) < 6:
            self.equipe.append(self.pendente)
            self.pendente = None
        self.conferir_limites()
        return pokemon

    def retirar_do_professor(self, codigo):
        if len(self.equipe) >= 6 or self.ocupacao >= 7 or self.pendente:
            raise AcaoInvalida("Não há espaço livre na equipe.")
        pokemon = next((p for p in self.deposito if p.codigo == codigo), None)
        if pokemon is None:
            raise AcaoInvalida("Pokémon não está no laboratório.")
        self.deposito.remove(pokemon)
        self.equipe.append(pokemon)
        self.conferir_limites()

    def escolher_trio(self, codigos=None):
        codigos = codigos or [p.codigo for p in self.conscientes[:3]]
        if len(codigos) != 3 or len(set(codigos)) != 3:
            raise AcaoInvalida("Escolha exatamente três Pokémon distintos.")
        por_id = {p.codigo: p for p in self.conscientes}
        if any(c not in por_id for c in codigos):
            raise AcaoInvalida("Todos os escolhidos devem estar ativos e conscientes.")
        return [por_id[c] for c in codigos]


@dataclass(frozen=True)
class Ginasio:
    codigo: str
    vertice: str
    insignia: str
    lider: str
    movel: bool = False
    periodo: int = 300
    permanencia: int = 100
