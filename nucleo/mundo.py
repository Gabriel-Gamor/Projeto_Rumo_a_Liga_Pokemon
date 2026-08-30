"""Simulação de eventos discretos: sem percorrer cada unidade do relógio.

O heap agenda chegadas e decisões. Um NPC em trânsito não está disponível
para encontro em nenhum dos vértices; cada chegada atravessa uma única aresta.
"""

from collections import deque
from dataclasses import dataclass, field
from heapq import heappop, heappush
from math import inf
from random import Random

from nucleo.algoritmos import dijkstra, reconstruir
from nucleo.tipos import TabelaTipos
from nucleo.pokemon import Pokemon
from nucleo.treinador import Treinador
from nucleo.erros import AcaoInvalida


@dataclass
class Ator:
    codigo: str
    tipo: str
    posicao: str | None
    treinador: Treinador | None = None
    pokemon: Pokemon | None = None
    ginasio: str | None = None
    movimento: tuple | None = None  # origem, destino, partida, chegada
    versao: int = 0
    ativo: bool = True
    suspenso: bool = False
    invisivel_ate: int | None = None
    escondido_para: set = field(default_factory=set)
    roubados: list = field(default_factory=list)
    em_tratamento: bool = False

    @property
    def equipe(self):
        return self.treinador.equipe if self.treinador else [self.pokemon]


@dataclass
class Item:
    codigo: str
    tipo: str
    posicao: str
    filhote: Pokemon | None = None
    recolhido: bool = False


