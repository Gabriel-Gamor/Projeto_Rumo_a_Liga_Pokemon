"""Arquivos JSON legíveis; restaura relógio, referências, heap e gerador aleatório.

Não executa código do arquivo e não usa pickle. A gravação substitui o destino
somente depois de concluir um arquivo temporário no mesmo diretório.
"""

from collections import deque
from dataclasses import fields
from heapq import heapify
import json
from math import isfinite
import os
from pathlib import Path
from random import Random
from tempfile import NamedTemporaryFile

from nucleo.tipos import TabelaTipos
from nucleo.pokemon import Pokemon
from nucleo.treinador import Ovo, Treinador
from nucleo.erros import ErroFormato
from nucleo.regiao import inteiro, texto, validar_regiao
from nucleo.jogo import Jogo
from nucleo.mundo import Ator, Item, Mundo


def escrever_json(caminho, dados):
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=caminho.parent,
                                prefix=caminho.name + ".", suffix=".tmp", delete=False) as arq:
            temporario = Path(arq.name)
            json.dump(dados, arq, ensure_ascii=False, indent=2, allow_nan=False)
            arq.write("\n")
        os.replace(temporario, caminho)
    finally:
        if temporario and temporario.exists():
            temporario.unlink()


def estado(jogo):
    m, pokemons = jogo.mundo, {}

    def pokemon(p):
        if p is None:
            return None
        if p.codigo not in pokemons:
            dados = {f.name: getattr(p, f.name) for f in fields(Pokemon) if f.name != "especie"}
            dados["especie"] = p.especie.codigo
            pokemons[p.codigo] = dados
        return p.codigo

    def treinador(t):
        if t is None:
            return None
        return {"codigo": t.codigo, "nome": t.nome, "posicao": t.posicao,
                "xp": t.xp, "insignias": sorted(t.insignias), "incubadora": t.incubadora,
                "pokebolas": t.pokebolas, "equipe": [pokemon(p) for p in t.equipe],
                "deposito": [pokemon(p) for p in t.deposito], "pendente": pokemon(t.pendente),
                "ovos": [{"codigo": o.codigo, "filhote": pokemon(o.filhote),
                          "choca_em": o.choca_em} for o in t.ovos]}

    jogador = treinador(m.jogador)
    atores = []
    for a in m.atores.values():
        dados = {f.name: getattr(a, f.name) for f in fields(Ator)
                 if f.name not in {"treinador", "pokemon", "escondido_para"}}
        dados.update(treinador=treinador(a.treinador), pokemon=pokemon(a.pokemon),
                     escondido_para=sorted(a.escondido_para))
        atores.append(dados)
    itens = [{"codigo": i.codigo, "tipo": i.tipo, "posicao": i.posicao,
              "filhote": pokemon(i.filhote), "recolhido": i.recolhido} for i in m.itens.values()]
    return {"formato": "rumo-liga-pokemon", "versao": 1, "regiao": m.regiao.dados_originais,
            "semente": m.semente, "rng": m.rng.getstate(), "agora": m.agora,
            "sequencia": m.sequencia, "contador_pokemon": m.contador_pokemon,
            "distancia_percorrida": m.distancia_percorrida, "eventos": m.fila_eventos,
            "historico": list(m.historico), "inscrito": jogo.inscrito,
            "pokemons": pokemons, "jogador": jogador, "atores": atores, "itens": itens}


def salvar(jogo, caminho):
    escrever_json(caminho, estado(jogo))


def _tuplas(valor):
    return tuple(_tuplas(v) for v in valor) if isinstance(valor, list) else valor


