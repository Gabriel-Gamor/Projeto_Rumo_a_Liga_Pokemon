"""Leitura e validação do arquivo texto JSON da região."""

from dataclasses import dataclass
import json
from math import inf
from pathlib import Path

from nucleo.grafo import Grafo, Vertice
from nucleo.algoritmos import bfs
from nucleo.tipos import Ataque, Especie, Fase, TIPOS
from nucleo.treinador import Ginasio
from nucleo.erros import ErroFormato


@dataclass
class Regiao:
    nome: str
    grafo: Grafo
    prazo: int
    laboratorio: str
    estadio: str
    catalogo: dict
    iniciais: tuple
    ginasios: tuple
    quantidades: dict
    regras: dict
    vantagens: dict
    dados_originais: dict


def inteiro(valor, campo, minimo=0, maximo=None):
    if type(valor) is not int or valor < minimo or (maximo is not None and valor > maximo):
        raise ErroFormato(f"{campo}: inteiro esperado no intervalo permitido.")
    return valor


def texto(valor, campo):
    if not isinstance(valor, str) or not valor.strip():
        raise ErroFormato(f"{campo}: texto não vazio esperado.")
    return valor


def carregar_regiao(caminho):
    try:
        dados = json.loads(Path(caminho).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ErroFormato(f"Não foi possível ler a região: {exc}") from exc
    return validar_regiao(dados)


def validar_regiao(dados):
    try:
        if not isinstance(dados, dict):
            raise ErroFormato("A raiz do JSON deve ser um objeto.")
        nome = texto(dados["nome"], "nome")
        locais = {"comum", "laboratorio", "pmc", "estadio", "ginasio"}
        vertices = []
        for v in dados["vertices"]:
            tipo = v.get("tipo", "comum")
            if tipo not in locais:
                raise ErroFormato(f"Tipo de local desconhecido: {tipo}.")
            vertices.append(Vertice(texto(v["id"], "vértice.id"),
                                   texto(v["nome"], "vértice.nome"), tipo))
        grafo = Grafo(vertices, dados["arestas"])
        if "ordem_mapa" in dados:
            ordem = dados["ordem_mapa"]
            if not isinstance(ordem, list) or len(ordem) != grafo.ordem or set(ordem) != set(grafo.adj):
                raise ErroFormato("ordem_mapa deve listar todos os IDs de vértices exatamente uma vez.")
        desenho = dados.get("desenho", {})
        if not isinstance(desenho, dict):
            raise ErroFormato("desenho deve ser um objeto com posições opcionais do mapa.")
        posicoes = desenho.get("posicoes", {})
        if posicoes and set(posicoes) != set(grafo.adj):
            raise ErroFormato("As posições visuais devem incluir todos os vértices.")
        def ponto_valido(p):
            return isinstance(p, list) and len(p) == 2 and all(
                type(x) in (int, float) and 0 <= x <= 2000 for x in p)
        if any(not ponto_valido(p) for p in posicoes.values()):
            raise ErroFormato("Posição do mapa inválida: use duas coordenadas de 0 a 2000.")
        desvios = desenho.get("desvios", {})
        chaves = {f"{u}|{v}" for u,v,_ in grafo.arestas} | {f"{v}|{u}" for u,v,_ in grafo.arestas}
        if not isinstance(desvios, dict) or any(k not in chaves or not isinstance(ps, list)
                or any(not ponto_valido(p) for p in ps) for k,ps in desvios.items()):
            raise ErroFormato("Desvio visual deve referenciar uma estrada e coordenadas válidas.")
        if len(grafo.locais("laboratorio")) != 1 or len(grafo.locais("estadio")) != 1:
            raise ErroFormato("Declare exatamente um laboratório e um estádio.")
        if not grafo.locais("pmc"):
            raise ErroFormato("A região precisa de ao menos um PMC.")
        laboratorio, estadio = grafo.locais("laboratorio")[0], grafo.locais("estadio")[0]
        d, _ = bfs(grafo, laboratorio)
        if any(dist == inf for dist in d.values()):
            raise ErroFormato("A região deve ser conexa; há vértices inacessíveis do laboratório.")
        prazo = inteiro(dados["prazo"], "prazo", 1)
        if not 10 * grafo.soma_pesos <= prazo <= 15 * grafo.soma_pesos:
            raise ErroFormato("Prazo deve ficar entre 10 e 15 vezes a soma dos pesos originais.")
        catalogo, nomes_fases = {}, set()
        for especie in dados["especies"]:
            codigo = texto(especie["id"], "espécie.id")
            if codigo in catalogo or not 1 <= len(especie["fases"]) <= 3:
                raise ErroFormato("Espécie repetida ou quantidade de fases fora de 1..3.")
            fases = []
            for fase in especie["fases"]:
                nome_fase = texto(fase["nome"], "fase.nome")
                tipos = tuple(fase["tipos"])
                if nome_fase in nomes_fases or not 1 <= len(tipos) <= 2 or len(set(tipos)) != len(tipos):
                    raise ErroFormato("Nomes de formas devem ser distintos; use um ou dois tipos distintos.")
                if any(t not in TIPOS for t in tipos):
                    raise ErroFormato("Tipo de Pokémon desconhecido.")
                nomes_fases.add(nome_fase)
                ataques = []
                for ataque in fase["ataques"]:
                    if ataque["tipo"] not in TIPOS:
                        raise ErroFormato("Tipo de ataque desconhecido.")
                    ataques.append(Ataque(texto(ataque["nome"], "ataque.nome"), ataque["tipo"]))
                if not ataques:
                    raise ErroFormato("Cada fase precisa de pelo menos um ataque.")
                fases.append(Fase(nome_fase, tipos, tuple(ataques)))
            catalogo[codigo] = Especie(codigo, tuple(fases))
        iniciais = tuple(dados["iniciais"])
        if len(iniciais) != 3 or len(set(iniciais)) != 3 or any(i not in catalogo for i in iniciais):
            raise ErroFormato("Declare três espécies iniciais distintas existentes.")
        # Um representante para cada tipo; permite tipos secundários.
        tipos_iniciais = [set(catalogo[i].fases[0].tipos) for i in iniciais]
        atribuicoes = ((0,1,2), (0,2,1), (1,0,2), (1,2,0), (2,0,1), (2,1,0))
        if not any("agua" in tipos_iniciais[a] and "fogo" in tipos_iniciais[f]
                   and "planta" in tipos_iniciais[p] for a,f,p in atribuicoes):
            raise ErroFormato("O trio inicial deve representar água, fogo e planta.")
        ginasios = []
        for g in dados["ginasios"]:
            vertice = g["vertice"]
            if vertice not in grafo.adj or grafo.vertices[vertice].tipo != "ginasio":
                raise ErroFormato("Ginásio deve apontar para um vértice do tipo ginasio.")
            movel = g.get("movel", False)
            if type(movel) is not bool:
                raise ErroFormato("movel deve ser booleano.")
            periodo = inteiro(g.get("periodo", 300), "período", 2)
            permanencia = inteiro(g.get("permanencia", 100), "permanência", 1, periodo-1)
            ginasios.append(Ginasio(texto(g["id"], "ginásio.id"), vertice,
                                   texto(g["insignia"], "insígnia"),
                                   texto(g["lider"], "líder"), movel, periodo, permanencia))
        for campo in ("codigo", "vertice", "insignia"):
            if len({getattr(g, campo) for g in ginasios}) != len(ginasios):
                raise ErroFormato(f"Ginásios têm {campo} repetido.")
        if len(ginasios) < 8:
            raise ErroFormato("São necessários ao menos oito ginásios e insígnias distintos.")
        quantidades = {}
        for chave in ("selvagens", "treinadores", "ovos", "ervas", "rockets"):
            quantidades[chave] = inteiro(dados["quantidades"].get(chave, 0), chave, 0, 500)
        regras = dict(dados.get("regras", {}))
        for chave, padrao, minimo, maximo in [
            ("xp_selvagem_max", 500, 0, 10000), ("xp_lider_max", 150, 0, 10000),
            ("xp_treinador_max", 30, 0, 10000), ("hp_regiao_min", 20, 1, 100),
            ("hp_regiao_max", 100, 1, 100), ("pausa_npc_min", 5, 1, 1000),
            ("pausa_npc_max", 20, 1, 1000), ("limite_turnos", 2000, 1, 10000),
        ]:
            regras[chave] = inteiro(regras.get(chave, padrao), chave, minimo, maximo)
        if regras["hp_regiao_min"] > regras["hp_regiao_max"] or regras["pausa_npc_min"] > regras["pausa_npc_max"]:
            raise ErroFormato("Intervalo aleatório invertido.")
        for chave, padrao in (("ap_inicial", [35, 45]), ("dp_inicial", [15, 25]),
                              ("ap_regiao", [20, 35]), ("dp_regiao", [8, 20])):
            faixa = regras.get(chave, padrao)
            if not isinstance(faixa, list) or len(faixa) != 2:
                raise ErroFormato(f"{chave} deve ter dois limites.")
            regras[chave] = [inteiro(v, chave, 0, 1000) for v in faixa]
            if faixa[0] > faixa[1]:
                raise ErroFormato(f"{chave}: intervalo invertido.")
        aceitar = regras.get("chance_aceitar", 0.85)
        if type(aceitar) not in (int, float) or not 0 <= aceitar <= 1:
            raise ErroFormato("chance_aceitar deve ficar em [0,1].")
        regras["chance_aceitar"] = aceitar
        habilitar = regras.get("vantagens_tipos", False)
        if type(habilitar) is not bool:
            raise ErroFormato("vantagens_tipos deve ser booleano.")
        regras["vantagens_tipos"] = habilitar
        vantagens = dados.get("vantagens", {})
        if habilitar and set(vantagens) != set(TIPOS):
            raise ErroFormato("Com vantagens habilitadas, declare as 18 linhas da tabela.")
        for atacante, linha in vantagens.items():
            if atacante not in TIPOS or not isinstance(linha, dict):
                raise ErroFormato("Linha de vantagens inválida.")
            if any(t not in TIPOS or type(m) not in (int, float) or m not in (0, 0.5, 1, 2)
                   for t, m in linha.items()):
                raise ErroFormato("Vantagens: use tipos válidos e fatores 0, 0.5, 1 ou 2.")
        return Regiao(nome, grafo, prazo, laboratorio, estadio, catalogo, iniciais,
                      tuple(ginasios), quantidades, regras, vantagens, dados)
    except ErroFormato:
        raise
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise ErroFormato(f"Estrutura JSON inválida ou campo obrigatório ausente: {exc}") from exc
