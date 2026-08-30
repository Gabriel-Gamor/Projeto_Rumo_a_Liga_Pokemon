"""Casos de uso: cada ação valida suas precondições antes de alterar o mundo."""

from dataclasses import asdict

from nucleo.algoritmos import reconstruir
from nucleo.algoritmos import planejar_insignias
from nucleo.erros import AcaoInvalida, ErroFormato
from nucleo.batalha import (
    EstrategiaAutomatica, ResultadoBatalha, batalhar,
)
from nucleo.mundo import Mundo


class Jogo:
    def __init__(self, regiao, semente=3, nome="Treinador", iniciais="trio"):
        self.mundo = Mundo(regiao, semente, nome, iniciais)
        self.inscrito = False

    @property
    def jogador(self):
        return self.mundo.jogador

    @property
    def expirado(self):
        return not self.inscrito and self.mundo.agora > self.mundo.regiao.prazo

    def _ativo(self, inventario=True):
        if self.inscrito:
            raise AcaoInvalida("A inscrição foi realizada; a jornada está concluída.")
        if self.expirado:
            raise AcaoInvalida("O prazo terminou: treinador inapto para esta edição da Liga.")
        if inventario and self.jogador.pendente:
            raise AcaoInvalida("Na aba Minha equipe, escolha qual Pokémon enviar ao professor antes de continuar.")

    def _local_batalha(self):
        self._ativo()
        local = self.mundo.regiao.grafo.vertices[self.jogador.posicao]
        if local.tipo in {"pmc", "laboratorio"}:
            raise AcaoInvalida("Batalhas são proibidas no PMC e no laboratório.")

    def _encontrar_ator(self, codigo, tipos):
        if codigo in self.mundo.ginasios:
            codigo = "L-" + codigo
        ator = next((a for a in self.mundo.presentes() if a.codigo == codigo), None)
        if ator is None or ator.tipo not in tipos:
            raise AcaoInvalida("O alvo não está disponível neste vértice.")
        return ator

    def status(self):
        m, j = self.mundo, self.jogador
        return {"regiao": m.regiao.nome, "treinador": j.nome, "xp_treinador": j.xp,
                "tempo": m.agora, "prazo": m.regiao.prazo,
                "tempo_restante": max(0, m.regiao.prazo - m.agora),
                "distancia_percorrida": m.distancia_percorrida, "local": j.posicao,
                "insignias": sorted(j.insignias), "inscrito": self.inscrito,
                "inapto": self.expirado, "pokebolas": j.pokebolas,
                "incubadora": j.incubadora, "ocupacao": j.ocupacao,
                "equipe": [p.resumo() for p in j.equipe],
                "ovos": [{"codigo": o.codigo, "choca_em": o.choca_em,
                          "faltam": max(0, o.choca_em - m.agora)} for o in j.ovos],
                "pendente": j.pendente.resumo() if j.pendente else None,
                "deposito": [p.resumo() for p in j.deposito]}

    def olhar(self):
        m = self.mundo
        local = m.regiao.grafo.vertices[self.jogador.posicao]
        atores = []
        for ator in m.presentes():
            info = {"codigo": ator.codigo, "tipo": ator.tipo}
            if ator.treinador:
                info.update(nome=ator.treinador.nome, xp=ator.treinador.xp,
                            conscientes=len(ator.treinador.conscientes),
                            ginasio=ator.ginasio)
            else:
                info.update(pokemon=ator.pokemon.resumo())
            atores.append(info)
        itens = [{"codigo": i.codigo, "tipo": i.tipo} for i in m.itens.values()
                 if i.posicao == local.codigo and not i.recolhido]
        return {"codigo": local.codigo, "nome": local.nome, "tipo": local.tipo,
                "vizinhos": [{"vertice": v, "tempo": w} for v, w in m.regiao.grafo.adj[local.codigo]],
                "atores": atores, "itens": itens}

    def rota(self, destino):
        if destino not in self.mundo.regiao.grafo.adj:
            raise AcaoInvalida("Destino desconhecido.")
        d, pai = self.mundo.caminhos(self.jogador.posicao)
        return {"tempo": d[destino], "vertices": reconstruir(pai, self.jogador.posicao, destino)}

    def plano(self):
        candidatos = [g for g in self.mundo.regiao.ginasios if g.insignia not in self.jogador.insignias]
        plano = planejar_insignias(self.mundo.regiao.grafo, self.jogador.posicao,
                                   self.mundo.regiao.estadio, candidatos,
                                   max(0, 8-len(self.jogador.insignias)))
        return {**asdict(plano), "chegada_otimista": self.mundo.agora + plano.tempo_minimo,
                "dentro_do_prazo_otimista": self.mundo.agora + plano.tempo_minimo <= self.mundo.regiao.prazo,
                "limite": "Ignora derrotas, curas, encontros e ausência de líderes móveis."}

    def mover(self, destino):
        self._ativo()
        m, origem = self.mundo, self.jogador.posicao
        try:
            peso = m.regiao.grafo.peso(origem, destino)
        except ErroFormato as exc:
            raise AcaoInvalida(str(exc)) from exc
        self.jogador.posicao = None
        m.avancar(peso, viajando=True)
        self.jogador.posicao = destino
        m.registrar("movimento_jogador", origem=origem, destino=destino, duracao=peso)
        return self.olhar()

    def viajar(self, destino):
        self._ativo()
        caminho = self.rota(destino)["vertices"]
        percorrido = [self.jogador.posicao]
        for vertice in caminho[1:]:
            self.mover(vertice)
            percorrido.append(vertice)
            if self.jogador.pendente or self.expirado:
                break
        return {"percorrido": percorrido, "chegou": self.jogador.posicao == destino,
                "local": self.jogador.posicao, "tempo": self.mundo.agora,
                "selecao_pendente": self.jogador.pendente is not None, "inapto": self.expirado}

    def esperar(self, unidades):
        self._ativo()
        if type(unidades) is not int or unidades < 1:
            raise AcaoInvalida("Espera deve ser um inteiro positivo.")
        # Não processa uma espera arbitrariamente grande depois do fim do jogo.
        unidades = min(unidades, self.mundo.regiao.prazo - self.mundo.agora + 1)
        self.mundo.avancar(unidades)
        self.mundo.registrar("espera", duracao=unidades)
        return self.status()

    def coletar(self, codigo):
        self._ativo()
        item = self.mundo.itens.get(codigo)
        if not item or item.recolhido or item.posicao != self.jogador.posicao:
            raise AcaoInvalida("Item não está disponível neste vértice.")
        if item.tipo == "ovo":
            self.jogador.pegar_ovo(item.codigo, item.filhote, self.mundo.agora)
            efeito = {"ovo": codigo, "choca_em": self.mundo.agora + 100}
        else:
            curados = [p.codigo for p in self.jogador.equipe if p.tomar_erva()]
            efeito = {"erva": codigo, "pokemons_que_tomaram": curados}
        item.recolhido = True
        self.mundo.registrar("item_coletado", **efeito)
        return efeito

    def tratar(self):
        self._ativo(inventario=False)
        if self.mundo.regiao.grafo.vertices[self.jogador.posicao].tipo != "pmc":
            raise AcaoInvalida("O tratamento exige permanecer em um PMC.")
        pokemons = self.jogador.equipe + ([self.jogador.pendente] if self.jogador.pendente else [])
        tempos = {p.codigo: self.mundo.rng.randint(10, 50)
                  for p in pokemons if p.hp < 100 or not p.consciente}
        if not tempos:
            return {"duracao": 0, "tratados": []}
        inicio = self.mundo.agora
        # Tratamento em paralelo, sem fila, terminando cada paciente no seu prazo.
        for duracao in sorted(set(tempos.values())):
            self.mundo.avancar(inicio + duracao - self.mundo.agora)
            for p in pokemons:
                if tempos.get(p.codigo) == duracao:
                    p.tratar_pmc()
        self.mundo.registrar("tratamento_jogador", tempos=tempos, local=self.jogador.posicao)
        return {"duracao": max(tempos.values()), "tempos_individuais": tempos, "tratados": list(tempos)}

    def guardar(self, codigo):
        pokemon = self.jogador.enviar_ao_professor(codigo)
        self.mundo.registrar("envio_professor", pokemon=codigo)
        return pokemon.resumo()

    def retirar(self, codigo):
        self._ativo()
        if self.jogador.posicao != self.mundo.regiao.laboratorio:
            raise AcaoInvalida("Retire Pokémon pessoalmente no laboratório.")
        self.jogador.retirar_do_professor(codigo)
        self.mundo.registrar("retirada_professor", pokemon=codigo)

    def capturar(self, codigo, estrategia=None, abandonar=False, observador=None):
        self._local_batalha()
        ator = self._encontrar_ator(codigo, {"selvagem"})
        if not self.jogador.conscientes:
            raise AcaoInvalida("É necessário ao menos um Pokémon consciente para capturar.")
        if self.jogador.ocupacao >= 7:
            raise AcaoInvalida("Libere uma posição antes da captura; ovos também contam.")
        if abandonar:
            class Desistir(EstrategiaAutomatica):
                def desistir(self, turno, captura=False):
                    return captura
            estrategia = Desistir()
        self.mundo.suspender(ator)
        if not ator.pokemon.consciente and not abandonar:
            escolhido = self.jogador.conscientes[0]
            self.jogador.xp += 3
            escolhido.ganhar_xp(3)
            ator.pokemon.ganhar_xp(3)
            resultado = ResultadoBatalha(0, "captura_de_inconsciente", 0,
                                          [escolhido.codigo, ator.pokemon.codigo])
        elif abandonar:
            resultado = ResultadoBatalha(None, "captura_abandonada", 0)
        else:
            resultado = batalhar(self.jogador, None, self.jogador.conscientes,
                                 [ator.pokemon], self.mundo.tipos, self.mundo.rng,
                                 self.mundo.agora, estrategia_a=estrategia, captura=True,
                                 limite_turnos=self.mundo.regiao.regras["limite_turnos"],
                                 observador=observador)
        if resultado.vencedor == 0:
            destino = self.jogador.receber(ator.pokemon)
            self.mundo.remover_selvagem(ator)
        else:
            destino = None
            if resultado.vencedor is None:
                ator.escondido_para.add(self.jogador.codigo)
            self.mundo.retomar(ator)
        self.mundo.avancar(1)
        self.mundo.registrar("captura", alvo=codigo, resultado=resultado.motivo, destino=destino)
        return {**asdict(resultado), "capturado": resultado.vencedor == 0,
                "pokemon": ator.pokemon.resumo(), "destino": destino}

    def desafiar(self, codigo, trio=None, estrategia=None, como_desafiado=False, observador=None):
        self._local_batalha()
        ator = self._encontrar_ator(codigo, {"treinador", "lider", "rocket"})
        equipe_j = self.jogador.escolher_trio(trio)
        equipe_a = ator.treinador.escolher_trio()
        if not como_desafiado and ator.tipo == "treinador":
            if self.mundo.rng.random() >= self.mundo.regiao.regras["chance_aceitar"]:
                return {"aceitou": False, "motivo": "O treinador recusou o desafio."}
        self.mundo.suspender(ator)
        if como_desafiado:
            resultado = batalhar(ator.treinador, self.jogador, equipe_a, equipe_j,
                                 self.mundo.tipos, self.mundo.rng, self.mundo.agora,
                                 estrategia_b=estrategia,
                                 limite_turnos=self.mundo.regiao.regras["limite_turnos"],
                                 observador=observador)
            venceu = resultado.vencedor == 1
        else:
            resultado = batalhar(self.jogador, ator.treinador, equipe_j, equipe_a,
                                 self.mundo.tipos, self.mundo.rng, self.mundo.agora,
                                 estrategia_a=estrategia,
                                 limite_turnos=self.mundo.regiao.regras["limite_turnos"],
                                 observador=observador)
            venceu = resultado.vencedor == 0
        self.mundo.avancar(1)
        extras = {}
        if venceu and ator.ginasio:
            insignia = self.mundo.ginasios[ator.ginasio].insignia
            self.jogador.insignias.add(insignia)
            extras["insignia"] = insignia
        if ator.tipo == "rocket":
            if venceu:
                recuperados = []
                for p in list(ator.treinador.equipe):
                    if p.codigo in ator.roubados:
                        ator.treinador.equipe.remove(p)
                        self.jogador.deposito.append(p)
                        recuperados.append(p.codigo)
                ator.roubados.clear()
                extras["recuperados_no_laboratorio"] = recuperados
                self.mundo.expulsar_rocket(ator, self.jogador.posicao)
            else:
                if self.jogador.equipe and len(ator.treinador.equipe) < 6:
                    roubado = self.mundo.rng.choice(self.jogador.equipe)
                    self.jogador.equipe.remove(roubado)
                    ator.treinador.equipe.append(roubado)
                    ator.roubados.append(roubado.codigo)
                    extras["pokemon_roubado"] = roubado.codigo
                self.mundo.esconder_rocket(ator)
        else:
            self.mundo.retomar(ator)
        self.jogador.conferir_limites()
        self.mundo.registrar("batalha_treinador", alvo=ator.codigo, venceu=venceu,
                             motivo=resultado.motivo, **extras)
        return {**asdict(resultado), "aceitou": True, "venceu": venceu, **extras}

    def treinar(self, primeiro, segundo, estrategia=None, observador=None):
        self._local_batalha()
        por_id = {p.codigo: p for p in self.jogador.conscientes}
        if primeiro == segundo or primeiro not in por_id or segundo not in por_id:
            raise AcaoInvalida("Escolha dois Pokémon ativos, distintos e conscientes.")
        resultado = batalhar(self.jogador, self.jogador, [por_id[primeiro]], [por_id[segundo]],
                             self.mundo.tipos, self.mundo.rng, self.mundo.agora,
                             estrategia_a=estrategia, treino=True,
                             limite_turnos=self.mundo.regiao.regras["limite_turnos"],
                             observador=observador)
        self.mundo.avancar(1)
        self.mundo.registrar("treinamento", participantes=[primeiro, segundo])
        return asdict(resultado)

    def inscrever(self):
        self._ativo(inventario=False)
        if self.jogador.posicao != self.mundo.regiao.estadio:
            raise AcaoInvalida("Vá ao estádio para realizar a inscrição.")
        if len(self.jogador.insignias) < 8:
            raise AcaoInvalida("São necessárias oito insígnias distintas.")
        self.inscrito = True
        self.mundo.registrar("inscricao", insignias=sorted(self.jogador.insignias))
        return {"inscrito": True, "tempo": self.mundo.agora,
                "mensagem": "Classificação concluída: inscrição na Liga Pokémon realizada!"}