class Mundo:
    def __init__(self, regiao, semente=3, nome="Treinador", iniciais="trio"):
        if iniciais not in {"trio", "aleatorio"}:
            raise AcaoInvalida("Escolha trio ou aleatorio para os iniciais.")
        self.regiao, self.semente, self.agora = regiao, semente, 0
        self.rng = Random(semente)
        self.contador_pokemon = 0
        self.sequencia = 0
        self.fila_eventos = []
        self.historico = deque(maxlen=2000)
        self.atores, self.itens = {}, {}
        self.ginasios = {g.codigo: g for g in regiao.ginasios}
        self.cache_caminhos = {}
        self.distancia_percorrida = 0
        self.tipos = TabelaTipos(regiao.vantagens, regiao.regras["vantagens_tipos"])
        self.jogador = Treinador("jogador", nome, regiao.laboratorio)
        especies = regiao.iniciais if iniciais == "trio" else [self.rng.choice(list(regiao.catalogo))]
        for especie in especies:
            self.jogador.receber(self.criar_pokemon(especie, inicial=True))
        self._popular()
        self.registrar("inicio", mensagem=f"Jornada iniciada por {nome}.")

    def registrar(self, tipo, **dados):
        self.historico.append({"tempo": self.agora, "tipo": tipo, **dados})

    def criar_pokemon(self, especie=None, inicial=False, ovo=False, xp_max=None):
        self.contador_pokemon += 1
        especie = especie or self.rng.choice(list(self.regiao.catalogo))
        regras = self.regiao.regras
        ap = regras["ap_inicial" if inicial or ovo else "ap_regiao"]
        dp = regras["dp_inicial" if inicial or ovo else "dp_regiao"]
        p = Pokemon(f"P{self.contador_pokemon:04d}", self.regiao.catalogo[especie],
                    self.rng.randint(*ap), self.rng.randint(*dp))
        if not inicial and not ovo:
            p.ganhar_xp(self.rng.randint(0, regras["xp_selvagem_max"] if xp_max is None else xp_max))
            p.hp = float(self.rng.randint(regras["hp_regiao_min"], regras["hp_regiao_max"]))
            if p.hp < 20:
                p.inconsciente_ate = self.agora + self.rng.randint(10, 50)
        return p

    def _popular(self):
        vertices = list(self.regiao.grafo.adj)
        for g in self.regiao.ginasios:
            codigo = f"L-{g.codigo}"
            equipe = [self.criar_pokemon(xp_max=self.regiao.regras["xp_lider_max"]) for _ in range(3)]
            treinador = Treinador(codigo, g.lider, g.vertice, equipe,
                                  self.rng.randint(0, self.regiao.regras["xp_treinador_max"]))
            self.atores[codigo] = Ator(codigo, "lider", g.vertice, treinador=treinador, ginasio=g.codigo)
        for tipo, chave, prefixo in [("treinador", "treinadores", "T"), ("rocket", "rockets", "R")]:
            for i in range(self.regiao.quantidades[chave]):
                codigo, lugar = f"{prefixo}{i+1:02d}", self.rng.choice(vertices)
                equipe = [self.criar_pokemon() for _ in range(3)]
                nome = f"Equipe Rocket {i+1}" if tipo == "rocket" else f"Treinador {i+1}"
                treinador = Treinador(codigo, nome, lugar, equipe,
                                      self.rng.randint(0, self.regiao.regras["xp_treinador_max"]))
                self.atores[codigo] = Ator(codigo, tipo, lugar, treinador=treinador)
        for i in range(self.regiao.quantidades["selvagens"]):
            codigo = f"S{i+1:02d}"
            self.atores[codigo] = Ator(codigo, "selvagem", self.rng.choice(vertices),
                                      pokemon=self.criar_pokemon())
        for tipo, chave, prefixo in [("ovo", "ovos", "E"), ("erva", "ervas", "H")]:
            for i in range(self.regiao.quantidades[chave]):
                codigo = f"{prefixo}{i+1:02d}"
                filhote = self.criar_pokemon(ovo=True) if tipo == "ovo" else None
                self.itens[codigo] = Item(codigo, tipo, self.rng.choice(vertices), filhote)
        for ator in self.atores.values():
            self.agendar(ator, self.agora + 1, "decidir")

    def caminhos(self, origem):
        if origem not in self.cache_caminhos:
            self.cache_caminhos[origem] = dijkstra(self.regiao.grafo, origem)
        return self.cache_caminhos[origem]

    def agendar(self, ator, instante, acao, destino=None):
        if instante < self.agora:
            raise ValueError("Evento no passado.")
        self.sequencia += 1
        heappush(self.fila_eventos, (instante, self.sequencia, ator.codigo,
                                    ator.versao, acao, destino))

    def suspender(self, ator):
        if ator.movimento:
            raise AcaoInvalida("O ator está em trânsito.")
        ator.versao += 1
        ator.suspenso = True

    def retomar(self, ator):
        ator.suspenso = False
        ator.versao += 1
        if ator.ativo:
            self.agendar(ator, self.agora + 1, "decidir")

    def _mudar_posicao(self, ator, destino):
        ator.posicao = destino
        if ator.treinador:
            ator.treinador.posicao = destino

    def _partir(self, ator, destino):
        origem = ator.posicao
        duracao = self.regiao.grafo.peso(origem, destino)
        ator.movimento = (origem, destino, self.agora, self.agora + duracao)
        self._mudar_posicao(ator, None)
        self.agendar(ator, self.agora + duracao, "chegar", destino)

    def _passo_ate(self, ator, destino):
        _, pais = self.caminhos(ator.posicao)
        caminho = reconstruir(pais, ator.posicao, destino)
        if len(caminho) > 1:
            self._partir(ator, caminho[1])

    def _decidir(self, ator):
        if not ator.ativo or ator.suspenso or ator.invisivel_ate is not None:
            return
        posicao = ator.posicao
        # Qualquer treinador leva feridos graves ao PMC, um vértice por etapa.
        if ator.treinador and any(p.grave for p in ator.equipe):
            if self.regiao.grafo.vertices[posicao].tipo == "pmc":
                ator.em_tratamento = True
                duracao = max(self.rng.randint(10, 50) for _ in ator.equipe)
                self.agendar(ator, self.agora + duracao, "curar")
            else:
                distancias, _ = self.caminhos(posicao)
                pmc = min(self.regiao.grafo.locais("pmc"), key=distancias.get)
                self._passo_ate(ator, pmc)
            return
        if ator.ginasio:
            g = self.ginasios[ator.ginasio]
            if not g.movel:
                if posicao != g.vertice:
                    self._passo_ate(ator, g.vertice)
                return
            fase = self.agora % g.periodo
            if fase < g.permanencia:
                if posicao != g.vertice:
                    self._passo_ate(ator, g.vertice)
                else:
                    self.agendar(ator, self.agora + g.permanencia - fase, "decidir")
                return
            restante = g.periodo - fase
            ate_casa, _ = self.caminhos(g.vertice)
            opcoes = [(v, peso) for v, peso in self.regiao.grafo.adj[posicao]
                      if peso + ate_casa[v] <= restante]
            # A folga estrita permite passear; sem folga, retorna ao ginásio.
            passeios = [(v, peso) for v, peso in opcoes
                        if peso + ate_casa[v] < restante and v != g.vertice]
            if passeios:
                self._partir(ator, self.rng.choice(passeios)[0])
            elif posicao != g.vertice:
                self._passo_ate(ator, g.vertice)
            else:
                self.agendar(ator, self.agora + restante, "decidir")
            return
        if ator.pokemon and not ator.pokemon.consciente:
            self.agendar(ator, self.agora + 10, "decidir")
            return
        vizinhos = self.regiao.grafo.adj[posicao]
        if vizinhos:
            self._partir(ator, self.rng.choice(vizinhos)[0])

    def _processar(self, evento):
        _, _, codigo, versao, acao, destino = evento
        ator = self.atores.get(codigo)
        if not ator or not ator.ativo or ator.suspenso or versao != ator.versao:
            return
        if acao == "decidir":
            self._decidir(ator)
        elif acao == "chegar":
            origem, _, partida, chegada = ator.movimento
            self._mudar_posicao(ator, destino)
            ator.movimento = None
            for p in ator.equipe:
                p.percorrer(chegada - partida)
            self.registrar("movimento_npc", ator=codigo, origem=origem, destino=destino,
                           partida=partida, chegada=chegada)
            if ator.ginasio or any(p.grave for p in ator.equipe):
                self._decidir(ator)
            else:
                r = self.regiao.regras
                self.agendar(ator, self.agora + self.rng.randint(r["pausa_npc_min"], r["pausa_npc_max"]), "decidir")
        elif acao == "curar":
            for p in ator.equipe:
                p.tratar_pmc()
            ator.em_tratamento = False
            self.registrar("tratamento_npc", ator=codigo, local=ator.posicao)
            self.agendar(ator, self.agora + 1, "decidir")
        elif acao == "reaparecer":
            ator.invisivel_ate = None
            self._mudar_posicao(ator, self.rng.choice(list(self.regiao.grafo.adj)))
            self.registrar("rocket_reapareceu", ator=codigo, local=ator.posicao)
            self.agendar(ator, self.agora + 1, "decidir")

    def _pokemons_existentes(self):
        vistos = set()
        listas = [self.jogador.equipe, self.jogador.deposito]
        if self.jogador.pendente:
            listas.append([self.jogador.pendente])
        listas.extend(a.equipe for a in self.atores.values() if a.ativo)
        for lista in listas:
            for pokemon in lista:
                if pokemon.codigo not in vistos:
                    vistos.add(pokemon.codigo)
                    yield pokemon

    def avancar(self, unidades, viajando=False):
        if type(unidades) is not int or unidades < 0:
            raise AcaoInvalida("Tempo deve ser um inteiro não negativo.")
        fim = self.agora + unidades
        while self.agora < fim:
            proximo = min(fim, self.fila_eventos[0][0] if self.fila_eventos else fim)
            if self.jogador.ovos:
                proximo = min(proximo, min(o.choca_em for o in self.jogador.ovos))
            intervalo = proximo - self.agora
            for p in self._pokemons_existentes():
                p.passar_tempo(intervalo, proximo)
            self.agora = proximo
            if viajando:
                self.distancia_percorrida += intervalo
                for p in self.jogador.equipe:
                    for nome in p.percorrer(intervalo):
                        self.registrar("evolucao", pokemon=p.codigo, nova_forma=nome)
            for p in self.jogador.chocar(self.agora):
                self.registrar("ovo_chocou", pokemon=p.codigo, nome=p.nome)
            while self.fila_eventos and self.fila_eventos[0][0] <= self.agora:
                self._processar(heappop(self.fila_eventos))

    def presentes(self, local=None):
        local = self.jogador.posicao if local is None else local
        if local is None:
            return []
        return [a for a in self.atores.values() if a.ativo and a.posicao == local
                and a.invisivel_ate is None and self.jogador.codigo not in a.escondido_para]

    def remover_selvagem(self, ator):
        ator.ativo = False
        ator.suspenso = False
        ator.versao += 1

    def expulsar_rocket(self, ator, local):
        distancias, _ = self.caminhos(local)
        maior = max(d for d in distancias.values() if d < inf)
        distantes = [v for v, d in distancias.items() if d >= maior * 0.75 and v != local]
        ator.versao += 1
        ator.suspenso = False
        ator.movimento = None
        self._mudar_posicao(ator, self.rng.choice(distantes))
        self.registrar("rocket_expulsa", ator=ator.codigo, origem=local, destino=ator.posicao)
        self.agendar(ator, self.agora + 1, "decidir")

    def esconder_rocket(self, ator):
        ator.versao += 1
        ator.suspenso = False
        ator.invisivel_ate = self.agora + self.rng.randint(30, 80)
        self._mudar_posicao(ator, None)
        self.agendar(ator, ator.invisivel_ate, "reaparecer")
