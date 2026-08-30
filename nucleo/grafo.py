"""Grafo não direcionado ponderado com listas de adjacência.

As arestas originais são guardadas uma vez; a adjacência guarda os dois sentidos.
Paralelas são permitidas e preservadas. Os tempos devem ser inteiros positivos.
"""

from dataclasses import dataclass

from nucleo.erros import ErroFormato


@dataclass(frozen=True)
class Vertice:
    codigo: str
    nome: str
    tipo: str = "comum"


class Grafo:
    def __init__(self, vertices, arestas):
        self.vertices = {}
        for vertice in vertices:
            if vertice.codigo in self.vertices:
                raise ErroFormato(f"Vértice repetido: {vertice.codigo}.")
            self.vertices[vertice.codigo] = vertice
        if not self.vertices:
            raise ErroFormato("O grafo deve possuir vértices.")
        self.adj = {v: [] for v in self.vertices}
        self.arestas = []
        for u, v, peso in arestas:
            if u not in self.adj or v not in self.adj:
                raise ErroFormato(f"Aresta com extremidade desconhecida: {u}, {v}.")
            if type(peso) is not int or peso <= 0:
                raise ErroFormato("Pesos devem ser inteiros positivos.")
            self.adj[u].append((v, peso))
            self.adj[v].append((u, peso))
            self.arestas.append((u, v, peso))

    @property
    def ordem(self):
        return len(self.vertices)

    @property
    def tamanho(self):
        return len(self.arestas)

    @property
    def soma_pesos(self):
        return sum(peso for _, _, peso in self.arestas)

    def peso(self, origem, destino):
        """Menor tempo entre paralelas. Não permite saltar vértices."""
        if origem not in self.adj:
            raise ErroFormato(f"Vértice desconhecido: {origem}.")
        pesos = [p for v, p in self.adj[origem] if v == destino]
        if not pesos:
            raise ErroFormato(f"Não existe aresta entre {origem} e {destino}.")
        return min(pesos)

    def locais(self, tipo):
        return [v.codigo for v in self.vertices.values() if v.tipo == tipo]