def restaurar(dados):
    try:
        if dados["formato"] != "rumo-liga-pokemon" or dados["versao"] != 1:
            raise ErroFormato("Formato ou versão de partida desconhecido.")
        regiao = validar_regiao(dados["regiao"])
        agora = inteiro(dados["agora"], "agora")
        pokemons = {}
        for codigo, registro in dados["pokemons"].items():
            valores = dict(registro)
            if codigo != valores["codigo"]:
                raise ErroFormato("Identificador de Pokémon inconsistente.")
            valores["especie"] = regiao.catalogo[valores["especie"]]
            p = Pokemon(**valores)
            inteiro(p.xp, "xp")
            inteiro(p.fase, "fase", 0, len(p.especie.fases)-1)
            if p.fase != min(p.xp // 1000, len(p.especie.fases)-1):
                raise ErroFormato("Fase incompatível com a experiência.")
            for campo in ("ap_inicial", "dp_inicial", "hp", "bonus_evolucao_ap", "bonus_evolucao_dp"):
                valor = getattr(p, campo)
                if type(valor) not in (float, int) or not isfinite(valor) or valor < 0:
                    raise ErroFormato("Atributo numérico inválido de Pokémon.")
            if not 1 <= p.hp <= 100:
                raise ErroFormato("HP fora de 1..100.")
            inteiro(p.bonus_batalhas, "bônus de batalha")
            inteiro(p.resto_distancia, "resto de distância", 0, 99)
            inteiro(p.resto_tempo_hp, "resto de tempo de HP", 0, 9)
            if p.inconsciente_ate is not None:
                inteiro(p.inconsciente_ate, "fim do repouso")
            pokemons[codigo] = p

        def local(codigo, permitir_transito=False):
            if permitir_transito and codigo is None:
                return None
            if codigo not in regiao.grafo.adj:
                raise ErroFormato("Posição desconhecida na partida.")
            return codigo

        def treinador(t, jogador=False):
            if t is None:
                return None
            r = Treinador(texto(t["codigo"], "treinador.id"), texto(t["nome"], "nome"),
                          local(t["posicao"], not jogador),
                          [pokemons[p] for p in t["equipe"]], inteiro(t["xp"], "xp do treinador"),
                          set(t["insignias"]),
                          [Ovo(texto(o["codigo"], "ovo.id"), pokemons[o["filhote"]],
                               inteiro(o["choca_em"], "eclosão", agora+1)) for o in t["ovos"]],
                          [pokemons[p] for p in t["deposito"]],
                          pokemons[t["pendente"]] if t["pendente"] else None,
                          t["incubadora"], inteiro(t["pokebolas"], "pokébolas", 7, 7))
            if type(r.incubadora) is not bool:
                raise ErroFormato("Incubadora inválida.")
            if not r.insignias <= {g.insignia for g in regiao.ginasios}:
                raise ErroFormato("Insígnia inexistente na região.")
            r.conferir_limites()
            return r

        m = Mundo.__new__(Mundo)
        m.regiao, m.agora, m.semente = regiao, agora, dados["semente"]
        m.rng = Random()
        m.rng.setstate(_tuplas(dados["rng"]))
        m.sequencia = inteiro(dados["sequencia"], "sequência")
        m.contador_pokemon = inteiro(dados["contador_pokemon"], "contador", len(pokemons))
        m.distancia_percorrida = inteiro(dados["distancia_percorrida"], "distância")
        m.jogador = treinador(dados["jogador"], jogador=True)
        m.ginasios = {g.codigo: g for g in regiao.ginasios}
        m.cache_caminhos = {}
        m.tipos = TabelaTipos(regiao.vantagens, regiao.regras["vantagens_tipos"])
        m.historico = deque(dados["historico"], maxlen=2000)
        m.atores, m.itens = {}, {}
        for registro in dados["atores"]:
            v = dict(registro)
            v["treinador"] = treinador(v["treinador"])
            v["pokemon"] = pokemons[v["pokemon"]] if v["pokemon"] else None
            v["escondido_para"] = set(v["escondido_para"])
            v["movimento"] = tuple(v["movimento"]) if v["movimento"] else None
            a = Ator(**v)
            local(a.posicao, True)
            inteiro(a.versao, "versão do ator")
            if a.codigo in m.atores or a.tipo not in {"lider", "selvagem", "treinador", "rocket"}:
                raise ErroFormato("Ator repetido ou tipo desconhecido.")
            if (a.treinador is None) == (a.pokemon is None):
                raise ErroFormato("Ator deve representar um treinador ou um selvagem.")
            if a.treinador and a.treinador.posicao != a.posicao:
                raise ErroFormato("Posição inconsistente do treinador.")
            if a.ginasio is not None and a.ginasio not in m.ginasios:
                raise ErroFormato("Líder de ginásio desconhecido.")
            if a.suspenso:
                raise ErroFormato("Não é permitido salvar durante um turno de batalha.")
            if a.movimento:
                origem, destino, partida, chegada = a.movimento
                if a.posicao is not None or chegada <= agora or chegada-partida != regiao.grafo.peso(origem, destino):
                    raise ErroFormato("Movimento inválido no arquivo salvo.")
            elif a.ativo and a.posicao is None and a.invisivel_ate is None:
                raise ErroFormato("Ator sem posição, trânsito ou invisibilidade.")
            m.atores[a.codigo] = a
        for registro in dados["itens"]:
            v = dict(registro)
            v["filhote"] = pokemons[v["filhote"]] if v["filhote"] else None
            i = Item(**v)
            local(i.posicao)
            if i.codigo in m.itens or i.tipo not in {"ovo", "erva"}:
                raise ErroFormato("Item repetido ou desconhecido.")
            if (i.tipo == "ovo") != (i.filhote is not None):
                raise ErroFormato("Item e filhote inconsistentes.")
            m.itens[i.codigo] = i
        # Referências históricas de selvagens capturados e itens recolhidos podem
        # apontar para a equipe; apenas proprietários atuais devem ser distintos.
        donos = list(m.jogador.equipe) + list(m.jogador.deposito)
        donos += [o.filhote for o in m.jogador.ovos]
        if m.jogador.pendente:
            donos.append(m.jogador.pendente)
        for a in m.atores.values():
            if a.ativo:
                donos.extend(a.equipe)
        donos.extend(i.filhote for i in m.itens.values() if not i.recolhido and i.filhote)
        if len({p.codigo for p in donos}) != len(donos):
            raise ErroFormato("Pokémon com dois proprietários na partida.")
        m.fila_eventos = []
        for evento in dados["eventos"]:
            instante, seq, codigo, versao, acao, destino = evento
            inteiro(instante, "instante de evento", agora)
            inteiro(seq, "sequência de evento", 1, m.sequencia)
            inteiro(versao, "versão de evento")
            if codigo not in m.atores or acao not in {"decidir", "chegar", "curar", "reaparecer"}:
                raise ErroFormato("Evento desconhecido.")
            if destino is not None:
                local(destino)
            m.fila_eventos.append(tuple(evento))
        heapify(m.fila_eventos)
        jogo = Jogo.__new__(Jogo)
        jogo.mundo = m
        if type(dados["inscrito"]) is not bool:
            raise ErroFormato("Estado de inscrição inválido.")
        jogo.inscrito = dados["inscrito"]
        if jogo.inscrito and (len(m.jogador.insignias) < 8 or agora > regiao.prazo or m.jogador.posicao != regiao.estadio):
            raise ErroFormato("Inscrição incompatível com a partida.")
        return jogo
    except ErroFormato:
        raise
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError, RecursionError) as exc:
        raise ErroFormato(f"Partida salva inválida: {exc}") from exc


def carregar(caminho):
    try:
        dados = json.loads(Path(caminho).read_text(encoding="utf-8"))
        return restaurar(dados)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ErroFormato(f"Não foi possível carregar a partida: {exc}") from exc
