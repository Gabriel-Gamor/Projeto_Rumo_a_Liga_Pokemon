"""BFS, Dijkstra e reconstrução implementados diretamente.

collections.deque e heapq fornecem apenas fila e heap; não resolvem o grafo.
"""

from dataclasses import dataclass
from collections import deque
from heapq import heappop, heappush
from math import inf, log2

from nucleo.erros import ErroFormato, ErroProjeto


def bfs(grafo, origem):
    """Distâncias em número de arestas, não em tempo: O(n+m)."""
    if origem not in grafo.adj:
        raise ErroFormato(f"Origem desconhecida: {origem}.")
    distancia = {v: inf for v in grafo.adj}
    pai = {v: None for v in grafo.adj}
    distancia[origem] = 0
    fila = deque([origem])
    while fila:
        u = fila.popleft()
        for v, _ in grafo.adj[u]:
            if distancia[v] == inf:
                distancia[v] = distancia[u] + 1
                pai[v] = u
                fila.append(v)
    return distancia, pai


def dijkstra(grafo, origem, metodo="auto"):
    """Caminhos de menor tempo; escolhe heap ou varredura conforme a densidade.

    Heap com entradas obsoletas: O(n+m+(m+1) log(m+2)).
    Varredura: O(n²+m). O grafo já valida pesos positivos na construção.
    """
    if origem not in grafo.adj:
        raise ErroFormato(f"Origem desconhecida: {origem}.")
    if metodo not in {"auto", "heap", "quadratico"}:
        raise ErroFormato("Método de Dijkstra inválido.")
    n, m = grafo.ordem, grafo.tamanho
    if metodo == "auto":
        metodo = "quadratico" if n*n < (m+1)*log2(m+2) else "heap"
    d = {v: inf for v in grafo.adj}
    pai = {v: None for v in grafo.adj}
    d[origem] = 0
    if metodo == "heap":
        heap = [(0, origem)]
        while heap:
            du, u = heappop(heap)
            if du != d[u]:
                continue
            for v, peso in grafo.adj[u]:
                if du + peso < d[v]:
                    d[v], pai[v] = du + peso, u
                    heappush(heap, (d[v], v))
    else:
        fixos = set()
        for _ in grafo.adj:
            u = None
            for v in grafo.adj:
                if v not in fixos and (u is None or d[v] < d[u]):
                    u = v
            if u is None or d[u] == inf:
                break
            fixos.add(u)
            for v, peso in grafo.adj[u]:
                if v not in fixos and d[u] + peso < d[v]:
                    d[v], pai[v] = d[u] + peso, u
    return d, pai


def reconstruir(pai, origem, destino):
    if origem not in pai or destino not in pai:
        raise ErroFormato("Extremidade desconhecida na reconstrução.")
    caminho, vistos = [], set()
    v = destino
    while v is not None:
        if v in vistos:
            raise ErroFormato("Vetor de pais contém um ciclo.")
        vistos.add(v)
        caminho.append(v)
        if v == origem:
            caminho.reverse()
            return caminho
        v = pai[v]
    return []


def menor_rota(grafo, origem, destino):
    d, pai = dijkstra(grafo, origem)
    if destino not in d:
        raise ErroFormato(f"Destino desconhecido: {destino}.")
    return d[destino], reconstruir(pai, origem, destino)


@dataclass(frozen=True)
class Plano:
    ginasios: tuple
    vertices: tuple
    tempo_minimo: int
    estados: int
    metodo: str


def planejar_insignias(grafo, origem, estadio, ginasios, faltam=8):
    """Held-Karp truncado em 'faltam' visitas; cada ginásio tem insígnia única.

    Estado (máscara, último) guarda o melhor custo de uma sequência de visitas.
    O último ginásio é conectado ao estádio apenas na seleção da resposta.
    """
    if type(faltam) is not int or faltam < 0:
        raise ErroProjeto("A quantidade de insígnias não pode ser negativa.")
    if len({g.codigo for g in ginasios}) != len(ginasios):
        raise ErroProjeto("A lista de ginásios contém duplicatas.")
    if faltam > len(ginasios):
        raise ErroProjeto("Não há ginásios suficientes para as insígnias restantes.")
    if estadio not in grafo.adj:
        raise ErroProjeto("Estádio desconhecido.")
    if faltam == 0:
        d, pai = dijkstra(grafo, origem)
        if d[estadio] == inf:
            raise ErroProjeto("Estádio inalcançável.")
        return Plano((), tuple(reconstruir(pai, origem, estadio)),
                     int(d[estadio]), 0, "Dijkstra")
    if len(ginasios) > 16:
        raise ErroProjeto("O planejamento exato aceita até 16 ginásios candidatos; "
                          "use rotas individuais para mapas maiores.")
    fontes = {origem, *(g.vertice for g in ginasios)}
    buscas = {v: dijkstra(grafo, v) for v in fontes}
    dp, anterior = {}, {}
    for j, g in enumerate(ginasios):
        valor = buscas[origem][0][g.vertice]
        if valor != inf:
            dp[(1 << j, j)] = valor + 1
            anterior[(1 << j, j)] = None
    camada = list(dp)
    for _ in range(1, faltam):
        proxima = set()
        for mascara, i in camada:
            for j, g in enumerate(ginasios):
                if mascara & (1 << j):
                    continue
                custo = dp[(mascara, i)] + buscas[ginasios[i].vertice][0][g.vertice] + 1
                chave = (mascara | (1 << j), j)
                if custo < dp.get(chave, inf):
                    dp[chave] = custo
                    anterior[chave] = (mascara, i)
                    proxima.add(chave)
        camada = sorted(proxima)
    melhor, estado = inf, None
    for chave in camada:
        valor = dp[chave] + buscas[ginasios[chave[1]].vertice][0][estadio]
        if valor < melhor:
            melhor, estado = valor, chave
    if estado is None:
        raise ErroProjeto("Não existe rota ligando os ginásios ao estádio.")
    indices = []
    while estado is not None:
        indices.append(estado[1])
        estado = anterior[estado]
    indices.reverse()
    vertices = [origem]
    for destino in [ginasios[i].vertice for i in indices] + [estadio]:
        partida = vertices[-1]
        vertices.extend(reconstruir(buscas[partida][1], partida, destino)[1:])
    return Plano(tuple(ginasios[i].codigo for i in indices), tuple(vertices),
                 int(melhor), len(dp), "Dijkstra + programação dinâmica de subconjuntos")
